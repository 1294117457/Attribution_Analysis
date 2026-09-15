# Step 5: 股票分析与 K 线图表 — 前端实现指南

> 本文档描述前端如何展示股票分析视图：K 线图表（叠加 MA / EMA / BOLL 主图 + MACD / RSI / KDJ 副图）、技术形态摘要、所在池信息, 以及与后端新接口 `/stocks/{symbol}/analysis` 的对接方式。
>
> **核心决策**（与后端方案 A 对齐）：
> 1. K 线 + 指标数据由后端一次性返回, **前端不再做指标计算**（避免重复实现 + 保证一致性）
> 2. AI 归因分析接口 `/stocks/{symbol}/analysis` 同时给前端图表 + 后续 AI Agent 用

---

## 1. 目标与范围

### 功能目标

| 功能 | 用户路径 | 说明 |
|------|---------|------|
| **K 线图表** | 股票信息 → 详情抽屉 K 线 Tab / 独立分析页 | 蜡烛图 + 成交量 + 指标叠加 |
| **技术形态摘要** | 独立分析页 → 右侧信号面板 | 后端聚合, 前端直接展示 |
| **AI 归因数据查看** | 独立分析页 → 「查看 AI 输入」 | 调试用, 看 `/analysis` 原始 JSON |
| **池级批量拉取** | 操作池 → 采集 K 线按钮 | 异步任务, 复用现有 |
| **单只股票拉取** | 股票详情抽屉 → 「拉取 K 线」 | 调用 `POST /klines/collect` |
| **进度查看** | 操作池 → 操作记录 Tab | 复用 `PoolOperations.vue` |

### 设计原则

1. **数据单源**：所有指标从后端 `daily_klines` 取, 前端不重复计算
2. **复用**：复出现有 Element Plus 风格、Pinia store、HTTP 工具
3. **可视化专业**：用 `klinecharts` 渲染蜡烛图（金融级 UI 开箱即用）
4. **响应式**：适配桌面 / 平板

---

## 2. 整体布局（关键）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Header: 📊 归因分析平台                                                          │
├──────────────┬───────────────────────────────┬──────────────────────────────────┤
│              │                                │                                   │
│  📋 股票信息  │   主工作区                       │    侧栏（条件显示）              │
│              │                                │                                   │
│  ─────────  │   ┌─面包屑 / 搜索栏──────────┐│  各页面独立：                      │
│  搜索筛选     │   │                         ││                                   │
│  ─────────  │   └─────────────────────────┘│  • /stock-info     → 无侧栏       │
│  ┌────────┐ │   ┌─K 线图 / 列表 ──────────┐│  • /stock-analysis → 技术形态摘要  │
│  │股票列表│ │   │                         ││  • /stock-pool     → 无侧栏        │
│  │        │ │   │  蜡烛图 + 主图指标       ││                                   │
│  │        │ │   │  副图: MACD/RSI/KDJ      ││                                   │
│  │        │ │   │                         ││                                   │
│  │        │ │   └─────────────────────────┘│                                   │
│  │        │ │   ┌─Tabs: K线 / 摘要 / 池 ──┐│                                   │
│  └────────┘ │   │                       ││                                   │
│              │   └───────────────────────┘│                                   │
│              │                                │                                   │
├──────────────┴───────────────────────────────┴──────────────────────────────────┤
│  路由                                                                          │
│   /stock-info                  — 股票列表（左侧抽屉展示 K 线 Tab）               │
│   /stock-analysis/:symbol      — 🆕 股票独立分析页（K 线 + 信号摘要）           │
│   /stock-pool                  — 操作池（K 线采集入口）                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 三个视图的关系

| 视图 | URL | K 线入口 | 适用场景 |
|------|-----|---------|----------|
| **股票信息** | `/stock-info` | 抽屉内 Tab（小窗） | 浏览多只股票, 快速看 K 线 |
| **股票分析** | `/stock-analysis/:symbol` | 全屏 + 信号面板 | 深入研究单只股票 / 给 AI 看 |
| **操作池** | `/stock-pool/:id` | 池详情 Tab | 管理持仓池, 批量采集 |

### 2.2 路由结构

```typescript
// frontend/src/router/index.ts

const routes = [
  // ... 已有
  {
    path: '/stock-info',
    name: 'StockInfo',
    component: () => import('@/views/stock-info/components/StockPanel.vue'),
  },
  {
    // 🆕 独立分析页（替代原来的 /home/kline/:symbol）
    path: '/stock-analysis/:symbol',
    name: 'StockAnalysis',
    component: () => import('@/views/stock-analysis/components/AnalysisMainView.vue'),
    props: true,
    meta: { title: '股票分析' },
  },
]
```

### 2.3 视图目录结构

