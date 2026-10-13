<template>
  <div class="expand-row">
    <!-- 🆕 概念 chips 区（顶部独立一行；外部高度锁死 30px）
     *
     *   关键不变式（外部高度锁死）：
     *   - div 始终渲染（无 v-if），高度锁死 30px（max-height + nowrap）
     *     → chart 起始位置恒定，**chip 加载前/后 chart 不下移**
     *   - 内部内容（loading / chips / 空状态）用 v-show 控制可见性
     *     → 内容增减不影响 div 高度
     *   - chip 数量 1→5→10 变化时 chips 区高度不变（max-height + 横滚）
     *
     *   不渲染条件：仅在用户禁用 / 永不适用概念功能时通过外层 props 控制；
     *   当前实现默认始终占位，避免外层布局抖动。 -->
    <div class="expand-concepts">
      <span class="expand-concepts__label">概念</span>
      <span v-show="chipsLoading && chips.length === 0" class="concept-skeleton-chip">
        <el-icon class="is-loading"><Loading /></el-icon>
        加载中…
      </span>
      <template v-for="c in chips.slice(0, MAX_CHIPS_VISIBLE)" :key="c.index_code">
        <el-tag
          v-show="!chipsLoading || chips.length > 0"
          size="small"
          :type="chipTagType(c)"
          effect="light"
          class="concept-chip"
          :class="{ 'is-stale': c.stale }"
          :title="chipTooltip(c)"
        >
          <span class="concept-chip__name">{{ c.concept_name }}</span>
          <span v-if="c.pct_change != null" class="concept-chip__pct">
            {{ c.pct_change >= 0 ? '+' : '' }}{{ c.pct_change.toFixed(2) }}%
          </span>
        </el-tag>
      </template>
      <el-tooltip
        v-if="chips.length > MAX_CHIPS_VISIBLE"
        :content="chips.slice(MAX_CHIPS_VISIBLE).map(c => chipTooltip(c)).join('\n')"
        placement="top"
      >
        <span class="concept-chip concept-chip--more">+{{ chips.length - MAX_CHIPS_VISIBLE }}</span>
      </el-tooltip>
      <span v-if="chips.some(c => c.stale)" class="expand-concepts__hint">行情源暂不可用</span>
      <span v-if="!chipsLoading && chips.length === 0" class="expand-concepts__empty">—</span>
    </div>

    <div class="expand-charts">
      <DailyKlineChart class="chart-col" :symbol="symbol" />
      <InfoCard class="chart-col">
        <template #title>
          <span class="chart-label">
            分 K
            <b v-if="lastMinute?.close != null">{{ lastMinute.close.toFixed(2) }}</b>
          </span>
        </template>
        <template #tools>
          <el-select
            v-model="minuteInterval"
            size="small"
            placeholder="周期"
            style="width: 68px"
            @change="onIntervalChange"
          >
            <el-option v-for="o in intervalOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-select
            v-model="minuteDays"
            size="small"
            placeholder="天数"
            style="width: 68px"
            @change="loadMinuteKlines()"
          >
            <el-option v-for="o in minuteDayOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-tag v-if="trading && !paused" size="small" type="danger" effect="plain">实时 · 15 秒</el-tag>
          <el-tag v-else-if="!trading" size="small" type="info" effect="plain">已收盘</el-tag>
        </template>
        <template #extra>
          <span>{{ minuteLoading ? '加载中…' : `${minuteKlines.length} 根` }}</span>
          <el-link v-if="paused" type="warning" :underline="false" @click="resume">
            实时更新已暂停 · 重试
          </el-link>
          <span v-else-if="minuteUpdatedAt">{{ minuteUpdatedAt }}</span>
        </template>
        <MiniKlineChart
          :title="''"
          hide-header
          :klines="minuteKlinesAsDaily"
          :loading="minuteLoading"
          :height="145"
          :show-main="[]"
        />
      </InfoCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import MiniKlineChart from './MiniKlineChart.vue'
