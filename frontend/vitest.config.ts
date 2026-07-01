import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const currentDirectory = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  define: {
    // 测试环境不执行 Vite 生产构建，需要显式提供编译期版本常量。
    __APP_VERSION__: JSON.stringify("0.1.0-test"),
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": join(currentDirectory, "src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
