// Stock Info API - 股票基础信息 + K 线（含 17 个指标列）+ AI 归因分析
import http, { unwrap } from '@/common/utils/http'

// ═══════════════════════════════════════════════════════════════
//  类型定义
// ═══════════════════════════════════════════════════════════════

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
  latest_close: number | null  // 最新收盘价
  total_mv:  number | null     // 总市值（万元）
  pe_ttm:    number | null     // 市盈率TTM
}

/** 股票查询项（GET /stocks/ 响应，含富字段 + K 线统计） */
export interface StockListItem {
  symbol:        string
  ts_code:       string | null
  name:          string | null
  area:          string | null
  industry:      string | null
  market:        string | null
  exchange:      string | null
  list_date:     string | null
  list_status:   string | null
  is_hs:         string | null
  record_count:  number
  kline_start:   string | null
  kline_end:     string | null
}

/** K 线数据（含 17 个技术指标列 — 方案 A 展宽） */
export interface Kline {
  date:       string     // YYYY-MM-DD
  open:       number
  high:       number
  low:        number
  close:      number
  volume:     number     // 成交量（手）
  amount:     number     // 成交额（元）
  change_pct: number | null

  // ── 技术指标（来自 daily_klines 展宽列）────────────────
  // 均线
  ma5:  number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  // EMA
  ema12: number | null
  ema26: number | null
  // MACD
  macd_dif: number | null
  macd_dea: number | null
  macd_bar: number | null
  // RSI
  rsi6:  number | null
  rsi12: number | null
  rsi24: number | null
  // KDJ
  kdj_k: number | null
  kdj_d: number | null
  kdj_j: number | null
  // BOLL
  boll_up:  number | null
  boll_mid: number | null
  boll_dn:  number | null
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

// ═══════════════════════════════════════════════════════════════
//  🆕 AI 归因分析接口
// ═══════════════════════════════════════════════════════════════

/** 技术形态摘要（后端 SignalDetector 算好） */
export interface TechnicalSummary {
  latest_close: number
  pct_change_1d: number
  pct_change_30d: number

  ma_alignment: 'bullish' | 'bearish' | 'neutral'
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  ma5_above_ma20: boolean
  golden_cross_recent: boolean

  macd_status: 'golden_cross' | 'death_cross' | 'above_zero' | 'below_zero' | 'neutral'
  macd_dif: number
  macd_dea: number
  macd_bar: number

  rsi6: number
  rsi_status: 'overbought' | 'oversold' | 'neutral'

  kdj_k: number
  kdj_d: number
  kdj_j: number
  kdj_status: 'golden_cross' | 'death_cross' | 'overbought' | 'oversold' | 'neutral'

  boll_up: number | null
  boll_mid: number | null
  boll_dn: number | null
  boll_position: 'above_upper' | 'below_lower' | 'upper_half' | 'lower_half' | 'middle'

