<template>
  <PageWrapper>
    <template #title>
      <el-icon class="mr-1"><Upload /></el-icon>
      采集管理
      <nav class="title-tabs">
        <button
          v-for="tab in tabDefs"
          :key="tab.value"
          class="title-tab"
          :class="{ active: activeTab === tab.value }"
          @click="switchTab(tab.value)"
        >{{ tab.label }}</button>
      </nav>
    </template>

    <template #toolbar>
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
            <el-badge v-if="filterCount > 0 && !showFilters" :value="filterCount" class="ml-1" />
          </el-button>
        </div>

        <div class="toolbar-actions">
          <template v-if="activeTab === 'daily_kline'">
            <el-button size="small" @click="startKline({ days: 1 })">今日</el-button>
            <el-button size="small" @click="startKline({ days: 7 })">7天</el-button>
            <el-button size="small" @click="startKline({ days: 30 })">30天</el-button>
          </template>
          <template v-else-if="activeTab === 'daily_basic'">
            <el-button size="small" @click="startTask('daily_basic', { days: 1 })">同步今日</el-button>
            <el-button size="small" @click="startTask('daily_basic', { days: 3 })">近3天</el-button>
            <el-button size="small" @click="startTask('daily_basic', { days: 7 })">近7天</el-button>
          </template>
          <template v-else-if="activeTab === 'concept'">
            <el-button type="primary" size="small" @click="startConcept()">
              <el-icon class="mr-1"><Refresh /></el-icon>
              全量同步概念
            </el-button>
            <el-button size="small" :disabled="!hasConceptHistory" @click="gotoStockInfo">
              <el-icon class="mr-1"><View /></el-icon>
              查看概念归属
            </el-button>
          </template>
          <template v-else>
            <el-button size="small" @click="startTask('stock_basic')">全量同步</el-button>
          </template>
        </div>
      </div>

      <!-- 可折叠筛选区 -->
      <div class="advanced-wrapper" :class="{ open: showFilters }">
        <div class="advanced-filters">
          <template v-if="activeTab === 'daily_kline'">
            <el-select
              v-model="klineExchange"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="全部交易所"
              clearable
              size="small"
              style="width: 190px"
            >
              <el-option label="上交所 (SSE)" value="SSE" />
              <el-option label="深交所 (SZSE)" value="SZSE" />
              <el-option label="北交所 (BSE)" value="BSE" />
            </el-select>
            <el-date-picker
              v-model="klineDateRange"
              type="daterange"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYYMMDD"
              size="small"
              style="width: 240px"
            />
            <el-button
              type="primary"
              size="small"
              :disabled="!klineDateRange || klineDateRange.length < 2"
              @click="startKline({ start_date: klineDateRange![0], end_date: klineDateRange![1] })"
            >
              按日期采集
            </el-button>
            <span class="filter-divider" />
            <span class="filter-label">并发度</span>
            <el-radio-group v-model="klineConcurrency" size="small">
              <el-radio-button :value="1">1</el-radio-button>
              <el-radio-button :value="2">2</el-radio-button>
              <el-radio-button :value="3">3</el-radio-button>
              <el-radio-button :value="5">5</el-radio-button>
              <el-radio-button :value="8">8</el-radio-button>
            </el-radio-group>
          </template>
          <template v-else-if="activeTab === 'concept'">
            <span class="filter-label">数据源</span>
            <el-select v-model="conceptSource" size="small" style="width: 160px">
              <el-option
                v-for="opt in CONCEPT_SOURCE_OPTIONS"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <span class="filter-divider" />
            <span class="filter-label">强制重传</span>
            <el-switch
              v-model="conceptForceResync"
              size="small"
              inline-prompt
              active-text="是"
              inactive-text="否"
            />
            <span class="text-xs text-gray-400 ml-1">
              （当前采集器对所有概念均 upsert，强制开关仅作为审计记录）
            </span>
          </template>
          <template v-else>
            <span class="text-sm text-gray-400">暂无额外筛选条件</span>
          </template>
        </div>
      </div>
    </template>

    <!-- ═══ Middle Area: 任务列表 ═══ -->
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
      @expand-change="onExpandChange"
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
              <span class="mono text-xs">
                已完成 <b>{{ progressMap[row.id].done }}</b> / {{ progressMap[row.id].total }}
              </span>
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
            >
              取消
            </el-button>
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

    <!-- ═══ Bottom Area ═══ -->
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
          @current-change="loadTasks"
          @size-change="onTaskPageSizeChange"
        />
      </el-row>
    </template>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, ArrowDown, ArrowUp, Refresh, View } from '@element-plus/icons-vue'

