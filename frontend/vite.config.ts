import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// React aplikacija je cijeli interfejs (/); Django služi samo JSON API (/api/).
// U razvoju Vite prosljeđuje /api na Django (manage.py runserver), pa sve radi na istom
// originu kao u produkciji - kolačići i CSRF bez CORS-a.
const DJANGO = 'http://127.0.0.1:8000';

export default defineConfig({
  base: '/',
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: DJANGO, changeOrigin: false } },
  },
  build: {
    sourcemap: false,          // bez izvornog koda u produkciji
    assetsInlineLimit: 0,      // bez data: URI-ja; sve kao zasebne datoteke (CSP)
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
