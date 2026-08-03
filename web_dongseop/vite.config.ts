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
    // 파이썬 하네스(:8765)의 API. 실행 상태만 휘발성으로 바뀌며 registry는 읽기 전용입니다.
    // 서버가 꺼져 있으면 콘솔은 결정론적 폴백 해설로 계속 동작합니다.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: false },
    },
  },
  // `vite preview`는 server.proxy를 쓰지 않으므로, 빌드 산출물을 하네스와 함께
  // 서빙할 때 /api가 404로 죽지 않도록 동일한 프록시를 preview에도 명시합니다.
  preview: {
    port: 4173,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: false },
    },
  },
})
