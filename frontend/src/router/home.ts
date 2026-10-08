import type { RouteRecordRaw } from 'vue-router'
import Shell from '@/layouts/Shell.vue'
import { useAuthStore } from '@/stores/auth'

const homeRoutes: RouteRecordRaw = {
  path: '/home',
  component: Shell,
  redirect: '/home/index',
  children: [
    {
      path: 'index',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '数据大盘', icon: 'odometer' },
    },
    {
      path: 'stock-panel',
      name: 'StockInfoList',
      component: () => import('@/views/stock-info/StockInfoList.vue'),
      meta: { title: '股票信息', icon: 'data-line' },
    },
    {
      path: 'pool',
      name: 'PoolList',
      component: () => import('@/views/stock-pool/PoolList.vue'),
      meta: { title: '操作池', icon: 'folder' },
    },
    {
      path: 'pool/:poolId',
      name: 'PoolDetail',
      component: () => import('@/views/stock-pool/components/PoolDetail.vue'),
      meta: { title: '池详情', icon: 'folder', hidden: true },
      props: true,
    },
    {
      path: 'collect-manage',
      name: 'CollectManage',
      component: () => import('@/views/collect-manage/CollectManage.vue'),
      meta: { title: '采集管理', icon: 'upload' },
    },
    {
      path: 'market',
      name: 'MarketDashboard',
      component: () => import('@/views/market/MarketDashboard.vue'),
      meta: { title: '市场全局', icon: 'data-analysis', hidden: true },
    },
    {
      path: 'market/sectors',
      name: 'SectorBoard',
      component: () => import('@/views/market/SectorBoard.vue'),
      meta: { title: '板块行情', icon: 'grid', hidden: true },
    },
    {
      // 账户管理（admin）
      path: 'account',
      name: 'AccountManage',
      component: () => import('@/views/auth/AccountPage.vue'),
      meta: {
        title: '账户管理',
        icon: 'user-filled',
      },
    },
    {
      // 自助改密
      path: 'change-password',
      name: 'ChangePassword',
      component: () => import('@/views/auth/ChangePasswordPage.vue'),
      meta: { title: '修改密码', icon: 'lock', hidden: true, requiresAuth: true },
    },

    // ════════════════════════════════════════════════════════════════
    //  概念大盘 v2（01 概念大盘页 · 纯追加，挂在末尾的「实验性」菜单组下）
    // ════════════════════════════════════════════════════════════════
    {
      // 实验性：概念大盘
      path: 'concepts',
      name: 'ConceptBoard',
      component: () => import('@/views/concept-board/ConceptBoard.vue'),
      meta: { title: '概念大盘', icon: 'data-line' },
    },
    {
      path: 'data-board/:symbol?',
      name: 'DataBoard',
      component: () => import('@/views/data-board/DataBoard.vue'),
      props: true,
      meta: { title: '数据看板', icon: 'data-analysis', hidden: false },
    },

    // ════════════════════════════════════════════════════════════════
    //  数据备份与恢复
    // ════════════════════════════════════════════════════════════════
    {
      path: 'backup',
      component: () => import('@/views/backup/BackupLayout.vue'),
      redirect: '/home/backup/create',
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
      path: 'restore',
      name: 'Restore',
      component: () => import('@/views/backup/RestorePage.vue'),
      meta: { title: '数据恢复', icon: 'refresh-left', requiresAuth: true },
    },
  ],
}

// 全局路由守卫：未登录 → /login；已登录但 userInfo 缺失 → fetchMe
export function setupAuthGuard(router: import('vue-router').Router) {
  router.beforeEach(async (to, _from, next) => {
    const authStore = useAuthStore()
    const isPublic = to.path === '/login'

    // 启动时拉一次 userInfo（F5 后 token 还在但 userInfo 已清）
    if (authStore.isLoggedIn && !authStore.userInfo) {
      try {
        await authStore.bootstrap()
      } catch {
        authStore.clear()
      }
    }

    if (!authStore.isLoggedIn && !isPublic) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
    if (authStore.isLoggedIn && isPublic) {
      next('/home/index')
      return
    }
    next()
  })
}

export default homeRoutes