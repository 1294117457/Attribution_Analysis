// Market API - 市场全局视图 API（开发指南 §8）
import http, { unwrap } from '@/common/utils/http'
import type {
  TopListItem,
  SectorDailyItem,
  IndexMemberItem,
} from '@/views/stock-info/api'

// 重导出共享类型，供本目录组件 import
export type { TopListItem, SectorDailyItem, IndexMemberItem }

// ═══════════════════════════════════════════════════════════════
//  市场全局 API
// ═══════════════════════════════════════════════════════════════

/** GET /top-lists/  今日龙虎榜 */
export const listTopLists = (params: {
  trade_date?: string
  start_date?: string
  end_date?: string
}) =>
  http
    .get<{ total: number; items: TopListItem[] }>('/top-lists/', { params })
    .then(unwrap)

/** GET /sector-dailys/  板块日行情 */
export const listSectorDailys = (params: {
  sector_type?: string
  trade_date?: string
  limit?: number
}) =>
  http
    .get<{ total: number; items: SectorDailyItem[] }>('/sector-dailys/', { params })
    .then(unwrap)

/** GET /index-members/  板块成分 */
export const listIndexMembers = (params: {
  sector_type: string
  sector_code: string
}) =>
  http
    .get<{ total: number; items: IndexMemberItem[] }>('/index-members/', { params })
    .then(unwrap)
