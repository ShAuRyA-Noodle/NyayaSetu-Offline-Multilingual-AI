import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `base: './'` works for Electron (relative paths).
// `base: '/'` works for Vercel (absolute paths for SPA routing).
// We auto-switch based on an env flag set by the build command.
const isElectronBuild = process.env.BUILD_TARGET === 'electron'

// TODO: PWA — once `vite-plugin-pwa` is added to package.json AND the
// `/manifest.webmanifest` + service-worker assets are created by another
// agent, uncomment the import + plugin block below.
//
// import { VitePWA } from 'vite-plugin-pwa'
//
// const pwaPlugin = VitePWA({
//   registerType: 'autoUpdate',
//   manifest: false, // we ship a static /manifest.webmanifest
//   workbox: {
//     globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
//     navigateFallback: '/index.html',
//   },
// })

export default defineConfig({
  plugins: [
    react(),
    // pwaPlugin, // <- enable once vite-plugin-pwa is installed
  ],
  server: {
    port: 5173,
  },
  base: isElectronBuild ? './' : '/',
  build: {
    outDir: 'dist',
    // Hidden source maps: emitted for debugging/Sentry, but not referenced
    // from the served JS, so end users cannot retrieve them via the browser.
    sourcemap: isElectronBuild ? false : 'hidden',
    // Keep chunk size warnings actionable but not noisy
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // Manual chunks: keep heavy/optional deps in their own bundles.
        // `three` is large and only used on Login (3D scene); splitting it
        // keeps the initial bundle small for first paint.
        manualChunks: (id: string) => {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('three') || id.includes('@react-three')) return 'three-vendor';
          if (id.includes('framer-motion') || id.includes('lenis') || id.includes('@studio-freight'))
            return 'motion-vendor';
          if (id.includes('recharts')) return 'charts-vendor';
          if (id.includes('react-router-dom') || /\/react\//.test(id) || /\/react-dom\//.test(id))
            return 'react-vendor';
          return undefined;
        },
      },
    },
  },
})
