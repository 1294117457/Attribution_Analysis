import http, { unwrap, type ApiResponse } from '@/common/utils/http'

/**
 * 采集管理 API — v2 采集日志进度优化（2026-10-19）
 *
 * 后端路由（contexts/collect/interface/manage/）：
 *   GET  /collect/catalog                        28 service 元数据 catalog
 *   POST /collect/{facet}/{service_name}         触发采集，返回 log_id
 *   GET  /collect/logs/{service_name}           查询日志列表
 *   GET  /collect/logs/{service_name}/{log_id}  查询单条日志详情
 *   GET  /collect/query/{name}                  实时查询 service.get()
 */

// ═══════════════════════════════════════════════════════════════════════════
//  Types
// ═══════════════════════════════════════════════════════════════════════════

/** 采集日志 */
export interface CollectLog {
  id: string
  service_name: string
  facet: string
  kind: 'incremental' | 'full_refresh' | 'realtime'
  trigger_source: 'manual' | 'script' | 'schedule'
  trigger_user: string | null
  params: Record<string, any>
  status: 'pending' | 'running' | 'success' | 'partial_fail' | 'failed' | 'skipped'
  total_count: number
  saved_count: number
  fail_count: number
  progress: number           // 0-100
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string | null
  updated_at: string | null
}

/** 日志列表响应 */
export interface CollectLogListResponse {
  items: CollectLog[]
}

/** 触发采集响应 */
export interface CollectStartResponse {
  log_id: string
  status: string
  service_name: string
  facet: string
  message: string
}

/** Service 元数据（GET /collect/catalog 列表项） */
export interface ServiceItem {
  name: string
  facet: string
  label: string
  description: string
  default_params: Record<string, any>
  param_schema: ParamSchema[]
  rate_limit: [string, number, number] | null
  concurrency: number
  supports_query: boolean
  kind: 'incremental' | 'full_refresh' | 'realtime'
  /** 增量采集（需前端提供时间范围）；true → 显示时间选择器 */
  incremental: boolean
  path: string
  query_path: string | null
}

/** 单个 param 的 UI schema */
export interface ParamSchema {
  key: string
  ui: ParamUiType
  required: boolean
  default?: any
  description: string
  example?: any
}

/** UI 控件类型 */
export type ParamUiType =
  | 'symbols_list' | 'index_codes_list' | 'str_list'
  | 'date_str' | 'list_status' | 'exchange_multi'
  | 'interval_kline' | 'period_kline' | 'bool_flag'
  | 'minutes_int' | 'days_int' | 'years_int' | 'limit_int' | 'int'
  | 'ts_code_str' | 'symbol_str' | 'index_code_str' | 'str' | 'json'

/** Service 列表响应 */
export interface ServiceListResponse {
  total: number
  items: ServiceItem[]
}

/** 采集启动 payload（删除 mode 字段） */
export interface CollectStartPayload {
  params: Record<string, any>
}

// ═══════════════════════════════════════════════════════════════════════════
//  Catalog / Services
// ═══════════════════════════════════════════════════════════════════════════

/** 拉 catalog */
export const listServices = () =>
  http.get<ApiResponse<ServiceListResponse>>('/collect/catalog').then(unwrap)

/** 内部缓存 */
let _cachedServices: ServiceItem[] | null = null
function cacheServices(items: ServiceItem[]) {
  _cachedServices = items
  if (cachedResolve && items.length > 0) {
    cachedResolve(items)
    cachedResolve = null
  }
}
let cachedResolve: ((items: ServiceItem[]) => void) | null = null
function waitForServices(): Promise<ServiceItem[]> {
  if (_cachedServices && _cachedServices.length > 0) return Promise.resolve(_cachedServices)
  return new Promise((resolve) => {
    cachedResolve = resolve
    listServices()
      .then((res) => {
        _cachedServices = res.items || []
        if (cachedResolve) {
          cachedResolve(_cachedServices)
          cachedResolve = null
        }
      })
      .catch(() => resolve([]))
  })
}

function findServiceByName(name: string): ServiceItem | undefined {
  return _cachedServices?.find((s) => s.name === name)
}

function buildPath(name: string, fallback: string): string {
  const svc = findServiceByName(name)
  if (!svc) {
    console.warn('[collect-manage/api] service not in cache:', name, '— using fallback:', fallback)
    return fallback
  }
  return svc.path.replace(/^\/api/, '')
}

function buildQueryPath(name: string): string | null {
  const svc = findServiceByName(name)
  return svc?.query_path?.replace(/^\/api/, '') ?? null
}

export const listServicesCached = async (): Promise<ServiceItem[]> => {
  const res = await listServices()
  cacheServices(res.items || [])
  return res.items || []
}

// ═══════════════════════════════════════════════════════════════════════════
//  Collect Logs（v2 新增）
// ═══════════════════════════════════════════════════════════════════════════

