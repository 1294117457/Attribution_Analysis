# 04 — 多股对比 Drawer（全链路方案）

> 状态：方案，**未改代码**
> 范围：**纯前端**通用组件（嵌入到 realtime-board / concept-board / my-views 三页）
> 后端：**0 改动**（复用 `/stocks/{symbol}/analysis` 已有接口）

---

## 1. 业务需求

| 维度 | 说明 |
|---|---|
| 场景 | 选中 2~5 只股票快速比较（基础信息 + 叠加 K 线 + 关键指标对比） |
| 核心功能 | ① 基础信息并列卡片（代码 / 行业 / PE / PB / 总市值） ② 关键财务对比表（17 指标最新值） ③ K 线叠加图（同一图表画多股 close） ④ 涨跌对比柱状图 |
| 入口 | ① `/home/realtime-board` 顶部「对比 (N)」按钮（选中 2~5 行） ② `/home/concept-board` 成分股表格勾选 2~5 行 ③ `/home/my-views` 卡片占位（未来扩展） |
| 实时 | 仅分 K 部分每 15s 轮询（复用 `useRealtimePoll`） |

---

## 2. 后端设计

**0 改动**。复用现有：

| 接口 | 用途 |
|---|---|
| `GET /stocks/{symbol}/analysis` | 单股完整数据（stock + summary + klines + pools），详见 `stockInfo概要.md` |
| `GET /klines/{symbol}?days=N` | K 线列表 |
| `GET /concepts/board/members` | 成分股列表（仅概念大盘用） |

数据获取策略：在前端并发请求 N 次 `/stocks/{symbol}/analysis`，Promise.all 等待。

---

## 3. 前端设计

### 3.1 文件清单

```
frontend/src/
├── components/
│   └── StockCompareDrawer.vue          ← 通用对比抽屉（核心）
└── views/
    └── realtime-board/                （02 已建）
        └── components/
            └── RealtimeBoard.vue        ← 嵌入点（顶部按钮 + 抽屉）
```

### 3.2 `frontend/src/components/StockCompareDrawer.vue`

