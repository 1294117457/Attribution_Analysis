import http, { unwrap, type ApiResponse } from '@/common/utils/http'

// ═══════════════════════════════════════════════════════════════════════════
//  采集管理 API — 配套后端 infrastructure/adapter/scheduler/collect/
//  配套设计文档：
//    docs/dev/step2/02datamanage/01-采集管理四维重构方案.md
//    docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md
// ═══════════════════════════════════════════════════════════════════════════

export interface CollectTask {
  id: number
  task_type: string
  trigger_type: string
  params: Record<string, any> | null
  status: string
  total_count: number
  success_count: number
  fail_count: number
  skip_count: number
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  message: string | null
  /** 同一次采集方案执行的各项共享（= 该次第一项的 task_id） */
  plan_run_id: number | null
  created_at: string
}

export interface TaskProgress {
  total: number
  done: number
  success: number
  fail: number
  skip: number
  status: string
  current: string
  percent: number
}

// ───────────────────────────────────────────────────────────────────────────
// 四面分类目录树（PR2-PR3 新增）
// ───────────────────────────────────────────────────────────────────────────

export type FacetKey = 'tech' | 'capital' | 'fundamental' | 'news'

export interface TaskDef {
  task_type: string
  label: string
  description: string
  status: 'ready' | 'planned'
  default_params: Record<string, any>
  /** 支持按单元同步调用（业务复用 collect_one） */
  supports_run_one: boolean
  /** batch：采集入库（任务 / 方案 / 任务组）；realtime：按需查询 + Redis 缓存 */
  kind: 'batch' | 'realtime'
  /** 实时接口：数据源分组 ths / tdx */
  source?: string | null
  source_label?: string | null
  /** 实时接口：交易时段缓存秒数 */
  ttl_trading?: number | null
  /** 实时接口：业务调用方 */
  consumers?: string[]
}

export interface FacetGroup {
  facet: FacetKey
  label: string
  icon: string
  sort_order: number
  sub_groups: Record<string, TaskDef[]>
}

/** 拉取采集任务目录树 */
export const getCatalog = () =>
  http.get<ApiResponse<{ items: FacetGroup[] }>>('/collect/catalog').then(unwrap)

// ───────────────────────────────────────────────────────────────────────────
// 任务 CRUD（既有 — 保持不变）
// ───────────────────────────────────────────────────────────────────────────

/** 成功有 task_id；冲突 / 不支持的类型只有 message */
export interface CreateTaskResult {
  task_id?: number
  task_type?: string
  total_count?: number
  message?: string
}

export interface TaskPage {
  total: number
  page: number
  page_size: number
  items: CollectTask[]
}

export const createTask = (body: { task_type: string; params?: Record<string, any> }) =>
  http.post<ApiResponse<CreateTaskResult>>('/collect/tasks', body).then(unwrap)

export const listTasks = (params?: {
  task_type?: string
  status?: string
  plan_run_id?: number
  page?: number
  page_size?: number
}) => http.get<ApiResponse<TaskPage>>('/collect/tasks', { params }).then(unwrap)

export const getTaskProgress = (taskId: number) =>
  http.get<ApiResponse<TaskProgress>>(`/collect/tasks/${taskId}/progress`).then(unwrap)

export const cancelTask = (taskId: number, force = false) =>
  http
    .post<ApiResponse<{ message?: string; forced?: boolean }>>(`/collect/tasks/${taskId}/cancel`, null, {
      params: { force },
    })
    .then(unwrap)

/** 重跑失败 / 已取消任务（保留原 task_type + params，新开 task_id） */
export const retryTask = (taskId: number) =>
  http
    .post<ApiResponse<CreateTaskResult>>(`/collect/tasks/${taskId}/retry`)
    .then(unwrap)

// ───────────────────────────────────────────────────────────────────────────
// 采集接口元数据（代码的 DB 镜像；方案编排的接口选择器数据源）
// ───────────────────────────────────────────────────────────────────────────

export type FetcherKind = 'batch' | 'realtime'
export type FetcherStatus = 'ready' | 'planned' | 'orphan'

export interface CollectFetcher {
  task_type: string
  label: string
  facet: string
  sub_facet: string
  description: string
  kind: FetcherKind
  status: FetcherStatus
  default_params: Record<string, any>
  supports_run_one: boolean
  sort_order: number
}