```
frontend/src/views/
├── stock-info/                          # 现有：股票信息页
│   ├── api.ts                            # 🆕 见 §6 重写
│   ├── components/
│   │   ├── StockPanel.vue                # 列表 + 抽屉（K 线 Tab）
│   │   └── KLineDrawerTab.vue            # 🆕 抽屉内 K 线 Tab
│   └── index.ts
│
├── stock-analysis/                       # 🆕 新增：独立分析页
│   ├── index.ts
│   └── components/
│       ├── AnalysisMainView.vue          # 主视图（左右布局）
│       ├── KLineChartPanel.vue           # K 线图（左）
│       ├── SignalSummaryPanel.vue        # 技术形态摘要（右）
│       └── PoolMembershipPanel.vue       # 所在池（右）
│
└── stock-pool/                           # 现有：操作池（K 线采集入口）
    └── components/PoolDetail.vue         # 加「采集 K 线」按钮即可
```

### 2.4 共享组件

```
frontend/src/components/kline/
├── CandleChart.vue                       # 🆕 纯展示组件, 数据由父组件传入
├── IndicatorSwitcher.vue                 # 🆕 主图/副图指标切换
└── index.ts

frontend/src/common/styles/
└── chart-theme.ts                        # 🆕 A 股配色（红涨绿跌）

frontend/src/stores/
└── kline.ts             # 🆕 缓存 + 用户偏好
```

---

## 3. 候选方案对比（图表库）

### 方案 A：klinecharts ✅ 推荐

```
优点：
- 专业金融级 UI（蜡烛图 + 副图 + 指标叠加）
- 体积适中（~80 KB gzip）
- TypeScript 支持好
- 自定义主图/副图布局灵活
- 与 Element Plus 风格适配容易

缺点：
- 默认暗黑主题, 需 setStyles 覆盖为浅色
```

### 方案 B：ECharts 自实现

```
优点：
- 项目已用 ECharts

缺点：
- 蜡烛图坐标系要自己拼
- 副图/主图布局工作量大
- 缩放、十字光标需调 ECharts API
```

**决策**：用 `klinecharts`，指标计算由后端做, 前端只负责渲染。

---

## 4. 技术选型

### 4.1 新增依赖

```json
{
  "dependencies": {
    "klinecharts": "^9.8.0"
  }
}
```

### 4.2 A 股配色（与 Element Plus 一致）

```typescript
// frontend/src/common/styles/chart-theme.ts

export const chartTheme = {
  candle: {
    up:       '#ef4444',   // 阳线（涨）- 红色（A 股惯例）
    down:     '#22c55e',   // 阴线（跌）- 绿色
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
  indicators: {
    // 主图
    MA5:       '#fbbf24',
    MA10:      '#3b82f6',
    MA20:      '#a855f7',
    MA60:      '#06b6d4',
    BOLL_UP:   '#a855f7',
    BOLL_MID:  '#f97316',
    BOLL_DN:   '#a855f7',
    // 副图
    MACD_DIF:  '#3b82f6',
    MACD_DEA:  '#fbbf24',
    MACD_BAR:  '#ef4444',
    KDJ_K:     '#14b8a6',
    KDJ_D:     '#f97316',
    KDJ_J:     '#a855f7',
    RSI:       '#ec4899',
  },
} as const
```

---

## 5. 数据流（前端)

### 5.1 单只股票分析

```
AnalysisMainView 挂载
   │
   ├─► GET /stocks/{symbol}/analysis?days=90
   │     │
   │     ├─► summary（技术形态摘要）
   │     ├─► klines[]（每行含 OHLC + 17 指标列）
   │     └─► pools[]（所在池）
   │
   ├─► KLineChartPanel：klines → 蜡烛图 + 副图（用 indicator 列直接画）
   ├─► SignalSummaryPanel：summary → 信号标签列表
   └─► PoolMembershipPanel：pools → 表格
```

### 5.2 抽屉内 K 线（精简版）

```
StockPanel 抽屉打开 → 切到「K 线」Tab
   │
   └─► GET /klines/{symbol}?limit=90
         │
         └─► 每行带 ma5/ma20/macd_dif/... 直接画图
```

### 5.3 池级批量拉取（异步）

```
操作池详情 → 「采集 K 线」按钮
   │
   ├─► POST /pools/{id}/operations { operation_type: "kline_collect", days: 365 }
   ├─► 创建 Operation (status=pending)
   └─► OperationDispatcher 在后台依次 collect 每只股票
         （每只股票含 K 线 + 指标一并入库, 不再单独算指标）

前端轮询 /operations/{id}/progress, 2 秒一次
```

---

## 6. API 层

### 6.1 `frontend/src/views/stock-info/api.ts` 重写

