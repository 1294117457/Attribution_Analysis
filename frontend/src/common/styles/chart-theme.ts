/**
 * A 股 K 线图配色规范
 *
 * - 阳线（涨）= 红 / 阴线（跌）= 绿（A 股惯例，与欧美相反）
 * - 与 Element Plus 浅色主题协调
 */

export const chartTheme = {
  candle: {
    up:       '#ef4444',   // 阳线 - 红
    down:     '#22c55e',   // 阴线 - 绿
    noChange: '#9ca3af',
  },
  volume: {
    up:   'rgba(239, 68, 68, 0.6)',
    down: 'rgba(34, 197, 94, 0.6)',
  },
  grid: {
    line: '#f0f2f5',
    text: '#9ca3af',
  },
  axis: {
    line: '#d1d5db',
    text: '#6b7280',
  },
  indicators: {
    // 主图叠加
    MA5:       '#fbbf24',   // 黄
    MA10:      '#3b82f6',   // 蓝
    MA20:      '#a855f7',   // 紫
    MA60:      '#06b6d4',   // 青
    BOLL_UP:   '#a855f7',
    BOLL_MID:  '#f97316',   // 橙
    BOLL_DN:   '#a855f7',
    // MACD
    MACD_DIF:  '#3b82f6',   // 蓝
    MACD_DEA:  '#fbbf24',   // 黄
    MACD_BAR_UP:   '#ef4444',  // 红柱
    MACD_BAR_DOWN: '#22c55e',  // 绿柱
    // KDJ
    KDJ_K:     '#14b8a6',   // 青
    KDJ_D:     '#f97316',   // 橙
    KDJ_J:     '#a855f7',   // 紫
    // RSI
    RSI:       '#ec4899',   // 粉
  },
} as const

export type ChartTheme = typeof chartTheme