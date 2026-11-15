import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The Flask app serves the build under /static/<asset-version>/app/ (see
// web/app/assets.py), so every URL inside the bundle has to be relative.
// File names carry no hash: the asset version already changes with the files.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  build: {
    outDir: fileURLToPath(new URL("../web/app/static/app", import.meta.url)),
    emptyOutDir: true,
    cssCodeSplit: false,
    sourcemap: false,
    target: "es2022",
    // Browsers that read oklch() themselves, the same floor Tailwind 4 has. Converting the
    // colours for older ones rounds differently on Windows and Linux, and the committed
    // build must come out byte for byte the same in CI.
    cssTarget: ["chrome111", "safari16.4", "firefox128"],
    rollupOptions: {
      input: fileURLToPath(new URL("./src/main.tsx", import.meta.url)),
      output: {
        entryFileNames: "assets/app.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: (asset) =>
          asset.names.some((name) => name.endsWith(".css")) ? "assets/app.css" : "assets/[name][extname]",
      },
    },
  },
});
