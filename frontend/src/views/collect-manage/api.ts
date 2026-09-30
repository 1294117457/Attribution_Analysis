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
  /** 同一次任务组执行的各项共享（= 该次第一项的 task_id） */
  group_run_id: number | null
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
  group_run_id?: number
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

// ───────────────────────────────────────────────────────────────────────────
// 采集方案（每个 task_type 一条：默认参数 + 定时 + 启停）
//   参数优先级：手动传入 > 方案 params > default_params
// ───────────────────────────────────────────────────────────────────────────

export interface CollectPlan {
  task_type: string
  label: string
  status: 'ready' | 'planned'
  /** false = 尚未保存过方案，字段为默认值 */
  configured: boolean
  enabled: boolean
  cron: string | null
  params: Record<string, any>
  trading_day_only: boolean
  default_params: Record<string, any>
  last_run_at: string | null
  last_task_id: number | null
  next_run_at: string | null
  updated_at: string | null
}

export interface CollectPlanSave {
  enabled: boolean
  cron: string | null
  params: Record<string, any>
  trading_day_only: boolean
}

export const listPlans = () => http.get<ApiResponse<CollectPlan[]>>('/collect/plans').then(unwrap)

export const getPlan = (taskType: string) =>
  http.get<ApiResponse<CollectPlan>>(`/collect/plans/${taskType}`).then(unwrap)

export const savePlan = (taskType: string, body: CollectPlanSave) =>
  http.put<ApiResponse<CollectPlan>>(`/collect/plans/${taskType}`, body).then(unwrap)

/** 按方案参数立即执行一次（返回同 createTask：成功有 task_id，冲突只有 message） */
export const runPlan = (taskType: string) =>
  http.post<ApiResponse<CreateTaskResult>>(`/collect/plans/${taskType}/run`).then(unwrap)

// ───────────────────────────────────────────────────────────────────────────
// 采集任务组（按 items 顺序串行执行多个接口）
// ───────────────────────────────────────────────────────────────────────────

export interface CollectGroupItem {
  task_type: string
  params: Record<string, any>
}

export interface CollectGroupSave {
  name: string
  items: CollectGroupItem[]
  enabled: boolean
  cron: string | null
  trading_day_only: boolean
  stop_on_fail: boolean
}

export interface CollectGroup extends CollectGroupSave {
  id: number
  last_run_at: string | null
  last_group_run_id: number | null
  next_run_at: string | null
  created_at: string | null
  updated_at: string | null
}

export const listGroups = () => http.get<ApiResponse<CollectGroup[]>>('/collect/groups').then(unwrap)

export const createGroup = (body: CollectGroupSave) =>
  http.post<ApiResponse<CollectGroup>>('/collect/groups', body).then(unwrap)

export const updateGroup = (id: number, body: CollectGroupSave) =>
  http.put<ApiResponse<CollectGroup>>(`/collect/groups/${id}`, body).then(unwrap)

export const deleteGroup = (id: number) => http.delete(`/collect/groups/${id}`).then(unwrap)

export const runGroup = (id: number) =>
  http.post<ApiResponse<CollectGroup & { message: string }>>(`/collect/groups/${id}/run`).then(unwrap)

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

// ───────────────────────────────────────────────────────────────────────────
// cron 预设（5 段：分 时 日 月 周；时区 Asia/Shanghai）
// ───────────────────────────────────────────────────────────────────────────

export const CRON_PRESETS: { label: string; value: string }[] = [
  { label: '工作日 09:00', value: '0 9 * * 1-5' },
  { label: '工作日 15:30（收盘后）', value: '30 15 * * 1-5' },
  { label: '工作日 17:00', value: '0 17 * * 1-5' },
  { label: '工作日 20:00', value: '0 20 * * 1-5' },
  { label: '交易时段每 30 分钟', value: '*/30 9-15 * * 1-5' },
  { label: '每周六 02:00', value: '0 2 * * 6' },
]

export function cronLabel(cron: string | null | undefined): string {
  if (!cron) return '仅手动'
  return CRON_PRESETS.find((p) => p.value === cron)?.label ?? cron
}