```typescript
// ── 已有 ────────────────────────────────────────────────
export interface StockInfo {
  symbol: string
  name: string
  industry?: string
  market?: string
}

/** 查询 K 线 + 指标（一行一交易日, 含 17 个指标列） */
export interface Kline {
  date: string                       // YYYY-MM-DD
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  change_pct?: number
  // 指标（来自后端 daily_klines, 前端直接展示, 不计算）
  ma5?: number | null
  ma10?: number | null
  ma20?: number | null
  ma60?: number | null
  ema12?: number | null
  ema26?: number | null
  macd_dif?: number | null
  macd_dea?: number | null
  macd_bar?: number | null
  rsi6?: number | null
  rsi12?: number | null
  rsi24?: number | null
  kdj_k?: number | null
  kdj_d?: number | null
  kdj_j?: number | null
  boll_up?: number | null
  boll_mid?: number | null
  boll_dn?: number | null
}

export const getKlines = (
  symbol: string,
  params: { start_date?: string; end_date?: string; limit?: number } = {},
) =>
  http.get<PaginatedResponse<Kline>>(`/klines/${symbol}`, { params }).then(unwrap)

/** 单只股票拉取（同步, 后端会一并算指标） */
export const collectKlines = (data: { symbol: string; days?: number }) =>
  http.post<{ saved_count: number; total_count: number }>(
    '/klines/collect',
    data
  ).then(unwrap)

// ── 🆕 AI 归因分析接口 ──────────────────────────────────

/** 技术形态摘要（后端聚合好） */
export interface TechnicalSummary {
  latest_close: number
  pct_change_1d: number
  pct_change_30d: number
  ma_alignment: 'bullish' | 'bearish' | 'neutral'
  ma5_above_ma20: boolean
  golden_cross_recent: boolean
  macd_status: 'golden_cross' | 'death_cross' | 'above_zero' | 'below_zero' | 'neutral'
  macd_dif: number
  macd_dea: number
  macd_bar: number
  rsi6: number
  rsi_status: 'overbought' | 'oversold' | 'neutral'
  kdj_k: number
  kdj_d: number
  kdj_j: number
  kdj_status: 'golden_cross' | 'death_cross' | 'overbought' | 'oversold' | 'neutral'
  boll_position: 'above_upper' | 'below_lower' | 'upper_half' | 'lower_half' | 'middle'
  signals: string[]                  // ["MA 多头排列", "MACD 金叉", ...]
}

export interface PoolMembership {
  pool_id: number
  pool_name: string
  joined_at: string
}

export interface StockAnalysisResponse {
  stock: StockInfo
  summary: TechnicalSummary
  klines: Kline[]
  pools: PoolMembership[]
}

/** 🆕 AI 归因分析接口（前端 + Agent 共用） */
export const getStockAnalysis = (
  symbol: string,
  params: { days?: number } = {},
) =>
  http.get<{ code: number; data: StockAnalysisResponse }>(
    `/stocks/${symbol}/analysis`,
    { params }
  ).then(unwrap)
```

### 6.2 池级操作（保留 + 简化)

```typescript
// frontend/src/views/stock-pool/api.ts

/** 池级 K 线采集（同步触发, 后台异步执行） */
export const createKlineCollectOperation = (
  poolId: number,
  data: { operation_type: 'kline_collect'; days?: number },
) =>
  http.post<PoolOperationCreateResponse>(
    `/pools/${poolId}/operations`,
    { pool_id: poolId, ...data },
  ).then(unwrap)

// ❌ 移除：createIndicatorCalcOperation（K 线采集已经包含指标）
```

### 6.3 管理后台（可选）

```typescript
// 全市场重算（管理员）
export const recalculateAllIndicators = () =>
  http.post<{ success: number; failed: number }>(
    '/admin/indicators/recalculate'
  ).then(unwrap)
```

---

## 7. 核心组件

### 7.1 `CandleChart.vue`（纯展示, 数据由父组件传入）

> **关键变化**：之前是自己计算指标, 现在只负责展示后端给的指标数据。

