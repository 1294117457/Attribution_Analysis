import http, { unwrap } from '@/common/utils/http'

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
  http.get<{ items: FacetGroup[] }>('/collect/catalog').then(unwrap)

// ───────────────────────────────────────────────────────────────────────────
// 任务 CRUD（既有 — 保持不变）
// ───────────────────────────────────────────────────────────────────────────

export const createTask = (body: { task_type: string; params?: Record<string, any> }) =>
  http.post('/collect/tasks', body).then(unwrap)

export const listTasks = (params?: { task_type?: string; status?: string; page?: number; page_size?: number }) =>
  http.get('/collect/tasks', { params }).then(unwrap)

export const getTaskProgress = (taskId: number) =>
  http.get(`/collect/tasks/${taskId}/progress`).then(unwrap)

export const cancelTask = (taskId: number, force = false) =>
  http.post(`/collect/tasks/${taskId}/cancel`, null, { params: { force } }).then(unwrap)