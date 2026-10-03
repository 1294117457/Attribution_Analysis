<!--
 * ConceptMinuteChart.vue
 *
 * 概念当日分时折线图（SVG 手画，无图表库依赖）
 *
 * 数据来源：getConceptMinute(index_code)
 *  - points: 9:30~15:00 每分钟 1 点，共 ≤ 241 点
 *  - pre_close: 昨收基线（虚线）
 *  - price / change / change_pct: 最后一点
 *
 * 展示策略：
 *  - 折线颜色：涨红跌绿平灰（同花顺配色）
 *  - pre_close 基线：虚线
 *  - X 轴：09:30 / 10:30 / 11:30 / 13:00 / 14:00 / 15:00 五个刻度
 *  - Y 轴：以 pre_close 为中心上下等比
 *  - hover（移动端暂不支持）：tooltip 显示 trade_time / price / change_pct
 *
 * 不实时刷新（用户要求"获取后不实时刷新"）。
 *
 * 配套设计文档：docs/dev/step3/04概念看板/stock_info详情中的概念.md §3.3
-->
<template>
  <div class="cmc-wrap">
    <!-- 头部信息 -->
    <div class="cmc-header">
      <div class="cmc-title">
        <span class="font-semibold">⏱️ 当日分时</span>
        <el-tag v-if="data?.points?.length" size="small" type="info" effect="plain">
          共 {{ data.points.length }} 点
        </el-tag>
        <el-tag v-else-if="!loading" size="small" type="info" effect="plain">暂无</el-tag>
      </div>
      <div class="cmc-meta">
        <span v-if="effectivePctChange != null" :class="colorClass" class="mono font-bold">
          {{ effectivePctChange > 0 ? '+' : '' }}{{ effectivePctChange.toFixed(2) }}%
        </span>
        <span v-if="data?.pre_close != null" class="text-xs text-gray-400">
          昨收 {{ data.pre_close.toFixed(2) }}
        </span>
        <el-tag v-if="data?.stale" type="warning" size="small">STALE</el-tag>
      </div>
    </div>

    <!-- 加载中 / 空态 -->
    <div v-if="loading" v-loading="true" class="cmc-body" :style="{ height: `${height}px` }" />
    <div v-else-if="!points.length" class="cmc-empty" :style="{ height: `${height}px` }">
      <span class="text-xs text-gray-400">
        {{ data?.stale ? '行情源暂不可用' : '暂无分时数据（非交易时段或概念已归档）' }}
      </span>
    </div>

    <!-- 折线图 -->
    <div v-else class="cmc-body" :style="{ height: `${height}px` }">
      <svg
        :viewBox="`0 0 ${chartW} ${chartH}`"
        preserveAspectRatio="none"
        class="cmc-svg"
        @mousemove="onHover"
        @mouseleave="hoveredIdx = null"
      >
        <!-- pre_close 基线（虚线） -->
        <line
          v-if="preClose != null && preClose >= yMin && preClose <= yMax"
          :x1="0" :x2="chartW"
          :y1="yToPx(preClose)" :y2="yToPx(preClose)"
          stroke="#94a3b8"
          stroke-width="1"
          stroke-dasharray="3 3"
        />

        <!-- 价格折线 + 区域填充 -->
        <path :d="areaPath" :fill="`url(#cmc-grad-${colorKey})`" opacity="0.18" />
        <path :d="linePath" :stroke="lineColor" stroke-width="1.4" fill="none" />

        <!-- hover 高亮点 -->
        <circle
          v-if="hoveredIdx != null && points[hoveredIdx]"
          :cx="xToPx(hoveredIdx)"
          :cy="yToPx(points[hoveredIdx].price)"
          :r="3"
          :fill="lineColor"
        />

        <!-- 渐变定义 -->
        <defs>
          <linearGradient :id="`cmc-grad-${colorKey}`" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="lineColor" stop-opacity="0.5" />
            <stop offset="100%" :stop-color="lineColor" stop-opacity="0" />
          </linearGradient>
        </defs>
      </svg>

      <!-- X 轴时间刻度 -->
      <div class="cmc-x-axis">
        <span
          v-for="t in xLabels"
          :key="t.label"
          class="cmc-x-label"
          :style="{ left: `${t.pos * 100}%` }"
        >
          {{ t.label }}
        </span>
      </div>

      <!-- hover tooltip -->
      <div
        v-if="hoveredPoint"
        class="cmc-tooltip"
        :style="tooltipStyle"
      >
        <div>{{ hoveredPoint.trade_time }}</div>
        <div class="mono font-bold">{{ hoveredPoint.price.toFixed(2) }}</div>
        <div v-if="hoveredPoint.change_pct != null" :class="colorClass" class="mono text-xs">
          {{ hoveredPoint.change_pct > 0 ? '+' : '' }}{{ hoveredPoint.change_pct.toFixed(2) }}%
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ConceptMinuteResponse } from '../api'

