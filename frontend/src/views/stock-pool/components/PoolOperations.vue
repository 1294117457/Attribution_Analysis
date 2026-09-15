<template>
  <div v-loading="loading" class="operations-tab">
    <div class="flex items-center gap-3 mb-3">
      <h3 class="text-base font-semibold">操作历史</h3>
      <el-button size="small" @click="refresh">
        <el-icon class="mr-1"><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <div v-if="operations.length === 0" class="empty">
      <el-empty description="暂无操作记录" />
    </div>

    <div v-else class="space-y-3">
      <el-card
        v-for="op in operations"
        :key="op.id"
        shadow="never"
        class="operation-card"
        :class="`status-${op.status}`"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <el-tag :type="statusTag(op.status)" size="small">
              {{ statusLabel(op.status) }}
            </el-tag>
            <span class="font-medium">{{ operationLabel(op.operation_type) }}</span>
            <span class="text-xs text-gray-500">
              参数: {{ formatParams(op.params) }}
            </span>
          </div>
          <span class="text-xs text-gray-400">{{ formatDate(op.created_at) }}</span>
        </div>

        <!-- 进度条 -->
        <div v-if="op.progress.total > 0" class="mb-2">
          <div class="flex items-center justify-between text-xs mb-1">
            <span class="text-gray-500">
              进度 {{ op.progress.done }}/{{ op.progress.total }}
              · 失败 {{ op.progress.failed }}
            </span>
            <span class="text-gray-500">{{ progressPercent(op.progress) }}%</span>
          </div>
          <el-progress
            :percentage="progressPercent(op.progress)"
            :status="progressStatus(op.status)"
            :stroke-width="6"
          />
        </div>

        <!-- 结果摘要 -->
        <div v-if="op.result_summary" class="text-xs text-gray-500 mb-2">
          共 {{ op.result_summary.total }} · 保存 {{ op.result_summary.saved }}
          · 失败 {{ op.result_summary.failed }} · 耗时 {{ duration(op) }}
        </div>

        <div v-if="op.error_message" class="text-xs text-red-500">
          {{ op.error_message }}
        </div>

        <!-- 操作按钮 -->
        <div class="flex items-center gap-2 mt-2">
          <el-button
            v-if="op.status === 'running' || op.status === 'pending'"
            size="small"
            type="danger"
            @click="cancelOp(op.id)"
          >
            取消
          </el-button>
          <el-button size="small" link @click="viewDetails(op)">
            查看详情
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 操作详情弹窗 -->
    <el-drawer
      v-model="detailVisible"
      title="操作详情"
      size="500px"
      direction="rtl"
    >
      <div v-if="currentOp">
        <div class="mb-4">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="操作类型">
              {{ operationLabel(currentOp.operation_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTag(currentOp.status)" size="small">
                {{ statusLabel(currentOp.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(currentOp.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="开始时间">
              {{ formatDate(currentOp.started_at) || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="完成时间">
              {{ formatDate(currentOp.finished_at) || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="耗时">
              {{ duration(currentOp) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <h4 class="text-sm font-semibold mb-2">参数</h4>
        <pre class="params-block">{{ JSON.stringify(currentOp.params, null, 2) }}</pre>

        <h4 class="text-sm font-semibold mb-2 mt-4">结果明细</h4>
        <el-table
          v-if="currentOp.result_summary?.details?.length"
          :data="currentOp.result_summary.details"
          stripe
          max-height="400"
        >
          <el-table-column prop="symbol" label="代码" width="100" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="itemStatusTag(row.status)" size="small">
                {{ itemStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="count" label="保存条数" width="90" />
          <el-table-column prop="message" label="信息" />
        </el-table>
        <el-empty v-else description="无明细数据" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { usePoolStore } from '@/stores/pool'
import * as poolApi from '@/views/stock-pool/api'
import type { PoolOperation, OperationProgress } from '@/views/stock-pool/api'

const props = defineProps<{ poolId: number }>()
const store = usePoolStore()

const loading = ref(false)
const detailVisible = ref(false)
const currentOp = ref<PoolOperation | null>(null)

const operations = computed(() => store.operations)

async function refresh() {
  loading.value = true
  try {
    await store.fetchOperations(props.poolId)
  } finally {
    loading.value = false
  }
}

async function cancelOp(opId: number) {
  try {
    await store.cancelOperation(opId)
    ElMessage.success('操作已取消')
  } catch (e) {
    ElMessage.error('取消失败: ' + (e as Error).message)
  }
}

async function viewDetails(op: PoolOperation) {
  try {
    const fresh = await poolApi.getOperation(op.id)
    currentOp.value = fresh
    detailVisible.value = true
  } catch (e) {
    currentOp.value = op
    detailVisible.value = true
  }
}

// ── 轮询：有运行中的任务时持续刷新 ────────────────────────────────────
let pollTimer: ReturnType<typeof setInterval> | null = null
function ensurePolling() {
  const hasRunning = operations.value.some(
    (o) => o.status === 'running' || o.status === 'pending',
  )
  if (hasRunning && !pollTimer) {
    pollTimer = setInterval(async () => {
      try {
        for (const op of operations.value) {
          if (op.status === 'running' || op.status === 'pending') {
            const progress: OperationProgress = await poolApi.getOperationProgress(op.id)
            op.progress = progress
            if (progress.done === progress.total && progress.total > 0) {
              const fresh = await poolApi.getOperation(op.id)
              Object.assign(op, fresh)
            }
          }
        }
      } catch (_) {
        /* ignore */
      }
    }, 2000)
  } else if (!hasRunning && pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ── 显示辅助 ─────────────────────────────────────────────────────────
function statusTag(s: string) {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    partial: 'warning',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[s] || 'info'
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '进行中',
    success: '已完成',
    partial: '部分失败',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[s] || s
}

function operationLabel(t: string) {
  const map: Record<string, string> = {
    kline_collect: '采集 K 线',
    news_fetch: '获取新闻',
    factor_calc: '因子计算',
  }
  return map[t] || t
}

function progressPercent(p: OperationProgress) {
  if (p.total === 0) return 0
  return Math.round((p.done / p.total) * 100)
}

function progressStatus(s: string): '' | 'success' | 'warning' | 'exception' {
  if (s === 'success') return 'success'
  if (s === 'partial') return 'warning'
  if (s === 'failed') return 'exception'
  return ''
}

function itemStatusTag(s: string) {
  const map: Record<string, string> = {
    success: 'success',
    skipped: 'info',
    failed: 'danger',
  }
  return map[s] || 'info'
}

function itemStatusLabel(s: string) {
  const map: Record<string, string> = {
    success: '成功',
    skipped: '跳过',
    failed: '失败',
  }
  return map[s] || s
}

function formatParams(p: Record<string, unknown>) {
  if (!p || Object.keys(p).length === 0) return '—'
  return Object.entries(p)
    .map(([k, v]) => `${k}=${v ?? '—'}`)
    .join(', ')
}

function duration(op: PoolOperation) {
  if (!op.started_at || !op.finished_at) return '—'
  const start = new Date(op.started_at).getTime()
  const end = new Date(op.finished_at).getTime()
  const sec = Math.round((end - start) / 1000)
  if (sec < 60) return `${sec} 秒`
  return `${Math.floor(sec / 60)} 分 ${sec % 60} 秒`
}

function formatDate(v?: string | null) {
  if (!v) return ''
  const d = new Date(v)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString('zh-CN', { hour12: false })
}

// ── 生命周期 ─────────────────────────────────────────────────────────
onMounted(async () => {
  await refresh()
  ensurePolling()
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.operations-tab {
  height: 100%;
}

.operation-card {
  border-radius: 6px;
}

.operation-card.status-running {
  border-color: #e6a23c;
}
.operation-card.status-success {
  border-color: #67c23a;
}
.operation-card.status-failed {
  border-color: #f56c6c;
}

.params-block {
  background: #f8f9fb;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 12px;
  font-family: ui-monospace, monospace;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.empty {
  padding: 60px 0;
  text-align: center;
}
</style>
