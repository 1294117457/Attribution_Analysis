import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import homeRoutes, { setupAuthGuard } from './home'
import Shell from '@/layouts/Shell.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home/index' },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginPage.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/data-board',
    component: Shell,
    children: [
      {
        path: ':symbol?',
        name: 'DataBoardStandalone',
        component: () => import('@/views/data-board/DataBoard.vue'),
        props: true,
        meta: { title: '数据看板', hidden: true, requiresAuth: true },
      },
    ],
  },

  homeRoutes,
  { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFound.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  // 同步标题
  const title = (to.meta?.title as string) || '智能金融归因分析平台'
  document.title = `${title} · 归因分析`
  next()
})

setupAuthGuard(router)

export default router