```vue
<template>
  <el-drawer v-model="visible" :size="1080" :with-header="false" direction="rtl">
    <div class="sc-wrap" v-if="symbols.length">
      <!-- Header -->
      <header class="sc-header">
        <button class="sc-close" @click="close">×</button>
        <div>
          <div class="sc-title">📊 多股对比</div>
          <div class="sc-meta">已选 {{ symbols.length }} 只：{{ symbols.join(' · ') }}</div>
        </div>
        <div class="sc-actions">
          <el-button @click="refreshAll">刷新</el-button>
          <el-button type="primary" @click="close">关闭</el-button>
        </div>
      </header>

      <!-- Section 1：基础信息卡片 -->
      <section class="sc-section">
        <h3 class="sc-h3">🏷️ 基础信息</h3>
        <div class="sc-cards">
          <div v-for="d in dataList" :key="d.symbol" class="sc-card">
            <div class="sc-card__head">
              <span class="sc-card__sym">{{ d.symbol }}</span>
              <span class="sc-card__name">{{ d.stock.name }}</span>
            </div>
            <div class="sc-card__row"><span>市场</span><span>{{ d.stock.industry || '—' }}</span></div>
            <div class="sc-card__row"><span>行业</span><span>{{ d.stock.industry || '—' }}</span></div>
            <div class="sc-card__row"><span>PE(TTM)</span><span class="mono">{{ d.summary.pe_ttm.toFixed(1) }}</span></div>
            <div class="sc-card__row"><span>所属池</span>
              <span>
                <el-tag v-for="p in d.pools" :key="p.pool_id" size="small" effect="plain" class="mr-1">{{ p.name }}</el-tag>
                <span v-if="!d.pools.length" class="text-gray-400">—</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Section 2：关键财务指标对比表 -->
      <section class="sc-section">
        <h3 class="sc-h3">📈 关键指标对比</h3>
        <el-table :data="indicatorRows" class="sc-table">
          <el-table-column prop="label" label="指标" width="140" fixed />
          <el-table-column v-for="d in dataList" :key="d.symbol" :label="d.symbol" align="right">
            <template #default="{ row }">
              <span class="mono">{{ row.values[d.symbol] }}</span>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <!-- Section 3：K 线叠加图 -->
      <section class="sc-section">
        <h3 class="sc-h3">📊 K 线对比（近 30 个交易日收盘价）</h3>
        <div class="sc-chart">
          <component
            :is="CompareKlineChart"
            :series="klineSeries"
          />
        </div>
      </section>

      <!-- Section 4：日涨跌幅对比柱状图 -->
      <section class="sc-section">
        <h3 class="sc-h3">🔥 近 30 日日度涨跌幅</h3>
        <div class="sc-chart">
          <component :is="ComparePctBarChart" :series="pctSeries" />
        </div>
      </section>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http, { unwrap } from '@/common/utils/http'
import { useRealtimePoll } from '@/composables/useRealtimePoll'
import CompareKlineChart from './compare/CompareKlineChart.vue'
import ComparePctBarChart from './compare/ComparePctBarChart.vue'

interface AnalysisResp {
  stock: { symbol: string; name: string; industry: string | null; market: string | null }
  summary: {
    latest_close: number
    pct_change_1d: number
    pct_change_30d: number
    ma5: number | null
    ma20: number | null
    ma60: number | null
    macd_dif: number
    macd_dea: number
    rsi6: number
    rsi_status: 'overbought' | 'oversold' | 'neutral'
    kdj_status: 'golden_cross' | 'death_cross' | 'overbought' | 'oversold' | 'neutral'
    boll_position: 'above_upper' | 'below_lower' | 'upper_half' | 'lower_half' | 'middle'
    signals: string[]
  }
  klines: { date: string; close: number; change_pct: number | null }[]
  pools: { pool_id: number; name: string; pool_type: string }[]
}

const props = defineProps<{
  visible: boolean
  symbols: string[]
}>()
const emit = defineEmits<{ (e: 'update:visible', v: boolean): void }>()

const visible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

const dataList = ref<AnalysisResp[]>([])
const loading = ref(false)

async function loadAll() {
  if (!props.symbols.length) return
  loading.value = true
  try {
    const results = await Promise.allSettled(
      props.symbols.map(s => http.get<AnalysisResp>(`/stocks/${s}/analysis`, { params: { days: 60 } }).then(unwrap))
    )
    dataList.value = results
      .filter((r): r is PromiseFulfilledResult<AnalysisResp> => r.status === 'fulfilled')
      .map(r => r.value)
    if (results.some(r => r.status === 'rejected')) {
      ElMessage.warning('部分股票数据获取失败')
    }
  } finally {
    loading.value = false
  }
}

watch(() => props.symbols, () => loadAll(), { immediate: true })

// 15s 轮询（仅前 60 天分 K 即可，复用实时）
const { start, stop } = useRealtimePoll(loadAll, { intervalMs: 15000 })
watch(visible, v => { v ? start() : stop() })

function close() { visible.value = false }
function refreshAll() { loadAll() }

// ── 派生：关键指标对比表 ──
const indicatorRows = computed(() => {
  const rows: { label: string; values: Record<string, string> }[] = [
    { label: '最新价',     values: obj(d => d.summary.latest_close.toFixed(2)) },
    { label: '今日涨跌%',  values: obj(d => d.summary.pct_change_1d.toFixed(2)) },
    { label: '30 日涨跌%', values: obj(d => d.summary.pct_change_30d.toFixed(2)) },
    { label: 'MA5',        values: obj(d => d.summary.ma5?.toFixed(2) ?? '—') },
    { label: 'MA20',       values: obj(d => d.summary.ma20?.toFixed(2) ?? '—') },
    { label: 'MA60',       values: obj(d => d.summary.ma60?.toFixed(2) ?? '—') },
    { label: 'MACD DIF',   values: obj(d => d.summary.macd_dif.toFixed(3)) },
    { label: 'MACD DEA',   values: obj(d => d.summary.macd_dea.toFixed(3)) },
    { label: 'RSI6',       values: obj(d => d.summary.rsi6.toFixed(1)) },
    { label: 'BOLL 位置',  values: obj(d => d.summary.boll_position) },
    { label: '技术形态',   values: obj(d => d.summary.signals.join(' / ') || '—') },
  ]
  return rows

  function obj(fn: (d: AnalysisResp) => string): Record<string, string> {
    return Object.fromEntries(dataList.value.map(d => [d.symbol, fn(d)]))
  }
})

// ── 派生：K 线叠加数据 ──
const klineSeries = computed(() =>
  dataList.value.map(d => ({
    name: d.symbol,
    type: 'line',
    data: d.klines.map(k => [k.date, k.close]),
    smooth: true,
  }))
)

// ── 派生：日涨跌幅柱状图 ──
const pctSeries = computed(() =>
  dataList.value.map(d => ({
    name: d.symbol,
    type: 'bar',
    data: d.klines.map(k => [k.date, k.change_pct ?? 0]),
  }))
)
</script>

<style scoped>
.sc-wrap { padding: 1rem; display: flex; flex-direction: column; gap: 1.5rem; height: 100%; overflow: auto; }
.sc-header { display: flex; align-items: center; gap: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #e2e8f0; }
.sc-close { ... }
.sc-title { font-size: 1.25rem; font-weight: 700; }
.sc-meta { font-size: 0.85rem; color: #64748b; }
.sc-actions { margin-left: auto; }
.sc-section { display: flex; flex-direction: column; gap: 0.75rem; }
.sc-h3 { font-size: 1.05rem; font-weight: 600; color: #1e293b; }
.sc-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; }
.sc-card { padding: 0.75rem; background: #f8fafc; border-radius: 6px; }
.sc-card__head { display: flex; gap: 0.5rem; align-items: baseline; margin-bottom: 0.5rem; }
.sc-card__sym { font-weight: 700; color: #1e40af; }
.sc-card__name { font-size: 0.85rem; color: #64748b; }
.sc-card__row { display: flex; justify-content: space-between; font-size: 0.85rem; padding: 2px 0; }
.sc-card__row > span:first-child { color: #94a3b8; }
.sc-chart { height: 320px; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 1rem; }
</style>
```

