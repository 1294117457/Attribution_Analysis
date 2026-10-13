<!--
  CollectActionCard — 批量采集接口的采集卡片

  行 1：title + description
  行 2：采集类型（全量采集 / 条件采集）
  行 3：采集条件（按 task_type 查 SCHEMAS；全量采集时全部禁用）
  底部：并发度（仅支持的接口）+ 开始采集

  两种类型都下发 params.mode，后端跳过库中已有数据（增量）：
    - full:      后端用接口的 full_params，忽略条件
    - condition: 按所选条件
-->
<template>
  <CollectCard :title="taskDef.label" :description="taskDef.description">
    <template #tags>
      <el-tag v-if="taskDef.status === 'planned'" size="small" type="info">待实现</el-tag>
    </template>

    <CollectCardRow label="采集类型">
      <el-radio-group v-model="mode" size="small" :disabled="!ready">
        <el-radio-button value="full">全量采集</el-radio-button>
        <el-radio-button value="condition" :disabled="fields.length === 0">条件采集</el-radio-button>
      </el-radio-group>
      <span class="hint">{{ modeHint }}</span>
    </CollectCardRow>

    <CollectCardRow label="采集条件">
      <template v-if="fields.length > 0">
        <div v-for="f in fields" :key="f.key" class="cond">
          <span class="cond__label">{{ f.label }}</span>
          <el-select
            v-model="selections[f.key]"
            size="small"
            style="width: 130px"
            :disabled="condDisabled"
          >
            <el-option v-for="o in f.options" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-date-picker
            v-if="f.daterange && selections[f.key] === CUSTOM"
            v-model="daterange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYYMMDD"
            size="small"
            style="width: 240px"
            :disabled="condDisabled"
          />
        </div>
      </template>
      <span v-else class="hint">该接口无可选条件</span>
    </CollectCardRow>

    <template #footer>
      <template v-if="schema.concurrency">
        <span class="hint">并发度</span>
        <el-radio-group v-model="concurrency" size="small" :disabled="!ready">
          <el-radio-button v-for="n in CONCURRENCY_OPTIONS" :key="n" :value="n">{{ n }}</el-radio-button>
        </el-radio-group>
      </template>
      <el-button type="primary" size="small" :loading="starting" :disabled="!canStart" @click="start">
        开始采集
      </el-button>
    </template>
  </CollectCard>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import CollectCard from './CollectCard.vue'
import CollectCardRow from './CollectCardRow.vue'
import type { TaskDef } from '../api'

interface CondOption {
  label: string
  value: string
  params?: Record<string, any>
}

interface CondField {
  key: string
  label: string
  options: CondOption[]
  /** 选「自定义」时显示日期范围选择器（start_date / end_date） */
  daterange?: boolean
}

interface ActionSchema {
  fields: CondField[]
  /** 接口读取 params.concurrency */
  concurrency?: boolean
}

const props = defineProps<{
  taskType: string
  taskDef: TaskDef
  starting?: boolean
}>()

const emit = defineEmits<{
  (e: 'start', params: Record<string, any>): void
}>()

// ── 条件定义 ────────────────────────────────────────────
const CUSTOM = 'custom'
const CONCURRENCY_OPTIONS = [1, 2, 3, 5, 8]

const DAYS_FIELD: CondField = {
  key: 'time',
  label: '采集时间',
  daterange: true,
  options: [
    { label: '今日', value: '1', params: { days: 1 } },
    { label: '近 7 天', value: '7', params: { days: 7 } },
    { label: '近 30 天', value: '30', params: { days: 30 } },
    { label: '近 1 年', value: '365', params: { days: 365 } },
    { label: '自定义', value: CUSTOM },
  ],
}

const YEARS_FIELD: CondField = {
  key: 'time',
  label: '采集时间',
  options: [
    { label: '近 1 年', value: '1', params: { years: 1 } },
    { label: '近 3 年', value: '3', params: { years: 3 } },
    { label: '近 5 年', value: '5', params: { years: 5 } },
  ],
}