```vue
<!-- frontend/src/components/kline/CandleChart.vue -->

<template>
  <div ref="chartRef" class="kline-chart" />
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, shallowRef } from 'vue'
import { klinechartsInit, type Chart } from 'klinecharts'
import type { Kline } from '@/views/stock-info/api'
import { chartTheme } from '@/common/styles/chart-theme'

interface Props {
  klines: Kline[]                              // 后端返回, 含指标字段
  showMain?: ('MA5' | 'MA10' | 'MA20' | 'MA60' | 'BOLL')[]
  showSub?: 'MACD' | 'RSI' | 'KDJ' | ''
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  height: 600,
  showMain: () => ['MA5', 'MA20'],
  showSub: 'MACD',
})

const chartRef = ref<HTMLDivElement>()
const chart = shallowRef<Chart>()

onMounted(() => {
  if (!chartRef.value) return
  chart.value = klinechartsInit(chartRef.value)

  // A 股配色
  chart.value.setStyles({
    candle: {
      bar: {
        upColor: chartTheme.candle.up,
        downColor: chartTheme.candle.down,
        noChangeColor: chartTheme.candle.noChange,
      },
    },
    grid: {
      horizontal: { show: true, color: chartTheme.grid.line },
      vertical:   { show: true, color: chartTheme.grid.line },
    },
  })

  applyData()
})

watch(() => props.klines, applyData, { deep: false })
watch([() => props.showMain, () => props.showSub], applyIndicators, { deep: true })

function applyData() {
  if (!chart.value) return
  const data = props.klines.map((k) => ({
    timestamp: new Date(k.date).getTime(),
    open:   k.open,
    high:   k.high,
    low:    k.low,
    close:  k.close,
    volume: k.volume,
    // 把指标列塞进 data, 自定义指标面板从 data 里取
    ma5:    k.ma5,
    ma10:   k.ma10,
    ma20:   k.ma20,
    ma60:   k.ma60,
    boll_up:  k.boll_up,
    boll_mid: k.boll_mid,
    boll_dn:  k.boll_dn,
    macd_dif: k.macd_dif,
    macd_dea: k.macd_dea,
    macd_bar: k.macd_bar,
    rsi6:   k.rsi6,
    kdj_k:  k.kdj_k,
    kdj_d:  k.kdj_d,
    kdj_j:  k.kdj_j,
  }))
  chart.value.applyNewData(data)
}

function applyIndicators() {
  if (!chart.value) return
  chart.value.removeAllIndicators()

  // 主图叠加 MA / BOLL（用自定义 series）
  props.showMain.forEach((name) => {
    if (name === 'BOLL') {
      chart.value!.createIndicator('BOLL', false, { id: 'candle_pane' })
    } else if (name.startsWith('MA')) {
      // 用 createIndicator('MA') 或自己画 line
      chart.value!.createIndicator('MA', false, {
        id: 'candle_pane',
        params: [Number(name.slice(2))],
      })
    }
  })

  // 副图
  if (props.showSub) {
    chart.value!.createIndicator(props.showSub, false, {
      id: `${props.showSub.toLowerCase()}_pane`,
    })
  }
}

onBeforeUnmount(() => {
  chart.value?.dispose()
})
</script>

<style scoped>
.kline-chart { width: 100%; height: v-bind('`${height}px`'); }
</style>
```

### 7.2 `IndicatorSwitcher.vue`（指标切换工具栏）

```vue
<!-- frontend/src/components/kline/IndicatorSwitcher.vue -->

<template>
  <div class="indicator-switcher">
    <el-checkbox-group v-model="mainSelected" size="small">
      <el-checkbox label="MA5">MA5</el-checkbox>
      <el-checkbox label="MA10">MA10</el-checkbox>
      <el-checkbox label="MA20">MA20</el-checkbox>
      <el-checkbox label="MA60">MA60</el-checkbox>
      <el-checkbox label="BOLL">BOLL</el-checkbox>
    </el-checkbox-group>

    <el-divider direction="vertical" />

    <el-radio-group v-model="subSelected" size="small">
      <el-radio-button label="">无</el-radio-button>
      <el-radio-button label="MACD">MACD</el-radio-button>
      <el-radio-button label="RSI">RSI</el-radio-button>
      <el-radio-button label="KDJ">KDJ</el-radio-button>
    </el-radio-group>
  </div>
</template>

<script setup lang="ts">
const mainSelected = defineModel<string[]>('main', { default: () => ['MA5', 'MA20'] })
const subSelected  = defineModel<string>(   'sub',  { default: 'MACD' })
</script>

<style scoped>
.indicator-switcher { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
</style>
```

---

## 8. 独立分析页（核心视图）

### 8.1 `AnalysisMainView.vue`（左右布局）

