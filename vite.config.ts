import { resolve } from "node:path";
/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  root: "frontend",
  plugins: [react()],
  build: {
    outDir: "../www",
    emptyOutDir: false,
    rollupOptions: {
      input: {
        index: resolve(__dirname, "frontend/index.html"),
        lendingbot: resolve(__dirname, "frontend/lendingbot.html"),
        charts: resolve(__dirname, "frontend/charts.html")
      },
      output: {
        entryFileNames: "assets/[name].js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
        manualChunks: {
          antd: ["antd", "@ant-design/icons"],
          charts: ["echarts", "echarts-for-react"]
        }
      }
    }
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/stream-logs": "http://127.0.0.1:8000",
      "/images": "http://127.0.0.1:8000"
    }
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "../vitest.setup.ts"
  }
});