import PageWrapper from '@/components/PageWrapper.vue'
import {
  createTask,
  listTasks,
  getTaskProgress,
  cancelTask,
  type CollectTask,
  type TaskProgress,
  CONCEPT_SOURCE_OPTIONS,
} from './api'

const LOG_PREFIX = '[CollectManage]'

// ── Tab 定义 ──
const tabDefs = [
  { value: 'daily_kline', label: '日K线' },
  { value: 'daily_basic', label: '日频估值' },
  { value: 'stock_basic', label: '股票信息' },
  { value: 'concept', label: '概念同步' },
] as const

const activeTab = ref<string>('daily_kline')

function switchTab(tab: string) {
  if (activeTab.value === tab) return
  activeTab.value = tab
  onTabChange()
}

// ── 可折叠筛选 ──
const showFilters = ref(false)

const filterCount = computed(() => {
  if (activeTab.value === 'daily_kline') {
    let n = 0
    if (klineExchange.value.length > 0) n++
    if (klineDateRange.value) n++
    if (klineConcurrency.value !== 3) n++
    return n
  }
  if (activeTab.value === 'concept') {
    return conceptForceResync.value ? 1 : 0
  }
  return 0
})

// ── 日K筛选 ──
const klineDateRange = ref<[string, string] | null>(null)
const klineExchange = ref<string[]>([])
const klineConcurrency = ref(3)

// ── 概念同步筛选 ──
const conceptSource = ref<'em' | 'ths'>('em')
const conceptForceResync = ref(false)

// ── 任务列表 ──
const tasks = ref<CollectTask[]>([])
const taskTotal = ref(0)
const taskPage = ref(1)
const taskPageSize = ref(20)
const tasksLoading = ref(false)

/** 是否存在概念同步历史（用于「查看概念归属」按钮置灰判断） */
const hasConceptHistory = computed(() => tasks.value.length > 0)

/** 路由跳转（按 symbol 不一定，跳到列表即可） */
const router = useRouter()
function gotoStockInfo() {
  router.push('/home/stock-info')
}

// ── 展开行 ──
const tableRef = ref()
const expandedRowKeys = ref<number[]>([])

function onExpandChange(row: CollectTask, expanded: CollectTask[]) {
  expandedRowKeys.value = expanded.map((r) => r.id)
}

// ── 实时进度 ──
const progressMap = reactive<Record<number, TaskProgress>>({})
const finishedIds = new Set<number>()
const watchingIds = new Set<number>()
let pollTimer: ReturnType<typeof setInterval> | null = null

// ── 数据加载 ──

async function loadTasks() {
  tasksLoading.value = true
  try {
    const data = await listTasks({
      task_type: activeTab.value,
      page: taskPage.value,
      page_size: taskPageSize.value,
    })
    tasks.value = data.items || []
    taskTotal.value = data.total || 0

    const statusSummary = tasks.value.map((t) => `${t.id}:${t.status}`).join(', ')
    console.log(LOG_PREFIX, 'loadTasks', activeTab.value,
      `${tasks.value.length} items, total=${taskTotal.value}`,
      `statuses=[${statusSummary}]`)

    const dbRunningIds = tasks.value
      .filter((t) => t.status === 'running' || t.status === 'pending')
      .map((t) => t.id)

    const allActiveIds = [...new Set([...dbRunningIds, ...watchingIds])]
      .filter((id) => !finishedIds.has(id))

    expandedRowKeys.value = allActiveIds

    if (allActiveIds.length > 0) {
      if (!pollTimer) {
        console.log(LOG_PREFIX, 'startPolling for', allActiveIds,
          '(db:', dbRunningIds, 'watching:', [...watchingIds], ')')
        startPolling()
      }
    } else {
      stopPolling()
    }
  } catch (err) {
    console.error(LOG_PREFIX, 'loadTasks error', err)
    tasks.value = []
    taskTotal.value = 0
  } finally {
    tasksLoading.value = false
  }
}

