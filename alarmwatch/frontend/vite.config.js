import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: process.env.VITE_ALARM_BASE || '/',
  plugins: [react()],
  server: { proxy: {
    '/api': 'http://127.0.0.1:8001',
    '/ws': { target: 'ws://127.0.0.1:8001', ws: true },
    '/plant-api': { target: 'http://127.0.0.1:8000', rewrite: path => path.replace(/^\/plant-api/, '') }
  } }
});