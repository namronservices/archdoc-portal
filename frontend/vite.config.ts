import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    // Dev-only: accept any Host header (Docker service name, LAN IP, ...).
    allowedHosts: true,
  },
});
