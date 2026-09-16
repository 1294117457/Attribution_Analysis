<!--
  完整 K 线分析面板（可复用）
  - 作为独立页面 AnalysisMainView 的主体
  - 也作为 PoolDetail 右侧主面板的嵌入组件

  接收 symbol prop，自动加载分析数据并展示:
    顶部信息条 → 左侧 K 线图 + 右侧 信号/池/AI 输入 Tabs
-->
<template>
  <div class="analysis-detail flex flex-col h-full" v-loading="loading">
    <!-- 顶部信息条 -->
    <div
      v-if="data?.stock"
      class="info-bar flex items-center gap-3 px-4 py-3 border-b bg-white"
    >
      <span class="symbol mono text-lg font-bold">{{ data.stock.symbol }}</span>
      <span class="name text-base font-medium text-gray-800">{{ data.stock.name }}</span>
      <el-tag v-if="data.stock.industry" size="small" type="info">
        {{ data.stock.industry }}
      </el-tag>
      <el-tag v-if="data.stock.market" size="small" effect="plain">
        {{ data.stock.market }}
      </el-tag>

      <div class="flex-1"></div>

      <span
        class="text-xl font-bold"
        :class="data.summary.pct_change_1d >= 0 ? 'text-red-500' : 'text-green-500'"
      >
        {{ formatPrice(data.summary.latest_close) }}
      </span>
      <span
        class="text-sm font-semibold"
        :class="data.summary.pct_change_1d >= 0 ? 'text-red-500' : 'text-green-500'"
      >
        {{ data.summary.pct_change_1d >= 0 ? '+' : '' }}{{ data.summary.pct_change_1d.toFixed(2) }}%
      </span>

      <el-button
        size="small"
        type="primary"
        :loading="collecting"
        @click="onCollect"
      >
        <el-icon class="mr-1"><Download /></el-icon>
        拉取 K 线
      </el-button>
    </div>

    <!-- 主体：左右布局 -->
    <div class="body flex flex-1 min-h-0 overflow-hidden gap-3 p-3">
      <!-- 左侧：K 线图 -->
      <div class="left-card flex flex-col min-h-0 overflow-hidden">
        <div class="px-3 pt-3 flex-shrink-0">
          <IndicatorSwitcher
            v-model:main="mainIndicators"
            v-model:sub="subIndicator"
          />
        </div>
        <div class="px-3 pb-3 flex-1 min-h-0 overflow-hidden">
          <CandleChart
            v-if="data?.klines.length"
            :klines="data.klines"
            :show-main="mainIndicators"
            :show-sub="subIndicator"
            :height="chartHeight"
          />
          <el-empty
            v-else-if="!loading"
            description="暂无 K 线数据"
          />
        </div>
      </div>

      <!-- 右侧：信号 + 池 -->
      <div class="right-card flex-shrink-0 overflow-y-auto">
        <el-tabs v-model="rightTab" class="h-full">
          <el-tab-pane label="技术信号" name="signal">
            <SignalSummaryPanel v-if="data" :summary="data.summary" />
          </el-tab-pane>
          <el-tab-pane label="所在池" name="pools">
            <PoolMembershipPanel v-if="data" :pools="data.pools" />
          </el-tab-pane>
          <el-tab-pane label="AI 输入" name="ai">
            <pre class="json-view">{{ JSON.stringify(data, null, 2) }}</pre>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 错误 -->
    <el-empty v-if="loadError && !loading" :description="loadError" class="my-8" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import CandleChart from '@/components/kline/CandleChart.vue'
import IndicatorSwitcher from '@/components/kline/IndicatorSwitcher.vue'
import SignalSummaryPanel from './SignalSummaryPanel.vue'
import PoolMembershipPanel from './PoolMembershipPanel.vue'
import {
  getStockAnalysis,
  collectKlines,
  type StockAnalysisResponse,
} from '@/views/stock-info/api'

const props = defineProps<{
  symbol: string
  /** 默认拉取天数，默认 365 */
  days?: number
  /** 图表高度（px），不传则自适应 */
  chartHeight?: number
}>()

const data = ref<StockAnalysisResponse | null>(null)
const loading = ref(false)
const collecting = ref(false)
const loadError = ref('')

const mainIndicators = ref(['MA5', 'MA20'])
const subIndicator = ref('MACD')
const rightTab = ref('signal')

const chartHeight = ref(props.chartHeight ?? 0)

function refreshChartHeight() {
  if (props.chartHeight) {
    chartHeight.value = props.chartHeight
    return
  }
  // 自适应：父容器高度 - 信息条 - 指标切换
  nextTick(() => {
    const el = document.querySelector('.analysis-detail .left-card') as HTMLElement | null
    if (el) {
      const headerH = 56 + 48 // info-bar + indicator-switcher 近似高
      chartHeight.value = Math.max(360, el.clientHeight - headerH)
    } else {
      chartHeight.value = 460
    }
  })
}

async function load(symbol: string) {
  if (!symbol) return
  loading.value = true
  loadError.value = ''
  try {
    const days = props.days ?? 365
    data.value = await getStockAnalysis(symbol, { days })
    refreshChartHeight()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e)
    loadError.value = msg
    data.value = null
  } finally {
    loading.value = false
  }
}

async function onCollect() {
  if (!props.symbol) return
  collecting.value = true
  try {
    const r = (await collectKlines({
      symbol: props.symbol,
      days: props.days ?? 365,
    })) as unknown as { saved_count: number }
    ElMessage.success(`已采集 ${r.saved_count} 条`)
    await load(props.symbol)
  } catch (e) {
    ElMessage.error('采集失败: ' + (e as Error).message)
  } finally {
    collecting.value = false
  }
}

function formatPrice(v: number | null | undefined) {
  if (v === null || v === undefined) return '—'
  return v.toFixed(2)
}

watch(
  () => props.symbol,
  (s) => {
    if (s) load(s)
  },
)

onMounted(() => {
  if (props.symbol) load(props.symbol)
  window.addEventListener('resize', refreshChartHeight)
})
</script>

<style scoped>
.analysis-detail {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  background: #fafbfc;
  overflow: hidden;
}

.info-bar {
  flex-shrink: 0;
}

.body {
  min-height: 0;
  flex: 1;
}

.left-card {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 6px;
  overflow: hidden;
}

.right-card {
  width: 360px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 6px;
  overflow-y: auto;
  padding: 0 12px;
}

.symbol {
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.json-view {
  font-size: 11px;
  max-height: 600px;
  overflow: auto;
  background: #f9fafb;
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