import DailyKlineChart from './DailyKlineChart.vue'
import InfoCard from '@/components/InfoCard.vue'
import {
  getMinuteKlines,
  getConceptTabForSymbol,
  getConceptQuotes,
} from '@/views/stock-info/api'
import type { Kline, MinuteKline, ConceptSnapshot } from '@/views/stock-info/api'
import { useRealtimePoll } from '@/composables/useRealtimePoll'

const props = defineProps<{
  symbol: string
}>()

// ── 分K 选项（周期 + 天数 两个独立选择器） ────────────
const intervalOptions = [
  { label: '1min',  value: '1min' },
  { label: '5min',  value: '5min' },
  { label: '15min', value: '15min' },
  { label: '30min', value: '30min' },
  { label: '60min', value: '60min' },
]
// 1 分钟只看当天；其他周期最多 5 日（多日走势看日 K）
const minuteInterval = ref('5min')
const minuteDays = ref(1)
const minuteDayOptions = computed(() =>
  minuteInterval.value === '1min'
    ? [{ label: '当天', value: 1 }]
    : [
        { label: '当天', value: 1 },
        { label: '3 日', value: 3 },
        { label: '5 日', value: 5 },
      ],
)

function onIntervalChange() {
  if (minuteInterval.value === '1min') minuteDays.value = 1
  loadMinuteKlines()
}

// ── 数据 ───────────────────────────────────────────────
const minuteKlines = ref<MinuteKline[]>([])
const minuteLoading = ref(false)

const lastMinute = computed(() => minuteKlines.value[0] ?? null)

const minuteKlinesAsDaily = computed<Kline[]>(() =>
  minuteKlines.value.map(m => ({
    date: m.datetime,
    open: m.open,
    high: m.high,
    low: m.low,
    close: m.close,
    volume: m.volume,
    amount: m.amount,
    change_pct: null,
    ma5: null, ma10: null, ma20: null, ma60: null,
    ema12: null, ema26: null,
    macd_dif: null, macd_dea: null, macd_bar: null,
    rsi6: null, rsi12: null, rsi24: null,
    kdj_k: null, kdj_d: null, kdj_j: null,
    boll_up: null, boll_mid: null, boll_dn: null,
  }))
)

// ── 加载 ───────────────────────────────────────────────
const minuteUpdatedAt = ref('')

/** silent=true：轮询刷新，不显示 loading、失败时保留上一次的图并把错误抛给轮询器计数 */
async function loadMinuteKlines(silent = false) {
  if (!silent) minuteLoading.value = true
  try {
    const res = await getMinuteKlines(props.symbol, {
      interval: minuteInterval.value,
      days: minuteDays.value,
    })
    minuteKlines.value = res.items ?? []
    minuteUpdatedAt.value = res.fetched_at ? `更新于 ${res.fetched_at.slice(11, 19)}` : ''
  } catch (e) {
    if (silent) throw e
    minuteKlines.value = []
  } finally {
    if (!silent) minuteLoading.value = false
  }
}

const { paused, trading, resume } = useRealtimePoll(() => loadMinuteKlines(true), { interval: 15_000 })

// ── 🆕 概念 chips（顶部摘要区） ──────────────────────────
//
// 数据流：
//   1. mount / symbol 变化 → loadConceptChips()
//   2. 调 getConceptTabForSymbol → 提取 sections[*].concepts[*].index_code
//   3. 调 getConceptQuotes(codes) → 15s 缓存、同源限流、自动降级（stale=true）
//   4. 合并到 chips.value；轮询复用 useRealtimePoll（跟分 K 同 15s 节奏）
//
// 配套设计：docs/dev/step2/04采集管理优化/06实时数据接口.md §6.3
const MAX_CHIPS_VISIBLE = 5
const chips = ref<ConceptSnapshot[]>([])
const chipsLoading = ref(false)

function chipTagType(c: ConceptSnapshot): 'success' | 'danger' | 'info' {
  if (c.stale || c.pct_change == null) return 'info'
  if (c.pct_change > 0) return 'danger'   // 红涨（A 股惯例）
  if (c.pct_change < 0) return 'success'   // 绿跌
  return 'info'
}

