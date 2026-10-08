/**
 * Backup API — 配套后端 route/api/v1/backup.py
 * 12 个端点封装 + 通用类型
 */
import http, { unwrap } from '@/common/utils/http'

// ── 类型定义 ──────────────────────────────────────────────
export type BackupType = 'full' | 'schema' | 'data'
export type BackupScope = 'all' | 'partial'
export type BackupStatus = 'pending' | 'running' | 'success' | 'failed' | 'interrupted'
export type RestoreMode = 'cover' | 'upsert'
export type RestoreSourceType = 'history' | 'upload' | 'file'

export interface CreateBackupRequest {
  backup_type: BackupType
  scope: BackupScope
  tables?: string[]
  output_dir?: string | null
  name?: string | null
}

export interface RestoreRequest {
  source_type: RestoreSourceType
  source_backup_id?: number | null
  upload_id?: string | null
  source_path?: string | null
  restore_mode: RestoreMode
  confirm: boolean
}

export interface UpdateConfigRequest {
  default_output_dir?: string | null
  allowed_roots?: string[] | null
}

export interface BackupRecord {
  id: number
  name: string
  backup_type: BackupType
  scope: BackupScope
  tables: string[]
  tables_count: number
  output_dir: string
  file_path: string | null
  file_size: number | null
  row_count: number
  progress: number
  progress_msg: string
  status: BackupStatus
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_by: number
  created_at: string
}

export interface BackupListResponse {
  items: BackupRecord[]
  total: number
  page: number
  page_size: number
}

export interface RestoreRecord {
  id: number
  name: string
  source_type: 'file' | 'upload' | 'history'
  source_path: string
  source_backup_id: number | null
  restore_mode: RestoreMode
  tables: string[]
  tables_count: number
  pre_backup_id: number | null
  progress: number
  progress_msg: string
  status: 'pending' | 'running' | 'success' | 'failed'
  rows_inserted: number
  rows_skipped: number
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_by: number
  created_at: string
}

export interface TableInfo {
  name: string
  row_count: number
  size_mb: number
  category: 'system' | 'market' | 'financial' | 'concept' | 'business'
}

export interface BackupConfig {
  default_output_dir: string
  allowed_roots: string[]
  schema_version: number
  max_file_size: number
}

export interface UploadResponse {
  upload_id: string
  filename: string
  size: number
  header: Record<string, string>
}

// ── API 调用 ──────────────────────────────────────────────
const BASE = '/backups'

export const createBackup = (data: CreateBackupRequest) =>
  http.post(BASE, data).then(unwrap<{ id: number }>)

export const listBackups = (params: {
  page?: number
  page_size?: number
  status?: BackupStatus
}) =>
  http.get(BASE, { params }).then(unwrap<BackupListResponse>)

export const getBackup = (id: number) =>
  http.get(`${BASE}/${id}`).then(unwrap<BackupRecord>)

export const deleteBackup = (id: number) =>
  http.delete(`${BASE}/${id}`).then(unwrap<null>)

/**
 * 下载 .sql（带 Authorization Header → 通过 http.get blob 方式）
 * 普通 window.open(url) 会丢失 token → 401
 */
export async function downloadBackup(id: number, filename: string): Promise<void> {
  const { default: http } = await import('@/common/utils/http')
  const res = await http.get(`${BASE}/${id}/download`, { responseType: 'blob' })
  const blobUrl = URL.createObjectURL(new Blob([res.data]))
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(blobUrl)
}

/** 直接拿下载 URL（用于已签发 CDN 等场景；本项目不适用） */
export const getDownloadUrl = (id: number) =>
  `${import.meta.env.VITE_API_BASE || ''}/api/v1${BASE}/${id}/download`

export const listTables = () =>
  http.get(`${BASE}/_tables`).then(unwrap<TableInfo[]>)

export const getBackupConfig = () =>
  http.get(`${BASE}/config`).then(unwrap<BackupConfig>)

export const updateBackupConfig = (data: UpdateConfigRequest) =>
  http.put(`${BASE}/config`, data).then(unwrap<null>)

export const restore = (data: RestoreRequest) =>
  http.post(`${BASE}/restore`, data).then(unwrap<{ id: number }>)

export const listRestores = (params: { page?: number; page_size?: number }) =>
  http.get(`${BASE}/restore`, { params }).then(unwrap<Omit<BackupListResponse, 'page' | 'page_size'> & { items: RestoreRecord[] }>)

export const getRestore = (id: number) =>
  http.get(`${BASE}/restore/${id}`).then(unwrap<RestoreRecord>)

export const uploadBackupFile = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return http
    .post(`${BASE}/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then(unwrap<UploadResponse>)
}