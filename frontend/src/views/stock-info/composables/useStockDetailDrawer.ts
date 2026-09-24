/**
 * 详情抽屉状态管理 composable
 *
 * 解耦 StockInfoList 与 StockDetailDrawer 的状态：
 * - visible：抽屉开关
 * - currentStock：当前展示的股票
 * - open(row)：打开抽屉
 * - close()：关闭抽屉（延迟清空避免动画闪屏）
 */
import { ref } from 'vue'
import type { StockInfo } from '@/views/stock-info/api'

export function useStockDetailDrawer() {
  const visible = ref(false)
  const currentStock = ref<StockInfo | null>(null)

  function open(stock: StockInfo) {
    currentStock.value = stock
    visible.value = true
  }

  function close() {
    visible.value = false
    // 延迟清空，等抽屉关闭动画（约 300ms）结束
    setTimeout(() => {
      currentStock.value = null
    }, 300)
  }

  return { visible, currentStock, open, close }
}
