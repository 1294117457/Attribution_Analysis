<!--
  AdvancedFilters — 采集条件（常驻显示，内联在采集卡片中）

  按 task_type 查 SCHEMAS 渲染对应控件；无 schema 的 task_type 不渲染。
  - daily_kline: 交易所多选 / 日期范围 / 并发度

  state 由父组件持有，子组件仅 emit 新 state，父组件合并后调用 startTask(taskType, state)。

  配套：docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §3.2.4
-->
<template>
  <div v-if="fields.length > 0" class="advanced-filters">
    <template v-for="f in fields" :key="f.key">
      <template v-if="f.kind === 'exchange-multiselect'">
        <el-select
          :model-value="state.exchange"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="全部交易所"
          clearable
          size="small"
          style="width: 190px"
          @update:model-value="update('exchange', $event)"
        >
          <el-option label="上交所 (SSE)" value="SSE" />
          <el-option label="深交所 (SZSE)" value="SZSE" />
          <el-option label="北交所 (BSE)" value="BSE" />
        </el-select>
      </template>

      <template v-else-if="f.kind === 'kline-daterange'">
        <el-date-picker
          :model-value="state.daterange"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYYMMDD"
          size="small"
          style="width: 240px"
          @update:model-value="update('daterange', $event)"
        />
        <el-button
          type="primary"
          size="small"
          :disabled="!state.daterange || state.daterange.length < 2"
          @click="emit('startWithDates', { start_date: state.daterange![0], end_date: state.daterange![1] })"
        >
          按日期采集
        </el-button>
      </template>

      <template v-else-if="f.kind === 'concurrency-radio'">
        <span class="filter-divider" />
        <span class="filter-label">并发度</span>
        <el-radio-group :model-value="state.concurrency" size="small" @update:model-value="update('concurrency', $event)">
          <el-radio-button :value="1">1</el-radio-button>
          <el-radio-button :value="2">2</el-radio-button>
          <el-radio-button :value="3">3</el-radio-button>
          <el-radio-button :value="5">5</el-radio-button>
          <el-radio-button :value="8">8</el-radio-button>
        </el-radio-group>
      </template>

      <template v-else-if="f.kind === 'switch'">
        <span class="filter-divider" />
        <span class="filter-label">{{ f.label }}</span>
        <el-switch
          :model-value="state[f.key]"
          size="small"
          inline-prompt
          active-text="是"
          inactive-text="否"
          @update:model-value="update(f.key, $event)"
        />
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// ── 类型定义 ────────────────────────────────────────────
type FieldKind =
  | 'exchange-multiselect'
  | 'kline-daterange'
  | 'concurrency-radio'
  | 'switch'

interface FieldDef {
  key: string
  kind: FieldKind
  label?: string
}

interface FilterSchema {
  task_type: string
  fields: FieldDef[]
}

const props = defineProps<{
  taskType: string
  /** 父组件持有的 state，子组件仅修改后回传 */
  state: Record<string, any>
}>()

const emit = defineEmits<{
  (e: 'update:state', state: Record<string, any>): void
  (e: 'startWithDates', params: { start_date: string; end_date: string }): void
}>()

// ── Schema 定义 ─────────────────────────────────────────
const SCHEMAS: FilterSchema[] = [
  {
    task_type: 'daily_kline',
    fields: [
      { key: 'exchange', kind: 'exchange-multiselect' },
      { key: 'daterange', kind: 'kline-daterange' },
      { key: 'concurrency', kind: 'concurrency-radio' },
    ],
  },
]

const fields = computed<FieldDef[]>(
  () => SCHEMAS.find((s) => s.task_type === props.taskType)?.fields || [],
)

/** 单值更新：emits 整个新 state */
function update(key: string, value: any) {
  emit('update:state', { ...props.state, [key]: value })
}
</script>

<style scoped>
.advanced-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.filter-divider {
  width: 1px;
  height: 20px;
  background: #e2e8f0;
  flex-shrink: 0;
}

.filter-label {
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
