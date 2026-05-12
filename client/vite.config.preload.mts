import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [],
  build: {
    outDir: "dist/preload",
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "src/main/preload.ts"),
      formats: ["cjs"],
      fileName: () => "preload.js",
    },
    rollupOptions: {
      external: ["electron"],
    },
    minify: false,
  },
});
