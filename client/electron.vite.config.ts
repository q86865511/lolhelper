import { defineConfig } from "electron-vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  main: {
    build: {
      outDir: "dist/main",
      lib: { entry: resolve(__dirname, "src/main/index.ts") },
    },
  },
  preload: {
    build: {
      outDir: "dist/preload",
      rollupOptions: {
        input: {
          main: resolve(__dirname, "src/preload/main-preload.ts"),
          overlay: resolve(__dirname, "src/preload/overlay-preload.ts"),
        },
      },
    },
  },
  renderer: {
    root: ".",
    plugins: [react()],
    resolve: { alias: { "@": resolve(__dirname, "src") } },
    build: {
      outDir: "dist/renderer",
      rollupOptions: {
        input: {
          main: resolve(__dirname, "src/renderer/main.html"),
          overlay: resolve(__dirname, "src/overlay/overlay.html"),
        },
      },
    },
  },
});
