import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import homeRoutes from './home'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home/index' },
  homeRoutes,
  { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFound.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
