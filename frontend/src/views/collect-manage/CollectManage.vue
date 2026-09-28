<!--
  CollectManage.vue — 采集管理（四面分类重构）

  结构：
    - 左：catalog 目录树（按 facet / sub_facet 二级聚合）
    - 右：当前选中 task 的工具栏 + 任务列表

  改造：
    - 删 tabDefs / onTabChange / 4 个 v-if 工具栏块
    - 拆 composables (useCatalog / useCollectTasks)
    - 抽 QuickStartBar / AdvancedFilters 组件
    - catalog 通过 GET /collect/catalog 拉取（左树 + 按钮组完全数据驱动）

  配套：docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §3.2
-->
<template>
  <PageWrapper>
    <template #title>
      <el-icon class="mr-1"><Upload /></el-icon>
      采集管理
    </template>

    <div class="layout-body">
      <!-- ═══ 左：目录树 ═══ -->
      <aside class="catalog-tree">
        <div v-if="catalogLoading" class="loading-tip">加载中...</div>
        <div v-else-if="catalog.length === 0" class="empty-tip">无采集任务</div>
        <div
          v-for="facet in catalog"
          :key="facet.facet"
          class="facet-block"
        >
          <div
            class="facet-header"
            role="button"
            :aria-expanded="!isCollapsed(facet.facet)"
            @click="toggleCollapsed(facet.facet)"
          >
            <el-icon class="collapse-arrow" :class="{ collapsed: isCollapsed(facet.facet) }"><ArrowDown /></el-icon>
            <el-icon class="mr-1"><TrendCharts v-if="facet.facet === 'tech'"
              /><Money v-else-if="facet.facet === 'capital'"
              /><PieChart v-else-if="facet.facet === 'fundamental'"
              /><Document v-else /></el-icon>
            <b>{{ facet.label }}</b>
            <el-badge
              v-if="countReady(facet) > 0"
              :value="countReady(facet)"
              type="success"
              class="ml-1"
            />
            <el-badge
              v-if="countPlanned(facet) > 0"
              :value="countPlanned(facet)"
              type="info"
              class="ml-1"
            />
          </div>
          <div v-show="!isCollapsed(facet.facet)" class="sub-facet-list">
            <div
              v-for="(tasks, subKey) in facet.sub_groups"
              :key="subKey"
              class="sub-facet-block"
            >
              <div
                class="sub-facet-label"
                role="button"
                :aria-expanded="!isCollapsed(`${facet.facet}/${subKey}`)"
                @click="toggleCollapsed(`${facet.facet}/${subKey}`)"
              >
                <el-icon class="collapse-arrow" :class="{ collapsed: isCollapsed(`${facet.facet}/${subKey}`) }"><ArrowDown /></el-icon>
                {{ SUB_FACET_LABELS[subKey] || subKey }}
                <span class="sub-facet-count">{{ tasks.length }}</span>
              </div>
              <button
                v-show="!isCollapsed(`${facet.facet}/${subKey}`)"
                v-for="t in tasks"
                :key="t.task_type"
                class="task-btn"
                :class="{ active: activeTaskType === t.task_type, planned: t.status === 'planned' }"
                @click="switchTask(t.task_type)"
              >
                <el-tooltip :content="t.description" placement="right" :show-after="300">
                  <span class="task-btn-inner">
                    <span class="task-btn-label">{{ t.label }}</span>
                    <el-tag v-if="t.status === 'planned'" size="small" type="info" class="ml-1">待实现</el-tag>
                  </span>
                </el-tooltip>
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- ═══ 右：当前 task 主区 ═══ -->
      <main class="main-pane">
        <div v-if="!currentTaskDef" class="empty-tip">请从左侧选择采集任务</div>

        <template v-else>
          <!-- 顶部：标题 + 启动按钮组 + 筛选 -->
          <header class="task-toolbar">
            <div class="task-header">
              <h3>
                {{ currentTaskDef.label }}
                <el-tag v-if="currentTaskDef.status === 'planned'" size="small" type="info" class="ml-1">待实现</el-tag>
              </h3>
              <p class="task-desc">{{ currentTaskDef.description }}</p>
            </div>

            <div class="toolbar-row">
              <div class="toolbar-search">
                <el-button
                  :type="showFilters ? 'primary' : 'default'"
                  :text="!showFilters"
                  size="small"
                  @click="showFilters = !showFilters"
                >
                  <el-icon class="mr-1"><ArrowDown v-if="!showFilters" /><ArrowUp v-else /></el-icon>
                  采集条件
                  <el-badge v-if="activeFilterCount > 0 && !showFilters" :value="activeFilterCount" class="ml-1" />
                </el-button>
              </div>

              <div class="toolbar-actions">
                <QuickStartBar
                  :task-type="activeTaskType"
                  :disabled="currentTaskDef.status !== 'ready' || startingTasks.has(activeTaskType)"
                  :loading="startingTasks.has(activeTaskType)"
                  @start="onQuickStart"
                />
              </div>
            </div>

            <AdvancedFilters
              :task-type="activeTaskType"
              :open="showFilters"
              :state="filterState"
              @update:state="filterState = $event"
              @startWithDates="onStartWithDates"
            />
          </header>

          <!-- 任务列表 -->
          <el-table
            ref="tableRef"
            :data="tasks"
            v-loading="tasksLoading"
            stripe
            size="small"
            row-key="id"
            :row-class-name="rowClassName"
            :expand-row-keys="expandedRowKeys"
            empty-text="暂无采集任务"
          >
            <el-table-column type="expand" width="1">
              <template #default="{ row }">
                <div v-if="progressMap[row.id]" class="expand-progress">
                  <el-progress
                    :percentage="progressMap[row.id].percent"
                    :stroke-width="14"
                    striped
                    striped-flow
                    class="expand-progress-bar"
                  />
                  <div class="expand-stats">
                    <span class="mono text-xs">已完成 <b>{{ progressMap[row.id].done }}</b> / {{ progressMap[row.id].total }}</span>
                    <span class="mono text-xs text-green-600">成功 {{ progressMap[row.id].success }}</span>
                    <span class="mono text-xs text-red-500">失败 {{ progressMap[row.id].fail }}</span>
                    <span v-if="row.params?.concurrency > 1" class="mono text-xs text-indigo-500">
                      并发 ×{{ row.params.concurrency }}
                    </span>
                    <span v-if="progressMap[row.id].current" class="mono text-xs text-gray-500">
                      当前: {{ progressMap[row.id].current }}
                    </span>
                    <el-button type="danger" text size="small" @click="handleCancel(row)">取消任务</el-button>
                  </div>
                </div>
                <div v-else class="expand-progress">
                  <span class="text-sm text-gray-400">等待进度数据...</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="状态" width="130">
              <template #default="{ row }">
                <div class="status-cell">
                  <el-tag :type="statusColor(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
                  <el-button
                    v-if="row.status === 'running' || row.status === 'pending'"
                    type="danger"
                    text
                    size="small"
                    class="cancel-inline-btn"
                    @click.stop="handleCancel(row)"
                  >取消</el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="参数" min-width="150">
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
            <el-table-column label="开始时间" width="145">
              <template #default="{ row }">
                <span class="mono text-sm">{{ formatTime(row.started_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="日志" min-width="200">
              <template #default="{ row }">
                <el-tooltip v-if="row.message" :content="row.message" placement="top" :show-after="300">
                  <span
                    class="text-sm log-text"
                    :class="{
                      'text-red-500': row.status === 'failed',
                      'text-orange-400': row.status === 'cancelled',
                      'text-gray-500': row.status === 'success',
                      'text-blue-500': row.status === 'running',
                    }"
                  >{{ row.message || (row.status === 'running' ? '采集中...' : '-') }}</span>
                </el-tooltip>
                <span v-else class="text-sm" :class="row.status === 'running' ? 'text-blue-500' : 'text-gray-300'">
                  {{ row.status === 'running' ? '采集中... (点击展开查看进度)' : '-' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </main>
    </div>

    <template #bottom>
      <el-row justify="end">
        <el-pagination
          v-model:current-page="taskPage"
          v-model:page-size="taskPageSize"
          :total="taskTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          size="small"
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </el-row>
    </template>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import {
  Upload, ArrowDown, ArrowUp,
  TrendCharts, Money, PieChart, Document,
} from '@element-plus/icons-vue'

import PageWrapper from '@/components/PageWrapper.vue'
import QuickStartBar from './QuickStartBar.vue'
import AdvancedFilters, { countActiveFilters } from './AdvancedFilters.vue'
import type { CollectTask } from './api'

import { useCatalog } from './composables/useCatalog'
import { useCollectTasks } from './composables/useCollectTasks'

const LOG_PREFIX = '[CollectManage]'

// ── Catalog（左树 + 元数据） ─────────────────────────────────
const {
  catalog,
  loading: catalogLoading,
  load: loadCatalog,
  getTaskDef,
  countReady,
  countPlanned,
  SUB_FACET_LABELS,
} = useCatalog()

// ── 左树折叠状态（key = facet 或 facet/subKey，持久化到 localStorage） ──
const COLLAPSE_STORAGE_KEY = 'collect-manage:collapsed'

function loadCollapsed(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(COLLAPSE_STORAGE_KEY) || '[]'))
  } catch {
    return new Set()
  }
}

const collapsed = ref<Set<string>>(loadCollapsed())

function isCollapsed(key: string): boolean {
  return collapsed.value.has(key)
}

function toggleCollapsed(key: string) {
  const next = new Set(collapsed.value)
  if (!next.delete(key)) next.add(key)
  collapsed.value = next
  localStorage.setItem(COLLAPSE_STORAGE_KEY, JSON.stringify([...next]))
}

// ── 当前选中 task_type ────────────────────────────────────────
const activeTaskType = ref<string>('daily_kline')
const currentTaskDef = computed(() => getTaskDef(activeTaskType.value))

function switchTask(taskType: string) {
  if (activeTaskType.value === taskType) return
  activeTaskType.value = taskType
  // useCollectTasks 通过 watch 自动重新加载
}

// ── 任务列表 / 进度轮询 / 操作 ──────────────────────────────
const {
  tasks,
  taskTotal,
  taskPage,
  taskPageSize,
  tasksLoading,
  expandedRowKeys,
  progressMap,
  startingTasks,
  startTask,
  handleCancel,
  onPageChange,
  onPageSizeChange,
} = useCollectTasks(() => activeTaskType.value)

// ── 筛选条件 ────────────────────────────────────────────────
const showFilters = ref(false)
const filterState = reactive<Record<string, any>>({
  exchange: [] as string[],
  daterange: null as [string, string] | null,
  concurrency: 3,
})

const activeFilterCount = computed(() =>
  countActiveFilters(activeTaskType.value, filterState),
)

// ── 启动逻辑 ────────────────────────────────────────────────
function onQuickStart(taskType: string, params: Record<string, any>) {
  // daily_kline 需要合并 exchange / concurrency
  if (taskType === 'daily_kline') {
    const merged: Record<string, any> = { ...params }
    if (Array.isArray(filterState.exchange) && filterState.exchange.length > 0) {
      merged.exchange = [...filterState.exchange]
    }
    merged.concurrency = filterState.concurrency
    startTask(taskType, merged)
    return
  }
  startTask(taskType, params)
}

function onStartWithDates(params: { start_date: string; end_date: string }) {
  const merged: Record<string, any> = {
    ...params,
    concurrency: filterState.concurrency,
  }
  if (Array.isArray(filterState.exchange) && filterState.exchange.length > 0) {
    merged.exchange = [...filterState.exchange]
  }
  startTask('daily_kline', merged)
}

// ── 格式化工具 ──────────────────────────────────────────────
function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending: '等待中', running: '采集中', success: '成功', failed: '失败', cancelled: '已取消',
  }
  return map[s] || s
}

