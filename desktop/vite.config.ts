import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `base: './'` works for Electron (relative paths).
// `base: '/'` works for Vercel (absolute paths for SPA routing).
// We auto-switch based on an env flag set by the build command.
const isElectronBuild = process.env.BUILD_TARGET === 'electron'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  base: isElectronBuild ? './' : '/',
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Keep chunk size warnings actionable but not noisy
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'motion-vendor': ['framer-motion', 'lenis', '@studio-freight/react-lenis'],
          'charts-vendor': ['recharts'],
          'three-vendor': ['three', '@react-three/fiber', '@react-three/drei'],
        },
      },
    },
  },
})