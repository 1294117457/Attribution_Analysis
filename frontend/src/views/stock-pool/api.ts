// Stock Pool API - 操作池
import http, { unwrap } from '@/common/utils/http'

// ═══════════════════════════════════════════════════════
//  类型定义
// ═══════════════════════════════════════════════════════

export type PoolType = 'watchlist' | 'industry' | 'strategy' | 'custom'

export type OperationType = 'kline_collect' | 'news_fetch' | 'factor_calc'

export type OperationStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'partial'
  | 'failed'
  | 'cancelled'

/** 池成员 */
export interface PoolMember {
  symbol: string
  name?: string | null
  industry?: string | null
  market?: string | null
  exchange?: string | null
  memo?: string | null
  sort_order: number
  added_at?: string | null
  is_valid: boolean
}

/** 操作池视图对象 */
export interface Pool {
  id: number
  name: string
  pool_type: PoolType
  description?: string | null
  color?: string | null
  icon?: string | null
  sort_order: number
  is_default: boolean
  is_archived: boolean
  member_count: number
  created_at?: string | null
  updated_at?: string | null
}

/** 池详情（含成员） */
export interface PoolDetail extends Pool {
  members: PoolMember[]
}

/** 操作进度 */
export interface OperationProgress {
  done: number
  total: number
  failed: number
}

/** 操作记录详情 */
export interface OperationDetailItem {
  symbol: string
  status: string
  count?: number | null
  message?: string | null
}

/** 操作结果汇总 */
export interface OperationResult {
  total: number
  saved: number
  skipped: number
  failed: number
  details?: OperationDetailItem[]
}

/** 池操作记录 */
export interface PoolOperation {
  id: number
  pool_id?: number | null
  operation_type: OperationType
  status: OperationStatus
  params: Record<string, unknown>
  result_summary?: OperationResult | null
  progress: OperationProgress
  error_message?: string | null
  started_at?: string | null
  finished_at?: string | null
  created_at?: string | null
}

// ── 请求类型 ──────────────────────────────────────────────

export interface PoolCreateRequest {
  name: string
  pool_type?: PoolType
  description?: string
  color?: string
  icon?: string
}

export interface PoolUpdateRequest {
  name?: string
  description?: string
  color?: string
  icon?: string
  sort_order?: number
}

export interface PoolAddMembersRequest {
  symbols: string[]
  validate_exists?: boolean
}

export interface PoolRemoveMembersRequest {
  symbols: string[]
}

export interface PoolUpdateMemberMemoRequest {
  symbol: string
  memo: string
}

export interface PoolKlineCollectRequest {
  operation_type: 'kline_collect'
  days: number
}

// ── 响应类型 ──────────────────────────────────────────────

export interface PoolListResponse {
  total: number
  /** 当前页数据列表（与后端 PageVO.dataList 对齐） */
  dataList: Pool[]
  /** 兼容旧字段名 */
  items?: Pool[]
}

export interface PoolMemberListResponse {
  pool_id: number
  total: number
  dataList: PoolMember[]
  items?: PoolMember[]
}

export interface PoolAddMembersResponse {
  pool_id: number
  added: string[]
  skipped: string[]
  total_added: number
  total_skipped: number
}

export interface PoolPoolsBySymbolResponse {
  symbol: string
  pools: Pool[]
  total: number
}

export interface PoolOperationListResponse {
  pool_id: number
  total: number
  items: PoolOperation[]
}

export interface PoolOperationCreateResponse {
  operation_id: number
  pool_id: number
  operation_type: OperationType
  status: OperationStatus
  total: number
  message: string
}

export interface OperationProgressResponse {
  done: number
  total: number
  failed: number
}

// ═══════════════════════════════════════════════════════
//  API
// ═══════════════════════════════════════════════════════

// ── 池管理 ────────────────────────────────────────────────

export const createPool = (data: PoolCreateRequest) =>
  http.post<Pool>('/pools', data).then(unwrap)

export const listPools = (params?: {
  include_archived?: boolean
  limit?: number
  offset?: number
}) =>
  http
    .get<PoolListResponse>('/pools', {
      params,
      paramsSerializer: {
        indexes: null,
      },
    })
    .then(unwrap)

export const getPool = (poolId: number) =>
  http.get<PoolDetail>(`/pools/${poolId}`).then(unwrap)

export const updatePool = (poolId: number, data: PoolUpdateRequest) =>
  http.patch<Pool>(`/pools/${poolId}`, data).then(unwrap)

export const deletePool = (poolId: number) =>
  http.delete(`/pools/${poolId}`).then(unwrap)

// ── 成员管理 ──────────────────────────────────────────────

export const addMembers = (poolId: number, data: PoolAddMembersRequest) => {
  if (typeof poolId !== 'number' || Number.isNaN(poolId)) {
    const display = typeof poolId === 'number' ? String(poolId) : typeof poolId
    throw new Error(`[addMembers API] poolId 必须是有效数字，实际类型: ${display}`)
  }
  return http.post<PoolAddMembersResponse>(`/pools/${poolId}/members`, data).then(unwrap)
}

export const removeMembers = (poolId: number, symbols: string[]) =>
  http
    .delete<{ removed_count: number }>(`/pools/${poolId}/members`, {
      data: { symbols },
    })
    .then(unwrap)

export const listMembers = (
  poolId: number,
  params?: { limit?: number; offset?: number },
) =>
  http.get<PoolMemberListResponse>(`/pools/${poolId}/members`, { params }).then(unwrap)

export const updateMemberMemo = (
  poolId: number,
  symbol: string,
  memo: string,
) =>
  http
    .patch<PoolMember>(`/pools/${poolId}/members/${symbol}`, { memo })
    .then(unwrap)

export const removeMember = (poolId: number, symbol: string) =>
  http.delete(`/pools/${poolId}/members/${symbol}`).then(unwrap)

// ── 反向查询 ──────────────────────────────────────────────

export const findPoolsBySymbol = (symbol: string) =>
  http
    .get<PoolPoolsBySymbolResponse>(`/pools/by-symbol/${symbol}`)
    .then(unwrap)

// ── 池级操作 ──────────────────────────────────────────────

export const createOperation = (
  poolId: number,
  data: PoolKlineCollectRequest,
) =>
  http
    .post<PoolOperationCreateResponse>(
      `/pools/${poolId}/operations`,
      { pool_id: poolId, ...data },
    )
    .then(unwrap)

export const listOperations = (
  poolId: number,
  params?: { limit?: number; offset?: number },
) =>
  http
    .get<PoolOperationListResponse>(`/pools/${poolId}/operations`, { params })
    .then(unwrap)

export const getOperation = (opId: number) =>
  http.get<PoolOperation>(`/operations/${opId}`).then(unwrap)

export const getOperationProgress = (opId: number) =>
  http
    .get<OperationProgressResponse>(`/operations/${opId}/progress`)
    .then(unwrap)

export const cancelOperation = (opId: number) =>
  http
    .post<{ id: number; status: string }>(
      `/operations/${opId}/cancel`,
      {},
    )
    .then(unwrap)
