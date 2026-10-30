import http, { unwrap, type ApiResponse } from '@/common/utils/http'

/**
 * 采集管理 API — 全异步任务式（Java 透传 Collector :8001）
 *
 * 后端路由（Java CollectProxyController + CollectLogController）：
 *   GET  /collect/services                目录元数据（前端左侧树数据源）
 *   POST /collect/tasks/{facet}/{name}    建任务，立即返回 {task_id, total}
 *   GET  /collect/tasks/{task_id}         轮询进度（Redis，Java 透传）
 *   GET  /collect/tasks?limit=            最近任务（Redis capped list，Java 透传）
 *   GET  /collect/logs?...                历史审计（Java 查 PG collect_logs）
 *   GET  /collect/query/{name}            实时查询 service.get()（仅 supports_query=true）
 */

// ═══════════════════════════════════════════════════════════════════════════
//  Service — 已注册的采集服务（统一 task / fetcher / catalog）
// ═══════════════════════════════════════════════════════════════════════════

/** Service 元数据（GET /collect/services 列表项） */
export interface ServiceItem {
  /** ★ service 名（= collector 的 name 属性）：日志关联键 + 目录唯一键 */
  name: string
  /** ★ 五数据面（唯一分组维度）：tech / capital / fundamental / news / sentiment */
  facet: string
  /** ★ 中文显示名 */
  label: string
  description: string
  /** ★ 采集方式：incremental（增量）/ full（全量覆盖）/ realtime（实时直查，不入库） */
  strategy: CollectStrategy
  /** ★ 是否有实时直查入口（与 strategy 正交，替代旧 kind='both' 的读语义） */
  queryable: boolean
  /** ★ 增量维度（full / realtime 为 null） */
  range: CollectRange | null
  /** ★ 全量覆盖的清理模式（前端据此决定文案与二次确认强度） */
  clear_mode: 'none' | 'domain'
  /**
   * ★ 实际的「步」粒度（进度分母的口径）：
   *   trade_day → 区间拆成 N 个交易日，每步一天（进度 = 已采天数 / 总天数）
   *   day       → 区间自理，单步完成
   *   null      → 非增量（full / realtime）
   * ⚠️ 与 `range.granularity` 的区别：`range.granularity` 是 service 的**声明**，
   *    `step_granularity` 是**实际**的拆步结果（有些 service 声明 day 但实现了展开钩子）。
   */
  step_granularity: 'day' | 'trade_day' | null
  rate_limit: [string, number, number] | null
  concurrency: number
  /** 实际 POST 路径 */
  path: string
  /** 实时查询路径（queryable=true 时才有） */
  query_path: string | null
}

/** ★ 采集方式 */
export type CollectStrategy = 'incremental' | 'full' | 'realtime'

/** ★ 增量维度（由 collector 的 RANGE 声明） */
export interface CollectRange {
  start_key: string
  end_key: string
  /** day = 区间自理（service 内部处理起止）；trade_day = 按交易日展开（collector 逐日调用） */
  granularity: 'day' | 'trade_day'
}

/** Service 列表响应（与后端 PageResult 口径一致：total / list / page / page_size） */
export interface ServiceListResponse {
  total: number
  page: number
  page_size: number
  list: ServiceItem[]
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
        _cachedServices = res.list || []
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
  cacheServices(res.list || [])
  return res.list || []
}

/** 采集启动 payload（strategy 决定前端表单形态与写入语义） */
export interface CollectStartPayload {
  /** ★ 采集方式：incremental（增量）/ full（全量覆盖） */
  strategy: 'incremental' | 'full'
  /** 采集参数：增量只带 {start_date, end_date}；全量通常为空对象 */
  params: Record<string, any>
  /** 编排来源：manual（手动）/ retry（重跑） */
  trigger_source?: 'manual' | 'retry'
  /** 重跑时指向原任务（审计用，写入 collect_logs.parent_task_id） */
  parent_task_id?: string
}

/** 采集执行结果（后端 svc.collect() 返回 CollectResult.to_dict()，已下线，仅兼容旧类型） */
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