/**
 * 查询某 service 的最近采集日志
 * @param serviceName 服务名
 * @param limit 返回条数
 */
export const listCollectLogs = (serviceName: string, limit: number = 20) =>
  http.get<ApiResponse<CollectLogListResponse>>(`/collect/logs/${serviceName}?limit=${limit}`).then(unwrap)

/**
 * 查询单条采集日志详情
 * @param serviceName 服务名
 * @param logId 日志 ID
 */
export const getCollectLog = (serviceName: string, logId: string) =>
  http.get<ApiResponse<CollectLog>>(`/collect/logs/${serviceName}/${logId}`).then(unwrap)

// ═══════════════════════════════════════════════════════════════════════════
//  触发采集
// ═══════════════════════════════════════════════════════════════════════════

/**
 * 手动触发一次 service（POST /collect/{facet}/{name}）
 * 返回 log_id，前端用于轮询进度
 */
export const runService = async (
  name: string,
  payload: CollectStartPayload | Record<string, any> = { params: {} },
): Promise<CollectStartResponse> => {
  if (!_cachedServices || _cachedServices.length === 0) {
    await waitForServices()
  }
  const path = buildPath(name, `/collect/_unknown/${name}`)

  // 兼容旧调用：直接传 params dict 时自动包装
  const body: CollectStartPayload = 'params' in (payload as any)
    ? (payload as CollectStartPayload)
    : { params: (payload as Record<string, any>) || {} }

  console.log('[collect-manage/api] runService', name, '→', path, body)
  return await http
    .post<ApiResponse<CollectStartResponse>>(path, body)
    .then(unwrap)
}

/** 实时查询 service.get() */
export const queryService = async (
  name: string,
  params: Record<string, any> = {},
): Promise<any> => {
  if (!_cachedServices || _cachedServices.length === 0) {
    await waitForServices()
  }
  const path = buildQueryPath(name)
  if (!path) {
    throw new Error(`service ${name} 不支持实时查询（supports_query=false）`)
  }
  const qs = Object.keys(params).length > 0
    ? '?params=' + encodeURIComponent(JSON.stringify(params))
    : ''
  return http
    .get<ApiResponse<any>>(path + qs)
    .then(unwrap)
}

// ═══════════════════════════════════════════════════════════════════════════
//  Catalog 聚合视图
// ═══════════════════════════════════════════════════════════════════════════

export const FACET_LABELS: Record<string, string> = {
  tech: '技术面',
  capital: '资金面',
  fundamental: '基本面',
  news: '资讯',
  sentiment: '情绪',
}

export const FACET_ICONS: Record<string, string> = {
  tech: 'Monitor',
  capital: 'Money',
  fundamental: 'DataAnalysis',
  news: 'Document',
  sentiment: 'ChatDotRound',
}

export const FACET_SORT: Record<string, number> = {
  tech: 1,
  capital: 2,
  fundamental: 3,
  news: 4,
  sentiment: 5,
}

/** 单个 service 在 UI 目录树中的视图 */
export interface CatalogItem {
  service_name: string
  label: string
  description: string
  default_params: Record<string, any>
  param_schema: ParamSchema[]
  supports_query: boolean
  kind: 'incremental' | 'full_refresh' | 'realtime'
  /** 增量采集标志（true → 前端显示时间选择器） */
  incremental: boolean
  facet: string
  path: string
  query_path: string | null
  rate_limit: [string, number, number] | null
}

export interface CatalogGroup {
  facet: string
  label: string
  icon: string
  sort_order: number
  /** 扁平 service 列表（按 label 排序） */
  items: CatalogItem[]
}

export interface Catalog {
  items: CatalogGroup[]
}

export function buildCatalog(services: ServiceItem[]): Catalog {
  const groups = new Map<string, CatalogGroup>()
  for (const s of services) {
    const facetKey = s.facet || 'other'
    if (!groups.has(facetKey)) {
      groups.set(facetKey, {
        facet: facetKey,
        label: FACET_LABELS[facetKey] || facetKey,
        icon: FACET_ICONS[facetKey] || 'Grid',
        sort_order: FACET_SORT[facetKey] ?? 99,
        items: [],
      })
    }
    const g = groups.get(facetKey)!
    g.items.push({
      service_name: s.name,
      label: s.label || s.name,
      description: s.description || '',
      default_params: s.default_params || {},
      param_schema: s.param_schema || [],
      supports_query: !!s.supports_query,
      kind: s.kind || (s.supports_query ? 'realtime' : 'full_refresh'),
      incremental: !!s.incremental,
      facet: s.facet,
      path: s.path,
      query_path: s.query_path,
      rate_limit: s.rate_limit || null,
    })
  }
  // 组内按 label 排序
  for (const g of groups.values()) {
    g.items.sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
  }
  return {
    items: Array.from(groups.values()).sort(
      (a, b) => a.sort_order - b.sort_order,
    ),
  }
}
