/// <reference types="vitest/config" />
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 5173,
    // Mismo origen en desarrollo: la cookie del refresh token (SameSite=Strict) funciona sin CORS.
    proxy: { '/api': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8001', changeOrigin: true } },
  },
  build: {
    rollupOptions: {
      output: {
        // Librerías en bloques separados: se cachean entre despliegues y el código propio pesa poco.
        manualChunks: {
          react: ['react', 'react-dom', 'react-router'],
          ui: ['radix-ui', 'motion', 'sonner', 'lucide-react'],
          data: ['@tanstack/react-query', 'openapi-fetch', 'zustand', 'react-hook-form', 'zod', '@hookform/resolvers'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
})
