/**
 * 采集任务目录树 composable
 *
 * 启动时拉一次 catalog，提供：
 * - catalog: ref<FacetGroup[]>
 * - getTaskDef(taskType): 找某个 task_type 对应的元数据
 * - countReady / countPlanned: 统计（用于左树 facet badge）
 *
 * 配套：docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §3.2
 */

import { ref, computed } from 'vue'
import { getCatalog, type FacetGroup, type TaskDef } from '../api'

export function useCatalog() {
  const catalog = ref<FacetGroup[]>([])
  const loading = ref(false)
  const error = ref<unknown>(null)

  /** 拉一次（启动期调用） */
  async function load() {
    loading.value = true
    try {
      const res = await getCatalog()
      catalog.value = res.items || []
    } catch (e) {
      error.value = e
      catalog.value = []
    } finally {
      loading.value = false
    }
  }

  /** 按 task_type 找 TaskDef（在所有 facet / sub_facet 下搜） */
  function getTaskDef(taskType: string): TaskDef | null {
    for (const facet of catalog.value) {
      for (const tasks of Object.values(facet.sub_groups)) {
        const hit = tasks.find((t) => t.task_type === taskType)
        if (hit) return hit
      }
    }
    return null
  }

  /** 统计 ready 数 */
  function countReady(facet: FacetGroup): number {
    let n = 0
    for (const tasks of Object.values(facet.sub_groups)) {
      n += tasks.filter((t) => t.status === 'ready').length
    }
    return n
  }

  /** 统计 planned 数 */
  function countPlanned(facet: FacetGroup): number {
    let n = 0
    for (const tasks of Object.values(facet.sub_groups)) {
      n += tasks.filter((t) => t.status === 'planned').length
    }
    return n
  }

  /** sub_facet 中文标签表（UI 副标题用，无则显示 key） */
  const SUB_FACET_LABELS: Record<string, string> = {
    kline: 'K 线',
    base: '基础数据',
    valuation: '估值',
    core: '核心实体',
    report: '财务报告',
    holder: '股东结构',
    dividend: '分红',
    margin: '两融',
    moneyflow: '资金流向',
    dragon_tiger: '龙虎榜',
    block_trade: '大宗交易',
    chip: '筹码',
    article: '资讯',
    concept: '概念',
  }

  const totalReady = computed(() =>
    catalog.value.reduce((acc, f) => acc + countReady(f), 0),
  )
  const totalPlanned = computed(() =>
    catalog.value.reduce((acc, f) => acc + countPlanned(f), 0),
  )

  return {
    catalog,
    loading,
    error,
    load,
    getTaskDef,
    countReady,
    countPlanned,
    SUB_FACET_LABELS,
    totalReady,
    totalPlanned,
  }
}