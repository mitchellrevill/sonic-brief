import { resolve } from "node:path";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    TanStackRouterVite({ autoCodeSplitting: true }),
    viteReact(),
    tailwindcss(),
  ],
  test: {
    globals: true,
    environment: "jsdom",
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
    },
  },
  optimizeDeps: {
    exclude: ['@ffmpeg/ffmpeg', '@ffmpeg/util', 'worker.js'],
  },
  build: {
    // Target modern browsers for smaller bundle size
    target: 'es2020',
    // Enable minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.logs in production
        drop_debugger: true,
      },
    },
    // Optimize chunk sizes
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks for better caching
          'react-vendor': ['react', 'react-dom'],
          'router-vendor': ['@tanstack/react-router'],
          'query-vendor': ['@tanstack/react-query'],
          // UI library chunks
          'radix-ui': [
            '@radix-ui/react-accordion',
            '@radix-ui/react-alert-dialog',
            '@radix-ui/react-avatar',
            '@radix-ui/react-checkbox',
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-label',
            '@radix-ui/react-popover',
            '@radix-ui/react-progress',
            '@radix-ui/react-scroll-area',
            '@radix-ui/react-select',
            '@radix-ui/react-separator',
            '@radix-ui/react-slider',
            '@radix-ui/react-switch',
            '@radix-ui/react-tabs',
            '@radix-ui/react-toast',
            '@radix-ui/react-tooltip',
          ],
          // Heavy document viewers - lazy load these
          'document-viewers': [
            '@react-pdf-viewer/core',
            '@react-pdf-viewer/default-layout',
            'docx-preview',
            'mammoth',
          ],
          // Markdown editors - lazy load
          'markdown-tools': [
            '@uiw/react-markdown-preview',
            '@uiw/react-md-editor',
            'react-markdown',
            'remark-gfm',
            'rehype-raw',
          ],
        },
      },
    },
    // Source maps for production debugging
    sourcemap: true,
    // Increase chunk size warning limit for better optimization
    chunkSizeWarningLimit: 1000,
  },
});
