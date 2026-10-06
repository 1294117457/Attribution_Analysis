<!--
  数据看板 · 技术面 Tab (tech)
  4 卡片：日 K 线 / 复权因子 / 停复牌 / 曾用名
-->
<template>
  <div class="grid-2">
    <!-- 日 K 线 -->
    <el-card shadow="never">
      <template #header>
        <span class="font-bold">日 K 线（含 17 指标）</span>
        <el-tag size="small" type="info" class="ml-2">{{ klineData.length }} 根</el-tag>
      </template>
      <MiniKlineChart
        :title="`${stockName || symbol} · 日K线`"
        :klines="klineData"
        :loading="loadingKline"
        :height="320"
        :show-main="['MA5','MA10','MA20','MA60','BOLL']"
        show-sub="MACD"
      />
    </el-card>

    <!-- 右侧三小卡片 -->
    <div class="flex-col">
      <!-- 复权因子 -->
      <el-card shadow="never" class="mb-2">
        <template #header>
          <span class="font-bold">复权因子</span>
          <el-tag size="small" type="info" class="ml-2">{{ adjFactor.length }} 条</el-tag>
        </template>
        <div v-loading="loadingAdj" class="mini-table">
          <el-table :data="adjFactor.slice(0, 30)" size="small" stripe max-height="200">
            <el-table-column prop="trade_date" label="日期" width="120" />
            <el-table-column label="因子" align="right">
              <template #default="{ row }">
                <span class="mono">{{ row.adj_factor != null ? row.adj_factor.toFixed(4) : '—' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <!-- 停复牌 -->
      <el-card shadow="never" class="mb-2">
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

      <!-- 曾用名 -->
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
  </div>
</template>

<script setup lang="ts">
import { ref, toRefs } from 'vue'
import MiniKlineChart from '@/views/stock-info/components/MiniKlineChart.vue'
import type { Kline } from '@/views/stock-info/api'
import * as API from './api'

const props = defineProps<{ symbol: string; stockName: string }>()

// template 里直接用 symbol / stockName（props 顶层名可自动解构）
const { symbol, stockName } = toRefs(props)

const klineData = ref<Kline[]>([])
const adjFactor = ref<API.AdjFactor[]>([])
const suspend = ref<API.SuspendEvent[]>([])
const nameChange = ref<API.NameChange[]>([])
const loadingKline = ref(false)
const loadingAdj = ref(false)
const loadingSuspend = ref(false)
const loadingName = ref(false)

async function load() {
  const s = props.symbol
  loadingKline.value = loadingAdj.value = loadingSuspend.value = loadingName.value = true
  await Promise.all([
    API.getKline(s, 250).then(r => {
      klineData.value = r.klines.map(b => ({
        symbol: s, name: props.stockName,
        date: b.trade_date, open: b.open, high: b.high, low: b.low, close: b.close,
        volume: b.volume, amount: b.amount ?? null, change_pct: b.change_pct ?? null,
      }))
    }).catch(e => console.warn('[TechPanel] K线', e)),
    API.getAdjFactor(s).then(r => adjFactor.value = r.factors).catch(e => console.warn('[TechPanel] 复权', e)),
    API.getSuspend(s).then(r => suspend.value = r.events).catch(e => console.warn('[TechPanel] 停牌', e)),
    API.getNameChange(s).then(r => nameChange.value = r.history).catch(e => console.warn('[TechPanel] 曾用名', e)),
  ])
  loadingKline.value = loadingAdj.value = loadingSuspend.value = loadingName.value = false
}

defineExpose({ load })
</script>

<style scoped>
.grid-2 {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 0.75rem; padding: 0.5rem 0;
}
@media (max-width: 1100px) { .grid-2 { grid-template-columns: 1fr; } }
.flex-col { display: flex; flex-direction: column; gap: 0.5rem; min-width: 0; }
.mb-2 { margin-bottom: 0.5rem; }
.mini-table { padding: 0.25rem; }
.mono { font-family: ui-monospace, monospace; font-weight: 600; }
.font-bold { font-weight: 700; }
.ml-2 { margin-left: 0.5rem; }
</style>