```vue
<!-- frontend/src/views/stock-analysis/components/AnalysisMainView.vue -->

<template>
  <div class="analysis-page" v-loading="loading">
    <!-- 顶部：搜索 + 标的 -->
    <div class="header">
      <el-input
        v-model="symbolInput"
        placeholder="输入代码"
        style="width: 200px"
        clearable
        @keyup.enter="onSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <div class="stock-info" v-if="data?.stock">
        <span class="symbol">{{ data.stock.symbol }}</span>
        <span class="name">{{ data.stock.name }}</span>
        <span class="industry" v-if="data.stock.industry">
          <el-tag size="small">{{ data.stock.industry }}</el-tag>
        </span>
        <span class="price" :class="(data.summary.pct_change_1d >= 0) ? 'up' : 'down'">
          {{ data.summary.latest_close.toFixed(2) }}
        </span>
        <span class="pct" :class="(data.summary.pct_change_1d >= 0) ? 'up' : 'down'">
          {{ data.summary.pct_change_1d >= 0 ? '+' : '' }}{{ data.summary.pct_change_1d.toFixed(2) }}%
        </span>
      </div>

      <el-button type="primary" :loading="collecting" @click="onCollect">
        <el-icon class="mr-1"><Download /></el-icon>
        拉取 K 线
      </el-button>
    </div>

    <!-- 左右布局 -->
    <div class="body">
      <!-- 左侧：K 线 -->
      <el-card shadow="never" class="left">
        <IndicatorSwitcher v-model:main="mainIndicators" v-model:sub="subIndicator" />

        <CandleChart
          :klines="data?.klines ?? []"
          :show-main="mainIndicators"
          :show-sub="subIndicator"
          :height="640"
        />
      </el-card>

      <!-- 右侧：信号摘要 + 所在池 -->
      <el-card shadow="never" class="right">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="技术信号" name="signal">
            <SignalSummaryPanel v-if="data" : summary="data.summary" />
          </el-tab-pane>
          <el-tab-pane label="所在池" name="pools">
            <PoolMembershipPanel v-if="data" :pools="data.pools" />
          </el-tab-pane>
          <el-tab-pane label="AI 输入 JSON" name="ai">
            <pre class="json">{{ JSON.stringify(data, null, 2) }}</pre>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Download } from '@element-plus/icons-vue'
import CandleChart from '@/components/kline/CandleChart.vue'
import IndicatorSwitcher from '@/components/kline/IndicatorSwitcher.vue'
import SignalSummaryPanel from '@/views/stock-analysis/components/SignalSummaryPanel.vue'
import PoolMembershipPanel from '@/views/stock-analysis/components/PoolMembershipPanel.vue'
import { getStockAnalysis, collectKlines, type StockAnalysisResponse } from '@/views/stock-info/api'

const route = useRoute()
const router = useRouter()

const symbolInput = ref('')
const data = ref<StockAnalysisResponse | null>(null)
const loading = ref(false)
const collecting = ref(false)

const mainIndicators = ref(['MA5', 'MA20'])
const subIndicator = ref('MACD')
const activeTab = ref('signal')

async function load(symbol: string) {
  loading.value = true
  try {
    const resp = await getStockAnalysis(symbol, { days: 365 })
    data.value = resp.data
    symbolInput.value = symbol
  } catch (e) {
    ElMessage.error('加载失败: ' + (e as Error).message)
    data.value = null
  } finally {
    loading.value = false
  }
}

function onSearch() {
  if (!symbolInput.value) return
  router.push(`/stock-analysis/${symbolInput.value}`)
}

async function onCollect() {
  if (!symbolInput.value) return
  collecting.value = true
  try {
    const r = await collectKlines({ symbol: symbolInput.value, days: 365 })
    ElMessage.success(`已采集 ${r.saved_count} 条`)
    await load(symbolInput.value)
  } finally {
    collecting.value = false
  }
}

onMounted(() => {
  const sym = String(route.params.symbol || '')
  if (sym) load(sym)
})

watch(() => route.params.symbol, (v) => {
  if (v) load(String(v))
})
</script>

<style scoped>
.analysis-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  height: 100%;
}
.header {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stock-info {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.symbol { font-weight: 600; font-size: 18px; }
.name { color: #6b7280; }
.up { color: #ef4444; }    /* A 股：红涨 */
.down { color: #22c55e; }  /* A 股：绿跌 */
.price { font-size: 20px; font-weight: 700; }
.pct { font-size: 14px; }

.body {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 12px;
  flex: 1;
  min-height: 0;
}
.left, .right {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.json {
  font-size: 12px;
  max-height: 640px;
  overflow: auto;
  background: #f9fafb;
  padding: 12px;
  border-radius: 4px;
}
</style>
```

### 8.2 `SignalSummaryPanel.vue`（技术形态摘要）

