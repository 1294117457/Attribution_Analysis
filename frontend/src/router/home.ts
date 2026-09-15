import type { RouteRecordRaw } from 'vue-router'
import Shell from '@/layouts/Shell.vue'

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
      name: 'StockPanel',
      component: () => import('@/views/stock-info/components/StockPanel.vue'),
      meta: { title: '股票信息', icon: 'data-line' },
    },
    {
      path: 'pool',
      name: 'PoolList',
      component: () => import('@/views/stock-pool/components/PoolList.vue'),
      meta: { title: '操作池', icon: 'folder' },
    },
    {
      path: 'pool/:poolId',
      name: 'PoolDetail',
      component: () => import('@/views/stock-pool/components/PoolDetail.vue'),
      meta: { title: '池详情', icon: 'folder', hidden: true },
      props: true,
    },
  ],
}

export default homeRoutes
