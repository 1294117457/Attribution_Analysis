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

/** 池成员关系（列表 / 详情通用）

  与后端 PoolMembershipVO 对齐：
  pool_id / name / pool_type / joined_at。
  用于列表 with_pools=true 场景，避免前端逐条反向查询池。
  */
export interface PoolMembership {
  pool_id: number
  name: string
  pool_type: string
  joined_at: string | null
}

// ═══════════════════════════════════════════════════════════════════════
//  概念板块相关 VO
//  配套设计文档：docs/dev/06gainian/03-application-and-route-design.md §1.1
// ═══════════════════════════════════════════════════════════════════════

/** 概念数据源（adata 采集的同花顺数据） */
export type ConceptSource = 'ths'

/** 概念类型 */
export type ConceptType =
  | 'industry'   // 行业概念
  | 'theme'      // 主题概念
  | 'style'      // 风格概念
  | 'region'     // 地域概念
  | 'event'      // 事件概念
  | 'other'      // 其他概念

/** 概念类型展示标签 */
export const CONCEPT_TYPE_LABELS: Record<ConceptType, string> = {
  industry: '行业概念',
  theme:    '主题概念',
  style:    '风格概念',
  region:   '地域概念',
  event:    '事件概念',
  other:    '其他概念',
}

/** 简略 VO（嵌入到 StockInfo.concepts，给详情抽屉预热用）

  08concept 增量：
  - 新增 concept_type 可选字段，用于主概念列排序与前端染色
  - 向后兼容：旧响应无该字段时默认 "other" */
export interface ConceptBrief {
  concept_id: number
  name: string
  source: ConceptSource
  /** 08concept 新增：概念类型 */
  concept_type?: ConceptType
}

/** 主概念 VO（08concept 新增，列表行渲染专用）

  与 ConceptBrief 的区别：
  - ConceptBrief：通用简略视图（无业务排序）
  - ConceptMainVO：业务排序视图（多了 display_order）

  display_order: 1=最优先（industry），越大越靠后 */
export interface ConceptMainVO {
  concept_id: number
  name: string
  source: ConceptSource
  concept_type: ConceptType
  display_order: number
  /** 09concept 新增：板块行情快照（None 表示暂无快照数据） */
  snapshot?: ConceptSnapshot | null
}

/** 概念实时行情（实时接口 concept_minute，15 秒缓存；涨跌染色用） */
export interface ConceptSnapshot {
  index_code: string
  concept_name: string
  price: number | null
  prev_close: number | null
  change: number | null
  pct_change: number | null
  color: 'up' | 'down' | 'flat'
  trade_time: string | null
  /** 数据源取数时间 */
  captured_at: string | null
  /** true：行情源不可用，显示的是最近一条日 K 收盘 */
  stale: boolean
  /** 兼容旧字段，恒为空 */
  rank_label: string
  up_down_label: string
}

/** 分组 VO（详情抽屉「概念」Tab 用） */
export interface ConceptGroupedVO {
  concept_id: number
  index_code?: string | null
  name: string
  source: ConceptSource
  concept_type: ConceptType
  description: string | null
  /** 入选理由（概念入选理由采集任务写入） */
  reason?: string | null
}

/** 概念 Tab 单个分组区块 */
export interface ConceptTabSectionVO {
  type: ConceptType
  type_label: string
  /** merge_live=true 时 dict 额外携带 is_realtime / concept_code 字段 */
  concepts: (ConceptGroupedVO & {
    concept_code?: string | null
    is_realtime?: boolean
    /** 09concept 新增：板块行情快照（涨跌染色用） */
    snapshot?: ConceptSnapshot | null
  })[]
}

/** 概念 Tab 完整渲染模型（与后端 ConceptTabContentVO 1:1） */
export interface ConceptTabContentVO {
  symbol: string
  stock_name: string
  sections: ConceptTabSectionVO[]
  total_count: number
  /** 08concept 新增：是否经过实时合并 */
  is_merged?: boolean
  /** 08concept 新增：合并时间（ISO 字符串） */
  last_merged_at?: string | null
}

