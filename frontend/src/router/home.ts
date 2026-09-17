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
      // 🆕 市场全局（开发指南 §8.6）
      path: 'market',
      name: 'MarketDashboard',
      component: () => import('@/views/market/MarketDashboard.vue'),
      meta: { title: '市场全局', icon: 'data-analysis', hidden: true },
    },
    {
      // 🆕 板块行情列表（开发指南 §8.6）
      path: 'market/sectors',
      name: 'SectorBoard',
      component: () => import('@/views/market/SectorBoard.vue'),
      meta: { title: '板块行情', icon: 'grid', hidden: true },
    },
  ],
}

export default homeRoutes