function onTabChange() {
  console.log(LOG_PREFIX, 'tab →', activeTab.value)
  stopPolling()
  finishedIds.clear()
  watchingIds.clear()
  taskPage.value = 1
  loadTasks()
}

function onTaskPageSizeChange(s: number) {
  taskPageSize.value = s
  taskPage.value = 1
  loadTasks()
}

// ── 任务操作 ──

async function startTask(taskType: string, params?: Record<string, any>) {
  console.log(LOG_PREFIX, 'startTask', taskType, params)
  try {
    const res = await createTask({ task_type: taskType, params })
    console.log(LOG_PREFIX, 'createTask response:', res)
    if (res.task_id) {
      ElMessage.success(res.message || '任务已创建')
      watchingIds.add(res.task_id)
      console.log(LOG_PREFIX, 'added to watchingIds:', res.task_id)
      if (!pollTimer) startPolling()
    } else {
      ElMessage.warning(res.message || '操作未完成')
    }
    if (taskType !== activeTab.value) {
      activeTab.value = taskType
    }
    await loadTasks()

    if (res.task_id && !tasks.value.some((t) => t.id === res.task_id)) {
      console.log(LOG_PREFIX, 'new task not in list yet, retry in 500ms')
      setTimeout(() => loadTasks(), 500)
    }
  } catch (e) {
    console.error(LOG_PREFIX, 'startTask error:', e)
    ElMessage.error('创建任务失败: ' + (e as Error).message)
  }
}

function startKline(base: Record<string, any>) {
  const params = { ...base }
  if (klineExchange.value.length > 0) {
    params.exchange = [...klineExchange.value]
  }
  params.concurrency = klineConcurrency.value
  console.log(LOG_PREFIX, 'startKline', params, 'dateRange=', klineDateRange.value)
  startTask('daily_kline', params)
}

/** 概念全量同步启动 */
async function startConcept() {
  const params: Record<string, any> = {
    source: conceptSource.value,
    force_resync: conceptForceResync.value,
  }
  console.log(LOG_PREFIX, 'startConcept', params)
  await startTask('concept', params)
}

async function handleCancel(row: CollectTask) {
  try {
    const action = await ElMessageBox({
      title: '取消任务',
      message: '选择取消方式：\n• 正常取消：等待当前股票处理完后停止\n• 强制取消：立即标记任务为已取消（用于任务卡死的情况）',
      showCancelButton: true,
      distinguishCancelAndClose: true,
      confirmButtonText: '正常取消',
      cancelButtonText: '强制取消',
      confirmButtonClass: 'el-button--warning',
      cancelButtonClass: 'el-button--danger',
      type: 'warning',
    })
    console.log(LOG_PREFIX, 'soft cancel task', row.id)
    const res = await cancelTask(row.id, false)
    ElMessage.info(res.message || '已发送取消信号')
    await loadTasks()
  } catch (action) {
    if (action === 'cancel') {
      console.log(LOG_PREFIX, 'force cancel task', row.id)
      const res = await cancelTask(row.id, true)
      ElMessage.warning(res.message || '任务已强制取消')
      finishedIds.add(row.id)
      watchingIds.delete(row.id)
      delete progressMap[row.id]
      await loadTasks()
    }
  }
}

// ── 进度轮询 ──

