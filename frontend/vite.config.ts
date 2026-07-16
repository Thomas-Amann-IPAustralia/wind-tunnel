import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// GitHub Pages project sites serve from /<repo>/ (CLAUDE.md §9), so `base` is
// path-aware and routing is hash-based. Keep this in sync with the repo name in
// src/config.ts — one owner per fact, mirrored by hand across the Python/TS split.
export default defineConfig({
  base: "/wind-tunnel/",
  plugins: [react()],
  test: {
    globals: true,
    environment: "node",
  },
});
