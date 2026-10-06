// 四数据面数据看板 — API + VO
//
// 配套设计文档：docs/overview/数据面与采集总览.md
//
// 与 concept-board/api-data-board.ts 完全等价（同一组后端端点）。
// 保留独立文件，便于后续 data-board 子组件按面拆分 / 共享同一组类型。

import http, { etagGet, unwrap, type ApiResponse } from '@/common/utils/http'

// ETag 协商与缓存兜底统一收敛到 @/common/utils/http（etagGet），
// 这里不再各自维护一份 _etagCache，避免两处实现漂移。

// ── VO 类型 ──

export interface KLineBar {
  trade_date: string
  open: number; high: number; low: number; close: number
  volume: number; amount: number | null
  change_pct: number | null
  ma5: number | null; ma10: number | null; ma20: number | null; ma60: number | null
  ema12: number | null; ema26: number | null
  macd_dif: number | null; macd_dea: number | null; macd_bar: number | null
  rsi6: number | null; rsi12: number | null; rsi24: number | null
  kdj_k: number | null; kdj_d: number | null; kdj_j: number | null
  boll_up: number | null; boll_mid: number | null; boll_dn: number | null
}

export interface AdjFactor {
  trade_date: string; adj_factor: number
}

export interface SuspendEvent {
  trade_date: string
  suspend_timing: string | null
  suspend_type: string | null
}

export interface NameChange {
  name: string
  start_date: string
  end_date: string | null
  ann_date: string | null
  change_reason: string | null
}

export interface MoneyflowDay {
  trade_date: string
  buy_sm_amount: number | null; sell_sm_amount: number | null
  buy_md_amount: number | null; sell_md_amount: number | null
  buy_lg_amount: number | null; sell_lg_amount: number | null
  buy_elg_amount: number | null; sell_elg_amount: number | null
  net_mf_amount: number | null; net_mf_vol: number | null
}

export interface MarginDay {
  trade_date: string
  rzye: number | null; rqye: number | null; rzrqye: number | null
  rzmre: number | null; rzche: number | null
  rqyl: number | null; rqmcl: number | null; rqchl: number | null
}

export interface TopListRow {
  trade_date: string
  name: string | null
  close: number | null; pct_change: number | null
  turnover_rate: number | null; amount: number | null
  l_buy: number | null; l_sell: number | null; l_amount: number | null
  net_amount: number | null; net_rate: number | null
  amount_rate: number | null; float_values: number | null
  reason: string | null
}

export interface TopInstRow {
  trade_date: string
  exalter: string | null; side: string | null
  buy: number | null; buy_rate: number | null
  sell: number | null; sell_rate: number | null
  net_buy: number | null; reason: string | null
}

export interface BlockTradeRow {
  trade_date: string
  name: string | null
  price: number | null; vol: number | null; amount: number | null
  buyer: string | null; seller: string | null
}

export interface HolderNumRow {
  end_date: string; ann_date: string | null
  holder_num: number | null; holder_nums: number | null
}

export interface StockInfo {
  symbol: string; name: string
  industry: string | null; market: string | null; exchange: string | null
  area: string | null
  list_date: string | null; delist_date: string | null
  list_status: string | null; is_hs: string | null
  act_name: string | null
}

export interface DailyBasicRow {
  trade_date: string
  close: number | null
  turnover_rate: number | null; turnover_rate_f: number | null
  volume_ratio: number | null
  pe: number | null; pe_ttm: number | null
  pb: number | null; ps: number | null; ps_ttm: number | null
  dv_ratio: number | null; dv_ttm: number | null
  total_share: number | null; float_share: number | null
  total_mv: number | null; circ_mv: number | null
}

export interface FinReportRow {
  end_date: string; ann_date: string | null
  report_type: string | null
  basic_eps: number | null; diluted_eps: number | null
  total_revenue: number | null; revenue: number | null
  operate_profit: number | null; total_profit: number | null
  n_income: number | null; n_income_attr_p: number | null
  net_margin: number | null
}

export interface Top10Holder {
  end_date: string | null; ann_date: string | null
  holder_name: string
  hold_amount: number | null
  hold_ratio: number | null; hold_float_ratio: number | null
  hold_change: number | null
  holder_type: string | null
}

export interface DividendRow {
  end_date: string
  ann_date: string | null; record_date: string | null
  ex_date: string | null; pay_date: string | null
  div_proc: string | null
  stk_div: number | null; stk_bo_rate: number | null; stk_co_rate: number | null
  cash_div: number | null; cash_div_tax: number | null
}

export interface OverviewPanel {
  symbol: string
  stock: { name: string; industry: string | null; list_date: string | null } | null
  tech: { kline_count: number; kline_latest_date: string | null }
  fundamental: {
    latest_close: number | null; latest_pe: number | null; latest_pb: number | null
    latest_total_mv: number | null; latest_date: string | null
  }
  capital: {
    moneyflow_latest_date: string | null; moneyflow_count: number
    margin_latest_date: string | null; margin_count: number
    top_list_count: number; holder_count: number
  }
  news: { available: boolean; message: string }
}

