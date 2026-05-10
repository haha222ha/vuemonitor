import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
      "@shared": resolve(__dirname, "../shared"),
    },
  },
  server: {
    port: 5175,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
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
          if (id.includes("echarts") || id.includes("zrender")) return "echarts-vendor";
          if (id.includes("vue") || id.includes("pinia") || id.includes("@vueuse")) return "vue-vendor";
          if (id.includes("axios") || id.includes("dayjs")) return "utility-vendor";
        },
      },
    },
  },
});
