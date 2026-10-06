<!--
 * components/data-board-tabs/CapitalPanel.vue
 *
 * 资金面 Tab — 抽屉 / 看板共用
 *
 * 7 张子卡：资金流向 / 融资融券 / 龙虎榜每日 / 龙虎榜机构 / 大宗交易 / 股东户数
 *（与原 DataBoard 一致）。父级用 columns 控制双列 / 单列。
 -->
<template>
  <div class="capital-panel" :class="`cols-${columns}`">
    <el-card shadow="never">
      <template #header>
        <span class="font-bold">资金流向（主力/中单/小单）</span>
        <el-tag size="small" type="info" class="ml-2">{{ moneyflow.length }} 天</el-tag>
      </template>
      <div v-loading="loadingMF" class="mini-table">
        <el-table :data="moneyflow.slice(0, 30)" size="small" stripe :max-height="tableMaxH">
          <el-table-column prop="trade_date" label="日期" width="110" fixed />
          <el-table-column label="特大单净额(万)" align="right" width="120">
            <template #default="{ row }">
              <span :class="colorClass(el(row.buy_elg_amount) - el(row.sell_elg_amount))" class="mono">
                {{ yi(el(row.buy_elg_amount) - el(row.sell_elg_amount)) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="大单净额(万)" align="right" width="120">
            <template #default="{ row }">
              <span :class="colorClass(el(row.buy_lg_amount) - el(row.sell_lg_amount))" class="mono">
                {{ yi(el(row.buy_lg_amount) - el(row.sell_lg_amount)) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="中单净额(万)" align="right" width="120">
            <template #default="{ row }">
              <span :class="colorClass(el(row.buy_md_amount) - el(row.sell_md_amount))" class="mono">
                {{ yi(el(row.buy_md_amount) - el(row.sell_md_amount)) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="小单净额(万)" align="right" width="120">
            <template #default="{ row }">
              <span :class="colorClass(el(row.buy_sm_amount) - el(row.sell_sm_amount))" class="mono">
                {{ yi(el(row.buy_sm_amount) - el(row.sell_sm_amount)) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="总净流入(万)" align="right" width="120">
            <template #default="{ row }">
              <span :class="colorClass(row.net_mf_amount)" class="mono font-bold">
                {{ yi(row.net_mf_amount) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">融资融券</span>
        <el-tag size="small" type="warning" class="ml-2">{{ margin.length }} 天</el-tag>
      </template>
      <div v-loading="loadingMargin" class="mini-table">
        <el-table :data="margin.slice(0, 30)" size="small" stripe max-height="160">
          <el-table-column prop="trade_date" label="日期" width="110" />
          <el-table-column label="融资余额(亿)" align="right">
            <template #default="{ row }"><span class="mono">{{ yi(row.rzye) }}</span></template>
          </el-table-column>
          <el-table-column label="融券余额(亿)" align="right">
            <template #default="{ row }"><span class="mono">{{ yi(row.rqye) }}</span></template>
          </el-table-column>
          <el-table-column label="融资买入(亿)" align="right">
            <template #default="{ row }"><span class="mono">{{ yi(row.rzmre) }}</span></template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">龙虎榜每日</span>
        <el-tag size="small" type="danger" class="ml-2">{{ topList.length }} 条</el-tag>
      </template>
      <div v-loading="loadingTop" class="mini-table">
        <el-table :data="topList.slice(0, 30)" size="small" stripe max-height="160">
          <el-table-column prop="trade_date" label="日期" width="110" />
          <el-table-column label="涨跌幅" align="right" width="90">
            <template #default="{ row }">
              <span :class="colorClass(row.pct_change)" class="mono">{{ fmtPct(row.pct_change) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="净买入(万)" align="right">
            <template #default="{ row }">
              <span :class="colorClass(row.net_amount)" class="mono">{{ yi(row.net_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="上榜原因" show-overflow-tooltip />
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">大宗交易</span>
        <el-tag size="small" type="info" class="ml-2">{{ blockTrade.length }} 条</el-tag>
      </template>
      <div v-loading="loadingBlock" class="mini-table">
        <el-table :data="blockTrade.slice(0, 30)" size="small" stripe max-height="160">
          <el-table-column prop="trade_date" label="日期" width="110" />
          <el-table-column label="价格" align="right" width="80">
            <template #default="{ row }"><span class="mono">{{ row.price?.toFixed(2) ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column label="成交量(万)" align="right" width="100">
            <template #default="{ row }"><span class="mono">{{ row.vol?.toFixed(0) ?? '—' }}</span></template>
          </el-table-column>
          <el-table-column label="买方营业部" show-overflow-tooltip />
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">龙虎榜机构席位</span>
        <el-tag size="small" type="danger" class="ml-2">{{ topInst.length }} 条</el-tag>
      </template>
      <div v-loading="loadingInst" class="mini-table">
        <el-table :data="topInst.slice(0, 30)" size="small" stripe max-height="160">
          <el-table-column prop="trade_date" label="日期" width="110" />
          <el-table-column prop="exalter" label="营业部" show-overflow-tooltip />
          <el-table-column label="方向" align="center" width="60">
            <template #default="{ row }">
              <el-tag :type="row.side === '1' ? 'danger' : 'success'" size="small">
                {{ row.side === '1' ? '买' : '卖' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="净额(万)" align="right" width="100">
            <template #default="{ row }">
              <span :class="colorClass(row.net_buy)" class="mono">{{ yi(row.net_buy) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span class="font-bold">股东户数</span>
        <el-tag size="small" type="info" class="ml-2">{{ holderNum.length }} 条</el-tag>
      </template>
      <div v-loading="loadingHolder" class="mini-table">
        <el-table :data="holderNum.slice(0, 30)" size="small" stripe max-height="140">
          <el-table-column prop="end_date" label="截止日" width="110" />
          <el-table-column label="股东户数" align="right">
            <template #default="{ row }">
              <span class="mono">{{ row.holder_num?.toLocaleString() ?? '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="ann_date" label="公告日" width="110" />
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

// 抽屉窄（480px）时，资金流向 6 列会挤死，限定 max-height 走内部滚动
const tableMaxH = computed(() => props.columns === 1 ? 320 : 500)

const moneyflow = ref<API.MoneyflowDay[]>([])
const margin = ref<API.MarginDay[]>([])
const topList = ref<API.TopListRow[]>([])
const topInst = ref<API.TopInstRow[]>([])
const blockTrade = ref<API.BlockTradeRow[]>([])
const holderNum = ref<API.HolderNumRow[]>([])
const loadingMF = ref(false)
const loadingMargin = ref(false)
const loadingTop = ref(false)
const loadingInst = ref(false)
const loadingBlock = ref(false)
const loadingHolder = ref(false)

async function load(s: string) {
  if (!/^\d{6}$/.test(s)) return
  loadingMF.value = true; loadingMargin.value = true; loadingTop.value = true
  loadingInst.value = true; loadingBlock.value = true; loadingHolder.value = true
  const r = await Promise.allSettled([
    API.getMoneyflow(s, 60),
    API.getMargin(s, 60),
    API.getTopList(s, 90),
    API.getTopInst(s, 90),
    API.getBlockTrade(s, 180),
    API.getHolderNum(s),
  ])
  if (r[0].status === 'fulfilled') moneyflow.value = r[0].value.flows
  else { moneyflow.value = []; console.warn('[CapitalPanel] moneyflow failed', r[0].reason) }
  if (r[1].status === 'fulfilled') margin.value = r[1].value.details
  else { margin.value = []; console.warn('[CapitalPanel] margin failed', r[1].reason) }
  if (r[2].status === 'fulfilled') topList.value = r[2].value.lists
  else { topList.value = []; console.warn('[CapitalPanel] top-list failed', r[2].reason) }
  if (r[3].status === 'fulfilled') topInst.value = r[3].value.details
  else { topInst.value = []; console.warn('[CapitalPanel] top-inst failed', r[3].reason) }
  if (r[4].status === 'fulfilled') blockTrade.value = r[4].value.trades
  else { blockTrade.value = []; console.warn('[CapitalPanel] block-trade failed', r[4].reason) }
  if (r[5].status === 'fulfilled') holderNum.value = r[5].value.history
  else { holderNum.value = []; console.warn('[CapitalPanel] holder-num failed', r[5].reason) }
  loadingMF.value = false; loadingMargin.value = false; loadingTop.value = false
  loadingInst.value = false; loadingBlock.value = false; loadingHolder.value = false
}

watch(() => props.symbol, (s) => load(s), { immediate: true })

// ── 工具 ──
function el(v: number | null | undefined): number { return v ?? 0 }
function yi(v: number | null | undefined): string {
  if (v == null) return '—'
  return (v / 10000).toFixed(2)
}
function fmtPct(v: number | null | undefined): string {
  if (v == null) return '—'
  return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
}
function colorClass(v: number | null | undefined): string {
  if (v == null || v === 0) return 'text-gray-400'
  return v > 0 ? 'text-red-500' : 'text-green-600'
}
</script>

<style scoped>
.capital-panel {
  display: grid;
  gap: 0.75rem;
  padding: 0.5rem 0;
}
.capital-panel.cols-2 { grid-template-columns: 1fr 1fr; }
.capital-panel.cols-1 { grid-template-columns: 1fr; }

@media (max-width: 1100px) {
  .capital-panel.cols-2 { grid-template-columns: 1fr; }
}

.mini-table { padding: 0.25rem; }
.mono { font-family: ui-monospace, monospace; font-weight: 600; }
.font-bold { font-weight: 700; }
</style>
