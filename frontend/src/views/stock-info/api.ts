// Stock Info API - 股票基础信息 + K 线
import http, { unwrap } from '@/common/utils/http'

// ═══════════════════════════════════════════════════════
//  类型定义
// ═══════════════════════════════════════════════════════

/** 分页响应 */
export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

/** 股票信息（stock_basic / stock_info） */
export interface StockInfo {
  symbol:    string   // 股票代码  000001
  ts_code:   string   // TS 统一代码  000001.SZ
  name:      string   // 股票名称
  area:      string   // 地域
  industry:  string   // 行业
  market:    string   // 市场类型（主板/科创板/创业板/北交所）
  exchange:  string   // 交易所（SSE/SZSE/BSE）
  list_date: string   // 上市日期  YYYYMMDD
  delist_date: string // 退市日期
  is_hs:     string   // 沪深港通（N/H/S）
  act_name:  string   // 实控人名称
  act_ent_type: string // 实控人企业性质
  enname:    string   // 英文名
  cnspell:   string   // 拼音缩写
  list_status: string // 上市状态（L/D/P/UN）
}

/** 股票查询项（GET /stocks/ 响应，含富字段 + K 线统计） */
export interface StockListItem {
  // 基础信息
  symbol:        string
  ts_code:       string | null
  name:          string | null
  area:          string | null
  industry:      string | null
  market:        string | null
  exchange:      string | null
  list_date:     string | null  // YYYYMMDD
  list_status:   string | null
  is_hs:         string | null
  // K 线统计
  record_count:  number
  kline_start:   string | null
  kline_end:     string | null
}

/** K 线数据 */
export interface Kline {
  date:       string
  open:       number
  high:       number
  low:        number
  close:      number
  volume:     number   // 成交量（手）
  amount:     number   // 成交额（元）
  change_pct: number | null // 涨跌幅（%）
}

/** K 线统计 */
export interface KlineStats {
  count:         number
  latest_close:  number
  latest_volume: number
}

/** 采集结果 */
export interface CollectResult {
  symbol:      string
  name:        string
  saved_count: number
  total_count: number
  message:     string
}

/** 股票元数据（枚举值） */
export interface StockMeta {
  industries: string[]
  markets:    string[]
  exchanges:  string[]
}

/** 查询参数 */
export interface StockQueryParams {
  q?:           string
  industry?:    string
  market?:      string
  exchange?:    string
  is_hs?:       string
  list_status?: string
  page?:        number
  page_size?:   number
}

// ═══════════════════════════════════════════════════════
//  API
// ═══════════════════════════════════════════════════════

// ── 股票基础信息 ─────────────────────────────────────────────

/** GET /stocks/  查询股票列表（支持搜索/筛选/分页） */
export const queryStocks = (params: StockQueryParams = {}) =>
  http.get<PaginatedResponse<StockInfo>>('/stocks/', { params }).then(unwrap)

/** GET /stocks/meta  获取行业/市场/交易所枚举值 */
export const getStockMeta = (): Promise<StockMeta> =>
  http.get<StockMeta>('/stocks/meta').then(unwrap)

/** POST /stocks/sync  触发全量同步 */
export const syncStocks = (): Promise<{ synced_count: number }> =>
  http.post('/stocks/sync').then(unwrap)

// ── 已采集股票（kline 关联视图） ─────────────────────────────

/** GET /stocks/  股票列表（含 K 线统计） */
export const listStocks = (params?: { industry?: string; market?: string }) =>
  http.get<PaginatedResponse<StockListItem>>('/stocks/', { params }).then(unwrap)

/** GET /stocks/{symbol}  单个股票详情 */
export const getStock = (symbol: string) =>
  http.get<StockListItem>(`/stocks/${symbol}`).then(unwrap)

/** DELETE /stocks/{symbol}  删除股票 */
export const deleteStock = (symbol: string) =>
  http.delete(`/stocks/${symbol}`).then(unwrap)

// ── K 线采集 & 查询 ─────────────────────────────────────────

/** POST /klines/collect  采集 K 线 */
export const collectKlines = (body: { symbol: string; days?: number }) =>
  http.post<CollectResult>('/klines/collect', body).then(unwrap)

/** POST /klines/collect/batch  批量采集 */
export const collectBatch = (symbols: string[], days = 30) =>
  http.post<Record<string, CollectResult>>('/klines/collect/batch', null, {
    params: symbols.flatMap((s) => ['symbols', s]),
    paramsSerializer: (ps) =>
      ps
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&'),
  }).then(unwrap)

/** GET /klines/{symbol}  查询 K 线列表 */
export const getKlines = (
  symbol: string,
  params: { start_date?: string; end_date?: string; limit?: number; order_desc?: boolean } = {}
) =>
  http.get<PaginatedResponse<Kline>>(`/klines/${symbol}`, { params }).then(unwrap)

/** GET /klines/{symbol}/stats  K 线统计 */
export const getKlineStats = (symbol: string): Promise<KlineStats> =>
  http.get<KlineStats>(`/klines/${symbol}/stats`).then(unwrap)

/** DELETE /klines/{symbol}/{trade_date}  删除单条 K 线 */
export const deleteKline = (symbol: string, tradeDate: string) =>
  http.delete(`/klines/${symbol}/${tradeDate}`).then(unwrap)