const props = withDefaults(defineProps<{
  index_code: string
  concept_name: string
  data: ConceptMinuteResponse | null
  loading: boolean
  height?: number
  /** 点击时锁定的涨跌幅（从 Tag.snapshot.pct_change 传入） */
  frozen_pct_change?: number | null
}>(), {
  height: 160,
  frozen_pct_change: null,
})

// ── 常量 ──
const chartW = 600      // viewBox 宽（与 svg 实际宽度无关，由 CSS 拉伸）
const chartH = 120      // viewBox 高
const padTop = 8
const padBottom = 4

// ── 计算用的 ref ──
const hoveredIdx = ref<number | null>(null)

const points = computed(() => props.data?.points ?? [])
const preClose = computed(() => props.data?.pre_close ?? null)

/** 最终显示的涨跌幅：data.pct_change 优先，否则用 frozen 兜底 */
const effectivePctChange = computed<number | null>(() => {
  if (props.data?.pct_change != null) return props.data.pct_change
  if (props.frozen_pct_change != null) return props.frozen_pct_change
  // 从 points 最后一点反推
  const last = points.value[points.value.length - 1]
  return last?.change_pct ?? null
})

/** 折线主色（同花顺配色：红涨 / 绿跌 / 灰平） */
const lineColor = computed(() => {
  const pct = effectivePctChange.value
  if (pct == null || pct === 0) return '#9ca3af'
  return pct > 0 ? '#dc2626' : '#16a34a'
})

const colorKey = computed(() => {
  const pct = effectivePctChange.value
  if (pct == null || pct === 0) return 'flat'
  return pct > 0 ? 'up' : 'down'
})

const colorClass = computed(() => {
  const pct = effectivePctChange.value
  if (pct == null || pct === 0) return 'text-gray-400'
  return pct > 0 ? 'text-red-500' : 'text-green-600'
})

// ── Y 轴范围 ──
const yMin = computed(() => {
  if (preClose.value == null) {
    if (!points.value.length) return 0
    return Math.min(...points.value.map(p => p.price)) * 0.995
  }
  // 以 pre_close 为中心，所有点的 min/max 取上下等比
  const all = points.value.map(p => p.price).concat([preClose.value])
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const mid = preClose.value
  const range = Math.max(hi - mid, mid - lo, mid * 0.005)  // 至少 0.5% 的范围
  return mid - range
})
const yMax = computed(() => {
  if (preClose.value == null) {
    if (!points.value.length) return 1
    return Math.max(...points.value.map(p => p.price)) * 1.005
  }
  const all = points.value.map(p => p.price).concat([preClose.value])
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const mid = preClose.value
  const range = Math.max(hi - mid, mid - lo, mid * 0.005)
  return mid + range
})

