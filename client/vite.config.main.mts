import { defineConfig } from "vite";
import { resolve } from "path";
import { builtinModules } from "module";

export default defineConfig({
  plugins: [],
  build: {
    outDir: "dist/main",
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "src/main/index.ts"),
      formats: ["cjs"],
      fileName: () => "index.js",
    },
    rollupOptions: {
      external: [
        "electron",
        "electron-updater",
        "playwright-core",
        "playwright",
        ...builtinModules,
        ...builtinModules.map((m) => `node:${m}`),
      ],
    },
    minify: false,
    sourcemap: true,
    target: "node18",
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
      "@shared": resolve(__dirname, "../shared"),
    },
  },
});
