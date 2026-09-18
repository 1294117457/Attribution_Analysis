import http, { unwrap } from '@/common/utils/http'

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

export const createTask = (body: { task_type: string; params?: Record<string, any> }) =>
  http.post('/collect/tasks', body).then(unwrap)

export const listTasks = (params?: { task_type?: string; status?: string; page?: number; page_size?: number }) =>
  http.get('/collect/tasks', { params }).then(unwrap)

export const getTaskProgress = (taskId: number) =>
  http.get(`/collect/tasks/${taskId}/progress`).then(unwrap)

export const cancelTask = (taskId: number, force = false) =>
  http.post(`/collect/tasks/${taskId}/cancel`, null, { params: { force } }).then(unwrap)