/** 后台任务创建返回（POST /collect/tasks/{facet}/{name}） */
export interface CollectTaskCreated {
  task_id: string
  status: string
  total: number
  /** ★ 本次执行的采集方式 */
  strategy?: CollectStrategy
}

/** 任务进度（GET /collect/tasks/{task_id}，Java 透传 Redis） */
export interface CollectTaskState {
  task_id: string
  facet: string
  name: string
  /** ★ 采集方式（与 kind 同义） */
  strategy?: CollectStrategy
  kind: string
  mode: string
  params: Record<string, any>
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled' | string
  total: number
  done: number
  success: number
  fail: number
  /** 跳过的步数（如非交易日无数据） */
  skip: number
  saved_total: number
  progress: number
  message: string
  created_at: string
  started_at: string
  updated_at: string
  finished_at: string
}

/** 手动建任务（POST /collect/tasks/{facet}/{name}，立即返回 task_id） */
export const createCollectTask = async (
  name: string,
  payload: CollectStartPayload | Record<string, any> = { strategy: 'incremental', params: {} },
): Promise<CollectTaskCreated> => {
  if (!_cachedServices || _cachedServices.length === 0) {
    await waitForServices()
  }
  const svc = findServiceByName(name)
  const facet = svc?.facet || '_unknown'
  const body: CollectStartPayload = 'params' in (payload as any) && 'strategy' in (payload as any)
    ? (payload as CollectStartPayload)
    : { strategy: 'incremental', params: (payload as Record<string, any>) || {} }
  return http
    .post<ApiResponse<CollectTaskCreated>>(`/collect/tasks/${facet}/${name}`, body)
    .then(unwrap)
}

/** 轮询任务进度（GET /collect/tasks/{task_id}） */
export const getCollectTask = (taskId: string): Promise<CollectTaskState> =>
  http.get<ApiResponse<CollectTaskState>>(`/collect/tasks/${taskId}`).then(unwrap)

/** 最近任务列表（GET /collect/tasks?limit=） */
export const listCollectTasks = (limit = 20): Promise<{ total: number; list: CollectTaskState[] }> =>
  http.get<ApiResponse<{ total: number; list: CollectTaskState[] }>>('/collect/tasks', { params: { limit } }).then(unwrap)

/** 中断采集任务（POST /collect/tasks/{task_id}/cancel） */
export const cancelCollectTask = (taskId: string): Promise<{ task_id: string; status: string }> =>
  http.post<ApiResponse<{ task_id: string; status: string }>>(`/collect/tasks/${taskId}/cancel`).then(unwrap)

/**
 * 采集历史（GET /collect/logs，Java 查 PG collect_logs）
 *
 * ⚠️ ★ 字段名是 **snake_case**，不是 camelCase！
 * 后端全局 `spring.jackson.property-naming-strategy: SNAKE_CASE`
 * （见 application.yml）→ Java 的 `taskId` 序列化成 `task_id`。
 * 本文件之前写成 camelCase（taskId/createdAt/...），
 * 与真实响应不符 → 前端静默拿到 undefined（TS 不会报错）。
 * 全项目其他 Java 接口（pools / auth / stock-info / concept-board…）
 * 的 TS 类型一律是 snake_case，此处与之保持一致。
 */
export interface CollectLogRow {
  task_id: string
  facet: string
  name: string
  kind: string
  mode: string
  trigger_source: string
  trigger_user: string | null
  params_json: Record<string, any>
  range_start: string | null
  range_end: string | null
  status: string
  progress: number
  /** 计数器口径：total/done/success/fail/skip 是「步数」，saved_total 是「行数」 */
  total: number
  done: number
  success: number
  fail: number
  skip: number
  saved_total: number
  message: string
  error: string | null
  detail: Record<string, any>[] | null
  /** ISO-8601 带时区（如 2026-10-29T14:43:27.926076Z） */
  created_at: string | null
  started_at: string | null
  finished_at: string | null
  updated_at: string | null
  duration_ms: number | null
  cancel_requested: boolean
  cancelled_at: string | null
  parent_task_id: string | null
}

