<!--
  CollectTaskPane.vue — 采集管理右侧主区

  - 实时类任务 → RealtimePanel
  - 批量类任务 → 工具栏（标题 / 采集条件 / 启动按钮组）+ 任务列表 + 分页
  - 工具栏、分页固定，仅表格内部滚动
-->
<template>
  <main class="task-pane">
    <div v-if="!taskDef" class="tip">请从左侧选择采集任务</div>

    <RealtimePanel v-else-if="isRealtime" :task-def="taskDef" class="task-pane__scroll" />

    <template v-else>
      <!-- 顶部：标题 + 描述（一行）/ 采集条件 + 启动按钮组 -->
      <header class="task-toolbar">
        <div class="task-header">
          <h3>{{ taskDef.label }}</h3>
          <el-tag v-if="taskDef.status === 'planned'" size="small" type="info">待实现</el-tag>
          <el-tooltip
            v-if="taskDef.description"
            :content="taskDef.description"
            placement="bottom-start"
            :show-after="300"
          >
            <span class="task-desc">{{ taskDef.description }}</span>
          </el-tooltip>
        </div>

        <div class="toolbar-row">
          <AdvancedFilters
            :task-type="taskType"
            :state="filterState"
            @update:state="Object.assign(filterState, $event)"
            @startWithDates="onStartWithDates"
          />
          <QuickStartBar
            class="toolbar-actions"
            :task-type="taskType"
            :disabled="taskDef.status !== 'ready' || startingTasks.has(taskType)"
            :loading="startingTasks.has(taskType)"
            @start="onQuickStart"
          />
        </div>
      </header>

      <!-- 任务列表（内部滚动） -->
      <div class="task-table-wrap">
        <el-table
          :data="tasks"
          v-loading="tasksLoading"
          height="100%"
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

          <el-table-column label="状态" width="160">
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
                <el-button
                  v-else-if="row.status === 'failed' || row.status === 'cancelled'"
                  type="primary"
                  text
                  size="small"
                  :loading="retryingIds.has(row.id)"
                  @click.stop="handleRetry(row)"
                >重跑</el-button>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="来源" width="96">
            <template #default="{ row }">
              <el-tag size="small" effect="plain" :type="row.trigger_type === 'schedule' ? 'warning' : 'info'">
                {{ row.trigger_type === 'schedule' ? '定时' : '手动' }}
              </el-tag>
              <el-tooltip v-if="row.plan_run_id" :content="`采集方案执行 #${row.plan_run_id}`" placement="top">
                <el-tag size="small" effect="plain" type="success" class="ml-1">方案</el-tag>
              </el-tooltip>
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
      </div>

      <div class="task-pagination">
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
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'

import QuickStartBar from './QuickStartBar.vue'
import AdvancedFilters from './AdvancedFilters.vue'
import RealtimePanel from './RealtimePanel.vue'
import type { CollectTask, TaskDef } from '../api'
import { useCollectTasks } from '../composables/useCollectTasks'

const props = defineProps<{
  taskType: string
  taskDef: TaskDef | null | undefined
}>()

const isRealtime = computed(() => props.taskDef?.kind === 'realtime')

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
  handleRetry,
  retryingIds,
  onPageChange,
  onPageSizeChange,
} = useCollectTasks(() => props.taskType)

// ── 筛选条件 ────────────────────────────────────────────────
const filterState = reactive<Record<string, any>>({
  exchange: [] as string[],
  daterange: null as [string, string] | null,
  concurrency: 3,
})

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
  if (p.only_missing) parts.push('仅缺失')
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
</script>

<style scoped>
.task-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.task-pane__scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.task-toolbar {
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
}

.task-header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin-bottom: 10px;
}

.task-header h3 {
  flex-shrink: 0;
  margin: 0;
  font-size: 16px;
  color: #1e293b;
}

.task-desc {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #64748b;
}

.toolbar-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.toolbar-actions {
  margin-left: auto;
}

/* ── 任务列表 ── */
.task-table-wrap {
  flex: 1;
  min-height: 0;
}

.task-pagination {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

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

.tip {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}
</style>
