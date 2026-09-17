import { defineConfig } from 'vite';
export default defineConfig({ base: '/assets/workspace/', build: { outDir: '../web/workspace', emptyOutDir: true, sourcemap: false, chunkSizeWarningLimit: 750 } });
