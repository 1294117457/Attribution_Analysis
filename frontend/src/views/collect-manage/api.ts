import http, { unwrap, type ApiResponse } from '@/common/utils/http'

/**
 * 采集管理 API — step7 重构后简化版（仅保留「最基础的全量/条件采集」）
 *
 * 后端路由（contexts/collect/interface/router.py）：
 *   GET  /collect/services                28 service 元数据 catalog（前端左侧目录树数据源）
 *   POST /collect/{facet}/{service_name}  触发一次 service.collect()（mode=full/condition）
 *   GET  /collect/query/{name}            实时查询 service.get()（仅 supports_query=true）
 *
 * ⚠️ schedule / log / APScheduler / 取消 / 重跑 相关功能暂时不做（用户要求先跑通基本采集）。
 *    后续如需补齐，再加 listSchedules / listLogs 等函数。
 */

// ═══════════════════════════════════════════════════════════════════════════
//  Service — 已注册的采集服务（统一 task / fetcher / catalog）
// ═══════════════════════════════════════════════════════════════════════════

/** Service 元数据（GET /collect/services 列表项） */
export interface ServiceItem {
  name: string
  facet: string                  // 'tech' / 'capital' / 'fundamental' / 'news' / 'sentiment'
  sub_facet: string              // 'kline' / 'moneyflow' / 'concept' ...
  label: string
  description: string
  default_params: Record<string, any>
  /** 后端推导的每个 param 的 UI schema（前端按此渲染输入控件） */
  param_schema: ParamSchema[]
  rate_limit: [string, number, number] | null
  concurrency: number
  /** service 是否有 get() 入口（query 实时试查） */
  supports_query: boolean
  /** 主职责：collect (入库) / realtime (实时查询不入库) / both */
  kind: 'collect' | 'realtime' | 'both'
  /** 实际 POST 路径 */
  path: string
  /** 实时查询路径（supports_query=true 时才有） */
  query_path: string | null
}

/** 单个 param 的 UI schema（后端 _derive_param_schema 推导） */
export interface ParamSchema {
  key: string                    // param 名称（如 'symbols' / 'trade_date'）
  ui: ParamUiType                // 控件类型
  required: boolean              // 是否必填
  default?: any                  // 默认值
  description: string            // 中文描述
  example?: any                  // 示例值
}

/** UI 控件类型（后端 _infer_param_ui 定义） */
export type ParamUiType =
  | 'symbols_list'      // 股票代码列表（多行文本）
  | 'index_codes_list'  // 概念代码列表（多行文本）
  | 'str_list'          // 通用字符串列表
  | 'date_str'          // 日期字符串 YYYY-MM-DD
  | 'list_status'       // L / D / P 单选
  | 'exchange_multi'    // 交易所多选
  | 'interval_kline'    // 分钟周期 1/5/15/30/60
  | 'period_kline'      // 日/周/月
  | 'bool_flag'         // 布尔开关
  | 'minutes_int'       // 整数（回溯分钟）
  | 'days_int'          // 整数（回溯天数）
  | 'years_int'         // 整数（回溯年数）
  | 'limit_int'         // 整数（限制条数）
  | 'int'               // 通用整数
  | 'ts_code_str'       // Tushare 代码
  | 'symbol_str'        // 股票代码
  | 'index_code_str'    // 概念代码
  | 'str'               // 通用字符串
  | 'json'              // JSON 对象（兜底）

/** Service 列表响应 */
export interface ServiceListResponse {
  total: number
  items: ServiceItem[]
}

/** 拉一次 services（catalog 聚合） */
export const listServices = () =>
  http.get<ApiResponse<ServiceListResponse>>('/collect/services').then(unwrap)

/**
 * 内部：缓存最近一次 listServices 的结果，用于 runService / queryService 拼路径。
 * 因为新 URL 风格是 /collect/{facet}/{name}，调用方只传 name 时需要反查 facet。
 */
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
    // 兜底：若还没调过 listServices，主动拉一次
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
  if (svc) return svc.path.replace(/^\/api/, '')  // 去掉 /api 前缀（http baseURL 已带）
  return fallback
}

function buildQueryPath(name: string): string | null {
  const svc = findServiceByName(name)
  return svc?.query_path?.replace(/^\/api/, '') ?? null
}

