import express from 'express';
import path from 'path';
import { spawn } from 'child_process';
import { createServer as createViteServer } from 'vite';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const PORT = 3000;

// Spawn FastAPI server on port 8000
console.log('Starting FastAPI backend server on port 8000...');
const pythonProcess = spawn('python3', ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], {
  stdio: 'inherit'
});

pythonProcess.on('error', (err) => {
  console.error('Failed to start FastAPI server:', err);
});

// Ensure FastAPI dies when Node dies
process.on('exit', () => {
  pythonProcess.kill();
});
process.on('SIGINT', () => {
  pythonProcess.kill();
  process.exit();
});
process.on('SIGTERM', () => {
  pythonProcess.kill();
  process.exit();
});

// Proxy /api to FastAPI on port 8000
app.use('/api', createProxyMiddleware({
  target: 'http://127.0.0.1:8000',
  changeOrigin: true
}));

// Serve frontend with Vite in development, static files in production
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa'
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Node Gateway Server is running at http://localhost:${PORT}`);
    console.log('Proxying all /api/* requests to FastAPI backend on port 8000');
  });
}

startServer();