/**
 * 查询参数走 query string，**不受** Jackson SNAKE_CASE 影响 →
 * 参数名必须与 Java `CollectLogQuery` 字段名一致（`pageSize` 而非 `page_size`）。
 *
 * ⚠️ 响应体则**是** snake_case（全局 SNAKE_CASE 策略）→ 返回字段是 `page_size`。
 */
export const listCollectLogs = (params: {
  facet?: string
  name?: string
  status?: string
  triggerSource?: string
  /** ★ 按采集方式筛选：incremental / full */
  kind?: string
  startDate?: string
  endDate?: string
  hasFail?: boolean
  page?: number
  pageSize?: number
} = {}): Promise<{ total: number; list: CollectLogRow[]; page: number; page_size: number }> =>
  http.get<ApiResponse<{ total: number; list: CollectLogRow[]; page: number; page_size: number }>>(
    '/collect/logs', { params },
  ).then(unwrap)

/**
 * 手动触发一次 service（兼容旧名：内部已转后台任务，不再同步等待结果）。
 * @deprecated 用 createCollectTask + 轮询 getCollectTask 代替。
 */
export const runService = async (
  name: string,
  payload: CollectStartPayload | Record<string, any> = { strategy: 'incremental', params: {} },
): Promise<CollectRunResult> => {
  const created = await createCollectTask(name, payload)
  // 兼容旧调用：轮询到终态后拼成 CollectRunResult
  const final = await pollCollectTask(created.task_id)
  return {
    total: final.total,
    success: final.success,
    fail: final.fail,
    skip: 0,
    saved: final.saved_total,
    message: final.message,
  }
}

/** 轮询任务到终态（done/failed），默认 1s 一次、最多 30 分钟 */
export const pollCollectTask = async (
  taskId: string,
  opts: { intervalMs?: number; timeoutMs?: number; onTick?: (s: CollectTaskState) => void } = {},
): Promise<CollectTaskState> => {
  const intervalMs = opts.intervalMs ?? 1000
  const timeoutMs = opts.timeoutMs ?? 30 * 60 * 1000
  const started = Date.now()
  for (;;) {
    const state = await getCollectTask(taskId)
    opts.onTick?.(state)
    if (state.status === 'done' || state.status === 'failed') return state
    if (Date.now() - started > timeoutMs) throw new Error(`任务 ${taskId} 轮询超时`)
    await new Promise((r) => setTimeout(r, intervalMs))
  }
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
//  聚合视图：Catalog — 由 services 列表按 facet 单级聚合
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

/** 单个 service 在 UI 目录树中的视图（由 ServiceItem 派生） */
export interface CatalogItem {
  service_name: string
  label: string
  description: string
  /** ★ 是否有实时直查入口 */
  queryable: boolean
  /** ★ 采集方式 */
  strategy: CollectStrategy
  /** ★ 增量维度（full / realtime 为 null） */
  range: CollectRange | null
  /** ★ 全量覆盖的清理模式 */
  clear_mode: 'none' | 'domain'
  /** ★ 实际的拆步粒度（进度分母口径；非增量为 null） */
  step_granularity: 'day' | 'trade_day' | null
  /** facet（tech/capital/...） */
  facet: string
  /** 实际 POST 路径（去掉 /api 前缀，http baseURL 已带） */
  path: string
  /** 实时查询路径 */
  query_path: string | null
  /** 后端限速 [source, max_count, window_seconds] */
  rate_limit: [string, number, number] | null
}

/** 目录树分组：五数据面 → service 列表（**只有一级分组**） */
export interface CatalogGroup {
  facet: string
  label: string
  icon: string
  sort_order: number
  items: CatalogItem[]
}

export interface Catalog {
  items: CatalogGroup[]
}

/**
 * 把 service 列表聚合成 facet 单级树。
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
        items: [],
      })
    }
    groups.get(facetKey)!.items.push({
      service_name: s.name,
      label: s.label || s.name,
      description: s.description || '',
      queryable: s.queryable,
      strategy: s.strategy,
      range: s.range ?? null,
      clear_mode: s.clear_mode || 'none',
      step_granularity: s.step_granularity ?? null,
      facet: s.facet,
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
