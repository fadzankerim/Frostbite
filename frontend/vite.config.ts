import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Za vrijeme migracije React aplikacija živi pod /novo/, a stare Django stranice ostaju na svojim
// adresama. Obje dijele istu sesiju (isti domen, isti kolačić).
const BASE = '/novo/';

// U razvoju Vite prosljeđuje API i stare stranice na Django (manage.py runserver), pa sve radi
// na istom originu kao u produkciji - kolačići i CSRF bez CORS-a.
const DJANGO = 'http://127.0.0.1:8000';
const djangoPaths = ['/api', '/static', '/nalog', '/ture', '/drustva', '/odabir', '/moje-prijave',
  '/moja-clanstva', '/vodic', '/upravljanje', '/sistem'];

export default defineConfig({
  base: BASE,
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(djangoPaths.map((p) => [p, { target: DJANGO, changeOrigin: false }])),
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
