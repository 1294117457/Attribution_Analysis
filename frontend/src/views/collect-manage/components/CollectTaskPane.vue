<!--
  CollectTaskPane.vue — 采集管理右侧主区

  - 实时类任务 → RealtimePanel
  - 批量类任务 → CollectActionCard（采集类型 / 条件 / 开始采集）+ 任务列表 + 分页
  - 采集卡片、分页固定，仅表格内部滚动
-->
<template>
  <main class="task-pane">
    <div v-if="!taskDef" class="tip">请从左侧选择采集任务</div>

    <RealtimePanel v-else-if="isRealtime" :task-def="taskDef" class="task-pane__scroll" />

    <template v-else>
      <CollectActionCard
        :task-type="taskType"
        :task-def="taskDef"
        :starting="startingTasks.has(taskType)"
        @start="startTask(taskType, $event)"
      />

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
import { computed } from 'vue'

import CollectActionCard from './CollectActionCard.vue'
import RealtimePanel from './RealtimePanel.vue'
import type { CollectTask, TaskDef } from '../api'
import { useCollectTasks } from '../composables/useCollectTasks'
import {
  formatDuration, formatParams, formatTime, statusColor, statusLabel,
} from '../composables/taskFormat'

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

function rowClassName({ row }: { row: CollectTask }) {
  return row.status === 'running' ? 'running-row' : ''
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