```vue
<!-- frontend/src/views/stock-analysis/components/SignalSummaryPanel.vue -->

<template>
  <div class="signal-panel">
    <!-- 信号标签 -->
    <div class="signals">
      <el-tag
        v-for="s in summary.signals"
        :key="s"
        :type="signalTagType(s)"
        class="mr-1 mb-1"
        effect="dark"
      >
        {{ s }}
      </el-tag>
      <el-tag v-if="!summary.signals.length" type="info">无明显信号</el-tag>
    </div>

    <el-divider />

    <!-- 关键数值 -->
    <el-descriptions :column="1" border size="small">
      <el-descriptions-item label="最新价">
        {{ summary.latest_close.toFixed(2) }}
        <span :class="summary.pct_change_1d >= 0 ? 'up' : 'down'" class="ml-1">
          {{ summary.pct_change_1d >= 0 ? '+' : '' }}{{ summary.pct_change_1d.toFixed(2) }}%
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="30 日涨跌">
        <span :class="summary.pct_change_30d >= 0 ? 'up' : 'down'">
          {{ summary.pct_change_30d >= 0 ? '+' : '' }}{{ summary.pct_change_30d.toFixed(2) }}%
        </span>
      </el-descriptions-item>

      <el-descriptions-item label="均线排列">
        <el-tag :type="maType(summary.ma_alignment)" size="small">
          {{ maLabel(summary.ma_alignment) }}
        </el-tag>
      </el-descriptions-item>

      <el-descriptions-item label="MACD">
        <el-tag :type="macdType(summary.macd_status)" size="small">
          {{ macdLabel(summary.macd_status) }}
        </el-tag>
        <span class="ml-2 text-xs text-gray-500">
          DIF {{ summary.macd_dif.toFixed(3) }} / DEA {{ summary.macd_dea.toFixed(3) }}
        </span>
      </el-descriptions-item>

      <el-descriptions-item label="RSI6">
        {{ summary.rsi6.toFixed(1) }}
        <el-tag :type="rsiType(summary.rsi_status)" size="small" class="ml-2">
          {{ rsiLabel(summary.rsi_status) }}
        </el-tag>
      </el-descriptions-item>

      <el-descriptions-item label="KDJ">
        K {{ summary.kdj_k.toFixed(1) }}
        / D {{ summary.kdj_d.toFixed(1) }}
        / J {{ summary.kdj_j.toFixed(1) }}
        <el-tag :type="kdjType(summary.kdj_status)" size="small" class="ml-2">
          {{ kdjLabel(summary.kdj_status) }}
        </el-tag>
      </el-descriptions-item>

      <el-descriptions-item label="布林带位置">
        <el-tag :type="bollType(summary.boll_position)" size="small">
          {{ bollLabel(summary.boll_position) }}
        </el-tag>
      </el-descriptions-item>
    </el-descriptions>
  </div>
</template>

<script setup lang="ts">
import type { TechnicalSummary } from '@/views/stock-info/api'

defineProps<{ summary: TechnicalSummary }>()

// ── 标签辅助函数 ────────────────────────────────────
function signalTagType(s: string): 'success' | 'danger' | 'warning' | 'info' {
  if (s.includes('超买') || s.includes('死叉') || s.includes('跌破') || s.includes('空头')) return 'danger'
  if (s.includes('金叉') || s.includes('突破') || s.includes('多头')) return 'success'
  if (s.includes('超卖')) return 'warning'
  return 'info'
}
function maLabel(v: string)         { return v === 'bullish' ? '多头排列' : v === 'bearish' ? '空头排列' : '震荡' }
function maType(v: string)          { return v === 'bullish' ? 'success' : v === 'bearish' ? 'danger' : 'info' }
function macdLabel(v: string)       {
  return ({ golden_cross: '金叉', death_cross: '死叉', above_zero: '零轴上', below_zero: '零轴下', neutral: '—' } as any)[v] || v
}
function macdType(v: string)        {
  return ({ golden_cross: 'success', death_cross: 'danger', above_zero: 'success', below_zero: 'danger', neutral: 'info' } as any)[v] || 'info'
}
function rsiLabel(v: string)        { return v === 'overbought' ? '超买' : v === 'oversold' ? '超卖' : '中性' }
function rsiType(v: string)         { return v === 'overbought' ? 'danger' : v === 'oversold' ? 'warning' : 'success' }
function kdjLabel(v: string)        {
  return ({ golden_cross: '金叉', death_cross: '死叉', overbought: '超买', oversold: '超卖', neutral: '—' } as any)[v] || v
}
function kdjType(v: string)         {
  return ({ golden_cross: 'success', death_cross: 'danger', overbought: 'danger', oversold: 'warning', neutral: 'info' } as any)[v] || 'info'
}
function bollLabel(v: string)       {
  return ({ above_upper: '突破上轨', below_lower: '跌破下轨', upper_half: '上半区', lower_half: '下半区', middle: '中轨附近' } as any)[v] || v
}
function bollType(v: string)        {
  return ({ above_upper: 'success', below_lower: 'danger', upper_half: 'warning', lower_half: 'info', middle: 'info' } as any)[v] || 'info'
}
</script>

<style scoped>
.signal-panel { padding: 8px; }
.up { color: #ef4444; }
.down { color: #22c55e; }
</style>
```

### 8.3 `PoolMembershipPanel.vue`（所在池）

```vue
<!-- frontend/src/views/stock-analysis/components/PoolMembershipPanel.vue -->

<template>
  <el-table :data stripe size="small" :empty-text="emptyText">
    <el-table-column prop="pool_name" label="池名称" />
    <el-table-column prop="joined_at" label="加入时间" width="120" />
    <el-table-column label="操作" width="80">
      <template #default="{ row }">
        <el-button link type="primary" @click="goPool(row)">查看</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { PoolMembership } from '@/views/stock-info/api'

const props = defineProps<{ pools: PoolMembership[] }>()
const router = useRouter()
const emptyText = computed(() => (props.pools.length ? '' : '该股票不在任何操作池中'))

function goPool(row: PoolMembership) {
  router.push(`/stock-pool/${row.pool_id}`)
}
</script>
```

---

## 9. 股票信息抽屉 K 线 Tab

> 在 `StockPanel.vue` 的详情抽屉里加「K 线」Tab, 复用 `CandleChart.vue`。

### 9.1 `KLineDrawerTab.vue`

