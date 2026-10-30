import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@common': fileURLToPath(new URL('./src/common', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        // Java 后端（backend-java）本地监听 8080，与 application.yml 的 SERVER_PORT 一致
        // 可通过环境变量 VITE_API_PROXY_TARGET 覆盖（注意：该变量仅在进程启动时读取，改完需重启 dev server）
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
