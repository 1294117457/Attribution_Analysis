<!--
  CollectActionCard — 批量采集 service 的采集卡片（v3 重构）

  行 1：title + description
  行 2：增量采集 → 时间选择器（仅 incremental=true 时显示）
  行 3：默认行为摘要（轻量提示）
  底部：并发度 + 开始采集

  配套：backend/src/contexts/collect/interface/route/manage.py
-->
<template>
  <CollectCard :title="item.label" :description="item.description">
    <!-- 增量采集：时间选择器（仅 INCREMENTAL 类 service） -->
    <CollectCardRow v-if="item.incremental" label="时间范围">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="→"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        :shortcuts="dateShortcuts"
        class="!w-96"
      />
      <span class="hint">留空按 service 默认（增量）</span>
    </CollectCardRow>

    <div class="full-mode-banner">
      <div>默认行为：{{ defaultParamsHint }}</div>
      <div v-if="rateLimitHint" class="mt-1">限速：<code>{{ rateLimitHint }}</code></div>
    </div>

    <template #footer>
      <div class="flex items-center gap-2">
        <span>并发</span>
        <el-input-number v-model="form.concurrency" :min="1" :max="32" :step="1" class="!w-24" />
        <el-button
          type="primary"
          size="small"
          :loading="starting"
          :disabled="starting"
          @click="start"
        >开始采集</el-button>
      </div>
    </template>
  </CollectCard>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import CollectCard from './CollectCard.vue'
import CollectCardRow from './CollectCardRow.vue'
import type { CatalogItem, CollectStartPayload } from '../api'

const props = defineProps<{
  serviceName: string
  item: CatalogItem
  starting?: boolean
}>()

const emit = defineEmits<{
  (e: 'start', payload: CollectStartPayload): void
}>()

// ── 派生 ──────────────────────────────────────────────
const defaultParams = computed<Record<string, any>>(() => props.item.default_params || {})

/** 全量模式横幅：人类可读描述 "全市场（list_status=L）" */
const defaultParamsHint = computed<string>(() => {
  const p = defaultParams.value
  const bits: string[] = []
  if ('list_status' in p) bits.push(`list_status=${p.list_status}`)
  if ('exchange' in p) {
    const v = p.exchange
    bits.push(Array.isArray(v) && v.length ? v.join('/') : (v || '全部'))
  }
  if ('trade_date' in p) bits.push('按当日')
  if ('start_date' in p || 'end_date' in p) {
    const s = p.start_date || '不限'
    const e = p.end_date || '今天'
    bits.push(`${s} → ${e}`)
  }
  if ('symbols' in p) bits.push(Array.isArray(p.symbols) && p.symbols.length ? `${p.symbols.length} 只` : '全 A')
  if ('index_codes' in p) bits.push(Array.isArray(p.index_codes) && p.index_codes.length ? `${p.index_codes.length} 个` : '全概念')
  if ('days' in p) bits.push(`回溯 ${p.days} 天`)
  if ('years' in p) bits.push(`近 ${p.years} 年`)
  if (bits.length === 0) {
    if (props.item.kind === 'realtime') bits.push('实时查询（不写库）')
    else if (props.item.kind === 'full_refresh') bits.push('全量覆盖')
    else bits.push(props.item.description || '使用 service 默认行为')
  }
  return bits.join(' · ')
})

/** 后端限速描述 "tushare 200 次/60s" */
const rateLimitHint = computed<string | null>(() => {
  const r = props.item.rate_limit
  if (!r || !Array.isArray(r) || r.length < 3) return null
  const [src, cnt, win] = r
  return `${src} ${cnt} 次/${win}s`
})

// ── 时间选择器（增量采集） ──────────────────────────────
/** v-model: [startDate, endDate] | null */
const dateRange = ref<[string, string] | null>(null)

/** 快捷选项 */
const dateShortcuts = [
  { text: '今天', value: () => {
    const today = new Date()
    return [today, today]
  } },
  { text: '近 7 天', value: () => {
    const today = new Date()
    const ago = new Date(today.getTime() - 7 * 86400_000)
    return [ago, today]
  } },
  { text: '近 30 天', value: () => {
    const today = new Date()
    const ago = new Date(today.getTime() - 30 * 86400_000)
    return [ago, today]
  } },
  { text: '近 90 天', value: () => {
    const today = new Date()
    const ago = new Date(today.getTime() - 90 * 86400_000)
    return [ago, today]
  } },
]

// ── 表单状态 ─────────────────────────────────────────
/** 控件用的 form 字典：concurrency 是唯一由前端控制的字段 */
function makeForm(): Record<string, any> {
  return { concurrency: 5 }
}

const form = reactive<Record<string, any>>(makeForm())

/** 切 service 时重置 */
watch(
  () => props.serviceName,
  () => {
    for (const k of Object.keys(form)) delete (form as any)[k]
    Object.assign(form, makeForm())
    dateRange.value = null
  },
)

// ── 提交 ─────────────────────────────────────────
function start() {
  const params: Record<string, any> = {}

  // 增量采集：传时间范围
  if (props.item.incremental && dateRange.value) {
    const [start, end] = dateRange.value
    if (start) params.start_date = start
    if (end) params.end_date = end
  }

  // 并发总是传
  params.concurrency = (form as any).concurrency

  emit('start', { params })
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
  margin-left: 8px;
}

.full-mode-banner {
  margin-top: 6px;
  padding: 6px 10px;
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 12px;
  color: #92400e;
  line-height: 1.6;
}

.full-mode-banner code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #fef3c7;
  padding: 0 4px;
  border-radius: 3px;
  color: #78350f;
}

.mt-1 {
  margin-top: 4px;
}
</style>