```vue
<!-- frontend/src/views/stock-info/components/KLineDrawerTab.vue -->

<template>
  <div class="kline-drawer">
    <div class="flex items-center justify-between mb-2">
      <el-button-group size="small">
        <el-button :type="range === '90' ? 'primary' : ''" @click="range = '90'">90 日</el-button>
        <el-button :type="range === '180' ? 'primary' : ''" @click="range = '180'">180 日</el-button>
        <el-button :type="range === '365' ? 'primary' : ''" @click="range = '365'">1 年</el-button>
      </el-button-group>

      <el-button size="small" :loading="collecting" @click="onCollect">
        <el-icon class="mr-1"><Download /></el-icon>拉取 K 线
      </el-button>
    </div>

    <IndicatorSwitcher v-model:main="mainIndicators" v-model:sub="subIndicator" />

    <CandleChart
      v-if="klines.length"
      :klines="klines"
      :show-main="mainIndicators"
      :show-sub="subIndicator"
      :height="380"
    />
    <el-empty v-else description="暂无 K 线, 点击右上角拉取" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import CandleChart from '@/components/kline/CandleChart.vue'
import IndicatorSwitcher from '@/components/kline/IndicatorSwitcher.vue'
import { getKlines, collectKlines, type Kline } from '@/views/stock-info/api'

const props = defineProps<{ symbol: string }>()

const klines = ref<Kline[]>([])
const range = ref('180')
const mainIndicators = ref(['MA5', 'MA20'])
const subIndicator = ref('MACD')
const collecting = ref(false)

async function load() {
  klines.value = await getKlines(props.symbol, { limit: Number(range.value) })
}

async function onCollect() {
  collecting.value = true
  try {
    const r = await collectKlines({ symbol: props.symbol, days: Number(range.value) })
    ElMessage.success(`已采集 ${r.saved_count} 条`)
    await load()
  } finally {
    collecting.value = false
  }
}

watch(() => [props.symbol, range.value], load, { immediate: true })
</script>
```

### 9.2 `StockPanel.vue` 集成

```vue
<!-- StockPanel.vue 详情抽屉内, 把已有 Tabs 改为： -->

<el-tabs v-model="activeTab" class="mt-4">
  <el-tab-pane label="基本信息" name="info">
    <el-descriptions :column="1" border>
      <!-- 原有字段 -->
    </el-descriptions>
  </el-tab-pane>
  <el-tab-pane label="K 线图" name="kline">
    <KLineDrawerTab :symbol="selectedStock.symbol" />
  </el-tab-pane>
  <el-tab-pane label="归因分析" name="analysis">
    <el-button type="primary" @click="goAnalysis(selectedStock.symbol)">
      打开独立分析页
    </el-button>
  </el-tab-pane>
</el-tabs>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
function goAnalysis(symbol: string) {
  router.push(`/stock-analysis/${symbol}`)
}
</script>
```

---

## 10. 操作池（K 线采集入口, 简化)

> 操作池不需要改动太多, 只需移除「指标计算」按钮（采集 K 线已经包含指标）。

```vue
<!-- PoolDetail.vue 的操作区, 简化为单按钮 -->

<el-button
  type="primary"
  :loading="collecting"
  @click="onCollectKlines"
>
  <el-icon class="mr-1"><Download /></el-icon>
  采集 K 线（含技术指标）
</el-button>

<script setup>
async function onCollectKlines() {
  const days = await ElMessageBox.prompt('请输入回溯天数', '采集 K 线', { inputValue: '365' })
  const op = await createKlineCollectOperation(poolId, {
    operation_type: 'kline_collect',
    days: Number(days.value),
  })
  // 复用 PoolOperations 轮询
  pollProgress(op.operation_id)
}
</script>
```

---

## 11. Pinia Store

```typescript
// frontend/src/stores/kline.ts

import { defineStore } from 'pinia'
import type { Kline, StockAnalysisResponse } from '@/views/stock-info/api'

interface State {
  cache: Record<string, StockAnalysisResponse>   // symbol -> analysis
  defaultMain: string[]
  defaultSub: string
}

export const useKlineStore = defineStore('kline', {
  state: (): State => ({
    cache: {},
    defaultMain: ['MA5', 'MA20'],
    defaultSub: 'MACD',
  }),

  actions: {
    async load(symbol: string, force = false) {
      if (!force && this.cache[symbol]) return this.cache[symbol]
      const { data } = await getStockAnalysis(symbol, { days: 365 })
      this.cache[symbol] = data
      return data
    },

    invalidate(symbol: string) { delete this.cache[symbol] },
    invalidateAll() { this.cache = {} },
  },
})
```

---

## 12. UI 视觉规范

### 12.1 主图

```
┌─────────────────────────────────────────┐
│ 000001 平安银行 [银行] 12.34 +1.20%      │
├─────────────────────────────────────────┤
│                                         │
│   蜡烛图（红涨/绿跌）                    │
│                                         │
│   ── MA5  (黄色)                         │
│   ── MA20 (紫色)                         │
│   ── BOLL UP / MID / DN (橙紫虚线)        │
│                                         │
├─────────────────────────────────────────┤
│ 成交量（红绿柱状）                       │
└─────────────────────────────────────────┘
```

### 12.2 副图

