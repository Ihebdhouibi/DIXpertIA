import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';
export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { '@': path.resolve(__dirname, '.') } },
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
      hmr: process.env.DISABLE_HMR !== 'true',
      watch:
        process.env.DISABLE_HMR === 'true'
          ? null
          : {
              // Non-source folders. Watching them is useless and the brand-asset
              // folder in particular throws EBUSY when another app holds a file open.
              ignored: [
                '**/DI Xpertia Logo Concepts/**',
                '**/.venv/**',
                '**/__pycache__/**',
                '**/alembic/**',
                '**/docs/**',
                '**/db.json',
              ],
            },
    },
  };
});