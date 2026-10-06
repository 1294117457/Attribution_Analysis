<!--
 * components/data-board-tabs/TechPanel.vue
 *
 * 技术面 Tab — 抽屉 / 看板共用
 *
 * 设计要点：
 * - 同一份 <script setup> 同时被 480px 抽屉（StockDetailDrawer）和 1100px+ 看板
 *   （DataBoard）使用，因此不做「双列 / 单列」硬编码，由父容器决定布局。
 * - 父级传入 columns={1|2}，columns=1 时强制单列堆叠。
 * - 高度自适应父容器；图表卡片 `MiniKlineChart` 高度收窄到 240（抽屉）/ 320（看板）。
 -->
<template>
  <div class="tech-panel" :class="`cols-${columns}`">
    <el-card shadow="never">
      <template #header>
        <span class="font-bold">日 K 线（含 17 指标）</span>
      </template>
      <MiniKlineChart
        :klines="klineData"
        :loading="loadingKline"
        :height="klineHeight"
        :show-main="['MA5','MA10','MA20','MA60','BOLL']"
        show-sub="MACD"
      />
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">复权因子</span>
        <el-tag size="small" type="info" class="ml-2">{{ adjFactor.length }} 条</el-tag>
      </template>
      <div v-loading="loadingAdj" class="mini-table">
        <el-table :data="adjFactor.slice(0, 30)" size="small" stripe max-height="200">
          <el-table-column prop="trade_date" label="日期" width="120" />
          <el-table-column label="因子" align="right">
            <template #default="{ row }">
              <span class="mono">{{ row.adj_factor.toFixed(4) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">停复牌事件</span>
        <el-tag size="small" type="warning" class="ml-2">{{ suspend.length }} 条</el-tag>
      </template>
      <div v-loading="loadingSuspend" class="mini-table">
        <el-table :data="suspend.slice(0, 30)" size="small" stripe max-height="160">
          <el-table-column prop="trade_date" label="日期" width="120" />
          <el-table-column prop="suspend_type" label="类型" width="80">
            <template #default="{ row }">
              <el-tag :type="row.suspend_type === 'S' ? 'danger' : 'success'" size="small">
                {{ row.suspend_type === 'S' ? '停牌' : '复牌' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="时刻" align="center">
            <template #default="{ row }">
              <span class="text-xs text-gray-500">{{ row.suspend_timing || '—' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">曾用名</span>
        <el-tag size="small" type="info" class="ml-2">{{ nameChange.length }} 条</el-tag>
      </template>
      <div v-loading="loadingName" class="mini-table">
        <el-table :data="nameChange.slice(0, 30)" size="small" stripe max-height="160">
          <el-table-column prop="name" label="曾用名" />
          <el-table-column prop="start_date" label="起始日期" width="120" />
          <el-table-column prop="end_date" label="结束日期" width="120" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import MiniKlineChart from '@/views/stock-info/components/MiniKlineChart.vue'
import * as API from '@/views/concept-board/api-data-board'
import type { Kline } from '@/views/stock-info/api'

const props = withDefaults(defineProps<{
  symbol: string
  /** 双列（看板）还是单列（抽屉） */
  columns?: 1 | 2
  /** K 线图高度；默认 240（抽屉） / 320（看板） */
  klineHeight?: number
}>(), {
  columns: 2,
  klineHeight: 320,
})

// ── 数据状态 ──
const klineData = ref<Kline[]>([])
const adjFactor = ref<API.AdjFactor[]>([])
const suspend = ref<API.SuspendEvent[]>([])
const nameChange = ref<API.NameChange[]>([])
const loadingKline = ref(false)
const loadingAdj = ref(false)
const loadingSuspend = ref(false)
const loadingName = ref(false)

async function load(s: string) {
  if (!/^\d{6}$/.test(s)) return
  loadingKline.value = true
  loadingAdj.value = true
  loadingSuspend.value = true
  loadingName.value = true
  const results = await Promise.allSettled([
    API.getKline(s, 250),
    API.getAdjFactor(s),
    API.getSuspend(s),
    API.getNameChange(s),
  ])
  if (results[0].status === 'fulfilled') {
    klineData.value = results[0].value.klines.map((b) => ({
      symbol: s, name: '',
      date: b.trade_date, open: b.open, high: b.high, low: b.low, close: b.close,
      volume: b.volume, amount: b.amount ?? null, change_pct: b.change_pct ?? null,
    }))
  } else { klineData.value = []; console.warn('[TechPanel] kline failed', results[0].reason) }
  if (results[1].status === 'fulfilled') adjFactor.value = results[1].value.factors
  else { adjFactor.value = []; console.warn('[TechPanel] adj factor failed', results[1].reason) }
  if (results[2].status === 'fulfilled') suspend.value = results[2].value.events
  else { suspend.value = []; console.warn('[TechPanel] suspend failed', results[2].reason) }
  if (results[3].status === 'fulfilled') nameChange.value = results[3].value.history
  else { nameChange.value = []; console.warn('[TechPanel] name change failed', results[3].reason) }
  loadingKline.value = false
  loadingAdj.value = false
  loadingSuspend.value = false
  loadingName.value = false
}

watch(() => props.symbol, (s) => load(s), { immediate: true })
</script>

<style scoped>
.tech-panel {
  display: grid;
  gap: 0.75rem;
  padding: 0.5rem 0;
}
.tech-panel.cols-2 { grid-template-columns: 1fr 1fr; }
.tech-panel.cols-1 { grid-template-columns: 1fr; }

@media (max-width: 1100px) {
  .tech-panel.cols-2 { grid-template-columns: 1fr; }
}

.mini-table { padding: 0.25rem; }
.mono { font-family: ui-monospace, monospace; font-weight: 600; }
.font-bold { font-weight: 700; }
</style>
