<template>
  <div ref="rootRef" class="candle-chart" :style="{ height: `${height}px` }">
    <!-- 顶部工具提示（十字光标 + OHLC + 指标） -->
    <div v-if="hoverInfo" class="absolute z-10 bg-white/95 border border-gray-200 rounded px-2 py-1 text-xs shadow pointer-events-none"
         :style="{ left: `${hoverInfo.x + 12}px`, top: `${hoverInfo.y}px` }">
      <div class="font-semibold">{{ hoverInfo.date }}</div>
      <div class="text-gray-700">
        开 <span :class="hoverInfo.up ? 'text-red-500' : 'text-green-500'">{{ hoverInfo.open.toFixed(2) }}</span>
        高 <span class="text-red-500">{{ hoverInfo.high.toFixed(2) }}</span>
        低 <span class="text-green-500">{{ hoverInfo.low.toFixed(2) }}</span>
        收 <span :class="hoverInfo.up ? 'text-red-500' : 'text-green-500'">{{ hoverInfo.close.toFixed(2) }}</span>
      </div>
      <div v-if="hoverInfo.change_pct != null" class="text-gray-500">
        涨跌幅 <span :class="hoverInfo.change_pct >= 0 ? 'text-red-500' : 'text-green-500'">
          {{ hoverInfo.change_pct >= 0 ? '+' : '' }}{{ hoverInfo.change_pct.toFixed(2) }}%
        </span>
      </div>
      <div class="text-gray-500">成交量 {{ formatVolume(hoverInfo.volume) }}</div>
      <div v-if="hoverInfo.indicators" class="border-t border-gray-200 mt-1 pt-1 space-y-0.5">
        <div v-for="(v, k) in hoverInfo.indicators" :key="k">
          <span class="text-gray-500">{{ k }}:</span>
          <span class="ml-1">{{ v != null ? Number(v).toFixed(3) : '—' }}</span>
        </div>
      </div>
    </div>

    <!-- SVG K 线图 -->
    <svg
      ref="svgRef"
      :width="dims.width"
      :height="dims.height"
      class="w-full"
      @mousemove="onMove"
      @mouseleave="hoverInfo = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import type { Kline } from '@/views/stock-info/api'
import { chartTheme } from '@/common/styles/chart-theme'

interface Props {
  klines: Kline[]
  /** 主图叠加指标：MA5 / MA10 / MA20 / MA60 / BOLL */
  showMain?: string[]
  /** 副图指标：MACD / RSI / KDJ / ''（空=不显示） */
  showSub?: string
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  height: 600,
  showMain: () => ['MA5', 'MA20'],
  showSub: 'MACD',
})

const rootRef = ref<HTMLDivElement>()
const svgRef = ref<SVGSVGElement>()
const dims = ref({ width: 0, height: props.height })
const hoverInfo = ref<{
  x: number; y: number; date: string
  open: number; high: number; low: number; close: number
  up: boolean; change_pct: number | null; volume: number
  indicators: Record<string, number | null> | null
} | null>(null)

// ── ResizeObserver ─────────────────────────────────────────────
let ro: ResizeObserver | null = null
onMounted(async () => {
  await nextTick()
  if (!rootRef.value) return
  ro = new ResizeObserver(() => updateSize())
  ro.observe(rootRef.value)
  updateSize()
})
onBeforeUnmount(() => ro?.disconnect())

function updateSize() {
  if (!rootRef.value) return
  const rect = rootRef.value.getBoundingClientRect()
  dims.value = { width: Math.max(rect.width, 100), height: props.height }
}

// ── 布局 ────────────────────────────────────────────────────
// 主图占 65%（含成交量），副图占 25%，间距 2%
const MAIN_PCT = 0.62
const VOL_PCT  = 0.13   // 成交量条（在主图下方）
const SUB_PCT  = 0.22
const PAD_L    = 56
const PAD_R    = 12
const PAD_T    = 12
const PAD_B    = 24