// 包装 listServices：拉完自动缓存（保证 useCatalog 已 mount 后再调 runService 能命中）
export const listServicesCached = async (): Promise<ServiceItem[]> => {
  const res = await listServices()
  cacheServices(res.items || [])
  return res.items || []
}

/** 采集启动 payload（含采集模式：full = 全量 / condition = 条件） */
export interface CollectStartPayload {
  mode: 'full' | 'condition'
  params: Record<string, any>
}

/** 采集执行结果（后端 svc.collect() 返回 CollectResult.to_dict()） */
export interface CollectRunResult {
  total: number
  success: number
  fail: number
  skip: number
  saved: number
  message: string
  items?: any[]
  [k: string]: any
}

/** 手动触发一次 service（POST /collect/{facet}/{name}） */
export const runService = async (
  name: string,
  payload: CollectStartPayload | Record<string, any> = { mode: 'condition', params: {} },
): Promise<CollectRunResult> => {
  if (!_cachedServices || _cachedServices.length === 0) {
    await waitForServices()
  }
  const path = buildPath(name, `/collect/_unknown/${name}`)

  // 兼容旧调用：直接传 params dict 时自动包成 condition
  const body: CollectStartPayload = 'params' in (payload as any) && 'mode' in (payload as any)
    ? (payload as CollectStartPayload)
    : { mode: 'condition', params: (payload as Record<string, any>) || {} }

  return http
    .post<ApiResponse<CollectRunResult>>(path, body)
    .then(unwrap)
}

/** service.get() 实时查询（GET /collect/query/{name}?params=<JSON>） */
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
//  聚合视图：Catalog — 由 services 列表按 facet/sub_facet 二级聚合
//  （后端不再提供 /collect/catalog，前端自己聚）
// ═══════════════════════════════════════════════════════════════════════════

/** Facet 标签（前端可本地化；后端 service.facet 仍是英文 key） */
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

/** sub_facet 中文标签（前端 UI 副标题） */
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
  kline_daily: 'K 线（日）',
  kline_minute: 'K 线（分）',
  lhb: '龙虎榜',
  lhb_inst: '龙虎榜（机构）',
  north_flow: '北向',
}

/** 单个 service 在 UI 目录树中的视图（由 ServiceItem 派生） */
export interface CatalogItem {
  service_name: string
  label: string
  description: string
  default_params: Record<string, any>
  /** 后端推导的 param UI schema（CollectActionCard 用） */
  param_schema: ParamSchema[]
  /** service 是否有 get() 入口（query 入口） */
  supports_query: boolean
  /** 主职责：collect / realtime / both */
  kind: 'collect' | 'realtime' | 'both'
  /** facet（tech/capital/...） */
  facet: string
  /** sub_facet（kline/...） */
  sub_facet: string
  /** 实际 POST 路径（去掉 /api 前缀，http baseURL 已带） */
  path: string
  /** 实时查询路径 */
  query_path: string | null
  /** 后端限速 [source, max_count, window_seconds] */
  rate_limit: [string, number, number] | null
}

export interface CatalogGroup {
  facet: string
  label: string
  icon: string
  sort_order: number
  sub_groups: Record<string, CatalogItem[]>
}

export interface Catalog {
  items: CatalogGroup[]
}

/**
 * 把 service 列表聚合成 facet / sub_facet 二级树。
 */
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
        sub_groups: {},
      })
    }
    const g = groups.get(facetKey)!
    const subKey = s.sub_facet || 'other'
    if (!g.sub_groups[subKey]) g.sub_groups[subKey] = []
    g.sub_groups[subKey].push({
      service_name: s.name,
      label: s.label || s.name,
      description: s.description || '',
      default_params: s.default_params || {},
      param_schema: s.param_schema || [],
      supports_query: !!s.supports_query,
      kind: s.kind || (s.supports_query ? 'both' : 'collect'),
      facet: s.facet,
      sub_facet: s.sub_facet,
      path: s.path,
      query_path: s.query_path,
      rate_limit: s.rate_limit || null,
    })
  }
  return {
    items: Array.from(groups.values()).sort(
      (a, b) => a.sort_order - b.sort_order,
    ),
  }
}
