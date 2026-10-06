<!--
 * components/data-board-tabs/FundamentalPanel.vue
 *
 * 基本面 Tab — 抽屉 / 看板共用
 *
 * 包含：日频估值 / 季报财务 / 前十大股东 / 前十大流通股东 / 分红送股
 *
 * 注：原 DataBoard 基本面里还有「股票基本信息」card（代码/名称/行业等），
 *    详情抽屉已经把基本信息提到 header 展示，**这里不再重复**；
 *    看板由 DataBoard 父级决定是否在 <FundamentalPanel> 外再补一个 info card。
 -->
<template>
  <div class="fundamental-panel" :class="`cols-${columns}`">
    <el-card shadow="never">
      <template #header>
        <span class="font-bold">日频估值（最新 {{ dailyBasic.length }} 天）</span>
      </template>
      <div v-loading="loadingBasic" class="mini-table">
        <el-table :data="dailyBasic.slice(0, 30)" size="small" stripe :max-height="tableMaxH">
          <el-table-column prop="trade_date" label="日期" width="110" fixed />
          <el-table-column label="收盘" align="right" width="80">
            <template #default="{ row }"><span class="mono">{{ row.close?.toFixed(2) ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column label="PE" align="right" width="80">
            <template #default="{ row }"><span class="mono">{{ row.pe?.toFixed(2) ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column label="PB" align="right" width="80">
            <template #default="{ row }"><span class="mono">{{ row.pb?.toFixed(2) ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column label="换手率" align="right" width="80">
            <template #default="{ row }"><span class="mono">{{ row.turnover_rate?.toFixed(2) ?? '—' }}%</span></template>
          </el-table-column>
          <el-table-column label="总市值(亿)" align="right" width="100">
            <template #default="{ row }"><span class="mono">{{ yi(row.total_mv) }}</span></template>
          </el-table-column>
          <el-table-column label="流通市值(亿)" align="right" width="100">
            <template #default="{ row }"><span class="mono">{{ yi(row.circ_mv) }}</span></template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">季报财务</span>
        <el-tag size="small" type="info" class="ml-2">{{ finReport.length }} 期</el-tag>
      </template>
      <div v-loading="loadingReport" class="mini-table">
        <el-table :data="finReport.slice(0, 30)" size="small" stripe max-height="240">
          <el-table-column prop="end_date" label="报告期" width="110" fixed />
          <el-table-column label="营收(亿)" align="right">
            <template #default="{ row }"><span class="mono">{{ yi(row.total_revenue) }}</span></template>
          </el-table-column>
          <el-table-column label="净利润(亿)" align="right">
            <template #default="{ row }">
              <span :class="colorClass(row.n_income)" class="mono">{{ yi(row.n_income) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="EPS" align="right">
            <template #default="{ row }"><span class="mono">{{ row.basic_eps?.toFixed(3) ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column label="净利润率" align="right">
            <template #default="{ row }"><span class="mono">{{ row.net_margin?.toFixed(2) ?? '—' }}%</span></template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">前十大股东</span>
        <el-tag size="small" type="warning" class="ml-2">{{ top10Holders.length }} 条</el-tag>
      </template>
      <div v-loading="loadingHolders" class="mini-table">
        <el-table :data="top10Holders.slice(0, 30)" size="small" stripe max-height="240">
          <el-table-column prop="end_date" label="报告期" width="110" />
          <el-table-column prop="holder_name" label="股东" show-overflow-tooltip />
          <el-table-column label="占比" align="right" width="80">
            <template #default="{ row }"><span class="mono">{{ row.hold_ratio?.toFixed(2) ?? '—' }}%</span></template>
          </el-table-column>
          <el-table-column label="流通占比" align="right" width="90">
            <template #default="{ row }"><span class="mono">{{ row.hold_float_ratio?.toFixed(2) ?? '—' }}%</span></template>
          </el-table-column>
          <el-table-column label="变动" align="right" width="100">
            <template #default="{ row }">
              <span :class="colorClass(row.hold_change)" class="mono">{{ yi(row.hold_change) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">前十大流通股东</span>
        <el-tag size="small" type="warning" class="ml-2">{{ top10Float.length }} 条</el-tag>
      </template>
      <div v-loading="loadingFloat" class="mini-table">
        <el-table :data="top10Float.slice(0, 30)" size="small" stripe max-height="240">
          <el-table-column prop="end_date" label="报告期" width="110" />
          <el-table-column prop="holder_name" label="流通股东" show-overflow-tooltip />
          <el-table-column label="占比" align="right" width="80">
            <template #default="{ row }"><span class="mono">{{ row.hold_ratio?.toFixed(2) ?? '—' }}%</span></template>
          </el-table-column>
          <el-table-column label="变动" align="right" width="100">
            <template #default="{ row }">
              <span :class="colorClass(row.hold_change)" class="mono">{{ yi(row.hold_change) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">分红送股</span>
        <el-tag size="small" type="success" class="ml-2">{{ dividend.length }} 条</el-tag>
      </template>
      <div v-loading="loadingDividend" class="mini-table">
        <el-table :data="dividend.slice(0, 30)" size="small" stripe max-height="240">
          <el-table-column prop="end_date" label="报告期" width="110" fixed />
          <el-table-column label="每股派息(税前)" align="right" width="140">
            <template #default="{ row }"><span class="mono">{{ row.cash_div?.toFixed(3) ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column label="每股送转" align="right" width="120">
            <template #default="{ row }"><span class="mono">{{ row.stk_bo_rate?.toFixed(3) ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column prop="ex_date" label="除权日" width="110" />
          <el-table-column prop="div_proc" label="进度" width="100" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import * as API from '@/views/concept-board/api-data-board'

const props = withDefaults(defineProps<{
  symbol: string
  columns?: 1 | 2
}>(), {
  columns: 2,
})

const tableMaxH = computed(() => props.columns === 1 ? 320 : 500)

const dailyBasic = ref<API.DailyBasicRow[]>([])
const finReport = ref<API.FinReportRow[]>([])
const top10Holders = ref<API.Top10Holder[]>([])
const top10Float = ref<API.Top10Holder[]>([])
const dividend = ref<API.DividendRow[]>([])
const loadingBasic = ref(false)
const loadingReport = ref(false)
const loadingHolders = ref(false)
const loadingFloat = ref(false)
const loadingDividend = ref(false)

async function load(s: string) {
  if (!/^\d{6}$/.test(s)) return
  loadingBasic.value = true; loadingReport.value = true; loadingHolders.value = true
  loadingFloat.value = true; loadingDividend.value = true
  const r = await Promise.allSettled([
    API.getDailyBasic(s, 60),
    API.getFinReport(s),
    API.getTop10Holders(s),
    API.getTop10Float(s),
    API.getDividend(s),
  ])
  if (r[0].status === 'fulfilled') dailyBasic.value = r[0].value.valuation
  else { dailyBasic.value = []; console.warn('[FundamentalPanel] daily basic failed', r[0].reason) }
  if (r[1].status === 'fulfilled') finReport.value = r[1].value.reports
  else { finReport.value = []; console.warn('[FundamentalPanel] fin report failed', r[1].reason) }
  if (r[2].status === 'fulfilled') top10Holders.value = r[2].value.holders
  else { top10Holders.value = []; console.warn('[FundamentalPanel] top10 holders failed', r[2].reason) }
  if (r[3].status === 'fulfilled') top10Float.value = r[3].value.holders
  else { top10Float.value = []; console.warn('[FundamentalPanel] top10 float failed', r[3].reason) }
  if (r[4].status === 'fulfilled') dividend.value = r[4].value.dividends
  else { dividend.value = []; console.warn('[FundamentalPanel] dividend failed', r[4].reason) }
  loadingBasic.value = false; loadingReport.value = false; loadingHolders.value = false
  loadingFloat.value = false; loadingDividend.value = false
}

watch(() => props.symbol, (s) => load(s), { immediate: true })

function yi(v: number | null | undefined): string {
  if (v == null) return '—'
  return (v / 10000).toFixed(2)
}
function colorClass(v: number | null | undefined): string {
  if (v == null || v === 0) return 'text-gray-400'
  return v > 0 ? 'text-red-500' : 'text-green-600'
}
</script>

<style scoped>
.fundamental-panel {
  display: grid;
  gap: 0.75rem;
  padding: 0.5rem 0;
}
.fundamental-panel.cols-2 { grid-template-columns: 1fr 1fr; }
.fundamental-panel.cols-1 { grid-template-columns: 1fr; }

@media (max-width: 1100px) {
  .fundamental-panel.cols-2 { grid-template-columns: 1fr; }
}

.mini-table { padding: 0.25rem; }
.mono { font-family: ui-monospace, monospace; font-weight: 600; }
.font-bold { font-weight: 700; }
</style>
