<!--
  CollectHistory.vue — 采集历史（全部接口的采集任务记录）

  结构（参考 page-development-guide.md §7 / §8 / §9）：
    - toolbar-row：主筛选（采集接口）+ 高级筛选开关 + 重置 / 刷新
    - advanced-wrapper：采集时间 / 采集结果 / 触发来源（grid-rows 折叠）
    - 表格：占满剩余高度，内部滚动
    - 分页：固定在底部
-->
<template>
  <div class="collect-history">
    <div class="toolbar-row">
      <div class="toolbar-search">
        <el-select
          v-model="filters.task_type"
          placeholder="全部采集接口"
          clearable
          filterable
          style="width: 220px"
          @change="onFilterChange"
        >
          <el-option-group v-for="g in taskGroups" :key="g.label" :label="g.label">
            <el-option v-for="t in g.items" :key="t.task_type" :label="t.label" :value="t.task_type">
              <span class="opt-label">{{ t.label }}</span>
              <span class="opt-type">{{ t.task_type }}</span>
            </el-option>
          </el-option-group>
        </el-select>
        <el-button
          :type="showAdvanced ? 'primary' : 'default'"
          :text="!showAdvanced"
          @click="showAdvanced = !showAdvanced"
        >
          <el-icon class="mr-1"><ArrowDown v-if="!showAdvanced" /><ArrowUp v-else /></el-icon>
          高级筛选
          <el-badge v-if="advancedFilterCount > 0 && !showAdvanced" :value="advancedFilterCount" class="ml-1" />
        </el-button>
        <el-button v-if="hasActiveFilters" type="danger" link @click="resetFilters">重置</el-button>
      </div>

      <div class="toolbar-actions">
        <el-button :loading="loading" @click="load">
          <el-icon class="mr-1"><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div class="advanced-wrapper" :class="{ open: showAdvanced }">
      <div class="advanced-filters">
        <el-date-picker
          v-model="filters.daterange"
          type="daterange"
          start-placeholder="采集开始日期"
          end-placeholder="采集结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          :shortcuts="dateShortcuts"
          style="width: 260px"
          @change="onFilterChange"
        />
        <el-select v-model="filters.status" placeholder="采集结果" clearable style="width: 130px" @change="onFilterChange">
          <el-option v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-select v-model="filters.trigger_type" placeholder="触发来源" clearable style="width: 130px" @change="onFilterChange">
          <el-option label="手动" value="manual" />
          <el-option label="定时" value="schedule" />
        </el-select>
      </div>
    </div>

    <div class="history-table">
      <el-table
        v-loading="loading"
        :data="tasks"
        height="100%"
        stripe
        size="small"
        row-key="id"
        empty-text="暂无采集记录"
      >
        <el-table-column label="ID" width="70">
          <template #default="{ row }">
            <span class="mono text-sm text-gray-500">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="采集接口" min-width="170">
          <template #default="{ row }">
            <div class="iface">
              <span class="iface__label">{{ taskLabel(row.task_type) }}</span>
              <span class="iface__type">{{ row.task_type }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag :type="statusColor(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" :type="row.trigger_type === 'schedule' ? 'warning' : 'info'">
              {{ row.trigger_type === 'schedule' ? '定时' : '手动' }}
            </el-tag>
            <el-tooltip v-if="row.plan_run_id" :content="`采集方案执行 #${row.plan_run_id}`" placement="top">
              <el-tag size="small" effect="plain" type="success" class="ml-1">方案</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="参数" min-width="160">
          <template #default="{ row }">
            <span class="text-sm text-gray-600">{{ formatParams(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="成功" width="70" align="right">
          <template #default="{ row }">
            <span class="mono text-sm text-green-600">{{ row.success_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="失败" width="70" align="right">
          <template #default="{ row }">
            <span class="mono text-sm text-red-500">{{ row.fail_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="跳过" width="70" align="right">
          <template #default="{ row }">
            <span class="mono text-sm text-gray-500">{{ row.skip_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="总数" width="70" align="right">
          <template #default="{ row }">
            <span class="mono text-sm">{{ row.total_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="80" align="right">
          <template #default="{ row }">
            <span class="mono text-sm">{{ formatDuration(row.duration_ms) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="150">
          <template #default="{ row }">
            <span class="mono text-sm">{{ formatTime(row.started_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="结束时间" width="150">
          <template #default="{ row }">
            <span class="mono text-sm">{{ formatTime(row.finished_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日志" min-width="220">
          <template #default="{ row }">
            <el-tooltip v-if="row.message" :content="row.message" placement="top" :show-after="300">
              <span class="text-sm log-text" :class="{ 'text-red-500': row.status === 'failed' }">{{ row.message }}</span>
            </el-tooltip>
            <span v-else class="text-sm text-gray-300">-</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="bottom-area-inner">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        size="small"
        background
        @current-change="load"
        @size-change="onFilterChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowDown, ArrowUp, Refresh } from '@element-plus/icons-vue'

import { listTasks, type CollectTask, type FacetGroup, type TaskDef } from '../api'
import {
  STATUS_OPTIONS, formatDuration, formatParams, formatTime, statusColor, statusLabel,
} from '../composables/taskFormat'

const props = defineProps<{
  catalog: FacetGroup[]
}>()

/** 接口下拉：按 facet 分组，只列批量接口（实时接口不产生采集任务） */
const taskGroups = computed(() =>
  props.catalog
    .map((f) => ({
      label: f.label,
      items: Object.values(f.sub_groups).flat().filter((t) => t.kind !== 'realtime'),
    }))
    .filter((g) => g.items.length > 0),
)

const taskDefMap = computed(() => {
  const m = new Map<string, TaskDef>()
  for (const g of taskGroups.value) for (const t of g.items) m.set(t.task_type, t)
  return m
})

function taskLabel(taskType: string): string {
  return taskDefMap.value.get(taskType)?.label || taskType
}

// ── 筛选 ──────────────────────────────────────────────────
const showAdvanced = ref(false)

function emptyFilters() {
  return {
    task_type: '',
    daterange: null as [string, string] | null,
    status: '',
    trigger_type: '',
  }
}

const filters = ref(emptyFilters())

const advancedFilterCount = computed(() => {
  let n = 0
  if (filters.value.daterange) n++
  if (filters.value.status) n++
  if (filters.value.trigger_type) n++
  return n
})

const hasActiveFilters = computed(() => !!filters.value.task_type || advancedFilterCount.value > 0)

const dateShortcuts = [
  { text: '今天', value: () => { const d = new Date(); return [d, d] } },
  { text: '近 7 天', value: () => { const e = new Date(); return [new Date(e.getTime() - 6 * 864e5), e] } },
  { text: '近 30 天', value: () => { const e = new Date(); return [new Date(e.getTime() - 29 * 864e5), e] } },
]

function onFilterChange() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.value = emptyFilters()
  onFilterChange()
}

// ── 列表 ──────────────────────────────────────────────────
const tasks = ref<CollectTask[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const f = filters.value
    const data = await listTasks({
      task_type: f.task_type || undefined,
      status: f.status || undefined,
      trigger_type: f.trigger_type || undefined,
      started_from: f.daterange?.[0],
      started_to: f.daterange?.[1],
      page: page.value,
      page_size: pageSize.value,
    })
    tasks.value = data.items || []
    total.value = data.total || 0
  } catch {
    tasks.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
/*
  顶部 token 与 StockInfoList 的 --sil-top-* 同一基准值（page-development-guide.md §7.6）。
  本 Tab 无密度面板，density 固定为 1。
*/
.collect-history {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ch-top-gap);

  --ch-top-density: 1;
  --ch-top-gap:        calc(0.6rem  * var(--ch-top-density));
  --ch-top-button-h:   calc(2rem    * var(--ch-top-density));
  --ch-top-button-fs:  calc(0.95rem * var(--ch-top-density));
  --ch-top-button-px:  calc(0.75rem * var(--ch-top-density));
  --ch-top-icon-fs:    calc(0.95rem * var(--ch-top-density));
  --ch-top-icon-mr:    calc(0.25rem * var(--ch-top-density));
  --ch-top-filter-py:  calc(0.55rem * var(--ch-top-density));
  --ch-top-filter-px:  calc(0.85rem * var(--ch-top-density));
  --ch-top-control-h:  calc(2rem    * var(--ch-top-density));
  --ch-top-control-fs: calc(0.95rem * var(--ch-top-density));
}

/* ── Top：toolbar-row 三件套 ── */
.toolbar-row {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ch-top-gap);
}

.toolbar-search {
  display: flex;
  align-items: center;
  gap: var(--ch-top-gap);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--ch-top-gap);
  flex-shrink: 0;
}

/* 按钮：EP 的 height / font-size 是 sass 固化，必须 :deep 直接覆盖 */
.toolbar-row :deep(.el-button) {
  --el-button-size: var(--ch-top-button-h);
  height: var(--ch-top-button-h);
  padding-left: var(--ch-top-button-px);
  padding-right: var(--ch-top-button-px);
  font-size: var(--ch-top-button-fs);
  line-height: 1;
}

.toolbar-row :deep(.el-button span) {
  font-size: var(--ch-top-button-fs);
}

.toolbar-row :deep(.el-button .el-icon) {
  font-size: var(--ch-top-icon-fs);
  margin-right: var(--ch-top-icon-mr);
}

/* ── 高级筛选：grid-rows 折叠 ── */
.advanced-wrapper {
  flex-shrink: 0;
  display: grid;
  grid-template-rows: 0fr;
  margin-top: calc(-1 * var(--ch-top-gap));
  transition: grid-template-rows 0.25s cubic-bezier(0.4, 0, 0.2, 1),
              margin-top 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.advanced-wrapper.open {
  grid-template-rows: 1fr;
  margin-top: 0;
}

.advanced-wrapper > .advanced-filters {
  overflow: hidden;
  min-height: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ch-top-gap);
  padding: 0 var(--ch-top-filter-px);
  background: var(--color-admin-bg, #f8fafc);
  border-radius: 8px;
  transition: padding 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.advanced-wrapper.open > .advanced-filters {
  padding: var(--ch-top-filter-py) var(--ch-top-filter-px);
}

/* 输入类控件（主筛选 select + 高级筛选 select / 日期范围）：高度 / 字号统一 */
.toolbar-search :deep(.el-select),
.advanced-filters :deep(.el-select),
.advanced-filters :deep(.el-date-editor) {
  --el-input-height: var(--ch-top-control-h);
  --el-component-size: var(--ch-top-control-h);
  --el-input-font-size: var(--ch-top-control-fs);
  --el-select-font-size: var(--ch-top-control-fs);
  font-size: var(--ch-top-control-fs);
}

.toolbar-search :deep(.el-select__wrapper),
.advanced-filters :deep(.el-select__wrapper),
.advanced-filters :deep(.el-date-editor.el-input__wrapper) {
  height: var(--ch-top-control-h);
  min-height: var(--ch-top-control-h);
  padding: 4px 11px;
  line-height: calc(var(--ch-top-control-h) - 8px);
  box-sizing: border-box;
  font-size: var(--ch-top-control-fs);
}

.toolbar-search :deep(.el-select__placeholder),
.advanced-filters :deep(.el-select__placeholder),
.advanced-filters :deep(.el-range-input),
.advanced-filters :deep(.el-range-separator) {
  font-size: var(--ch-top-control-fs);
}

/* ── Middle：表格占满剩余高度，内部滚动 ── */
.history-table {
  flex: 1;
  min-height: 0;
  min-width: 0;
}

.iface {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.iface__label {
  font-size: 13px;
  color: #1e293b;
}

.iface__type,
.opt-type {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  color: #94a3b8;
}

.opt-label {
  margin-right: 8px;
}

.log-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

/* ── Bottom：分页靠右 ── */
.bottom-area-inner {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}
</style>
