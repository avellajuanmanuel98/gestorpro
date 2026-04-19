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
})