const layout = computed(() => {
  const w = dims.value.width - PAD_L - PAD_R
  const total = dims.value.height - PAD_T - PAD_B - 16  // 16 = 主图与副图间距 ×2
  const mainH = total * MAIN_PCT
  const volH  = total * VOL_PCT
  const subH  = total * SUB_PCT
  return {
    main: { x: PAD_L, y: PAD_T, w, h: mainH },
    vol:  { x: PAD_L, y: PAD_T + mainH + 4, w, h: volH },
    sub:  { x: PAD_L, y: PAD_T + mainH + volH + 12, w, h: subH },
  }
})

// ── 比例尺 ────────────────────────────────────────────────────
const sortedKlines = computed(() => {
  return [...props.klines].sort((a, b) => a.date.localeCompare(b.date))
})

const yRangeMain = computed(() => {
  const all = sortedKlines.value.flatMap(k => [k.high, k.low])
  if (props.showMain.includes('BOLL')) {
    sortedKlines.value.forEach(k => {
      if (k.boll_up != null) all.push(k.boll_up)
      if (k.boll_dn != null) all.push(k.boll_dn)
    })
  }
  if (all.length === 0) return { min: 0, max: 100 }
  return { min: Math.min(...all), max: Math.max(...all) }
})

const yRangeSub = computed(() => {
  const k = props.showSub
  if (!k) return { min: 0, max: 1 }
  const all: number[] = []
  sortedKlines.value.forEach(line => {
    if (k === 'MACD') {
      if (line.macd_dif != null) all.push(line.macd_dif)
      if (line.macd_dea != null) all.push(line.macd_dea)
      if (line.macd_bar != null) all.push(line.macd_bar, -line.macd_bar)
    } else if (k === 'RSI') {
      if (line.rsi6 != null) all.push(line.rsi6)
    } else if (k === 'KDJ') {
      if (line.kdj_k != null) all.push(line.kdj_k)
      if (line.kdj_d != null) all.push(line.kdj_d)
      if (line.kdj_j != null) all.push(line.kdj_j)
    }
  })
  if (k === 'RSI') return { min: 0, max: 100 }
  if (all.length === 0) return { min: -1, max: 1 }
  const abs = Math.max(...all.map(Math.abs))
  return { min: -abs, max: abs }
})

const volMax = computed(() => {
  return Math.max(...sortedKlines.value.map(k => k.volume), 1)
})

function xAt(i: number): number {
  const n = sortedKlines.value.length
  if (n <= 1) return layout.value.main.x + layout.value.main.w / 2
  return layout.value.main.x + (i / (n - 1)) * layout.value.main.w
}

function yMain(price: number): number {
  const { min, max } = yRangeMain.value
  const { y, h } = layout.value.main
  if (max === min) return y + h / 2
  return y + (1 - (price - min) / (max - min)) * h
}

function ySub(v: number): number {
  const { min, max } = yRangeSub.value
  const { y, h } = layout.value.sub
  if (max === min) return y + h / 2
  return y + (1 - (v - min) / (max - min)) * h
}

function yVol(v: number): number {
  const { y, h } = layout.value.vol
  return y + h - (v / volMax.value) * h
}

const candleWidth = computed(() => {
  const n = sortedKlines.value.length
  if (n === 0) return 4
  return Math.max(1, Math.min(8, (layout.value.main.w / n) * 0.7))
})