const EXCHANGE_FIELD: CondField = {
  key: 'scope',
  label: '采集范围',
  options: [
    { label: '全部', value: 'all' },
    { label: '上交所', value: 'SSE', params: { exchange: ['SSE'] } },
    { label: '深交所', value: 'SZSE', params: { exchange: ['SZSE'] } },
    { label: '北交所', value: 'BSE', params: { exchange: ['BSE'] } },
  ],
}

const LIMIT_FIELD: CondField = {
  key: 'scope',
  label: '采集范围',
  options: [
    { label: '全部', value: 'all' },
    { label: '前 20 个（测试）', value: '20', params: { limit: 20 } },
  ],
}

const SCHEMAS: Record<string, ActionSchema> = {
  daily_kline: { fields: [DAYS_FIELD, EXCHANGE_FIELD], concurrency: true },
  daily_basic: { fields: [DAYS_FIELD] },
  base_suspend: { fields: [DAYS_FIELD] },
  cap_moneyflow: { fields: [DAYS_FIELD] },
  cap_margin_detail: { fields: [DAYS_FIELD] },
  cap_top_list: { fields: [DAYS_FIELD] },
  cap_top_inst: { fields: [DAYS_FIELD] },
  cap_block_trade: { fields: [DAYS_FIELD] },
  fin_report: { fields: [YEARS_FIELD, LIMIT_FIELD] },
  base_adj_factor: { fields: [LIMIT_FIELD] },
  base_dividend: { fields: [LIMIT_FIELD] },
  fin_top10_holders: { fields: [LIMIT_FIELD] },
  fin_top10_floatholders: { fields: [LIMIT_FIELD] },
  cap_holder_num: { fields: [LIMIT_FIELD] },
  concept_membership: { fields: [LIMIT_FIELD] },
  concept_index_th: { fields: [LIMIT_FIELD] },
}

const schema = computed<ActionSchema>(() => SCHEMAS[props.taskType] || { fields: [] })
const fields = computed(() => schema.value.fields)

// ── 状态（切换接口时重置） ──────────────────────────────
const mode = ref<'full' | 'condition'>('full')
const selections = reactive<Record<string, string>>({})
const daterange = ref<[string, string] | null>(null)
const concurrency = ref(3)

watch(
  () => props.taskType,
  () => {
    mode.value = 'full'
    for (const k of Object.keys(selections)) delete selections[k]
    for (const f of fields.value) selections[f.key] = f.options[0].value
    daterange.value = null
  },
  { immediate: true },
)

const ready = computed(() => props.taskDef.status === 'ready')
const condDisabled = computed(() => !ready.value || mode.value === 'full')

const modeHint = computed(() =>
  mode.value === 'full'
    ? '采集该接口的全部数据，库中已有的自动跳过'
    : '按下方条件采集，库中已有的自动跳过',
)

const needsDaterange = computed(() =>
  fields.value.some((f) => f.daterange && selections[f.key] === CUSTOM),
)

const canStart = computed(() => {
  if (!ready.value || props.starting) return false
  if (mode.value === 'condition' && needsDaterange.value) {
    return !!daterange.value && daterange.value.length === 2
  }
  return true
})

function start() {
  const params: Record<string, any> = { mode: mode.value }
  if (schema.value.concurrency) params.concurrency = concurrency.value
  if (mode.value === 'condition') {
    for (const f of fields.value) {
      const v = selections[f.key]
      if (v === CUSTOM && daterange.value) {
        params.start_date = daterange.value[0]
        params.end_date = daterange.value[1]
      } else {
        Object.assign(params, f.options.find((o) => o.value === v)?.params)
      }
    }
  }
  emit('start', params)
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.cond {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cond__label {
  font-size: 13px;
  color: #475569;
  white-space: nowrap;
}
</style>
