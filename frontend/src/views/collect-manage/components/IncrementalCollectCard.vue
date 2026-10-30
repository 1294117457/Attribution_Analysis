<!--
  IncrementalCollectCard.vue — 增量采集卡片

  ★ 契约（见 backend-java/docs/开发文档/采集模块/采集模块重构开发文档.md §7.3）：
    增量采集**只暴露时间范围的选择**给前端，其余参数一律走 collector 默认值。

  表单只有：
    - 时间范围（el-date-picker daterange）
    - 一个「开始增量采集」按钮

  提交参数：**只提交** {start_date, end_date}。

  RANGE=null 的增量（如 news 的「最近 N 分钟」窗口）：不出日期控件，
  改显示固定窗口提示 + 一个按钮。
-->
<template>
  <CollectCard :title="item.label" :description="item.description">
    <template #tags>
      <el-tag size="small" type="success" effect="plain">增量采集</el-tag>
    </template>

    <!-- 有时间维度：只出日期范围 -->
    <CollectCardRow v-if="hasRange" label="时间范围">
      <el-date-picker
        v-model="range"
        type="daterange"
        size="small"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        :clearable="true"
        :disabled-date="disableFuture"
        :shortcuts="shortcuts"
      />
      <span class="hint">
        最多 {{ MAX_RANGE_DAYS }} 天 · {{ granularityHint }}
      </span>
    </CollectCardRow>

    <!-- 无时间维度（RANGE=null）：固定窗口提示 -->
    <CollectCardRow v-else label="采集窗口">
      <span class="hint">
        该采集源无时间维度，按采集源内置窗口执行（如「最近 N 分钟」）
      </span>
    </CollectCardRow>

    <!-- 已选区间的摘要 -->
    <CollectCardRow v-if="hasRange && range?.length === 2" label="区间">
      <span class="summary">{{ range[0] }} → {{ range[1] }}</span>
      <span class="hint">{{ dayCount }} 天</span>
    </CollectCardRow>

    <template #footer>
      <el-button
        type="primary"
        size="small"
        :loading="starting"
        :disabled="starting || !canSubmit"
        @click="start"
      >开始增量采集</el-button>
    </template>
  </CollectCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import CollectCard from './CollectCard.vue'
import CollectCardRow from './CollectCardRow.vue'
import type { CatalogItem, CollectStartPayload } from '../api'

/** 与 collector 的 MAX_RANGE_DAYS 对齐 */
const MAX_RANGE_DAYS = 366

const props = defineProps<{
  serviceName: string
  item: CatalogItem
  starting?: boolean
}>()

const emit = defineEmits<{
  (e: 'start', payload: CollectStartPayload): void
}>()

/** 是否有时间维度（range 由 collector 的 RANGE 声明） */
const hasRange = computed(() => !!props.item.range)

/** granularity 提示（用实际拆步口径 step_granularity，回退 range.granularity） */
const granularityHint = computed(() => {
  const g = props.item.step_granularity ?? props.item.range?.granularity
  if (g === 'trade_day') return '按交易日展开（自动跳过休市日），进度 = 已采天数 / 总天数'
  if (g === 'day') return '按自然日区间'
  return ''
})

/** 日期区间（[start, end]） */
const range = ref<[string, string] | null>(null)

/** 默认：最近 7 天 */
function defaultRange(): [string, string] {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 6)
  const fmt = (d: Date) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  return [fmt(start), fmt(end)]
}

watch(
  () => props.serviceName,
  () => {
    range.value = defaultRange()
  },
  { immediate: true },
)

/** 未来日期禁用 */
function disableFuture(date: Date) {
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return date.getTime() > today.getTime()
}

/** 快捷区间 */
const shortcuts = computed(() => [
  { text: '最近 7 天', value: () => pickDays(7) },
  { text: '最近 30 天', value: () => pickDays(30) },
  { text: '最近 90 天', value: () => pickDays(90) },
  { text: '本月', value: () => pickMonth(0) },
  { text: '上月', value: () => pickMonth(-1) },
])

function fmt(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function pickDays(n: number): [Date, Date] {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - (n - 1))
  return [start, end]
}

function pickMonth(offset: number): [Date, Date] {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth() + offset, 1)
  const end = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)
  return [start, end]
}

/** 区间天数（含首尾） */
const dayCount = computed(() => {
  if (!range.value || range.value.length !== 2) return 0
  const s = new Date(range.value[0] + 'T00:00:00')
  const e = new Date(range.value[1] + 'T00:00:00')
  return Math.round((e.getTime() - s.getTime()) / 86400000) + 1
})

/** 是否可提交（有区间的必须选了区间；无区间的直接可提交） */
const canSubmit = computed(() => {
  if (!hasRange.value) return true
  if (!range.value || range.value.length !== 2) return false
  return dayCount.value > 0 && dayCount.value <= MAX_RANGE_DAYS
})

function start() {
  if (hasRange.value) {
    if (!range.value || range.value.length !== 2) {
      ElMessage.warning('请选择时间范围')
      return
    }
    if (dayCount.value > MAX_RANGE_DAYS) {
      ElMessage.warning(`日期范围最多 ${MAX_RANGE_DAYS} 天`)
      return
    }
    // ★ 只提交时间范围，其余参数一律走 collector 默认值
    emit('start', {
      strategy: 'incremental',
      params: { start_date: range.value[0], end_date: range.value[1] },
    })
    return
  }
  emit('start', { strategy: 'incremental', params: {} })
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: #94a3b8;
}

.summary {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #475569;
}
</style>
