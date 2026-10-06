<!--
  数据看板 · 资金面 Tab (capital)
  6 卡片：资金流向 / 融资融券 / 龙虎榜每日 / 龙虎榜机构 / 大宗交易 / 股东户数
-->
<template>
  <div class="grid-2">
    <!-- 资金流向（占左半高） -->
    <el-card shadow="never">
      <template #header>
        <span class="font-bold">资金流向（主力/中单/小单）</span>
        <el-tag size="small" type="info" class="ml-2">{{ moneyflow.length }} 天</el-tag>
      </template>
      <div v-loading="loadingMF" class="mini-table">
        <el-table :data="moneyflow.slice(0, 30)" size="small" stripe max-height="500">
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

    <!-- 右侧五小卡片 -->
    <div class="flex-col">
      <!-- 融资融券 -->
      <el-card shadow="never" class="mb-2">
        <template #header>
          <span class="font-bold">融资融券</span>
          <el-tag size="small" type="warning" class="ml-2">{{ margin.length }} 天</el-tag>
        </template>
        <div v-loading="loadingMargin" class="mini-table">
          <el-table :data="margin.slice(0, 30)" size="small" stripe max-height="160">
            <el-table-column prop="trade_date" label="日期" width="110" />
            <el-table-column label="融资余额(亿)" align="right">
              <template #default="{ row }">
                <span class="mono">{{ yi(row.rzye) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="融券余额(亿)" align="right">
              <template #default="{ row }">
                <span class="mono">{{ yi(row.rqye) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="融资买入(亿)" align="right">
              <template #default="{ row }">
                <span class="mono">{{ yi(row.rzmre) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <!-- 龙虎榜每日 -->
      <el-card shadow="never" class="mb-2">
        <template #header>
          <span class="font-bold">龙虎榜每日</span>
          <el-tag size="small" type="danger" class="ml-2">{{ topList.length }} 条</el-tag>
        </template>
        <div v-loading="loadingTop" class="mini-table">
          <el-table :data="topList.slice(0, 30)" size="small" stripe max-height="160">
            <el-table-column prop="trade_date" label="日期" width="110" />
            <el-table-column label="涨跌幅" align="right" width="90">
              <template #default="{ row }">
                <span :class="colorClass(row.pct_change)" class="mono">
                  {{ fmtPct(row.pct_change) }}
                </span>
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

      <!-- 大宗交易 -->
      <el-card shadow="never" class="mb-2">
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

      <!-- 龙虎榜机构 -->
      <el-card shadow="never" class="mb-2">
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

      <!-- 股东户数 -->
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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import * as API from './api'

const props = defineProps<{ symbol: string }>()

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

async function load() {
  const s = props.symbol
  loadingMF.value = loadingMargin.value = loadingTop.value = true
  loadingInst.value = loadingBlock.value = loadingHolder.value = true
  await Promise.all([
    API.getMoneyflow(s, 60).then(r => moneyflow.value = r.flows).catch(e => console.warn('[CapitalPanel] 资金流', e)),
    API.getMargin(s, 60).then(r => margin.value = r.details).catch(e => console.warn('[CapitalPanel] 两融', e)),
    API.getTopList(s, 90).then(r => topList.value = r.lists).catch(e => console.warn('[CapitalPanel] 龙虎榜', e)),
    API.getTopInst(s, 90).then(r => topInst.value = r.details).catch(e => console.warn('[CapitalPanel] 机构席位', e)),
    API.getBlockTrade(s, 180).then(r => blockTrade.value = r.trades).catch(e => console.warn('[CapitalPanel] 大宗', e)),
    API.getHolderNum(s).then(r => holderNum.value = r.history).catch(e => console.warn('[CapitalPanel] 股东户数', e)),
  ])
  loadingMF.value = loadingMargin.value = loadingTop.value = false
  loadingInst.value = loadingBlock.value = loadingHolder.value = false
}

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