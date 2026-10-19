/**
 * 采集任务目录树 composable（v3：扁平一级 facet）

 * 启动时拉一次 /collect/catalog（2026-10 从 /collect/services 改名），
 * 前端自己按 facet 聚合成目录树（v3 去掉 sub_facet 一级）。
 * 提供：
 * - catalog: ref<CatalogGroup[]>
 * - getItem(serviceName): 找某个 service 的目录项
 * - countActive(facet): 统计（用于左树 facet badge）

 * 配套：backend/src/contexts/collect/interface/manage/catalog_handler.py
 */

import { ref, computed } from 'vue'
import {
  buildCatalog,
  listServicesCached,
  type CatalogGroup,
  type CatalogItem,
  type ServiceItem,
} from '../api'

/** facet badge：可入计划的 service 数（目前 = 全部可入库 service） */
export function countActive(facet: CatalogGroup): number {
  return facet.items.length
}

/** 兼容旧名：可执行的 service 数（= countActive） */
export const countReady = countActive
/** 兼容旧名：已计划的 service 数（= 0，因为 service 不再分 ready/planned 状态） */
export function countPlanned(_facet: CatalogGroup): number {
  return 0
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

  /** 按 service_name 找目录项 */
  function getItem(serviceName: string): CatalogItem | null {
    for (const facet of catalog.value) {
      const hit = facet.items.find((i) => i.service_name === serviceName)
      if (hit) return hit
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
    totalActive,
    totalPlanned,
  }
}