// ── 渲染 ─────────────────────────────────────────────────────
function buildSvg(): string {
  const klines = sortedKlines.value
  if (klines.length === 0) {
    return `<text x="50%" y="50%" text-anchor="middle" fill="#9ca3af" font-size="14">暂无数据</text>`
  }

  const parts: string[] = []

  // ── 主图：网格 + 坐标 ──
  parts.push(buildMainGrid())

  // ── 主图：蜡烛 ──
  klines.forEach((k, i) => {
    const x = xAt(i)
    const isUp = k.close >= k.open
    const color = isUp ? chartTheme.candle.up : chartTheme.candle.down
    const yOpen = yMain(k.open)
    const yClose = yMain(k.close)
    const yHigh = yMain(k.high)
    const yLow = yMain(k.low)
    const bodyTop = Math.min(yOpen, yClose)
    const bodyH = Math.max(1, Math.abs(yClose - yOpen))
    const w = candleWidth.value

    // 影线
    parts.push(`<line x1="${x}" y1="${yHigh}" x2="${x}" y2="${yLow}" stroke="${color}" stroke-width="1"/>`)
    // 实体
    parts.push(`<rect x="${x - w / 2}" y="${bodyTop}" width="${w}" height="${bodyH}" fill="${color}" stroke="${color}" rx="0.5"/>`)
  })

  // ── 主图：MA 叠加线 ──
  const maColors: Record<string, string> = {
    MA5:  chartTheme.indicators.MA5,
    MA10: chartTheme.indicators.MA10,
    MA20: chartTheme.indicators.MA20,
    MA60: chartTheme.indicators.MA60,
  }
  for (const m of props.showMain.filter(x => x.startsWith('MA'))) {
    const key = m.toLowerCase() as 'ma5' | 'ma10' | 'ma20' | 'ma60'
    const path = klines
      .map((k, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yMain((k as any)[key] ?? 0)}`)
      .filter(p => !p.includes(' NaN'))
      .join(' ')
    if (path) {
      parts.push(`<path d="${path}" fill="none" stroke="${maColors[m]}" stroke-width="1.2"/>`)
    }
  }

  // ── 主图：BOLL ──
  if (props.showMain.includes('BOLL')) {
    const upper = klines.map((k, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yMain(k.boll_up ?? 0)}`).join(' ')
    const mid   = klines.map((k, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yMain(k.boll_mid ?? 0)}`).join(' ')
    const lower = klines.map((k, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yMain(k.boll_dn ?? 0)}`).join(' ')
    parts.push(`<path d="${upper}" fill="none" stroke="${chartTheme.indicators.BOLL_UP}" stroke-width="1" stroke-dasharray="4,2"/>`)
    parts.push(`<path d="${mid}" fill="none" stroke="${chartTheme.indicators.BOLL_MID}" stroke-width="1"/>`)
    parts.push(`<path d="${lower}" fill="none" stroke="${chartTheme.indicators.BOLL_DN}" stroke-width="1" stroke-dasharray="4,2"/>`)
  }

  // ── 主图：最近价横线 ──
  const last = klines[klines.length - 1]
  if (last) {
    const y = yMain(last.close)
    parts.push(`<line x1="${layout.value.main.x}" y1="${y}" x2="${layout.value.main.x + layout.value.main.w}" y2="${y}" stroke="#9ca3af" stroke-dasharray="2,4"/>`)
    parts.push(`<text x="${layout.value.main.x + layout.value.main.w - 4}" y="${y - 4}" text-anchor="end" fill="${last.close >= last.open ? chartTheme.candle.up : chartTheme.candle.down}" font-size="11" font-weight="600">${last.close.toFixed(2)}</text>`)
  }

  // ── 成交量 ──
  parts.push(buildVolGrid())
  klines.forEach((k, i) => {
    const x = xAt(i)
    const w = candleWidth.value
    const isUp = k.close >= k.open
    const color = isUp ? chartTheme.volume.up : chartTheme.volume.down
    const yTop = yVol(k.volume)
    const h = layout.value.vol.y + layout.value.vol.h - yTop
    parts.push(`<rect x="${x - w / 2}" y="${yTop}" width="${w}" height="${Math.max(1, h)}" fill="${color}"/>`)
  })

  // ── 副图 ──
  if (props.showSub) {
    parts.push(buildSubContent())
  }

  return parts.join('')
}

function buildMainGrid(): string {
  const { x, y, w, h } = layout.value.main
  const lines: string[] = []
  // 5 条水平网格
  const { min, max } = yRangeMain.value
  for (let i = 0; i <= 4; i++) {
    const yy = y + (i / 4) * h
    const price = max - (i / 4) * (max - min)
    lines.push(`<line x1="${x}" y1="${yy}" x2="${x + w}" y2="${yy}" stroke="${chartTheme.grid.line}" stroke-width="0.5"/>`)
    lines.push(`<text x="${x - 4}" y="${yy + 4}" text-anchor="end" fill="${chartTheme.axis.text}" font-size="10">${price.toFixed(2)}</text>`)
  }
  return lines.join('')
}