export const listFetchers = () =>
  http.get<ApiResponse<CollectFetcher[]>>('/collect/fetchers').then(unwrap)

// ───────────────────────────────────────────────────────────────────────────
// 采集方案（触发配置 + 接口编排）
//   一个方案 = 若干个采集接口（M:N），按 items 顺序串行执行
//   参数优先级：手动传入 > 方案项 params > default_params
// ───────────────────────────────────────────────────────────────────────────

/** None = 仅手动（不注册定时 job） */
export type ScheduleType = 'time' | 'interval' | null

export interface CollectPlanItem {
  id: number
  task_type: string
  label: string
  params: Record<string, any>
  enabled: boolean
  sort_order: number
}

export interface CollectPlan {
  id: number
  name: string
  enabled: boolean
  schedule_type: ScheduleType
  times: string[]
  interval_seconds: number | null
  stop_on_fail: boolean
  items: CollectPlanItem[]
  last_run_at: string | null
  last_task_id: number | null
  next_run_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface CollectPlanItemSave {
  task_type: string
  params: Record<string, any>
  enabled: boolean
}

export interface CollectPlanSave {
  name: string
  enabled: boolean
  schedule_type: ScheduleType
  times: string[]
  interval_seconds: number | null
  stop_on_fail: boolean
  items: CollectPlanItemSave[]
}

export const listPlans = () => http.get<ApiResponse<CollectPlan[]>>('/collect/plans').then(unwrap)

export const getPlan = (planId: number) =>
  http.get<ApiResponse<CollectPlan>>(`/collect/plans/${planId}`).then(unwrap)

export const createPlan = (body: CollectPlanSave) =>
  http.post<ApiResponse<CollectPlan>>('/collect/plans', body).then(unwrap)

export const updatePlan = (planId: number, body: CollectPlanSave) =>
  http.put<ApiResponse<CollectPlan>>(`/collect/plans/${planId}`, body).then(unwrap)

export const deletePlan = (planId: number) =>
  http.delete<ApiResponse<null>>(`/collect/plans/${planId}`).then(unwrap)

/** 立即执行一次方案（后台按 items 顺序跑） */
export const runPlan = (planId: number) =>
  http.post<ApiResponse<CollectPlan & { message: string }>>(`/collect/plans/${planId}/run`).then(unwrap)

// ───────────────────────────────────────────────────────────────────────────
// 触发方式展示文案
// ───────────────────────────────────────────────────────────────────────────

/** 固定频率的秒数 → 人类可读（用于列表 / 卡片展示） */
export function formatInterval(seconds: number | null | undefined): string {
  if (!seconds || seconds <= 0) return '-'
  if (seconds < 60) return `${seconds} 秒`
  if (seconds < 3600) {
    const m = seconds / 60
    return Number.isInteger(m) ? `${m} 分钟` : `${m.toFixed(1)} 分钟`
  }
  const h = seconds / 3600
  return Number.isInteger(h) ? `${h} 小时` : `${h.toFixed(1)} 小时`
}

export function scheduleLabel(plan: Pick<CollectPlan, 'schedule_type' | 'times' | 'interval_seconds'>): string {
  if (!plan.schedule_type) return '仅手动'
  if (plan.schedule_type === 'time') {
    return plan.times.length > 0 ? `每日 ${plan.times.join(' / ')}` : '仅手动'
  }
  return `每 ${formatInterval(plan.interval_seconds)}`
}

// ───────────────────────────────────────────────────────────────────────────
// 实时接口（不建任务，结果只进 Redis；采集管理用于试查和看调用统计）
// ───────────────────────────────────────────────────────────────────────────

export interface RealtimeResult {
  data: any
  cached: boolean
  /** true：数据源失败，返回的是降级数据 */
  stale: boolean
  fetched_at: string | null
  latency_ms: number
  error: string | null
}

export interface RealtimeStats {
  date: string
  calls: number
  hits: number
  misses: number
  errors: number
  hit_rate: number | null
  avg_latency_ms: number | null
  last_error: string | null
  last_error_at: string | null
}

export const queryRealtime = (name: string, params: Record<string, any>) =>
  http.post<ApiResponse<RealtimeResult>>(`/collect/realtime/${name}/query`, params).then(unwrap)

export const getRealtimeStats = (name: string, days = 1) =>
  http
    .get<ApiResponse<RealtimeStats[]>>(`/collect/realtime/${name}/stats`, { params: { days } })
    .then(unwrap)