// ── 左侧股票列专用 VO ──

export interface StockListItem {
  symbol: string
  name: string | null
  industry: string | null
  market: string | null
  exchange: string | null
  list_status?: string | null
}

export interface StockListResponse {
  total: number
  items: StockListItem[]
}

export interface StockListAllResponse {
  total: number
  items: StockListItem[]
}

// ── API ──

const PREFIX = '/data-board'

export const getOverviewPanel = (symbol: string) =>
  http.get<OverviewPanel>(`${PREFIX}/overview/${symbol}`).then(unwrap)

export const getKline = (symbol: string, limit = 250) =>
  etagGet<{ symbol: string; klines: KLineBar[] }>(
    `${PREFIX}/tech/kline/${symbol}`, { limit },
  )

export const getAdjFactor = (symbol: string) =>
  etagGet<{ symbol: string; factors: AdjFactor[] }>(
    `${PREFIX}/tech/adj-factor/${symbol}`,
  )

export const getSuspend = (symbol: string) =>
  etagGet<{ symbol: string; events: SuspendEvent[] }>(
    `${PREFIX}/tech/suspend/${symbol}`,
  )

export const getNameChange = (symbol: string) =>
  etagGet<{ symbol: string; history: NameChange[] }>(
    `${PREFIX}/tech/name-change/${symbol}`,
  )

export const getMoneyflow = (symbol: string, days = 60) =>
  http.get<{ symbol: string; days: number; flows: MoneyflowDay[] }>(
    `${PREFIX}/capital/moneyflow/${symbol}`, { params: { days } },
  ).then(unwrap)

export const getMargin = (symbol: string, days = 60) =>
  http.get<{ symbol: string; days: number; details: MarginDay[] }>(
    `${PREFIX}/capital/margin/${symbol}`, { params: { days } },
  ).then(unwrap)

export const getTopList = (symbol: string, days = 90) =>
  http.get<{ symbol: string; days: number; lists: TopListRow[] }>(
    `${PREFIX}/capital/top-list/${symbol}`, { params: { days } },
  ).then(unwrap)

export const getTopInst = (symbol: string, days = 90) =>
  http.get<{ symbol: string; days: number; details: TopInstRow[] }>(
    `${PREFIX}/capital/top-inst/${symbol}`, { params: { days } },
  ).then(unwrap)

export const getBlockTrade = (symbol: string, days = 180) =>
  http.get<{ symbol: string; days: number; trades: BlockTradeRow[] }>(
    `${PREFIX}/capital/block-trade/${symbol}`, { params: { days } },
  ).then(unwrap)

export const getHolderNum = (symbol: string) =>
  http.get<{ symbol: string; history: HolderNumRow[] }>(
    `${PREFIX}/capital/holder-num/${symbol}`,
  ).then(unwrap)

export const getStockInfo = (symbol: string) =>
  http.get<StockInfo>(`${PREFIX}/fundamental/stock/${symbol}`).then(unwrap)

export const getDailyBasic = (symbol: string, days = 60) =>
  http.get<{ symbol: string; days: number; valuation: DailyBasicRow[] }>(
    `${PREFIX}/fundamental/daily-basic/${symbol}`, { params: { days } },
  ).then(unwrap)

export const getFinReport = (symbol: string) =>
  http.get<{ symbol: string; reports: FinReportRow[] }>(
    `${PREFIX}/fundamental/fin-report/${symbol}`,
  ).then(unwrap)

export const getTop10Holders = (symbol: string) =>
  http.get<{ symbol: string; holders: Top10Holder[] }>(
    `${PREFIX}/fundamental/top10-holders/${symbol}`,
  ).then(unwrap)

export const getTop10Float = (symbol: string) =>
  http.get<{ symbol: string; holders: Top10Holder[] }>(
    `${PREFIX}/fundamental/top10-float/${symbol}`,
  ).then(unwrap)

export const getDividend = (symbol: string) =>
  http.get<{ symbol: string; dividends: DividendRow[] }>(
    `${PREFIX}/fundamental/dividend/${symbol}`,
  ).then(unwrap)

// ── 左侧股票列 API ──

/** 全量轻量列表（一次性 5000+ 只，前端缓存 + 本地过滤） */
export const getStockListAll = () =>
  http.get<StockListAllResponse>(`${PREFIX}/stock-list-all`).then(unwrap)

/** 模糊搜索（symbol / name / ts_code） */
export const getStockList = (q: string, page = 1, pageSize = 50) =>
  http.get<StockListResponse>(`${PREFIX}/stock-list`, {
    params: { q, page, page_size: pageSize },
  }).then(unwrap)