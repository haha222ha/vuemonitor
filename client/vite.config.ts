import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
      "@renderer": resolve(__dirname, "src/renderer"),
      "@shared": resolve(__dirname, "../shared"),
    },
  },
  server: {
    port: 5173,
  },
  build: {
    outDir: "dist/renderer",
    emptyOutDir: true,
  },
});
