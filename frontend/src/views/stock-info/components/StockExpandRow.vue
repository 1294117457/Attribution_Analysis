<template>
  <div class="expand-row">
    <div class="expand-charts">
      <div class="chart-col">
        <div class="chart-toolbar">
          <span class="chart-label">日 K</span>
          <el-select
            v-model="dailyRange"
            size="small"
            placeholder="周期"
            style="width: 90px"
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
            style="width: 130px"
          >
            <el-option v-for="o in mainIndicatorOptions" :key="o.value" :label="o.label" :value="o.value">
              <span class="indicator-dot" :style="{ background: o.color }" />{{ o.label }}
            </el-option>
          </el-select>
          <el-select
            v-model="dailySub"
            size="small"
            clearable
            placeholder="副图"
            style="width: 90px"
          >
            <el-option v-for="o in subIndicatorOptions" :key="o.value" :label="o.label" :value="o.value">
              <span class="indicator-dot" :style="{ background: o.color }" />{{ o.label }}
            </el-option>
          </el-select>
        </div>
        <MiniKlineChart
          :title="''"
          :klines="dailyKlines"
          :loading="dailyLoading"
          :height="dailySub ? 200 : 150"
          :show-main="dailyIndicators"
          :show-sub="dailySub"
        />
      </div>
      <div class="chart-col">
        <div class="chart-toolbar">
          <span class="chart-label">分 K</span>
          <el-select
            v-model="minuteInterval"
            size="small"
            placeholder="周期"
            style="width: 80px"
            @change="onIntervalChange"
          >
            <el-option v-for="o in intervalOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-select
            v-model="minuteDays"
            size="small"
            placeholder="天数"
            style="width: 76px"
            @change="loadMinuteKlines()"
          >
            <el-option v-for="o in minuteDayOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-tag v-if="trading && !paused" size="small" type="danger" effect="plain">实时 · 15 秒</el-tag>
          <el-tag v-else-if="!trading" size="small" type="info" effect="plain">已收盘</el-tag>
          <el-link v-if="paused" type="warning" :underline="false" class="minute-hint" @click="resume">
            实时更新已暂停 · 重试
          </el-link>
          <span v-else-if="minuteUpdatedAt" class="minute-hint">{{ minuteUpdatedAt }}</span>
        </div>
        <MiniKlineChart
          :title="''"
          :klines="minuteKlinesAsDaily"
          :loading="minuteLoading"
          :height="150"
          :show-main="[]"
        />
      </div>
    </div>
    <div class="expand-summary">
      <span v-if="dailyKlines.length">
        日K最新 <b>{{ lastDaily?.close?.toFixed(2) ?? '—' }}</b>
      </span>
      <span v-if="minuteKlines.length">
        分K最新 <b>{{ lastMinute?.close?.toFixed(2) ?? '—' }}</b>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import MiniKlineChart from './MiniKlineChart.vue'
import { getKlines, getMinuteKlines } from '@/views/stock-info/api'
import type { Kline, MinuteKline } from '@/views/stock-info/api'
import { useRealtimePoll } from '@/composables/useRealtimePoll'

const props = defineProps<{
  symbol: string
}>()

// ── 日K 选项 ───────────────────────────────────────────
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

// ── 分K 选项（周期 + 天数 两个独立选择器） ────────────
const intervalOptions = [
  { label: '1min',  value: '1min' },
  { label: '5min',  value: '5min' },
  { label: '15min', value: '15min' },
  { label: '30min', value: '30min' },
  { label: '60min', value: '60min' },
]
// 1 分钟只看当天；其他周期最多 5 日（多日走势看日 K）
const minuteInterval = ref('5min')
const minuteDays = ref(1)
const minuteDayOptions = computed(() =>
  minuteInterval.value === '1min'
    ? [{ label: '当天', value: 1 }]
    : [
        { label: '当天', value: 1 },
        { label: '3 日', value: 3 },
        { label: '5 日', value: 5 },
      ],
)

function onIntervalChange() {
  if (minuteInterval.value === '1min') minuteDays.value = 1
  loadMinuteKlines()
}

// ── 数据 ───────────────────────────────────────────────
const dailyKlines = ref<Kline[]>([])
const minuteKlines = ref<MinuteKline[]>([])
const dailyLoading = ref(false)
const minuteLoading = ref(false)

const lastDaily = computed(() => dailyKlines.value[0] ?? null)
const lastMinute = computed(() => minuteKlines.value[0] ?? null)

const minuteKlinesAsDaily = computed<Kline[]>(() =>
  minuteKlines.value.map(m => ({
    date: m.datetime,
    open: m.open,
    high: m.high,
    low: m.low,
    close: m.close,
    volume: m.volume,
    amount: m.amount,
    change_pct: null,
    ma5: null, ma10: null, ma20: null, ma60: null,
    ema12: null, ema26: null,
    macd_dif: null, macd_dea: null, macd_bar: null,
    rsi6: null, rsi12: null, rsi24: null,
    kdj_k: null, kdj_d: null, kdj_j: null,
    boll_up: null, boll_mid: null, boll_dn: null,
  }))
)

// ── 加载 ───────────────────────────────────────────────
async function loadDailyKlines() {
  dailyLoading.value = true
  try {
    const res = await getKlines(props.symbol, { limit: dailyRange.value, order_desc: true })
    dailyKlines.value = res.items ?? []
  } catch {
    dailyKlines.value = []
  } finally {
    dailyLoading.value = false
  }
}

const minuteUpdatedAt = ref('')

/** silent=true：轮询刷新，不显示 loading、失败时保留上一次的图并把错误抛给轮询器计数 */
async function loadMinuteKlines(silent = false) {
  if (!silent) minuteLoading.value = true
  try {
    const res = await getMinuteKlines(props.symbol, {
      interval: minuteInterval.value,
      days: minuteDays.value,
    })
    minuteKlines.value = res.items ?? []
    minuteUpdatedAt.value = res.fetched_at ? `更新于 ${res.fetched_at.slice(11, 19)}` : ''
  } catch (e) {
    if (silent) throw e
    minuteKlines.value = []
  } finally {
    if (!silent) minuteLoading.value = false
  }
}

const { paused, trading, resume } = useRealtimePoll(() => loadMinuteKlines(true), { interval: 15_000 })

watch(() => props.symbol, () => {
  loadDailyKlines()
  loadMinuteKlines()
})

onMounted(() => {
  loadDailyKlines()
  loadMinuteKlines()
})
</script>

<style scoped>
.expand-row {
  padding: 8px 4px;
}

.expand-charts {
  display: flex;
  gap: 16px;
}

.chart-col {
  flex: 1;
  min-width: 0;
}

.chart-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.chart-label {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  white-space: nowrap;
}

.minute-hint {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
}

.indicator-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.expand-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}

.expand-summary b {
  color: #111827;
}
</style>
