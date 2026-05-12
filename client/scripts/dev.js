const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const electron = require("electron");

const ROOT = path.resolve(__dirname, "..");
const RENDERER_URL = "http://127.0.0.1:5173";

function waitForVite(maxRetries = 30) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const check = () => {
      attempts++;
      const req = http.get(RENDERER_URL, (res) => {
        if (res.statusCode === 200 || res.statusCode === 304) {
          console.log("[dev] Vite dev server is ready!");
          resolve();
        } else {
          retry();
        }
      });
      req.on("error", () => retry());
      req.setTimeout(2000, () => { req.destroy(); retry(); });

      function retry() {
        if (attempts >= maxRetries) {
          reject(new Error("Vite dev server not ready after max retries"));
        } else {
          setTimeout(check, 1000);
        }
      }
    };
    check();
  });
}

async function main() {
  console.log("[dev] Starting Vite renderer dev server...");
  const viteProcess = spawn("npx", ["vite", "--port", "5173", "--host", "127.0.0.1"], {
    cwd: ROOT,
    stdio: "pipe",
    shell: true,
  });

  viteProcess.stdout.on("data", (data) => {
    process.stdout.write(data.toString());
  });
  viteProcess.stderr.on("data", (data) => {
    process.stderr.write(data.toString());
  });

  console.log("[dev] Waiting for Vite dev server...");
  await waitForVite();

  console.log("[dev] Building main process...");
  const buildMain = spawn("npx", ["vite", "build", "--config", "vite.config.main.mts"], {
    cwd: ROOT,
    stdio: "pipe",
    shell: true,
  });

  await new Promise((resolve, reject) => {
    buildMain.stdout.on("data", (data) => {
      const msg = data.toString();
      process.stdout.write(msg);
    });
    buildMain.stderr.on("data", (data) => {
      process.stderr.write(data.toString());
    });
    buildMain.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`Build failed with code ${code}`));
    });
  });

  console.log("[dev] Building preload...");
  const buildPreload = spawn("npx", ["vite", "build", "--config", "vite.config.preload.mts"], {
    cwd: ROOT,
    stdio: "pipe",
    shell: true,
  });

  await new Promise((resolve, reject) => {
    buildPreload.stdout.on("data", (data) => {
      const msg = data.toString();
      process.stdout.write(msg);
    });
    buildPreload.stderr.on("data", (data) => {
      process.stderr.write(data.toString());
    });
    buildPreload.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`Preload build failed with code ${code}`));
    });
  });

  console.log("[dev] Starting Electron...");
  const mainPath = path.join(ROOT, "dist", "main", "index.js");
  const electronProcess = spawn(electron, [mainPath, "--enable-logging"], {
    cwd: ROOT,
    stdio: "inherit",
    env: { ...process.env, NODE_ENV: "development" },
  });

  electronProcess.on("close", (code) => {
    console.log(`[dev] Electron exited with code ${code}`);
    viteProcess.kill();
    process.exit(code || 0);
  });

  process.on("SIGINT", () => {
    viteProcess.kill();
    electronProcess.kill();
    process.exit(0);
  });
}

main().catch((err) => {
  console.error("[dev] Error:", err.message);
  process.exit(1);
});