function yToPx(price: number): number {
  const range = yMax.value - yMin.value || 1
  const ratio = (price - yMin.value) / range
  return padTop + (1 - ratio) * (chartH - padTop - padBottom)
}

function xToPx(idx: number): number {
  if (points.value.length <= 1) return 0
  return (idx / (points.value.length - 1)) * chartW
}

// ── 路径生成 ──
const linePath = computed(() => {
  if (!points.value.length) return ''
  return points.value
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xToPx(i).toFixed(2)} ${yToPx(p.price).toFixed(2)}`)
    .join(' ')
})

const areaPath = computed(() => {
  if (!points.value.length) return ''
  const top = points.value
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xToPx(i).toFixed(2)} ${yToPx(p.price).toFixed(2)}`)
    .join(' ')
  // 闭合到底部
  const last = points.value.length - 1
  return `${top} L ${xToPx(last).toFixed(2)} ${chartH} L 0 ${chartH} Z`
})

// ── X 轴时间标签（5 个：09:30 / 10:30 / 11:30 / 13:00 / 14:00 / 15:00 中选 5 个）
const xLabels = computed<{ label: string; pos: number }[]>(() => {
  if (!points.value.length) return []
  // 交易时段总长 240 分钟（9:30~15:00 含中午休市简化）
  // 用 idx / (N-1) 比例映射
  const total = points.value.length - 1
  const anchors = [
    { label: '09:30', min: 0 },
    { label: '10:30', min: 60 },
    { label: '11:30', min: 120 },
    { label: '13:30', min: 180 },
    { label: '15:00', min: 240 },
  ]
  return anchors.map(a => ({
    label: a.label,
    pos: total > 0 ? a.min / 240 : 0,
  }))
})

// ── hover ──
const hoveredPoint = computed(() => {
  if (hoveredIdx.value == null) return null
  return points.value[hoveredIdx.value] ?? null
})

const tooltipStyle = computed<Record<string, string>>(() => {
  if (hoveredIdx.value == null) return { display: 'none' }
  const xPct = (hoveredIdx.value / Math.max(1, points.value.length - 1))
  const left = `${xPct * 100}%`
  // 边界检测：左 25% 偏右 / 右 25% 偏左
  const anchor = xPct < 0.25 ? 'left' : xPct > 0.75 ? 'right' : 'center'
  return {
    left,
    transform: anchor === 'left' ? 'translateY(-50%)'
      : anchor === 'right' ? 'translate(-100%, -50%)'
      : 'translate(-50%, -50%)',
    top: '50%',
  }
})

function onHover(ev: MouseEvent) {
  if (!points.value.length) return
  const target = ev.currentTarget as SVGElement
  const rect = target.getBoundingClientRect()
  const xPct = (ev.clientX - rect.left) / rect.width
  const idx = Math.round(xPct * (points.value.length - 1))
  hoveredIdx.value = Math.max(0, Math.min(points.value.length - 1, idx))
}
</script>

<style scoped>
.cmc-wrap {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  overflow: hidden;
}

.cmc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px dashed #e5e7eb;
  background: #f8fafc;
}
.cmc-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.cmc-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cmc-body {
  position: relative;
  width: 100%;
}
.cmc-svg {
  display: block;
  width: 100%;
  height: calc(100% - 18px);
  cursor: crosshair;
}

.cmc-x-axis {
  position: relative;
  height: 18px;
  border-top: 1px solid #f1f5f9;
}
.cmc-x-label {
  position: absolute;
  top: 2px;
  font-size: 10px;
  color: #94a3b8;
  transform: translateX(-50%);
  font-family: ui-monospace, monospace;
  white-space: nowrap;
}

.cmc-empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.cmc-tooltip {
  position: absolute;
  background: rgba(15, 23, 42, 0.92);
  color: #f1f5f9;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  pointer-events: none;
  white-space: nowrap;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
.cmc-tooltip .mono {
  font-family: ui-monospace, monospace;
}
</style>