```
┌─────────────────────────────────────┐
│  [MACD]                              │
│   ── DIF (蓝) / DEA (黄)             │
│   ▌ 柱状 (红涨 / 绿跌)                │
└─────────────────────────────────────┘
```

### 12.3 信号摘要（右栏)

```
┌─ 技术信号 ──────────────────────────┐
│ [MA 多头排列] [MACD 金叉] [KDJ 超买] │
├─────────────────────────────────────┤
│ 最新价     12.34       +1.20%        │
│ 30 日涨跌                       +5.2%│
│ 均线排列    [多头排列]               │
│ MACD      [金叉] DIF 0.15 DEA 0.10  │
│ RSI6      65.3  [中性]              │
│ KDJ       78.5/72.3/91.0 [超买]      │
│ 布林带    [上半区]                   │
└─────────────────────────────────────┘
```

### 12.4 颜色

| 元素 | 颜色 | 含义 |
|------|------|------|
| 阳线 / 涨 | `#ef4444` 红 | A 股惯例 |
| 阴线 / 跌 | `#22c55e` 绿 | A 股惯例 |
| MA5 | `#fbbf24` 黄 | 主图 |
| MA10 | `#3b82f6` 蓝 | 主图 |
| MA20 | `#a855f7` 紫 | 主图 |
| MA60 | `#06b6d4` 青 | 主图 |
| BOLL MID | `#f97316` 橙 | 主图 |
| MACD DIF/DEA | 蓝/黄 | 副图 |
| MACD 柱 | 红/绿 | 副图 |
| KDJ K/D/J | 青/橙/紫 | 副图 |

---

## 13. 关键风险与对策

| 风险 | 对策 |
|------|------|
| 数据量大渲染卡顿（365 天 × 多股票对比） | 默认 90 / 180 / 365 三档；CandleChart 用 `shallowRef` 避免 deep watch |
| klinecharts 默认暗黑主题 | `setStyles()` 全量覆盖为浅色 |
| AI 分析接口返回大（365 天 × 17 列） | 后端默认 90 天；上限 1825 天 |
| 切换 symbol 时旧请求未完成 | 用 `AbortController` 取消上一个请求 |
| 池级批量拉取 progress 丢失 | 复用现有 OperationDispatcher, 已有持久化机制 |

---

## 14. 文件清单

### 新增

```
frontend/src/
├── views/
│   └── stock-analysis/
│       ├── index.ts
│       └── components/
│           ├── AnalysisMainView.vue
│           ├── SignalSummaryPanel.vue
│           └── PoolMembershipPanel.vue
│
├── components/
│   └── kline/
│       ├── CandleChart.vue
│       ├── IndicatorSwitcher.vue
│       └── index.ts
│
├── stores/
│   └── kline.ts
│
└── common/
    └── styles/
        └── chart-theme.ts
```

### 修改

| 文件 | 修改 |
|------|------|
| `frontend/src/views/stock-info/api.ts` | 重写, 用新 Kline（含指标）+ `getStockAnalysis` |
| `frontend/src/views/stock-info/components/StockPanel.vue` | 抽屉加 K 线 Tab + 跳转独立分析页 |
| `frontend/src/views/stock-info/components/KLineDrawerTab.vue` | 🆕 抽屉 K 线 Tab 内容 |
| `frontend/src/views/stock-pool/api.ts` | 删除 `createIndicatorCalcOperation` |
| `frontend/src/views/stock-pool/components/PoolDetail.vue` | 「采集 K 线」按钮保留, 不再有「计算指标」按钮 |
| `frontend/src/router/index.ts` | 注册 `/stock-analysis/:symbol` |
| `frontend/package.json` | 新增 `klinecharts ^9.8.0` |

---

## 15. 实施计划

### Step 5.1：依赖与基础设施
- [ ] 安装 klinecharts
- [ ] 创建 chart-theme.ts
- [ ] 创建 CandleChart.vue + IndicatorSwitcher.vue

### Step 5.2：API 层
- [ ] 重写 stock-info/api.ts（Kline + StockAnalysisResponse + getStockAnalysis）
- [ ] 删除 stock-pool/api.ts 中 indicator_calc 相关

### Step 5.3：股票信息抽屉 K 线
- [ ] 创建 KLineDrawerTab.vue
- [ ] StockPanel.vue 加 Tab

### Step 5.4：独立分析页（核心）
- [ ] 创建 AnalysisMainView.vue + SignalSummaryPanel + PoolMembershipPanel
- [ ] 路由 `/stock-analysis/:symbol`
- [ ] 联调 `/stocks/{symbol}/analysis` 接口

### Step 5.5：操作池调整
- [ ] PoolDetail.vue 简化采集按钮文案
- [ ] 测试异步采集流程（K 线 + 指标一次入库）

### Step 5.6：联调与优化
- [ ] 三视图联动（信息页抽屉跳分析页）
- [ ] 缓存（Pinia store）
- [ ] 响应式适配
- [ ] OpenAPI 文档 / TypeScript 类型同步