function statusColor(s: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    pending: 'info', running: 'primary', success: 'success', failed: 'danger', cancelled: 'info',
  }
  return map[s] || 'info'
}

function rowClassName({ row }: { row: CollectTask }) {
  return row.status === 'running' ? 'running-row' : ''
}

function formatParams(task: CollectTask): string {
  if (!task.params) return '-'
  const p = task.params
  const parts: string[] = []
  if (Array.isArray(p.exchange) && p.exchange.length > 0) {
    parts.push(p.exchange.join('/'))
  }
  if (p.days != null) {
    parts.push(`回溯${p.days}天`)
  } else if (p.start_date && p.end_date) {
    const s = String(p.start_date).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
    const e = String(p.end_date).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
    parts.push(`${s} ~ ${e}`)
  }
  if (p.concurrency != null && p.concurrency > 1) {
    parts.push(`并发×${p.concurrency}`)
  }
  if (p.limit != null) {
    parts.push(`前${p.limit}`)
  }
  if (p.full) parts.push('全量重写')
  if (p.only_missing) parts.push('仅缺失理由')
  if (p.list_status) parts.push(`状态: ${p.list_status}`)
  return parts.length > 0 ? parts.join(' · ') : '-'
}

function formatDuration(ms: number | null): string {
  if (ms == null || ms <= 0) return '-'
  const totalSec = Math.floor(ms / 1000)
  if (totalSec < 60) return `${totalSec}s`
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  if (min < 60) return sec > 0 ? `${min}m${sec}s` : `${min}m`
  const hr = Math.floor(min / 60)
  const rm = min % 60
  return rm > 0 ? `${hr}h${rm}m` : `${hr}h`
}