function chipTooltip(c: ConceptSnapshot): string {
  const parts = [`${c.concept_name} (${c.index_code})`]
  if (c.price != null) parts.push(`现价 ${c.price.toFixed(2)}`)
  if (c.prev_close != null) parts.push(`昨收 ${c.prev_close.toFixed(2)}`)
  if (c.pct_change != null) parts.push(`涨跌 ${c.pct_change >= 0 ? '+' : ''}${c.pct_change.toFixed(2)}%`)
  if (c.trade_time) parts.push(`时间 ${c.trade_time.slice(11, 19)}`)
  if (c.stale) parts.push('（行情源暂不可用）')
  return parts.join('\n')
}

/** silent=true：useRealtimePoll 周期性刷新时不显示 loading，避免 chips 闪烁 */
async function loadConceptChips(silent = false) {
  if (!silent) chipsLoading.value = true
  try {
    const tab = await getConceptTabForSymbol(props.symbol)
    const codes: string[] = []
    for (const sec of tab.sections ?? []) {
      for (const c of sec.concepts ?? []) {
        if (c.index_code) codes.push(c.index_code)
      }
    }
    if (codes.length === 0) {
      chips.value = []
      return
    }
    // 去重（同 code 不会重复出现，但下游接口对顺序敏感，先去重保稳定）
    const uniqueCodes = Array.from(new Set(codes))
    const quotes = await getConceptQuotes(uniqueCodes)
    chips.value = uniqueCodes
      .map(code => quotes[code])
      .filter((q): q is ConceptSnapshot => Boolean(q))
  } catch (e) {
    if (!silent) chips.value = []
    if (silent) throw e   // 让 useRealtimePoll 计数失败
  } finally {
    if (!silent) chipsLoading.value = false
  }
}

// 概念 chips 也走 15s 轮询（与分 K 同节奏、复用同一个 composable）
useRealtimePoll(loadConceptChips, { interval: 15_000 })

watch(() => props.symbol, () => {
  loadMinuteKlines()
  loadConceptChips()
})

onMounted(() => {
  loadMinuteKlines()
  loadConceptChips()
})
</script>

<style scoped>
.expand-row {
  /* ═══ 紧凑化密度变量（11 个）══════════════════════════════
   * 全部作用域限定在 .expand-row（scoped），不污染全局
   * 单一调节点：所有视觉密度由这 11 个变量派生 */
  --ex-fs-label:  11px;     /* 主标签字号（日 K / 概念 / 周期）*/
  --ex-fs-value:  11px;     /* 数值字号（价格 / 涨跌幅，tabular-nums）*/
  --ex-fs-chip:   10.5px;   /* chip 内字号（最细）*/
  --ex-fs-hint:   10px;     /* 提示字号（加载中 / 更新于 / 行情源）*/
  --ex-h-row:     22px;     /* chart-toolbar 行高（与 chip 同高）*/
  --ex-h-chip:    20px;     /* chip 高度 */
  --ex-h-bar:     26px;     /* chips 区总高（chip 20 + 上下 padding 3×2 = 26）*/
  --ex-gap-xs:    2px;
  --ex-gap-sm:    4px;
  --ex-gap-md:    8px;
  --ex-gap-lg:    12px;

  /* L1 容器背景（与 expanded-cell 同色）= 与表格行视觉分隔 */
  padding: 0;            /* 外边距统一由 StockInfoList 的 expanded-cell padding 控制 */
  margin: 0;
}

/* ════════════════════════════════════════════════════════════════
 * 顶部概念 chips 区（独立一行；外部高度锁死 26px）
 *
 * 关键不变式（外部高度锁死是核心）：
 *   - div 始终渲染（外部父模板无 v-if），高度锁死 26px（max-height + nowrap）
 *     → chart 起始位置恒定：chip 加载前/后、加载中/完成、chip=0 都不影响 chart 位置
 *   - 内部内容（loading / chips / 空状态「—」）用 v-show 控制可见性
 *     → 内容增减不影响 div 高度
 *   - chip 数量 1→5→10 变化时 chips 区高度不变（max-height + 横滚）
 *
 * 涨跌幅色：A 股惯例（红涨/绿跌）；stale 时灰显
 * chips 数量上限 MAX_CHIPS_VISIBLE，超出折成「+N」tooltip
 * ════════════════════════════════════════════════════════════════ */
