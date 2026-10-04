import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv, type Plugin} from 'vite';

// Link-preview crawlers (LinkedIn, Slack, WhatsApp) ignore relative og:image
// URLs, so index.html writes %FRONTEND_URL% and the public origin from .env is
// substituted at build and dev time.
function frontendUrl(origin: string): Plugin {
  return {
    name: 'frontend-url',
    transformIndexHtml: (html) => html.replaceAll('%FRONTEND_URL%', origin),
  };
}

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, process.cwd(), '');
  const origin = (env.FRONTEND_URL || 'http://localhost:3000').replace(/\/+$/, '');
  return {
    plugins: [react(), tailwindcss(), frontendUrl(origin)],
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
                '**/design/**',
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
