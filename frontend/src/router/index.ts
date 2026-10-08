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
    // 四数据面单股看板（顶级独立路径，便于分享/收藏 /data-board/000601）
    // 包裹在 Shell 内（顶部栏 + 左侧菜单）+ 复用 /home/data-board 同款组件
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

  // ════════════════════════════════════════════════════════════════
  //  数据备份与恢复（v1 新增模块；独立顶级路由，便于权限控制 + 跳转）
  // ════════════════════════════════════════════════════════════════
  {
    path: '/backup',
    component: () => import('@/views/backup/BackupLayout.vue'),
    redirect: '/backup/create',
    meta: { title: '数据备份', icon: 'folder-opened', requiresAuth: true },
    children: [
      {
        path: 'create',
        name: 'BackupCreate',
        component: () => import('@/views/backup/BackupCreatePage.vue'),
        meta: { title: '创建备份', hidden: true },
      },
      {
        path: 'history',
        name: 'BackupHistory',
        component: () => import('@/views/backup/BackupHistoryPage.vue'),
        meta: { title: '备份历史', hidden: true },
      },
    ],
  },
  {
    path: '/restore',
    component: () => import('@/views/backup/RestorePage.vue'),
    meta: { title: '数据恢复', icon: 'refresh-left', requiresAuth: true },
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