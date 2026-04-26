import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  // Para no escribir rutas relativas como ../../components
  // podemos escribir @/components directamente
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    // Proxy de desarrollo: las peticiones a /api/* se redirigen al backend Django.
    // Esto evita problemas de CORS y de IPv4 vs IPv6 en Windows.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
