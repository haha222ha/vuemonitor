import { defineConfig } from "vitest/config";
import { resolve } from "path";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["src/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["src/renderer/composables/**/*.ts"],
    },
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
      "@renderer": resolve(__dirname, "src/renderer"),
      "@shared": resolve(__dirname, "../shared"),
    },
  },
});
