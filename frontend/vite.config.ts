import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiPort = Number(process.env.V2_API_PORT ?? 8001)
if (!Number.isInteger(apiPort) || apiPort < 1024 || apiPort > 65535) {
  throw new Error('V2_API_PORT requiere un puerto local válido')
}
const local = {
  host: '127.0.0.1',
  strictPort: true,
  proxy: { '/api': { target: `http://127.0.0.1:${apiPort}` } },
  headers: { 'Cache-Control': 'no-store' },
}

export default defineConfig({
  plugins: [react()],
  server: { ...local, port: 5173, cors: false, forwardConsole: false },
  preview: { ...local, port: 5173 },
  build: { sourcemap: false },
})