function buildVolGrid(): string {
  const { x, y, w, h } = layout.value.vol
  return [
    `<text x="${x - 4}" y="${y + 10}" text-anchor="end" fill="${chartTheme.axis.text}" font-size="10">VOL</text>`,
    `<line x1="${x}" y1="${y}" x2="${x + w}" y2="${y}" stroke="${chartTheme.grid.line}" stroke-width="0.5"/>`,
    `<line x1="${x}" y1="${y + h}" x2="${x + w}" y2="${y + h}" stroke="${chartTheme.grid.line}" stroke-width="0.5"/>`,
  ].join('')
}

function buildSubContent(): string {
  const { x, y, w, h } = layout.value.sub
  const lines: string[] = []
  // 边框
  lines.push(`<line x1="${x}" y1="${y}" x2="${x + w}" y2="${y}" stroke="${chartTheme.grid.line}" stroke-width="0.5"/>`)
  lines.push(`<line x1="${x}" y1="${y + h}" x2="${x + w}" y2="${y + h}" stroke="${chartTheme.grid.line}" stroke-width="0.5"/>`)
  // 中线（0）
  const yMid = ySub(0)
  if (yMid >= y && yMid <= y + h) {
    lines.push(`<line x1="${x}" y1="${yMid}" x2="${x + w}" y2="${yMid}" stroke="${chartTheme.grid.line}" stroke-width="0.5" stroke-dasharray="3,3"/>`)
  }
  // 标题
  lines.push(`<text x="${x + 4}" y="${y + 12}" fill="${chartTheme.axis.text}" font-size="10" font-weight="600">${props.showSub}</text>`)

  const klines = sortedKlines.value

  if (props.showSub === 'MACD') {
    klines.forEach((k, i) => {
      const xc = xAt(i)
      const w = candleWidth.value
      const bar = k.macd_bar ?? 0
      const yBar = ySub(Math.max(0, bar))
      const yBar2 = ySub(Math.min(0, bar))
      const isUp = bar >= 0
      const color = isUp ? chartTheme.indicators.MACD_BAR_UP : chartTheme.indicators.MACD_BAR_DOWN
      const rectH = Math.max(1, Math.abs(yBar2 - yBar))
      lines.push(`<rect x="${xc - w / 2}" y="${isUp ? yBar : yMid}" width="${w}" height="${isUp ? rectH : Math.max(1, yBar2 - yMid)}" fill="${color}"/>`)
    })
    const dif = klines.map((k, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${ySub(k.macd_dif ?? 0)}`).join(' ')
    const dea = klines.map((k, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${ySub(k.macd_dea ?? 0)}`).join(' ')
    lines.push(`<path d="${dif}" fill="none" stroke="${chartTheme.indicators.MACD_DIF}" stroke-width="1.2"/>`)
    lines.push(`<path d="${dea}" fill="none" stroke="${chartTheme.indicators.MACD_DEA}" stroke-width="1.2"/>`)
  } else if (props.showSub === 'RSI') {
    const rsi = klines.map((k, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${ySub(k.rsi6 ?? 50)}`).join(' ')
    lines.push(`<path d="${rsi}" fill="none" stroke="${chartTheme.indicators.RSI}" stroke-width="1.2"/>`)
    // 70 / 30 横线
    const y70 = ySub(70), y30 = ySub(30)
    lines.push(`<line x1="${x}" y1="${y70}" x2="${x + w}" y2="${y70}" stroke="#ef4444" stroke-width="0.5" stroke-dasharray="3,3"/>`)
    lines.push(`<line x1="${x}" y1="${y30}" x2="${x + w}" y2="${y30}" stroke="#22c55e" stroke-width="0.5" stroke-dasharray="3,3"/>`)
  } else if (props.showSub === 'KDJ') {
    const k = klines.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${ySub(v.kdj_k ?? 0)}`).join(' ')
    const d = klines.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${ySub(v.kdj_d ?? 0)}`).join(' ')
    const j = klines.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${ySub(v.kdj_j ?? 0)}`).join(' ')
    lines.push(`<path d="${k}" fill="none" stroke="${chartTheme.indicators.KDJ_K}" stroke-width="1.2"/>`)
    lines.push(`<path d="${d}" fill="none" stroke="${chartTheme.indicators.KDJ_D}" stroke-width="1.2"/>`)
    lines.push(`<path d="${j}" fill="none" stroke="${chartTheme.indicators.KDJ_J}" stroke-width="1.2"/>`)
  }

  // Y 轴标尺
  const { min, max } = yRangeSub.value
  lines.push(`<text x="${x - 4}" y="${y + 8}" text-anchor="end" fill="${chartTheme.axis.text}" font-size="10">${max.toFixed(2)}</text>`)
  lines.push(`<text x="${x - 4}" y="${y + h}" text-anchor="end" fill="${chartTheme.axis.text}" font-size="10">${min.toFixed(2)}</text>`)

  return lines.join('')
}

// ── 坐标轴：底部日期 ──
const dateLabels = computed(() => {
  const klines = sortedKlines.value
  if (klines.length === 0) return ''
  const n = Math.min(6, klines.length)
  const indices: number[] = []
  for (let i = 0; i < n; i++) {
    indices.push(Math.floor((i / (n - 1)) * (klines.length - 1)))
  }
  return indices
    .map(i => `<text x="${xAt(i)}" y="${dims.value.height - 8}" text-anchor="middle" fill="${chartTheme.axis.text}" font-size="10">${klines[i].date.slice(5)}</text>`)
    .join('')
})

// ── 渲染管道 ──────────────────────────────────────────────────
function render() {
  if (!svgRef.value) return
  svgRef.value.innerHTML = buildSvg() + dateLabels.value
}

watch([
  () => props.klines,
  () => props.showMain,
  () => props.showSub,
  () => dims.value,
], render, { deep: true })

onMounted(render)

// ── 鼠标交互：十字光标 ──
function onMove(ev: MouseEvent) {
  if (!svgRef.value || sortedKlines.value.length === 0) return
  const rect = svgRef.value.getBoundingClientRect()
  const px = ev.clientX - rect.left
  const py = ev.clientY - rect.top

  // 找最近的 K 线
  const layout_ = layout.value
  const n = sortedKlines.value.length
  if (n === 0) return
  const xRel = (px - layout_.main.x) / layout_.main.w
  if (xRel < 0 || xRel > 1) {
    hoverInfo.value = null
    return
  }
  const idx = Math.round(xRel * (n - 1))
  const k = sortedKlines.value[idx]
  const x = xAt(idx)
  const up = k.close >= k.open

  hoverInfo.value = {
    x, y: py, date: k.date,
    open: k.open, high: k.high, low: k.low, close: k.close,
    up, change_pct: k.change_pct, volume: k.volume,
    indicators: buildIndicators(k),
  }
}

function buildIndicators(k: Kline) {
  const out: Record<string, number | null> = {}
  if (props.showMain.includes('MA5') && k.ma5 != null) out['MA5'] = k.ma5
  if (props.showMain.includes('MA10') && k.ma10 != null) out['MA10'] = k.ma10
  if (props.showMain.includes('MA20') && k.ma20 != null) out['MA20'] = k.ma20
  if (props.showMain.includes('MA60') && k.ma60 != null) out['MA60'] = k.ma60
  if (props.showSub === 'MACD') {
    if (k.macd_dif != null) out['DIF'] = k.macd_dif
    if (k.macd_dea != null) out['DEA'] = k.macd_dea
    if (k.macd_bar != null) out['BAR'] = k.macd_bar
  } else if (props.showSub === 'RSI' && k.rsi6 != null) {
    out['RSI6'] = k.rsi6
  } else if (props.showSub === 'KDJ') {
    if (k.kdj_k != null) out['K'] = k.kdj_k
    if (k.kdj_d != null) out['D'] = k.kdj_d
    if (k.kdj_j != null) out['J'] = k.kdj_j
  }
  return Object.keys(out).length > 0 ? out : null
}

// ── 工具 ──
function formatVolume(v: number): string {
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toString()
}
</script>

<style scoped>
.candle-chart { position: relative; user-select: none; }
.candle-chart svg { display: block; }
</style>