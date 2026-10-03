<!--
 * ConceptKlineCard.vue  （stock-info 版）
 *
 * 概念指数日 K + 实时快照（外层传入 data，本组件纯渲染）。
 * 配套设计文档：docs/dev/step3/04概念看板/stock_info详情中的概念.md §3.4
 *
 * 与 concept-board/ConceptKlineCard.vue 的差异：
 *  - import 路径锁定到本目录（避免跨目录耦合）
 *  - 顶部"指数走势"语义更明确
 *  - 其它样式、props 100% 兼容
-->
<template>
  <div class="ck-card">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <span class="font-bold">📈 {{ headerTitle }}</span>
            <el-tag v-if="meta" size="small" type="info">
              {{ meta.stock_count ?? 0 }} 只成分
            </el-tag>
            <el-tag v-if="meta?.source" size="small" effect="plain">
              {{ meta.source }}
            </el-tag>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="realtime" :class="realtimeColor" class="font-mono font-bold text-base">
              {{ realtime.price != null ? realtime.price.toFixed(2) : '—' }}
            </span>
            <span v-if="realtime?.pct_change != null" :class="realtimeColor" class="font-mono text-sm">
              {{ realtime.pct_change > 0 ? '+' : '' }}{{ realtime.pct_change.toFixed(2) }}%
            </span>
            <el-tag v-if="realtime?.stale" type="warning" size="small">STALE</el-tag>
            <el-tag v-else-if="realtime" type="success" size="small">实时</el-tag>
            <el-tag v-else size="small" type="info">无实时</el-tag>
          </div>
        </div>
      </template>

      <div v-loading="loading" class="ck-body">
        <MiniKlineChart
          v-if="klines.length"
          title=""
          :klines="klines"
          :loading="loading"
          :height="height"
          :show-main="['MA5', 'MA20']"
          show-sub="MACD"
        />
        <div v-else-if="!loading" class="ck-empty">
          <span class="text-gray-400 text-sm">暂无 K 线数据</span>
          <div v-if="hint" class="text-xs text-gray-400 mt-1">{{ hint }}</div>
        </div>
      </div>

      <div v-if="dataRange && klines.length" class="ck-footer text-xs text-gray-400">
        数据范围 {{ dataRange.start }} ~ {{ dataRange.end }} · 共 {{ dataRange.bars_count }} 根
        <span v-if="realtime?.trade_time"> · 最近行情 {{ realtime.trade_time }}</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MiniKlineChart from './MiniKlineChart.vue'
import type { Kline } from '../api'
import type {
  ConceptKlineBar,
  ConceptKlineMeta,
  ConceptKlineResponse,
  ConceptRealtime,
} from '../api'

const props = withDefaults(defineProps<{
  /** 概念名（顶部显示用） */
  conceptName: string
  /** 概念 index_code（用于区分同一概念多次进入） */
  indexCode: string
  /** K 线 + 实时 响应（外层传入，组件只负责渲染） */
  data: ConceptKlineResponse | null
  loading: boolean
  height?: number
  /** 错误提示（K 线为空时显示） */
  hint?: string
}>(), { height: 220 })

const klines = computed<Kline[]>(() => {
  if (!props.data) return []
  return props.data.kline.map((b: ConceptKlineBar) => ({
    symbol: props.indexCode,
    name: props.conceptName,
    date: b.date,
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
    volume: b.volume,
    amount: b.amount ?? null,
    change_pct: b.change_pct ?? null,
  }))
})

const realtime = computed<ConceptRealtime | null>(() => props.data?.realtime ?? null)
const meta = computed<ConceptKlineMeta | null>(() => props.data?.meta ?? null)
const dataRange = computed(() => props.data?.data_range)

const realtimeColor = computed(() => {
  const c = realtime.value?.color
  if (c === 'up') return 'text-red-500'
  if (c === 'down') return 'text-green-600'
  return 'text-gray-500'
})

const headerTitle = computed(() => {
  if (!props.conceptName) return '概念 K 线'
  return `${props.conceptName} · 指数走势`
})
</script>

<style scoped>
.ck-card { width: 100%; }
.ck-body { min-height: 220px; display: flex; align-items: center; justify-content: center; }
.ck-empty { padding: 2rem 0; text-align: center; }
.ck-footer { padding: 0.25rem 0.5rem 0; text-align: right; }
</style>
