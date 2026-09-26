/**
 * 详情抽屉状态管理 composable
 *
 * 解耦 StockInfoList 与 StockDetailDrawer 的状态：
 * - visible：抽屉开关
 * - currentStock：当前展示的股票
 * - preheatConcepts：列表阶段预热的概念简略版（ConceptBrief[]），
 *   抽屉打开瞬间即可在「概念」Tab 直接渲染，避免骨架屏
 * - open(row)：打开抽屉，并携带 row.concepts 作为预热数据
 * - close()：关闭抽屉（延迟清空避免动画闪屏）
 */
import { ref } from 'vue'
import type { StockInfo, ConceptBrief } from '@/views/stock-info/api'

export function useStockDetailDrawer() {
  const visible = ref(false)
  const currentStock = ref<StockInfo | null>(null)
  const preheatConcepts = ref<ConceptBrief[]>([])

  function open(stock: StockInfo) {
    currentStock.value = stock
    // 🆕 把列表阶段已下发的 ConceptBrief[] 作为预热数据透传给抽屉
    // 后端 with_concepts=true 一次性下发，前端零额外请求即可在概念 Tab 立即渲染
    preheatConcepts.value = stock.concepts ?? []
    visible.value = true
  }

  function close() {
    visible.value = false
    // 延迟清空，等抽屉关闭动画（约 300ms）结束
    setTimeout(() => {
      currentStock.value = null
      preheatConcepts.value = []
    }, 300)
  }

  return { visible, currentStock, preheatConcepts, open, close }
}
