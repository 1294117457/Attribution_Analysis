import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

export const stockApi = {
  // 股票列表
  listStocks() {
    return api.get('/stocks/')
  },

  // 股票详情
  getStock(symbol) {
    return api.get(`/stocks/${symbol}`)
  },

  // K线数据
  getKlines(symbol, params = {}) {
    return api.get(`/stocks/${symbol}/klines`, { params: { symbol, ...params } })
  },

  // 采集
  collect(symbol, days = 365, startDate = null, endDate = null) {
    return api.post('/stocks/collect', {
      symbol,
      days,
      start_date: startDate,
      end_date: endDate,
    })
  },

  // 删除股票
  deleteStock(symbol) {
    return api.delete(`/stocks/${symbol}`)
  },

  // 删除单条K线
  deleteKline(symbol, date) {
    return api.delete(`/stocks/${symbol}/klines/${date}`)
  },
}

export default stockApi