  signals: string[]    // ["MA 多头排列", "MACD 金叉", ...]
}

/** 所在池（简短信息） */
export interface PoolMembership {
  pool_id: number
  pool_name: string
  joined_at: string | null
}

/** 完整分析响应 */
export interface StockAnalysisResponse {
  stock: {
    symbol: string
    name: string
    industry: string | null
    market: string | null
  }
  summary: TechnicalSummary
  klines: Kline[]
  pools: PoolMembership[]
}

// ═══════════════════════════════════════════════════════════════
//  API
// ═══════════════════════════════════════════════════════════════

// ── 股票基础信息 ─────────────────────────────────────────────

/** GET /stocks/  查询股票列表 */
export const queryStocks = (params: StockQueryParams = {}) =>
  http.get<PaginatedResponse<StockInfo>>('/stocks/', { params }).then(unwrap)

/** GET /stocks/meta  获取行业/市场/交易所枚举值 */
export const getStockMeta = (): Promise<StockMeta> =>
  http.get<StockMeta>('/stocks/meta').then(unwrap)

/** POST /stocks/sync  触发全量同步 */
export const syncStocks = (): Promise<{ synced_count: number }> =>
  http.post('/stocks/sync').then(unwrap)

/** POST /stocks/sync-daily-basic  同步日频估值指标 */
export const syncDailyBasic = (days = 1): Promise<{ synced_count: number; dates: string[]; message: string }> =>
  http.post(`/stocks/sync-daily-basic?days=${days}`).then(unwrap)

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

// ── K 线采集 & 查询（响应含 17 个指标列）───────────────────────

/** POST /klines/collect  采集 K 线（后端会一并算指标） */
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

/** GET /klines/{symbol}  查询 K 线列表（含指标列） */
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

// ── 🆕 AI 归因分析（前端 + Agent 统一入口） ─────────────────

/** GET /stocks/{symbol}/analysis  一次拿齐 K 线 + 指标 + 摘要 + 池 */
export const getStockAnalysis = (
  symbol: string,
  params: { days?: number } = {}
): Promise<StockAnalysisResponse> =>
  http.get<StockAnalysisResponse>(`/stocks/${symbol}/analysis`, { params }).then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  🆕 数据分析层 API（对应后端 14 张新表）
//  参考 backend/docs/03dataana/02-dev-guide.md §8
// ═══════════════════════════════════════════════════════════════

// ── 资金流向 ───────────────────────────────────────────────────

/** 资金流向项（cap_moneyflows） */
export interface MoneyflowItem {
  symbol: string
  trade_date: string
  net_mf_amount: number | null
  net_mf_vol: number | null
  buy_lg_amount: number | null
  sell_lg_amount: number | null
  buy_elg_amount: number | null
  sell_elg_amount: number | null
  buy_sm_amount: number | null
  sell_sm_amount: number | null
  buy_md_amount: number | null
  sell_md_amount: number | null
}

/** GET /moneyflows/ 查询资金流向 */
export const getMoneyflows = (params: {
  symbol?: string
  trade_date?: string
  start_date?: string
  end_date?: string
  limit?: number
}) =>
  http
    .get<{ total: number; items: MoneyflowItem[] }>('/moneyflows/', { params })
    .then(unwrap)

/** POST /moneyflows/collect  触发资金流向采集 */
export const collectMoneyflows = (params?: { symbol?: string; trade_date?: string }) =>
  http.post<{ saved_count: number; total_count: number; message: string }>(
    '/moneyflows/collect',
    null,
    { params }
  ).then(unwrap)

// ── 两融明细 ───────────────────────────────────────────────────

/** 个股两融明细项（cap_margin_details） */
export interface MarginDetailItem {
  symbol: string
  trade_date: string
  rzye: number | null
  rqye: number | null
  rzmre: number | null
  rqyl: number | null
  rzche: number | null
  rqchl: number | null
  rqmcl: number | null
  rzrqye: number | null
}

/** GET /margin-details/ 查询两融明细 */
export const getMarginDetails = (params: {
  symbol: string
  start_date?: string
  end_date?: string
  limit?: number
}) =>
  http
    .get<{ total: number; items: MarginDetailItem[] }>('/margin-details/', { params })
    .then(unwrap)

// ── 龙虎榜 ─────────────────────────────────────────────────────

/** 龙虎榜单项（cap_top_lists） */
export interface TopListItem {
  trade_date: string
  symbol: string
  name: string | null
  close: number | null
  pct_change: number | null
  amount: number | null
  net_amount: number | null
  reason: string | null
}

/** GET /top-lists/ 查询龙虎榜 */
export const getTopLists = (params: {
  trade_date?: string
  start_date?: string
  end_date?: string
}) =>
  http
    .get<{ total: number; items: TopListItem[] }>('/top-lists/', { params })
    .then(unwrap)

// ── 日频估值 ───────────────────────────────────────────────────

/** 日频估值项（fin_daily_basics） */
export interface DailyBasicItem {
  symbol: string
  trade_date: string
  close: number | null
  pe: number | null
  pe_ttm: number | null
  pb: number | null
  ps: number | null
  ps_ttm: number | null
  dv_ratio: number | null
  turnover_rate: number | null
  total_mv: number | null
  circ_mv: number | null
}

/** GET /fin-daily-basics/ 查询日频估值 */
export const getFinDailyBasics = (params: {
  symbol: string
  start_date?: string
  end_date?: string
  limit?: number
}) =>
  http
    .get<{ total: number; items: DailyBasicItem[] }>('/fin-daily-basics/', { params })
    .then(unwrap)

// ── 前十大股东 ─────────────────────────────────────────────────

/** 十大股东项（fin_top10_holders） */
export interface Top10HolderItem {
  symbol: string
  holder_name: string
  end_date: string | null
  ann_date: string | null
  hold_amount: number | null
  hold_ratio: number | null
  hold_float_ratio: number | null
  hold_change: number | null
  holder_type: string | null
}

/** GET /top10-holders/ 查询十大股东 */
export const getTop10Holders = (params: {
  symbol: string
  end_date?: string
}) =>
  http
    .get<{ total: number; items: Top10HolderItem[] }>('/top10-holders/', { params })
    .then(unwrap)

// ── 复权因子 ───────────────────────────────────────────────────

/** 复权因子项（base_adj_factors） */
export interface AdjFactorItem {
  symbol: string
  trade_date: string
  adj_factor: number
}

/** GET /adj-factors/ 查询复权因子 */
export const getAdjFactors = (params: {
  symbol: string
  start_date?: string
  end_date?: string
  limit?: number
}) =>
  http
    .get<{ total: number; items: AdjFactorItem[] }>('/adj-factors/', { params })
    .then(unwrap)

// ── 分红送股 ───────────────────────────────────────────────────

/** 分红送股项（base_dividends） */
export interface DividendItem {
  symbol: string
  end_date: string
  ann_date: string | null
  record_date: string | null
  ex_date: string | null
  pay_date: string | null
  div_proc: string | null
  stk_div: number | null
  cash_div: number | null
  cash_div_tax: number | null
}

/** GET /dividends/ 查询分红送股 */
export const getDividends = (params: {
  symbol: string
  start_date?: string
  end_date?: string
}) =>
  http
    .get<{ total: number; items: DividendItem[] }>('/dividends/', { params })
    .then(unwrap)

// ── 停复牌 ─────────────────────────────────────────────────────

/** 停复牌项（base_suspends） */
export interface SuspendItem {
  symbol: string
  trade_date: string
  suspend_timing: string | null
  suspend_type: string | null
}

/** GET /suspends/ 查询停复牌 */
export const getSuspends = (params: {
  symbol?: string
  trade_date?: string
  start_date?: string
  end_date?: string
}) =>
  http
    .get<{ total: number; items: SuspendItem[] }>('/suspends/', { params })
    .then(unwrap)

// ── 板块行情 ───────────────────────────────────────────────────

/** 板块行情项（mkt_sector_dailys） */
export interface SectorDailyItem {
  sector_type: string
  sector_code: string
  sector_name: string | null
  trade_date: string
  close: number | null
  pct_change: number | null
  amount: number | null
  turnover_rate: number | null
}

/** GET /sector-dailys/ 查询板块日行情 */
export const getSectorDailys = (params: {
  sector_type?: string
  trade_date?: string
  limit?: number
}) =>
  http
    .get<{ total: number; items: SectorDailyItem[] }>('/sector-dailys/', { params })
    .then(unwrap)

// ── 板块成分 ───────────────────────────────────────────────────

/** 板块成分项（mkt_index_members） */
export interface IndexMemberItem {
  sector_type: string
  sector_code: string
  sector_name: string | null
  symbol: string
  name: string | null
  effective_date: string | null
  expiry_date: string | null
  is_new: string | null
}

/** GET /index-members/ 查询板块成分 */
export const getIndexMembers = (params: {
  sector_type: string
  sector_code: string
}) =>
  http
    .get<{ total: number; items: IndexMemberItem[] }>('/index-members/', { params })
    .then(unwrap)

// ── 股东户数 ───────────────────────────────────────────────────

/** 股东户数项（cap_holder_nums） */
export interface HolderNumItem {
  symbol: string
  end_date: string
  ann_date: string | null
  holder_num: number | null
}

/** GET /holder-nums/ 查询股东户数 */
export const getHolderNums = (params: {
  symbol: string
  start_date?: string
  end_date?: string
}) =>
  http
    .get<{ total: number; items: HolderNumItem[] }>('/holder-nums/', { params })
    .then(unwrap)

// ── 分钟 K 线（pytdx） ────────────────────────────────────────

/** 分钟 K 线数据 */
export interface MinuteKline {
  datetime:    string
  interval:    string
  open:        number
  high:        number
  low:         number
  close:       number
  volume:      number
  amount:      number
}

/** GET /minute-klines/{symbol}  实时获取分钟 K 线（不落库） */
export const getMinuteKlines = (
  symbol: string,
  params: { interval?: string; count?: number } = {}
) =>
  http
    .get<{ total: number; items: MinuteKline[] }>(`/minute-klines/${symbol}`, { params })
    .then(unwrap)