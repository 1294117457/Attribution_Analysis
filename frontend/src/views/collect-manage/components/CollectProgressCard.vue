<!--
  CollectProgressCard.vue — 采集进度卡片（v2 采集日志进度优化）

  实时显示采集进度：
    - 进度条（0-100%）
    - 状态标签（pending/running/success/partial_fail/failed）
    - 保存/失败数量
    - 开始时间、耗时
-->
<template>
  <div class="progress-card" :class="`progress-card--${log.status}`">
    <div class="progress-card__header">
      <div class="progress-card__title">
        <el-icon class="mr-1" :color="statusColor">
          <component :is="statusIcon" />
        </el-icon>
        <span>采集进度</span>
        <el-tag :type="statusTagType" size="small" class="ml-2">
          {{ statusLabel }}
        </el-tag>
      </div>
      <el-button
        v-if="log.status === 'pending' || log.status === 'running'"
        type="danger"
        size="small"
        text
        @click="$emit('stop')"
      >
        停止
      </el-button>
    </div>

    <div class="progress-card__body">
      <!-- 进度条 -->
      <div class="progress-card__bar">
        <el-progress
          :percentage="log.progress"
          :status="progressStatus"
          :stroke-width="10"
          :show-text="true"
        />
      </div>

      <!-- 统计 -->
      <div class="progress-card__stats">
        <div class="stat">
          <span class="stat__label">总进度</span>
          <span class="stat__value">{{ log.progress }}%</span>
        </div>
        <div class="stat">
          <span class="stat__label">已保存</span>
          <span class="stat__value text-green-600">{{ log.saved_count.toLocaleString() }}</span>
        </div>
        <div class="stat">
          <span class="stat__label">失败</span>
          <span class="stat__value text-red-500">{{ log.fail_count.toLocaleString() }}</span>
        </div>
        <div class="stat">
          <span class="stat__label">预估总数</span>
          <span class="stat__value">{{ log.total_count.toLocaleString() }}</span>
        </div>
      </div>

      <!-- 时间信息 -->
      <div class="progress-card__time">
        <span v-if="log.started_at">
          开始: {{ formatTime(log.started_at) }}
        </span>
        <span v-if="duration">
          &nbsp;|&nbsp; 耗时: {{ duration }}
        </span>
      </div>

      <!-- 错误信息 -->
      <div v-if="log.error_message" class="progress-card__error">
        <el-icon class="mr-1"><Warning /></el-icon>
        {{ log.error_message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, CircleClose, Loading, Clock, Warning } from '@element-plus/icons-vue'
import type { CollectLog } from '../api'

const props = defineProps<{
  log: CollectLog
}>()

defineEmits<{
  stop: []
}>()

/** 状态标签 */
const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '采集中',
    success: '成功',
    partial_fail: '部分失败',
    failed: '失败',
    skipped: '跳过',
  }
  return map[props.log.status] || props.log.status
})

/** 状态颜色 */
const statusColor = computed(() => {
  const map: Record<string, string> = {
    pending: '#94a3b8',
    running: '#3b82f6',
    success: '#22c55e',
    partial_fail: '#f59e0b',
    failed: '#ef4444',
    skipped: '#94a3b8',
  }
  return map[props.log.status] || '#94a3b8'
})

/** Element Plus tag 类型 */
const statusTagType = computed(() => {
  const map: Record<string, any> = {
    pending: 'info',
    running: 'primary',
    success: 'success',
    partial_fail: 'warning',
    failed: 'danger',
    skipped: 'info',
  }
  return map[props.log.status] || 'info'
})

/** 进度条状态 */
const progressStatus = computed(() => {
  if (props.log.status === 'success') return 'success'
  if (props.log.status === 'failed') return 'exception'
  if (props.log.status === 'partial_fail') return 'warning'
  return undefined
})

/** 状态图标 */
const statusIcon = computed(() => {
  if (props.log.status === 'running') return Loading
  if (props.log.status === 'success') return CircleCheck
  if (props.log.status === 'failed' || props.log.status === 'partial_fail') return CircleClose
  return Clock
})

/** 计算耗时 */
const duration = computed(() => {
  if (!props.log.started_at) return null
  const start = new Date(props.log.started_at).getTime()
  const end = props.log.finished_at
    ? new Date(props.log.finished_at).getTime()
    : Date.now()
  const diff = Math.floor((end - start) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`
})

/** 格式化时间 */
function formatTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<style scoped>
.progress-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  flex-shrink: 0;
}

.progress-card--running {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.progress-card--success {
  border-color: #22c55e;
}

.progress-card--failed {
  border-color: #ef4444;
}

.progress-card--partial_fail {
  border-color: #f59e0b;
}

.progress-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-card__title {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.progress-card__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.progress-card__bar {
  padding: 0 4px;
}

.progress-card__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat__label {
  font-size: 11px;
  color: #64748b;
}

.stat__value {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.progress-card__time {
  font-size: 12px;
  color: #64748b;
}

.progress-card__error {
  font-size: 12px;
  color: #ef4444;
  background: #fef2f2;
  padding: 8px 10px;
  border-radius: 4px;
  border-left: 3px solid #ef4444;
  word-break: break-all;
}

.ml-1 {
  margin-left: 4px;
}

.ml-2 {
  margin-left: 8px;
}

.text-green-600 {
  color: #16a34a;
}

.text-red-500 {
  color: #ef4444;
}
</style>
