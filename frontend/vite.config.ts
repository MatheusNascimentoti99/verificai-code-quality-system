import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          state: ['zustand'],
          query: ['@tanstack/react-query'],
          utils: ['clsx', 'class-variance-authority', 'date-fns'],
          forms: ['react-hook-form', '@hookform/resolvers', 'zod'],
        },
      },
    },
  },
  server: {
    port: 3011,
    proxy: {
      '/api/v1': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: process.env.VITE_WS_PROXY_TARGET || 'ws://localhost:8000',
        ws: true,
        secure: false,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(process.env.npm_package_version || '1.0.0'),
  },
}));