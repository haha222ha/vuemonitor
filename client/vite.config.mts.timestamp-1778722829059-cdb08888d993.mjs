// vite.config.mts
import { defineConfig } from "file:///D:/vuemonitor/client/node_modules/vite/dist/node/index.js";
import vue from "file:///D:/vuemonitor/client/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import vueJsx from "file:///D:/vuemonitor/client/node_modules/@vitejs/plugin-vue-jsx/dist/index.mjs";
import { resolve } from "path";
var __vite_injected_original_dirname = "D:\\vuemonitor\\client";
var vite_config_default = defineConfig({
  base: "./",
  plugins: [vue(), vueJsx()],
  resolve: {
    alias: {
      "@": resolve(__vite_injected_original_dirname, "src"),
      "@renderer": resolve(__vite_injected_original_dirname, "src/renderer"),
      "@shared": resolve(__vite_injected_original_dirname, "../shared")
    }
  },
  server: {
    port: 5173
  },
  build: {
    outDir: "dist/renderer",
    emptyOutDir: true
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcubXRzIl0sCiAgInNvdXJjZXNDb250ZW50IjogWyJjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZGlybmFtZSA9IFwiRDpcXFxcdnVlbW9uaXRvclxcXFxjbGllbnRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkQ6XFxcXHZ1ZW1vbml0b3JcXFxcY2xpZW50XFxcXHZpdGUuY29uZmlnLm10c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovdnVlbW9uaXRvci9jbGllbnQvdml0ZS5jb25maWcubXRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSBcInZpdGVcIjtcbmltcG9ydCB2dWUgZnJvbSBcIkB2aXRlanMvcGx1Z2luLXZ1ZVwiO1xuaW1wb3J0IHZ1ZUpzeCBmcm9tIFwiQHZpdGVqcy9wbHVnaW4tdnVlLWpzeFwiO1xuaW1wb3J0IHsgcmVzb2x2ZSB9IGZyb20gXCJwYXRoXCI7XG5cbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XG4gIGJhc2U6IFwiLi9cIixcbiAgcGx1Z2luczogW3Z1ZSgpLCB2dWVKc3goKV0sXG4gIHJlc29sdmU6IHtcbiAgICBhbGlhczoge1xuICAgICAgXCJAXCI6IHJlc29sdmUoX19kaXJuYW1lLCBcInNyY1wiKSxcbiAgICAgIFwiQHJlbmRlcmVyXCI6IHJlc29sdmUoX19kaXJuYW1lLCBcInNyYy9yZW5kZXJlclwiKSxcbiAgICAgIFwiQHNoYXJlZFwiOiByZXNvbHZlKF9fZGlybmFtZSwgXCIuLi9zaGFyZWRcIiksXG4gICAgfSxcbiAgfSxcbiAgc2VydmVyOiB7XG4gICAgcG9ydDogNTE3MyxcbiAgfSxcbiAgYnVpbGQ6IHtcbiAgICBvdXREaXI6IFwiZGlzdC9yZW5kZXJlclwiLFxuICAgIGVtcHR5T3V0RGlyOiB0cnVlLFxuICB9LFxufSk7XG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQXNQLFNBQVMsb0JBQW9CO0FBQ25SLE9BQU8sU0FBUztBQUNoQixPQUFPLFlBQVk7QUFDbkIsU0FBUyxlQUFlO0FBSHhCLElBQU0sbUNBQW1DO0FBS3pDLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLE1BQU07QUFBQSxFQUNOLFNBQVMsQ0FBQyxJQUFJLEdBQUcsT0FBTyxDQUFDO0FBQUEsRUFDekIsU0FBUztBQUFBLElBQ1AsT0FBTztBQUFBLE1BQ0wsS0FBSyxRQUFRLGtDQUFXLEtBQUs7QUFBQSxNQUM3QixhQUFhLFFBQVEsa0NBQVcsY0FBYztBQUFBLE1BQzlDLFdBQVcsUUFBUSxrQ0FBVyxXQUFXO0FBQUEsSUFDM0M7QUFBQSxFQUNGO0FBQUEsRUFDQSxRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsRUFDUjtBQUFBLEVBQ0EsT0FBTztBQUFBLElBQ0wsUUFBUTtBQUFBLElBQ1IsYUFBYTtBQUFBLEVBQ2Y7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
