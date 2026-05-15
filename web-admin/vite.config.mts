import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue()],
  base: process.env.VITE_BASE || "/",
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
      "@shared": resolve(__dirname, "../shared"),
    },
  },
  server: {
    port: 5174,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("@element-plus/icons-vue")) return "el-icons";
          if (
            id.includes("lodash-es") ||
            id.includes("lodash-unified") ||
            id.includes("/lodash/")
          ) return "el-lodash";
          if (id.includes("async-validator")) return "el-async-validator";
          if (id.includes("@popperjs") || id.includes("@sxzz/popperjs")) return "el-popper";
          if (id.includes("@ctrl/tinycolor")) return "el-tinycolor";
          if (id.includes("element-plus")) return "element-plus";
          if (id.includes("vue") || id.includes("pinia")) return "vue-vendor";
          if (id.includes("axios")) return "utility-vendor";
        },
      },
    },
  },
});
