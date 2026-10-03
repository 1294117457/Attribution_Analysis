// 概念大盘 — API + VO（01 概念大盘页 v2 纯增量方案）
//
// 配套设计文档：docs/dev/step3/02发散探索/01-概念大盘页.md §4.2
//
// 本文件为纯新增，不动任何已有 API。

import http, { unwrap } from '@/common/utils/http'

// ── VO 类型（与后端 1:1 对齐）──

export interface ConceptBoardItem {
  concept_id: number
  index_code: string
  name: string
  source: string
  concept_type: string
  concept_type_label: string
  stock_count: number
  description: string | null
  price: number | null
  prev_close: number | null
  change: number | null
  pct_change: number | null
  color: 'up' | 'down' | 'flat'
  trade_time: string | null
  captured_at: string | null
  stale: boolean
}

export interface ConceptMemberItem {
  symbol: string
  name: string | null
  industry: string | null
  market: string | null
  latest_close: number | null
  total_mv: number | null
  pe_ttm: number | null
  pct_change: number | null
  color: 'up' | 'down' | 'flat'
  pools: {
    pool_id: number
    name: string
    pool_type: string
    joined_at: string | null
  }[]
}

export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  pages: number
  items: T[]
}

// ── API ──
// v2 矫正：路径用 /concept-board 而非 /board（避免与后端 /{name} 通配符冲突）

export const getConceptBoard = (params: {
  type_filter?: 'all' | 'industry' | 'theme' | 'style' | 'region' | 'event' | 'other'
  sort_by?: 'pct_change' | 'stock_count' | 'name'
  order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}) =>
  http
    .get<PaginatedResponse<ConceptBoardItem>>('/concepts/concept-board', { params })
    .then(unwrap)

export const getConceptBoardMembers = (params: {
  concept_id: number
  sort_by?: 'pct_change' | 'latest_close' | 'total_mv' | 'name'
  order?: 'asc' | 'desc'
  with_pools?: boolean
  page?: number
  page_size?: number
}) =>
  http
    .get<PaginatedResponse<ConceptMemberItem>>('/concepts/concept-board/members', {
      params,
    })
    .then(unwrap)

// ── 概念日 K + 实时 ──

export interface ConceptKlineBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number | null
  change_pct: number | null
  color: 'up' | 'down' | 'flat'
}

export interface ConceptRealtime {
  index_code: string
  concept_name: string
  price: number | null
  prev_close: number | null
  change: number | null
  pct_change: number | null
  color: 'up' | 'down' | 'flat'
  trade_time: string | null
  captured_at: string | null
  stale: boolean
}

export interface ConceptKlineMeta {
  concept_id: number | null
  index_code: string
  name: string
  concept_type: string | null
  concept_type_label?: string | null
  stock_count: number | null
  description: string | null
  source: string | null
}

export interface ConceptKlineResponse {
  kline: ConceptKlineBar[]
  realtime: ConceptRealtime | null
  meta: ConceptKlineMeta | null
  data_range: {
    start: string | null
    end: string | null
    bars_count: number
  }
}

export const getConceptKline = (params: {
  index_code: string
  days?: number
  start_date?: string
  end_date?: string
}) =>
  http
    .get<ConceptKlineResponse>(`/concepts/${params.index_code}/kline`, {
      params: {
        days: params.days ?? 250,
        start_date: params.start_date,
        end_date: params.end_date,
      },
    })
    .then(unwrap)
