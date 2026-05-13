const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

exports.default = async function (context) {
  console.log("[before-build] 开始构建前检查...");

  const appDir = path.join(__dirname, "..");

  const distPath = path.join(appDir, "dist");
  if (!fs.existsSync(distPath)) {
    console.error("[before-build] dist 目录不存在，请先运行 npm run build");
    process.exit(1);
  }

  const packageJson = JSON.parse(fs.readFileSync(path.join(appDir, "package.json"), "utf-8"));
  console.log(`[before-build] 版本: ${packageJson.version}`);

  console.log("[before-build] 构建前检查完成");
};