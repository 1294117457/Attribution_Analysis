<!--
  数据看板 · 基本面 Tab (fundamental)
  6 卡片：股票基本信息 / 日频估值 / 季报财务 / 前十大股东 / 前十大流通股东 / 分红送股
  注：概念子分类后续单独迭代，本期不展示
-->
<template>
  <div class="grid-2">
    <!-- 股票基本信息 -->
    <el-card shadow="never">
      <template #header>
        <span class="font-bold">股票基本信息</span>
      </template>
      <div v-loading="loadingStock" class="info-grid">
        <template v-if="stockInfo">
          <div class="info-row"><label>代码</label><span class="mono">{{ stockInfo.symbol }}</span></div>
          <div class="info-row"><label>名称</label><span class="font-bold">{{ stockInfo.name }}</span></div>
          <div class="info-row"><label>行业</label>{{ stockInfo.industry || '—' }}</div>
          <div class="info-row"><label>市场</label>{{ stockInfo.market || '—' }}</div>
          <div class="info-row"><label>交易所</label>{{ stockInfo.exchange || '—' }}</div>
          <div class="info-row"><label>地域</label>{{ stockInfo.area || '—' }}</div>
          <div class="info-row"><label>上市日</label><span class="mono">{{ stockInfo.list_date || '—' }}</span></div>
          <div class="info-row"><label>沪深港通</label>{{ stockInfo.is_hs === 'N' ? '否' : stockInfo.is_hs }}</div>
          <div class="info-row"><label>法人</label>{{ stockInfo.act_name || '—' }}</div>
        </template>
        <div v-else-if="!loadingStock" class="text-gray-400 text-sm">暂无数据</div>
      </div>
    </el-card>

    <!-- 日频估值 -->
    <el-card shadow="never">
      <template #header>
        <span class="font-bold">日频估值（最新 {{ dailyBasic.length }} 天）</span>
      </template>
      <div v-loading="loadingBasic" class="mini-table">
        <el-table :data="dailyBasic.slice(0, 30)" size="small" stripe max-height="500">
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

    <!-- 季报财务 -->
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
            <template #default="{ row }"><span :class="colorClass(row.n_income)" class="mono">{{ yi(row.n_income) }}</span></template>
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

    <!-- 前十大股东 -->
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

    <!-- 前十大流通股东 -->
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

    <!-- 分红送股 -->
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
import { ref } from 'vue'
import * as API from './api'

const props = defineProps<{ symbol: string }>()

const stockInfo = ref<API.StockInfo | null>(null)
const dailyBasic = ref<API.DailyBasicRow[]>([])
const finReport = ref<API.FinReportRow[]>([])
const top10Holders = ref<API.Top10Holder[]>([])
const top10Float = ref<API.Top10Holder[]>([])
const dividend = ref<API.DividendRow[]>([])
const loadingStock = ref(false)
const loadingBasic = ref(false)
const loadingReport = ref(false)
const loadingHolders = ref(false)
const loadingFloat = ref(false)
const loadingDividend = ref(false)

async function load() {
  const s = props.symbol
  loadingStock.value = loadingBasic.value = loadingReport.value = true
  loadingHolders.value = loadingFloat.value = loadingDividend.value = true
  await Promise.all([
    API.getStockInfo(s).then(r => stockInfo.value = r).catch(e => console.warn('[FundamentalPanel] 股票信息', e)),
    API.getDailyBasic(s, 60).then(r => dailyBasic.value = r.valuation).catch(e => console.warn('[FundamentalPanel] 估值', e)),
    API.getFinReport(s).then(r => finReport.value = r.reports).catch(e => console.warn('[FundamentalPanel] 季报', e)),
    API.getTop10Holders(s).then(r => top10Holders.value = r.holders).catch(e => console.warn('[FundamentalPanel] 前十大', e)),
    API.getTop10Float(s).then(r => top10Float.value = r.holders).catch(e => console.warn('[FundamentalPanel] 流通股东', e)),
    API.getDividend(s).then(r => dividend.value = r.dividends).catch(e => console.warn('[FundamentalPanel] 分红', e)),
  ])
  loadingStock.value = loadingBasic.value = loadingReport.value = false
  loadingHolders.value = loadingFloat.value = loadingDividend.value = false
}

// ── 工具 ──
function yi(v: number | null | undefined): string {
  if (v == null) return '—'
  return (v / 10000).toFixed(2)
}
function colorClass(v: number | null | undefined): string {
  if (v == null || v === 0) return 'text-gray-400'
  return v > 0 ? 'text-red-500' : 'text-green-600'
}

defineExpose({ load })
</script>

<style scoped>
.grid-2 {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 0.75rem; padding: 0.5rem 0;
}
@media (max-width: 1100px) { .grid-2 { grid-template-columns: 1fr; } }

.info-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem 1rem;
  padding: 0.5rem;
}
.info-row { display: flex; gap: 0.5rem; align-items: center; padding: 0.25rem 0; border-bottom: 1px solid #f1f5f9; }
.info-row label { color: #94a3b8; min-width: 70px; font-size: 0.85rem; }

.mini-table { padding: 0.25rem; }
.mono { font-family: ui-monospace, monospace; font-weight: 600; }
.font-bold { font-weight: 700; }
.ml-2 { margin-left: 0.5rem; }
</style>