function startPolling() {
  stopPolling()
  pollOnce()
  pollTimer = setInterval(pollOnce, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollOnce() {
  const dbRunningIds = tasks.value
    .filter((t) => (t.status === 'running' || t.status === 'pending') && !finishedIds.has(t.id))
    .map((t) => t.id)

  const allIds = [...new Set([...dbRunningIds, ...watchingIds])]
    .filter((id) => !finishedIds.has(id))

  if (allIds.length === 0) {
    stopPolling()
    return
  }

  let anyFinished = false
  for (const taskId of allIds) {
    try {
      const p = await getTaskProgress(taskId)
      if (p.status === 'running' || p.status === 'pending') {
        progressMap[taskId] = p
      } else {
        finishedIds.add(taskId)
        watchingIds.delete(taskId)
        delete progressMap[taskId]
        anyFinished = true
        console.log(LOG_PREFIX, `task ${taskId} finished: ${p.status}`, p)
        if (p.status === 'success') {
          ElMessage.success(`采集完成: 成功 ${p.success}, 失败 ${p.fail}`)
        } else if (p.status === 'failed') {
          ElMessage.error('采集任务失败')
        } else if (p.status === 'cancelled') {
          ElMessage.info('任务已取消')
        }
      }
    } catch (err) {
      console.warn(LOG_PREFIX, `poll task ${taskId} error`, err)
    }
  }

  if (anyFinished) {
    await loadTasks()
  }
}

// ── 格式化工具 ──

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
  if (task.task_type === 'concept') {
    // 概念同步专用渲染
    const source = p.source === 'ths' ? '同花顺' : '东方财富'
    parts.push(source)
    if (p.force_resync) parts.push('强制重传')
    return parts.join(' · ') || '-'
  }
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

// ── 生命周期 ──

onMounted(() => {
  console.log(LOG_PREFIX, 'mounted')
  loadTasks()
})

onBeforeUnmount(() => {
  console.log(LOG_PREFIX, 'unmount, stopping poll')
  stopPolling()
})
</script>

<style scoped>
/* ── 标题栏 Tab ── */
.title-tabs {
  display: flex;
  align-items: stretch;
  gap: 0;
  margin-left: 20px;
  padding-left: 20px;
  border-left: 1.5px solid #e2e8f0;
  align-self: stretch;
}

.title-tab {
  position: relative;
  padding: 2px 14px 6px;
  font-size: 15px;
  font-weight: 500;
  color: #94a3b8;
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s ease;
  white-space: nowrap;
}

.title-tab::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 10px;
  right: 10px;
  height: 2px;
  border-radius: 1px;
  background: transparent;
  transition: background-color 0.2s ease, height 0.15s ease;
}

.title-tab:hover {
  color: #64748b;
}

.title-tab:hover::after {
  background: #cbd5e1;
}

.title-tab.active {
  color: #1e40af;
  font-weight: 700;
}

.title-tab.active::after {
  background: #3b82f6;
  height: 3px;
  bottom: -3px;
}

/* ── Toolbar ── */
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

/* ── 可折叠筛选区（grid-rows 动画） ── */
.advanced-wrapper {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.advanced-wrapper.open {
  grid-template-rows: 1fr;
}

.advanced-wrapper > .advanced-filters {
  overflow: hidden;
  min-height: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  background: var(--color-admin-bg, #f8fafc);
  border-radius: 8px;
  transition: padding 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.advanced-wrapper.open > .advanced-filters {
  padding: 12px 16px;
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

/* ── 展开行进度 ── */
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

/* ── 日志截断 ── */
.log-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

/* ── running 行高亮 ── */
:deep(.running-row) {
  background-color: #eff6ff !important;
}
:deep(.running-row:hover > td) {
  background-color: #dbeafe !important;
}

/* ── 隐藏展开列表头 ── */
:deep(.el-table__expand-column .cell) {
  padding: 0;
}

/* ── 状态列 ── */
.status-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}
.cancel-inline-btn {
  padding: 2px 4px !important;
  font-size: 12px !important;
}
</style>
