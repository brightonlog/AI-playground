import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Same origin as the API in dev, so no CORS setup on the backend.
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
