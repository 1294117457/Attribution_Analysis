import http, { unwrap } from '@/common/utils/http'

// ═══════════════════════════════════════════════════════════════
//  概念采集配套 — 配套后端 infrastructure/tasks/collect/concept.py
//  配套设计文档：
//    docs/dev/07collect-class/02-concept-collect-integration.md
//    docs/dev/06gainian/01-domain-design.md
// ═══════════════════════════════════════════════════════════════

/** 概念数据源 */
export type ConceptSource = 'em' | 'ths'

export const CONCEPT_SOURCE_OPTIONS: { label: string; value: ConceptSource }[] = [
  { label: '东方财富 (em)', value: 'em' },
  { label: '同花顺 (ths)', value: 'ths' },
]

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

/** 概念同步参数（POST /collect/tasks {task_type:'concept', params:...}） */
export interface ConceptSyncParams {
  /** 数据源：em 默认 / ths 预留 */
  source?: ConceptSource
  /** 是否强制重传（业务上当前对所有概念都 upsert，此参数作为日志/审计保留） */
  force_resync?: boolean
}

export const createTask = (body: { task_type: string; params?: Record<string, any> }) =>
  http.post('/collect/tasks', body).then(unwrap)

export const listTasks = (params?: { task_type?: string; status?: string; page?: number; page_size?: number }) =>
  http.get('/collect/tasks', { params }).then(unwrap)

export const getTaskProgress = (taskId: number) =>
  http.get(`/collect/tasks/${taskId}/progress`).then(unwrap)

export const cancelTask = (taskId: number, force = false) =>
  http.post(`/collect/tasks/${taskId}/cancel`, null, { params: { force } }).then(unwrap)
