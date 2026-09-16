/**
 * K 线 + AI 归因分析 Pinia store
 *
 * 设计要点：
 * - 单只股票的分析结果（StockAnalysisResponse）做内存缓存, 避免重复请求
 * - K 线 + 指标列表单独缓存, 方便在多个组件共享
 * - 拉取 K 线后自动失效对应缓存
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getKlines,
  collectKlines,
  getStockAnalysis,
  type Kline,
  type StockAnalysisResponse,
} from '@/views/stock-info/api'

export const useKlineStore = defineStore('kline', () => {
  // ── State ────────────────────────────────────────────────

  /** symbol -> 完整分析响应 */
  const analysisCache = ref<Record<string, StockAnalysisResponse>>({})

  /** symbol -> K 线列表（不含 summary/pools） */
  const klineCache = ref<Record<string, Kline[]>>({})

  /** 正在加载的 symbol 集合, 用于防止重复请求 */
  const loadingSymbols = ref<Set<string>>(new Set())

  const error = ref<string | null>(null)

  // ── Getters ──────────────────────────────────────────────

  function hasAnalysis(symbol: string): boolean {
    return !!analysisCache.value[symbol]
  }

  function getAnalysis(symbol: string): StockAnalysisResponse | null {
    return analysisCache.value[symbol] || null
  }

  function isLoading(symbol: string): boolean {
    return loadingSymbols.value.has(symbol)
  }

  // ── Actions ──────────────────────────────────────────────

  /** 获取完整分析（优先走缓存） */
  async function fetchAnalysis(
    symbol: string,
    days = 365,
    force = false,
  ): Promise<StockAnalysisResponse | null> {
    if (!symbol) return null

    // 缓存命中且非强制刷新
    if (!force && analysisCache.value[symbol]) {
      return analysisCache.value[symbol]
    }

    loadingSymbols.value.add(symbol)
    error.value = null
    try {
      const resp = await getStockAnalysis(symbol, { days })
      if (resp) {
        analysisCache.value[symbol] = resp
        // 同时把 klines 顺手缓存
        klineCache.value[symbol] = resp.klines
        return resp
      }
      return null
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      loadingSymbols.value.delete(symbol)
    }
  }

  /** 仅拉取 K 线（不取摘要、不取池） */
  async function fetchKlines(
    symbol: string,
    params: { limit?: number; start_date?: string; end_date?: string } = {},
    force = false,
  ): Promise<Kline[]> {
    if (!symbol) return []

    const cacheKey = `${symbol}:${params.limit ?? 365}:${params.start_date ?? ''}:${params.end_date ?? ''}`
    if (!force && klineCache.value[cacheKey]) {
      return klineCache.value[cacheKey]
    }

    loadingSymbols.value.add(symbol)
    try {
      const data = (await getKlines(symbol, params)) as unknown as { items?: Kline[] }
      const items = (data.items || []) as Kline[]
      klineCache.value[cacheKey] = items
      // 顺便刷新单股 K 线缓存 (symbol -> klines)
      klineCache.value[symbol] = items
      return items
    } finally {
      loadingSymbols.value.delete(symbol)
    }
  }

  /** 触发 K 线采集（后端会算指标） */
  async function collect(
    symbol: string,
    days = 365,
  ): Promise<{ saved_count: number; total_count: number; message: string }> {
    const result = (await collectKlines({ symbol, days })) as unknown as { saved_count: number; total_count: number; message: string }
    // 采集成功后失效该 symbol 的缓存
    invalidate(symbol)
    return {
      saved_count: result.saved_count,
      total_count: result.total_count,
      message: result.message,
    }
  }

  /** 失效某只股票的缓存 */
  function invalidate(symbol: string) {
    delete analysisCache.value[symbol]
    Object.keys(klineCache.value).forEach((k) => {
      if (k === symbol || k.startsWith(symbol + ':')) {
        delete klineCache.value[k]
      }
    })
  }

  /** 全量清空缓存 */
  function clearCache() {
    analysisCache.value = {}
    klineCache.value = {}
  }

  return {
    // state
    analysisCache,
    klineCache,
    loadingSymbols,
    error,
    // getters
    hasAnalysis,
    getAnalysis,
    isLoading,
    // actions
    fetchAnalysis,
    fetchKlines,
    collect,
    invalidate,
    clearCache,
  }
})