/** 股票信息（stock_basic / stock_info）

  后端 GET /stocks/ 响应（with_pools=true 时 items[].pools 会附带池信息）。 */
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
  profit_margin: number | null // 净利润率%
  record_count: number          // K 线记录数（with_pools=true 时附带）
  kline_start: string | null   // K 线开始日期（with_pools=true 时附带）
  kline_end:   string | null  // K 线结束日期（with_pools=true 时附带）
  // 🆕 所属操作池（with_pools=true 时由后端批量填充，避免 N+1）
  pools: PoolMembership[]

  /** 🆕 所属概念板块（with_concepts=true 时由后端批量填充，详情抽屉预热用）

  08concept 升级：
  - 类型从 ConceptBrief[] 升级为 ConceptMainVO[]
  - 兼容：ConceptMainVO 包含 ConceptBrief 所有字段 + display_order
  */
  concepts: ConceptMainVO[]

  /** 🆕 08concept：溢出数（行内"+N"显示用），仅概念总数 > top_k 时 > 0 */
  concepts_overflow: number
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
  exclude_st?:  boolean
  min_total_mv?: number
  /** 是否附带所属操作池（true 时响应 items[].pools 填充，避免 N+1） */
  with_pools?:  boolean
  /** 是否附带所属概念板块（true 时响应 items[].concepts 填充，详情抽屉预热用） */
  with_concepts?: boolean
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

/**
 * GET /api/v1/stock-panel/  面板列表（分页 + 多维筛选 + 4 表快照 + 池信息）
 *
 * 新端点，替代原 /stocks/ 的富字段查询职责。
 * 响应字段与 StockInfo 接口 1:1 对齐（items/total/page/page_size）。
 */
export const queryStocks = (params: StockQueryParams = {}) =>
  http.get<PaginatedResponse<StockInfo>>('/stock-panel/', { params }).then(unwrap)

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

/** GET /minute-klines/{symbol}  实时获取分钟 K 线（实时接口 stock_minute_kline，15 秒缓存）
 *  days：1min 仅 1（当天），其他周期 1–5 */
export const getMinuteKlines = (
  symbol: string,
  params: { interval?: string; days?: number } = {}
) =>
  http
    .get<{ total: number; items: MinuteKline[]; cached: boolean; fetched_at: string | null }>(
      `/minute-klines/${symbol}`,
      { params },
    )
    .then(unwrap)

// ═══════════════════════════════════════════════════════════════════════
//  🆕 概念板块 API（对应后端 06gainian）
//  配套设计文档：docs/dev/06gainian/03-application-and-route-design.md §5
// ═══════════════════════════════════════════════════════════════════════

/** GET /api/v1/concepts/by-symbol/{symbol}  单股票所属概念（简略版 ConceptBrief） */
export const getConceptsBySymbol = (symbol: string): Promise<ConceptBrief[]> =>
  http.get<ConceptBrief[]>(`/concepts/by-symbol/${symbol}`).then(unwrap)

/** GET /api/v1/concepts/tab-by-symbol/{symbol}  抽屉「概念」Tab 内容（按类型分组） */
export const getConceptTabForSymbol = (
  symbol: string,
  params: { stock_name?: string } = {},
): Promise<ConceptTabContentVO> =>
  http.get<ConceptTabContentVO>(`/concepts/tab-by-symbol/${symbol}`, { params }).then(unwrap)

/** 合并同花顺实时反查数据
 * GET /api/v1/concepts/tab-by-symbol/{symbol}?merge_live=true
 *
 * 与 getConceptTabForSymbol 的区别：
 * - 默认：仅库中数据（已含入选理由 reason）
 * - 本接口：库中 + 实时合并，含 is_realtime / concept_code 字段
 *
 * 适用场景：详情抽屉「概念」Tab 的"实时刷新"按钮 */
export const getConceptTabForSymbolMerged = (
  symbol: string,
  params: { stock_name?: string } = {},
): Promise<ConceptTabContentVO> =>
  http.get<ConceptTabContentVO>(
    `/concepts/tab-by-symbol/${symbol}`,
    { params: { ...params, merge_live: true } },
  ).then(unwrap)

/** GET /api/v1/concepts/{name}  单概念详情（含成分股） */
export const getConceptDetail = (
  name: string,
): Promise<{
  concept_id: number
  index_code: string
  name: string
  source: ConceptSource
  concept_type: ConceptType
  stock_count: number
  description: string | null
  is_active: boolean
  last_synced_at: string | null
  first_seen_at: string | null
  members: { symbol: string; name: string; reason: string | null }[]
}> =>
  http.get(`/concepts/${encodeURIComponent(name)}`).then(unwrap)

/** GET /api/v1/concepts/sync/status  查询同步状态 */
export const getConceptSyncStatus = (): Promise<{
  last_synced_at: string | null
  active_concepts: number
}> =>
  http.get('/concepts/sync/status').then(unwrap)

/** GET /api/v1/concepts/quotes?codes=  批量概念实时行情（最多 100 个；取不到的不在结果中） */
export const getConceptQuotes = (
  indexCodes: string[],
): Promise<Record<string, ConceptSnapshot>> =>
  http
    .get<Record<string, ConceptSnapshot>>('/concepts/quotes', {
      params: { codes: indexCodes.join(',') },
    })
    .then(unwrap)