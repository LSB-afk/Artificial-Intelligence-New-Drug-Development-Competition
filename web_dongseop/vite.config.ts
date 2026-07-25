import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 4173,
    // 파이썬 하네스(:8765)의 읽기 전용 과학 API.
    // 서버가 꺼져 있으면 콘솔은 결정론적 폴백 해설로 계속 동작합니다.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: false },
    },
  },
})