function formatTime(v: string | null): string {
  if (!v) return '-'
  return v.replace('T', ' ').replace(/\.\d+$/, '').slice(0, 19)
}

// ── 生命周期 ────────────────────────────────────────────────
onMounted(async () => {
  console.log(LOG_PREFIX, 'mounted, loading catalog')
  await loadCatalog()
})

// ── 占位 router（旧按钮"查看概念归属"已不再用，保留 stub） ───
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function _unused_router_push() {
  // 历史逻辑：点击"查看概念归属"跳转 /home/stock-info
  // 重构后该入口由 stock-info 页自己承担，此处不暴露
}
</script>

<style scoped>
.layout-body {
  display: flex;
  gap: 16px;
  align-items: stretch;
  min-height: 480px;
}

/* ── 左树 ── */
.catalog-tree {
  width: 240px;
  flex-shrink: 0;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px 8px;
  overflow-y: auto;
  max-height: 80vh;
}

.facet-block + .facet-block {
  margin-top: 12px;
}

.facet-header {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #1e293b;
  padding: 4px 6px;
  border-left: 3px solid #3b82f6;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
}

.facet-header:hover {
  background: #eff6ff;
}

.collapse-arrow {
  flex-shrink: 0;
  font-size: 12px;
  color: #94a3b8;
  transition: transform 0.15s;
}

