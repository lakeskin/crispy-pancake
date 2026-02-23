import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Important for Capacitor mobile apps
  base: './',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Optimize for mobile
    minify: true,
    sourcemap: false
  }
})
