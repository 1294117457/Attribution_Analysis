<!--
 * components/DailyKlineChart.vue
 *
 * 日 K：工具栏（周期 / 主图指标 / 副图）+ MiniKlineChart
 * 本身就是一张 InfoCard，直接放进面板 / 布局即可。
 * 指标由后端实时计算并随 getKlines 返回。
 * 使用方：StockExpandRow（表格展开行）、data-board-tabs/TechPanel（详情抽屉 / 数据看板）
 -->
<template>
  <InfoCard class="daily-kline">
    <template #title>
      <span class="chart-label">
        日 K
        <b v-if="lastDaily?.close != null">{{ lastDaily.close.toFixed(2) }}</b>
      </span>
    </template>
    <template #tools>
      <el-select
        v-model="dailyRange"
        size="small"
        placeholder="周期"
        style="width: 72px"
        @change="loadDailyKlines"
      >
        <el-option v-for="o in dailyOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-select
        v-model="dailyIndicators"
        size="small"
        multiple
        collapse-tags
        collapse-tags-tooltip
        placeholder="主图指标"
        style="width: 110px"
      >
        <el-option v-for="o in mainIndicatorOptions" :key="o.value" :label="o.label" :value="o.value">
          <span class="indicator-dot" :style="{ background: o.color }" />{{ o.label }}
        </el-option>
      </el-select>
      <el-select
        v-if="sub"
        v-model="dailySub"
        size="small"
        clearable
        placeholder="副图"
        style="width: 68px"
      >
        <el-option v-for="o in subIndicatorOptions" :key="o.value" :label="o.label" :value="o.value">
          <span class="indicator-dot" :style="{ background: o.color }" />{{ o.label }}
        </el-option>
      </el-select>
    </template>
    <template #extra>{{ dailyLoading ? '加载中…' : `${dailyKlines.length} 根` }}</template>
    <MiniKlineChart
      :title="''"
      hide-header
      :klines="dailyKlines"
      :loading="dailyLoading"
      :height="sub && dailySub ? height + subHeight : height"
      :show-main="dailyIndicators"
      :show-sub="sub ? dailySub : ''"
    />
  </InfoCard>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import InfoCard from '@/components/InfoCard.vue'
import MiniKlineChart from './MiniKlineChart.vue'
import { getKlines } from '@/views/stock-info/api'
import type { Kline } from '@/views/stock-info/api'

const props = withDefaults(defineProps<{
  symbol: string
  /** 无副图时的图表高度 */
  height?: number
  /** 开启副图时额外增加的高度 */
  subHeight?: number
  /** 是否提供副图（RSI / MACD / KDJ）选择 */
  sub?: boolean
}>(), {
  height: 145,
  subHeight: 35,
  sub: true,
})

const dailyOptions = [
  { label: '30 日', value: 30 },
  { label: '60 日', value: 60 },
  { label: '120 日', value: 120 },
  { label: '250 日', value: 250 },
]
const dailyRange = ref(60)

const mainIndicatorOptions = [
  { label: 'MA5',  value: 'MA5',  color: '#fbbf24' },
  { label: 'MA10', value: 'MA10', color: '#3b82f6' },
  { label: 'MA20', value: 'MA20', color: '#a855f7' },
  { label: 'MA60', value: 'MA60', color: '#06b6d4' },
  { label: 'BOLL', value: 'BOLL', color: '#f97316' },
]
const dailyIndicators = ref<string[]>(['MA5', 'MA20'])

const subIndicatorOptions = [
  { label: 'RSI',  value: 'RSI',  color: '#ec4899' },
  { label: 'MACD', value: 'MACD', color: '#3b82f6' },
  { label: 'KDJ',  value: 'KDJ',  color: '#14b8a6' },
]
const dailySub = ref('')

const dailyKlines = ref<Kline[]>([])
const dailyLoading = ref(false)
const lastDaily = computed(() => dailyKlines.value[0] ?? null)

async function loadDailyKlines() {
  dailyLoading.value = true
  try {
    const res = await getKlines(props.symbol, { limit: dailyRange.value, order_desc: true })
    dailyKlines.value = res.list ?? []
  } catch {
    dailyKlines.value = []
  } finally {
    dailyLoading.value = false
  }
}

watch(() => props.symbol, loadDailyKlines, { immediate: true })
</script>

<style scoped>
.chart-label {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}
.chart-label b {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.indicator-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

/* 外层已是卡片，占位符不再画边框 */
.daily-kline :deep(.mini-kline-placeholder) {
  background: transparent;
  border: none;
  color: #94a3b8;
}
</style>
