import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // CONTRACT §1
    strictPort: true,
    fs: { allow: ['..'] }, // lets the app import ../contracts/*.json (CONTRACT: load enums, never hard-code)
  },
})
