<!-- 技术形态信号摘要面板 -->
<template>
  <div class="signal-panel">
    <!-- 信号标签 -->
    <div class="flex flex-wrap gap-1 mb-3">
      <el-tag
        v-for="s in summary.signals"
        :key="s"
        :type="signalTagType(s)"
        effect="dark"
        size="small"
      >
        {{ s }}
      </el-tag>
      <el-tag v-if="!summary.signals.length" type="info" size="small">
        无明显信号
      </el-tag>
    </div>

    <!-- 关键数值 -->
    <el-descriptions :column="1" border size="small">
      <el-descriptions-item label="最新价">
        <span class="font-semibold">{{ summary.latest_close.toFixed(2) }}</span>
        <span
          class="ml-2"
          :class="summary.pct_change_1d >= 0 ? 'text-red-500' : 'text-green-500'"
        >
          {{ summary.pct_change_1d >= 0 ? '+' : '' }}{{ summary.pct_change_1d.toFixed(2) }}%
        </span>
      </el-descriptions-item>

      <el-descriptions-item label="30日涨跌">
        <span :class="summary.pct_change_30d >= 0 ? 'text-red-500' : 'text-green-500'">
          {{ summary.pct_change_30d >= 0 ? '+' : '' }}{{ summary.pct_change_30d.toFixed(2) }}%
        </span>
      </el-descriptions-item>

      <!-- 均线 -->
      <el-descriptions-item label="均线排列">
        <el-tag :type="maType(summary.ma_alignment)" size="small">
          {{ maLabel(summary.ma_alignment) }}
        </el-tag>
        <span v-if="summary.ma5 != null" class="ml-2 text-xs text-gray-400">
          MA5={{ summary.ma5.toFixed(2) }}
        </span>
        <span v-if="summary.ma20 != null" class="ml-1 text-xs text-gray-400">
          MA20={{ summary.ma20.toFixed(2) }}
        </span>
      </el-descriptions-item>

      <!-- MACD -->
      <el-descriptions-item label="MACD">
        <el-tag :type="macdType(summary.macd_status)" size="small">
          {{ macdLabel(summary.macd_status) }}
        </el-tag>
        <div class="text-xs text-gray-500 mt-0.5">
          DIF {{ summary.macd_dif.toFixed(3) }}
          / DEA {{ summary.macd_dea.toFixed(3) }}
          / BAR {{ summary.macd_bar.toFixed(3) }}
        </div>
      </el-descriptions-item>

      <!-- RSI -->
      <el-descriptions-item label="RSI6">
        {{ summary.rsi6.toFixed(1) }}
        <el-tag :type="rsiType(summary.rsi_status)" size="small" class="ml-2">
          {{ rsiLabel(summary.rsi_status) }}
        </el-tag>
      </el-descriptions-item>

      <!-- KDJ -->
      <el-descriptions-item label="KDJ">
        <span class="text-xs">
          K={{ summary.kdj_k.toFixed(1) }}
          / D={{ summary.kdj_d.toFixed(1) }}
          / J={{ summary.kdj_j.toFixed(1) }}
        </span>
        <el-tag :type="kdjType(summary.kdj_status)" size="small" class="ml-2">
          {{ kdjLabel(summary.kdj_status) }}
        </el-tag>
      </el-descriptions-item>

      <!-- BOLL -->
      <el-descriptions-item label="布林带">
        <el-tag :type="bollType(summary.boll_position)" size="small">
          {{ bollLabel(summary.boll_position) }}
        </el-tag>
        <div v-if="summary.boll_up != null" class="text-xs text-gray-500 mt-0.5">
          上轨={{ summary.boll_up.toFixed(2) }}
          中轨={{ summary.boll_mid?.toFixed(2) }}
          下轨={{ summary.boll_dn?.toFixed(2) }}
        </div>
      </el-descriptions-item>
    </el-descriptions>
  </div>
</template>

<script setup lang="ts">
import type { TechnicalSummary } from '@/views/stock-info/api'

defineProps<{ summary: TechnicalSummary }>()

// ── 标签类型辅助函数 ──────────────────────────────────
function signalTagType(s: string): 'success' | 'danger' | 'warning' | 'info' {
  if (s.includes('超买') || s.includes('死叉') || s.includes('跌破') || s.includes('空头')) return 'danger'
  if (s.includes('金叉') || s.includes('突破') || s.includes('多头')) return 'success'
  if (s.includes('超卖')) return 'warning'
  return 'info'
}

function maLabel(v: string)         { return v === 'bullish' ? '多头排列' : v === 'bearish' ? '空头排列' : '震荡' }
function maType(v: string)          { return v === 'bullish' ? 'success' : v === 'bearish' ? 'danger' : 'info' }

const MACD_LABELS: Record<string, string> = {
  golden_cross: '金叉', death_cross: '死叉',
  above_zero: '零轴上', below_zero: '零轴下', neutral: '—',
}
const MACD_TYPES: Record<string, string> = {
  golden_cross: 'success', death_cross: 'danger',
  above_zero: 'success', below_zero: 'danger', neutral: 'info',
}
function macdLabel(v: string) { return MACD_LABELS[v] ?? v }
function macdType(v: string) { return MACD_TYPES[v] as any ?? 'info' }

function rsiLabel(v: string)   { return v === 'overbought' ? '超买' : v === 'oversold' ? '超卖' : '中性' }
function rsiType(v: string)     { return v === 'overbought' ? 'danger' : v === 'oversold' ? 'warning' : 'success' }

const KDJ_LABELS: Record<string, string> = {
  golden_cross: '金叉', death_cross: '死叉',
  overbought: '超买', oversold: '超卖', neutral: '—',
}
const KDJ_TYPES: Record<string, string> = {
  golden_cross: 'success', death_cross: 'danger',
  overbought: 'danger', oversold: 'warning', neutral: 'info',
}
function kdjLabel(v: string) { return KDJ_LABELS[v] ?? v }
function kdjType(v: string)  { return KDJ_TYPES[v] as any ?? 'info' }

const BOLL_LABELS: Record<string, string> = {
  above_upper: '突破上轨', below_lower: '跌破下轨',
  upper_half: '上半区', lower_half: '下半区', middle: '中轨附近',
}
const BOLL_TYPES: Record<string, string> = {
  above_upper: 'success', below_lower: 'danger',
  upper_half: 'warning', lower_half: 'info', middle: 'info',
}
function bollLabel(v: string) { return BOLL_LABELS[v] ?? v }
function bollType(v: string) { return BOLL_TYPES[v] as any ?? 'info' }
</script>

<style scoped>
.signal-panel { padding: 4px 0; }
</style>