.expand-concepts {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;            /* 锁单行：chip 数变不影响 chips 区高度 */
  gap: var(--ex-gap-sm);
  height: var(--ex-h-bar);      /* 26px（外部高度锁死）*/
  min-height: var(--ex-h-bar);  /* 锁下限 */
  max-height: var(--ex-h-bar);  /* 锁上限 */
  padding: 3px 0;               /* 左右与下方卡片边缘对齐 */
  margin: 0 0 var(--ex-gap-sm); /* 与 .expand-charts 4px 分隔 */
  border-bottom: 1px dashed #cbd5e1;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
  box-sizing: border-box;
}

.expand-concepts::-webkit-scrollbar {
  height: 4px;
}
.expand-concepts::-webkit-scrollbar-track {
  background: transparent;
}
.expand-concepts::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 2px;
}
.expand-concepts::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.expand-concepts__label {
  font-size: var(--ex-fs-label);
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
  flex-shrink: 0;
}

.expand-concepts__hint {
  font-size: var(--ex-fs-hint);
  color: #9ca3af;
  margin-left: var(--ex-gap-sm);
}

.expand-concepts__empty {
  font-size: var(--ex-fs-hint);
  color: #cbd5e1;
  white-space: nowrap;
  flex-shrink: 0;
  user-select: none;
}

.concept-skeleton-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--ex-gap-xs);
  font-size: var(--ex-fs-hint);
  color: #94a3b8;
}

.concept-chip {
  display: inline-flex !important;
  align-items: center;
  gap: var(--ex-gap-sm);
  height: var(--ex-h-chip) !important;   /* 20px（与 chart-toolbar 同高）*/
  padding: 0 var(--ex-gap-md) !important;
  font-size: var(--ex-fs-chip) !important; /* 10.5px */
  line-height: 1 !important;
  border-radius: 3px;
  flex-shrink: 0;
}

.concept-chip__name {
  font-weight: 500;
}

.concept-chip__pct {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.concept-chip.is-stale {
  opacity: 0.55;
  filter: grayscale(0.6);
}

.concept-chip--more {
  display: inline-flex;
  align-items: center;
  height: var(--ex-h-chip);
  padding: 0 var(--ex-gap-md);
  font-size: var(--ex-fs-chip);
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  cursor: help;
  flex-shrink: 0;
}

/* ════════════════════════════════════════════════════════════════
 * 图表区：日 K / 分 K 两张卡片并排
 * 卡片统一使用 InfoCard（规范见 card-guide.md），这里只负责并排布局
 * ════════════════════════════════════════════════════════════════ */
.expand-charts {
  display: flex;
  gap: var(--ex-gap-md);        /* 8px */
}

.chart-col { flex: 1; }

.chart-label {
  display: inline-flex;
  align-items: baseline;
  gap: var(--ex-gap-sm);
}

.chart-label b {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

/* ════════════════════════════════════════════════════════════════
 * MiniKlineChart 占位符边框调整（避免与 L2 卡片边框重复成"双层"）
 *
 * 原 MiniKlineChart 内部 placeholder 自带 border-radius + dashed border
 * 现在父级 .chart-col 已是 InfoCard（白底 + border + radius + overflow:hidden）
 * placeholder 应透明，仅保留视觉"空态"暗示
 * ════════════════════════════════════════════════════════════════ */
.chart-col :deep(.mini-kline-placeholder) {
  background: transparent;             /* 透明：让 chart-col 白底透出 */
  border: none;                        /* 取消虚线边框：避免与 L2 卡片边框重复 */
  color: #94a3b8;
}

</style>
