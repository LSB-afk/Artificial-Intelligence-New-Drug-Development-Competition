import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 4173,
    // 포트가 막혀 있으면 조용히 4174, 4175로 밀리지 않고 멈춥니다. 밀린 서버는
    // QA 게이트 기본 주소와 어긋나고, 죽은 줄 알았던 예전 서버를 계속 보게 됩니다.
    strictPort: true,
    // 파이썬 하네스(:8765)의 읽기 전용 과학 API.
    // 서버가 꺼져 있으면 콘솔은 결정론적 폴백 해설로 계속 동작합니다.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: false },
    },
  },
})
