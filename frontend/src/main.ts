import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')

// 启动后异步拉取 userInfo（不阻塞首屏渲染）。
// 路由守卫会先 await 这个调用，避免出现"已登录但 userInfo 空"的闪烁。
import { useAuthStore } from '@/stores/auth'
const authStore = useAuthStore()
authStore.bootstrap().catch(() => undefined)