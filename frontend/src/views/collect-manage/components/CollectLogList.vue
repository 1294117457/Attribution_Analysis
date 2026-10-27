<!--
  CollectLogList.vue — 采集历史日志列表（v2 采集日志进度优化）

  展示历史采集记录：
    - 开始时间、状态、进度、保存/失败数
    - 点击可查看详情
-->
<template>
  <div class="log-list">
    <div class="log-list__header">
      <span class="log-list__title">采集历史</span>
      <span class="log-list__count">{{ logs.length }} 条记录</span>
    </div>

    <div v-if="logs.length === 0" class="log-list__empty">
      暂无采集记录
    </div>

    <div v-else class="log-list__items">
      <div
        v-for="log in logs"
        :key="log.id"
        class="log-item"
        :class="{
          'log-item--active': log.id === activeLogId,
          'log-item--running': log.status === 'running' || log.status === 'init',
        }"
        @click="$emit('select', log)"
      >
        <div class="log-item__main">
          <div class="log-item__left">
            <el-icon class="log-item__icon" :color="getStatusColor(log.status)">
              <component :is="getStatusIcon(log.status)" />
            </el-icon>
            <div class="log-item__info">
              <div class="log-item__time">{{ formatTime(log.started_at) }}</div>
              <div class="log-item__params">{{ formatLogParams(log.meta) }}</div>
            </div>
          </div>
          <div class="log-item__right">
            <el-tag :type="getStatusTagType(log.status)" size="small">
              {{ getStatusLabel(log.status) }}
            </el-tag>
          </div>
        </div>

        <div class="log-item__stats">
          <span class="log-item__stat">
            <el-progress
              :percentage="log.progress"
              :status="getProgressStatus(log.status)"
              :stroke-width="4"
              :show-text="false"
              style="width: 80px"
            />
            {{ log.progress }}%
          </span>
          <span class="log-item__stat log-item__stat--success">
            <el-icon><CircleCheck /></el-icon>
            {{ log.saved_count.toLocaleString() }}
          </span>
          <span class="log-item__stat log-item__stat--fail" v-if="log.fail_count > 0">
            <el-icon><CircleClose /></el-icon>
            {{ log.fail_count.toLocaleString() }}
          </span>
        </div>

        <div v-if="log.error_message" class="log-item__error">
          {{ log.error_message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CircleCheck, CircleClose, Loading, Clock, Warning } from '@element-plus/icons-vue'
import type { CollectLog } from '../api'

defineProps<{
  logs: CollectLog[]
  activeLogId: string | null
}>()

defineEmits<{
  select: [log: CollectLog]
}>()

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    init: '已创建',
    running: '采集中',
    success: '成功',
    partial_fail: '部分失败',
    failed: '失败',
    skipped: '跳过',
  }
  return map[status] || status
}

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    init: '#94a3b8',
    running: '#3b82f6',
    success: '#22c55e',
    partial_fail: '#f59e0b',
    failed: '#ef4444',
    skipped: '#94a3b8',
  }
  return map[status] || '#94a3b8'
}

function getStatusTagType(status: string): any {
  const map: Record<string, any> = {
    init: 'info',
    running: 'primary',
    success: 'success',
    partial_fail: 'warning',
    failed: 'danger',
    skipped: 'info',
  }
  return map[status] || 'info'
}

function getProgressStatus(status: string): string | undefined {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'partial_fail') return 'warning'
  return undefined
}

function getStatusIcon(status: string) {
  if (status === 'running') return Loading
  if (status === 'success') return CircleCheck
  if (status === 'failed' || status === 'partial_fail') return CircleClose
  return Clock
}

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** 日志参数展示：daily 的 start_date/end_date/ts_code 更可读 */
const PARAM_LABELS: Record<string, string> = {
  start_date: '起',
  end_date: '止',
  ts_code: '代码',
}

function formatLogParams(params: Record<string, any> | null): string {
  if (!params) return ''
  const entries = Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== '')
  if (entries.length === 0) return '全量采集'
  const parts = entries.map(([k, v]) => {
    const label = PARAM_LABELS[k] || k
    if (Array.isArray(v)) return `${label} ${v.length}个`
    return `${label} ${v}`
  })
  return parts.join(' · ')
}
</script>

<style scoped>
.log-list {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  flex-shrink: 0;
}

.log-list__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.log-list__title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.log-list__count {
  font-size: 12px;
  color: #64748b;
}

.log-list__empty {
  text-align: center;
  padding: 24px;
  color: #94a3b8;
  font-size: 13px;
}

.log-list__items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.log-item {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.log-item:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.log-item--active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.log-item--running {
  border-left: 3px solid #3b82f6;
}

.log-item__main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-item__left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-item__icon {
  font-size: 16px;
}

.log-item__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.log-item__time {
  font-size: 12px;
  color: #475569;
  font-weight: 500;
}

.log-item__params {
  font-size: 11px;
  color: #94a3b8;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-item__stats {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 6px;
}

.log-item__stat {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #475569;
}

.log-item__stat--success {
  color: #16a34a;
}

.log-item__stat--fail {
  color: #ef4444;
}

.log-item__error {
  margin-top: 4px;
  font-size: 11px;
  color: #ef4444;
  background: #fef2f2;
  padding: 4px 8px;
  border-radius: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
