import http, { unwrap, type ApiResponse } from '@/common/utils/http'

/**
 * 采集管理 API — v4 自管协议（2026-10-22）

 * 后端路由（contexts/collect/interface/）：
 *   GET  /collect/catalog                        service 元数据 catalog
 *   POST /collect/{facet}/{service_name}         触发采集，立即返回
 *                                                ★ daily 是强类型 DTO 路由，请求体扁平
 *                                                  （start_date / end_date / ts_code），
 *                                                  响应不含 log_id
 *   GET  /collect/logs/{service_name}           查询日志列表
 *   GET  /collect/logs/{service_name}/{log_id}  查询单条日志详情
 *   GET  /collect/query/{name}                  实时查询 service.get()
 */

// ═══════════════════════════════════════════════════════════════════════════
//  Types
// ═══════════════════════════════════════════════════════════════════════════

/** 采集日志（后端 collect_logs 表，字段已通用化） */
export interface CollectLog {
  id: string
  service_name: string
  category: string                                       // 分组维度（采集时 = facet）
  action: 'incremental' | 'full_refresh' | 'realtime'    // 动作类型（采集时 = kind）
  trigger_source: 'manual' | 'script' | 'schedule'
  trigger_user: string | null
  meta: Record<string, any>                             // 动态上下文（采集时 = 原始入参）
  status: 'init' | 'running' | 'success' | 'partial_fail' | 'failed' | 'skipped'
  total_count: number
  saved_count: number
  fail_count: number
  progress: number           // 0-100
  duration_ms: number | null // 耗时（毫秒）
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

/**
 * 触发采集响应
 *
 * ⚠️ v4 自管协议：log_id 不再透出边界（后端 collect() 只派发，不返回 log_id）。
 *    - daily（强类型 DTO 路由）→ data 为 null，只有 message
 *    - 其他 service → data 含 log_id / status
 * 前端统一按 service_name 轮询 GET /collect/logs/{service_name} 取进度。
 */
export interface CollectStartResponse {
  log_id?: string | null
  status?: string | null
  service_name?: string
  facet?: string
  message: string
}

/**
 * daily 强类型 DTO 请求体（POST /collect/tech/daily）
 * 注意：扁平结构，**没有** params 外层包装
 */
export interface DailyCollectPayload {
  start_date: string
  end_date: string
  ts_code?: string
}

/** Service 元数据（GET /collect/catalog 列表项） */
export interface ServiceItem {
  name: string
  facet: string
  label: string
  description: string
  kind: 'incremental' | 'full_refresh' | 'realtime'
  supports_query: boolean
  path: string
  query_path: string | null
}

/** UI 控件类型（保留供 RealtimePanel 内部使用） */
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

/** 采集启动 payload（通用 service：{ params } 包装） */
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
 * 强类型 DTO 路由的 service（请求体扁平，没有 { params } 包装）
 *
 * daily → POST /collect/tech/daily，body: { start_date, end_date, ts_code? }
 */
export const FLAT_BODY_SERVICES = new Set<string>(['daily'])

/**
 * 手动触发一次 service（POST /collect/{facet}/{name}）
 *
 * ⚠️ v4 自管协议：log_id 不再透出边界，返回可能没有 log_id。
 *    前端统一按 service_name 轮询 GET /collect/logs/{service_name} 取进度。
 */
export const runService = async (
  name: string,
  payload: CollectStartPayload | DailyCollectPayload | Record<string, any> = { params: {} },
): Promise<CollectStartResponse> => {
  if (!_cachedServices || _cachedServices.length === 0) {
    await waitForServices()
  }
  const path = buildPath(name, `/collect/_unknown/${name}`)

  let body: any
  if (FLAT_BODY_SERVICES.has(name)) {
    // 强类型 DTO 路由：扁平 body（去空值，避免 ts_code: '' 触发 422）
    const src = ('params' in (payload as any)
      ? (payload as CollectStartPayload).params
      : (payload as Record<string, any>)) || {}
    body = Object.fromEntries(
      Object.entries(src).filter(([, v]) => v !== null && v !== undefined && v !== ''),
    )
  } else {
    // 兼容旧调用：直接传 params dict 时自动包装
    body = 'params' in (payload as any)
      ? (payload as CollectStartPayload)
      : { params: (payload as Record<string, any>) || {} }
  }

  console.log('[collect-manage/api] runService', name, '→', path, body)
  const res = await http.post<ApiResponse<CollectStartResponse | null>>(path, body)
  const envelope = res.data
  const data = unwrap<CollectStartResponse | null>(res)
  // daily 的 response_model 是 ApiResponse[None] → data 为 null，用信封里的 message
  return (data ?? { message: envelope?.message || '采集任务派发成功' }) as CollectStartResponse
}

/** daily 专用触发（强类型 DTO，扁平 body） */
export const runDailyCollect = (
  payload: DailyCollectPayload,
): Promise<CollectStartResponse> => runService('daily', payload)

/**
 * 把采集触发失败转成可读的中文提示
 *
 * 后端异常处理器把 422 归一化成：
 *   { code: 422, message: "请求参数校验失败", data: { errors: [{loc, msg, type}, ...] } }
 * 所以优先从 data.errors 里取第一条明细；拿不到再退回 message。
 */
export function describeCollectError(e: any): string {
  const body = e?.response?.data
  const errors = body?.data?.errors
  if (Array.isArray(errors) && errors.length > 0) {
    const first = errors[0]
    const loc = Array.isArray(first?.loc)
      ? first.loc.filter((x: any) => x !== 'body').join('.')
      : ''
    const msg = first?.msg || '参数校验失败'
    return loc ? `${loc}: ${msg}` : msg
  }
  // 兼容 FastAPI 默认的 { detail: [...] } 格式
  const detail = body?.detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    const loc = Array.isArray(first?.loc)
      ? first.loc.filter((x: any) => x !== 'body').join('.')
      : ''
    const msg = first?.msg || '参数校验失败'
    return loc ? `${loc}: ${msg}` : msg
  }
  return body?.message || e?.message || '采集失败'
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
  supports_query: boolean
  kind: 'incremental' | 'full_refresh' | 'realtime'
  facet: string
  path: string
  query_path: string | null
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
      supports_query: !!s.supports_query,
      kind: s.kind || (s.supports_query ? 'realtime' : 'full_refresh'),
      facet: s.facet,
      path: s.path,
      query_path: s.query_path,
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
