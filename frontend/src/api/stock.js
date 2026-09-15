/**
 * API 层 — 对齐后端 /api/v1 路由
 *
 * 后端响应统一包装: { code: number, message: string, data: any }
 * - code 200/201 = 成功，data 即业务数据
 * - code >= 400  = 错误，data 是错误信息
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// ── 请求拦截器：统一处理 401 / 网络错误 ──────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      '网络异常'
    console.error('[API Error]', msg, error.response?.data)
    return Promise.reject(new Error(msg))
  }
)

// ── 辅助：提取业务数据，抛异常则透传 ──────────────────────────
function unwrap(res) {
  if (res.data.code >= 400) {
    throw new Error(res.data.message || '请求失败')
  }
  return res.data.data
}

// ═══════════════════════════════════════════════════════════════
//  股票管理
// ═══════════════════════════════════════════════════════════════

/** GET /api/v1/stocks/  股票列表 */
export const listStocks = () =>
  api.get('/stocks/').then(unwrap)

/** GET /api/v1/stocks/{symbol}  单个股票（含 K 线统计） */
export const getStock = (symbol) =>
  api.get(`/stocks/${symbol}`).then(unwrap)

/**
 * POST /api/v1/stocks/  新增股票（query 参数）
 * @param {{symbol, name, industry?, market?}} params
 */
export const createStock = (params) =>
  api.post('/stocks/', null, { params }).then(unwrap)

/**
 * PATCH /api/v1/stocks/{symbol}  部分更新
 * @param {string} symbol
 * @param {{name?, industry?, market?}} body
 */
export const updateStock = (symbol, body) =>
  api.patch(`/stocks/${symbol}`, body).then(unwrap)

/** DELETE /api/v1/stocks/{symbol}  删除股票 */
export const deleteStock = (symbol) =>
  api.delete(`/stocks/${symbol}`).then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  K 线采集 & 查询
// ═══════════════════════════════════════════════════════════════

/**
 * POST /api/v1/klines/collect  采集 K 线
 * @param {{symbol, days?, start_date?, end_date?}} body
 * @returns {{symbol, name, saved_count, total_count, message}}
 */
export const collectKlines = (body) =>
  api.post('/klines/collect', body).then(unwrap)

/**
 * POST /api/v1/klines/collect/batch  批量采集
 * @param {string[]} symbols  股票代码列表
 * @param {number} days      回溯天数
 * @returns {Record<string, KlineCollectResult>}
 */
export const collectBatch = (symbols, days = 30) =>
  api.post('/klines/collect/batch', null, {
    params: symbols.flatMap((s) => ['symbols', s]),
    paramsSerializer: (ps) =>
      ps.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&'),
  }).then(unwrap)

/**
 * GET /api/v1/klines/{symbol}  查询 K 线列表
 * @param {string} symbol
 * @param {{start_date?, end_date?, limit?, order_desc?}} params
 * @returns {{total, items[]}}
 */
export const getKlines = (symbol, params = {}) =>
  api.get(`/klines/${symbol}`, { params }).then(unwrap)

/** GET /api/v1/klines/{symbol}/stats  K 线统计 */
export const getKlineStats = (symbol) =>
  api.get(`/klines/${symbol}/stats`).then(unwrap)

/** DELETE /api/v1/klines/{symbol}  删除全部 K 线 */
export const deleteAllKlines = (symbol) =>
  api.delete(`/klines/${symbol}`).then(unwrap)

/** DELETE /api/v1/klines/{symbol}/{trade_date}  删除单条 K 线 */
export const deleteKline = (symbol, tradeDate) =>
  api.delete(`/klines/${symbol}/${tradeDate}`).then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  统一导出
// ═══════════════════════════════════════════════════════════════

export default {
  listStocks,
  getStock,
  createStock,
  updateStock,
  deleteStock,
  collectKlines,
  collectBatch,
  getKlines,
  getKlineStats,
  deleteAllKlines,
  deleteKline,
}