### 3.3 `components/compare/CompareKlineChart.vue`（ECharts 叠加）

```vue
<template>
  <div ref="chartRef" class="compare-chart"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { use } from 'echarts/core'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ series: any[] }>()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: props.series.map(s => s.name), top: 0 },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', boundaryGap: false },
    yAxis: { type: 'value', scale: true },
    series: props.series,
  })
}

onMounted(render)
watch(() => props.series, render, { deep: true })
onUnmounted(() => chart?.dispose())
</script>

<style scoped>
.compare-chart { width: 100%; height: 100%; }
</style>
```

### 3.4 `components/compare/ComparePctBarChart.vue`（ECharts 柱状）

```vue
<template>
  <div ref="chartRef" class="compare-chart"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { use } from 'echarts/core'

use([BarChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const props = defineProps<{ series: any[] }>()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: props.series.map(s => s.name), top: 0 },
    grid: { left: 50, right: 20, top: 30, bottom: 50 },
    xAxis: { type: 'category' },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20 }],
    series: props.series,
  })
}

onMounted(render)
watch(() => props.series, render, { deep: true })
onUnmounted(() => chart?.dispose())
</script>
```

### 3.5 嵌入点

#### 在 `RealtimeBoard.vue`：

```vue
<!-- toolbar 已有 -->
<el-button :disabled="selected.length < 2 || selected.length > 5" type="primary" @click="compareVisible = true">
  对比 ({{ selected.length }})
</el-button>

<!-- 模板末尾 -->
<StockCompareDrawer
  v-model:visible="compareVisible"
  :symbols="selected.map(s => s.symbol)"
/>
```

#### 在 `concept-board/ConceptMembersList.vue`：

```vue
<!-- 表格加 selection 列 + 顶部对比按钮 -->
<el-table :data="rows" @selection-change="onSelChange">...</el-table>
<el-button :disabled="membersSelected.length < 2 || membersSelected.length > 5" @click="compareVisible = true">对比</el-button>
<StockCompareDrawer v-model:visible="compareVisible" :symbols="membersSelected.map(s => s.symbol)" />
```

---

## 4. 性能与边界

| 维度 | 数值 | 备注 |
|---|---|---|
| 单只加载 | ~300ms | `/stocks/{s}/analysis` 单次（已有缓存） |
| 5 只并行 | ~600ms | Promise.all + 后端缓存命中 |
| 15s 轮询 | ~500ms | 同上 |
| 最大支持 | 5 只 | UI 上限（>5 时对比按钮 disabled） |
| K 线点数 | 60 个交易日 | 默认 60 天（3 个月） |

---

## 5. 关键决策

| 问 | 答 |
|---|---|
| 为什么用 ECharts 而不是同花顺自研？ | ECharts 是项目已有依赖（K 线已用），不引入新库 |
| 为什么 K 线叠加而非分别画？ | 同尺度叠加更直观比较走势（用户最常问 "这几只走势像不像"） |
| 为什么基础信息不用 ECharts？ | 简单 grid 卡片 + 数据表，可读性更好 |