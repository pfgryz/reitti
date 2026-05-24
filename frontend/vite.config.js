import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: '/app/',
  server: {
    proxy: {
      '/places': 'http://127.0.0.1:8000',
      '/trip': 'http://127.0.0.1:8000',
      '/stops': 'http://127.0.0.1:8000',
      '/distance': 'http://127.0.0.1:8000',
    },
  },
})
