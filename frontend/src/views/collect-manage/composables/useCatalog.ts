/**
 * 采集任务目录树 composable（step7 重构）
 *
 * 启动时拉一次 /collect/services，前端自己按 facet/sub_facet 聚合成目录树。
 * 提供：
 * - catalog: ref<CatalogGroup[]>
 * - getItem(serviceName): 找某个 service 的目录项
 * - countByFacet(facet, predicate): 统计（用于左树 facet badge）
 *
 * 配套：backend/src/contexts/collect/interface/route_service.py
 */

import { ref, computed } from 'vue'
import { buildCatalog, listServicesCached, type CatalogGroup, type CatalogItem, type ServiceItem } from '../api'

/** facet badge：可入计划的 service 数（目前 = 全部可入库 service） */
export function countActive(facet: CatalogGroup): number {
  let n = 0
  for (const items of Object.values(facet.sub_groups)) {
    n += items.length
  }
  return n
}

/** 兼容旧名：可执行的 service 数（= countActive） */
export const countReady = countActive
/** 兼容旧名：已计划的 service 数（= 0，因为 service 不再分 ready/planned 状态） */
export function countPlanned(_facet: CatalogGroup): number {
  return 0
}

/** sub_facet 中文标签（UI 副标题用） */
export const SUB_FACET_LABELS: Record<string, string> = {
  kline: 'K 线',
  adj: '复权因子',
  suspend: '停复牌',
  name: '名称变更',
  dividend: '分红',
  moneyflow: '资金流向',
  margin: '两融',
  top: '龙虎榜',
  block: '大宗交易',
  holder: '股东',
  hsgt: '沪深港通',
  limit: '涨跌停',
  valuation: '估值',
  fin: '财报',
  stock: '基础信息',
  concept: '概念',
}

export function useCatalog() {
  /** 原始 service 列表（用于 service 详情查表） */
  const services = ref<ServiceItem[]>([])
  const catalog = ref<CatalogGroup[]>([])
  const loading = ref(false)
  const error = ref<unknown>(null)

  /** 拉一次（启动期调用） */
  async function load() {
    loading.value = true
    try {
      const res = await listServicesCached()
      services.value = res
      catalog.value = buildCatalog(services.value).items
    } catch (e) {
      error.value = e
      services.value = []
      catalog.value = []
    } finally {
      loading.value = false
    }
  }

  /** 按 service_name 找目录项（在所有 facet / sub_facet 下搜） */
  function getItem(serviceName: string): CatalogItem | null {
    for (const facet of catalog.value) {
      for (const items of Object.values(facet.sub_groups)) {
        const hit = items.find((i) => i.service_name === serviceName)
        if (hit) return hit
      }
    }
    return null
  }

  /** 按 service_name 找原始 ServiceItem（用于查 default_params / label） */
  function getService(serviceName: string): ServiceItem | null {
    return services.value.find((s) => s.name === serviceName) || null
  }

  const totalActive = computed(() =>
    catalog.value.reduce((acc, f) => acc + countActive(f), 0),
  )
  const totalPlanned = computed(() =>
    catalog.value.reduce((acc, f) => acc + countPlanned(f), 0),
  )

  return {
    services,
    catalog,
    loading,
    error,
    load,
    getItem,
    getService,
    countActive,
    countReady,
    countPlanned,
    SUB_FACET_LABELS,
    totalActive,
    totalPlanned,
  }
}