.collapse-arrow.collapsed {
  transform: rotate(-90deg);
}

.sub-facet-list {
  margin-top: 4px;
  padding-left: 12px;
}

.sub-facet-block + .sub-facet-block {
  margin-top: 6px;
}

.sub-facet-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #94a3b8;
  padding: 2px 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
}

.sub-facet-label:hover {
  color: #475569;
  background: #f1f5f9;
}

.sub-facet-count {
  margin-left: auto;
  font-size: 11px;
  color: #cbd5e1;
}

.task-btn {
  display: block;
  width: 100%;
  padding: 6px 10px;
  margin-top: 2px;
  font-size: 13px;
  color: #475569;
  background: transparent;
  border: none;
  border-radius: 4px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.task-btn:hover {
  background: #e2e8f0;
  color: #1e40af;
}

.task-btn.active {
  background: #3b82f6;
  color: #fff;
  font-weight: 600;
}

.task-btn.planned {
  color: #94a3b8;
  font-style: italic;
}

.task-btn-inner {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
}

.task-btn-label {
  flex: 1;
}

/* ── 右主区 ── */
.main-pane {
  flex: 1;
  min-width: 0;
}

.task-toolbar {
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
}

.task-header h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #1e293b;
}

.task-desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: #64748b;
}

.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-search {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ── 任务列表 ── */
.expand-progress {
  padding: 8px 16px;
}

.expand-progress-bar {
  margin-bottom: 8px;
}

.expand-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.log-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

/* ── 行高亮 ── */
:deep(.running-row) {
  background-color: #eff6ff !important;
}
:deep(.running-row:hover > td) {
  background-color: #dbeafe !important;
}

/* ── 展开列 ── */
:deep(.el-table__expand-column .cell) {
  padding: 0;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}
.cancel-inline-btn {
  padding: 2px 4px !important;
  font-size: 12px !important;
}

/* ── 通用提示 ── */
.loading-tip,
.empty-tip {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}
</style>