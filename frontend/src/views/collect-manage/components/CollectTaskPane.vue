<!--
  CollectTaskPane.vue — 采集管理右侧主区（全异步任务式）

  按 service 的 strategy 分发到三种形态：
    strategy='incremental' → CollectActionCard（→ IncrementalCollectCard：只出时间范围）
    strategy='full'        → CollectActionCard（→ FullCollectCard：只出一个按钮）
    strategy='realtime'    → RealtimePanel（占位，不建任务）

  建任务 → 轮询 getCollectTask 显示进度条 → done/failed 显示终态。
  重跑 = 同参再建一次（trigger_source='retry' + parent_task_id 指原任务）。
-->
<template>
  <main class="task-pane">
    <div v-if="!item" class="tip">请从左侧选择采集任务</div>

    <RealtimePanel
      v-else-if="isRealtime"
      :service-name="serviceName"
      :item="item"
      class="task-pane__scroll"
    />

    <template v-else>
      <CollectActionCard
        :service-name="serviceName"
        :item="item"
        :starting="running"
        @start="startTask(serviceName, $event)"
      />

      <!-- 任务进度（轮询中 / 终态） -->
      <div v-if="task" class="result-card">
        <div class="result-card__title">
          <el-icon :color="taskColor" class="mr-1">
            <component :is="taskIcon" />
          </el-icon>
          任务 {{ task.task_id }} · {{ STATUS_LABEL[task.status] || task.status }}
          <el-tag v-if="taskStrategy" size="small" effect="plain" class="ml-2">
            {{ STRATEGY_LABEL[taskStrategy] }}
          </el-tag>
        </div>
        <el-progress
          :percentage="progressPct"
          :status="progressStatus"
          :stroke-width="8"
          class="task-progress"
        />
        <div class="result-card__stats">
          <span class="stat"><b>{{ task.done ?? 0 }}/{{ task.total ?? 0 }}</b> 步</span>
          <span class="stat"><b class="text-green-600">{{ task.success ?? 0 }}</b> 成功</span>
          <span v-if="(task.fail ?? 0) > 0" class="stat"><b class="text-red-500">{{ task.fail }}</b> 失败</span>
          <span v-if="(task.skip ?? 0) > 0" class="stat"><b>{{ task.skip }}</b> 跳过</span>
          <span class="stat"><b>{{ task.saved_total ?? 0 }}</b> 写入</span>
        </div>
        <div v-if="task.message" class="result-card__msg">
          {{ task.message }}
        </div>
        <div class="result-card__actions">
          <el-button size="small" :disabled="running" @click="retry">重跑（同参数）</el-button>
        </div>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleClose, CircleCheck, InfoFilled, Loading } from '@element-plus/icons-vue'

import CollectActionCard from './CollectActionCard.vue'
import RealtimePanel from './RealtimePanel.vue'
import type {
  CatalogItem,
  CollectStartPayload,
  CollectStrategy,
  CollectTaskState,
} from '../api'
import { createCollectTask, getCollectTask } from '../api'

const props = defineProps<{
  serviceName: string
  item: CatalogItem | null | undefined
}>()

/** 实时查询服务（strategy='realtime'）：只显示占位，不建任务 */
const isRealtime = computed(() => props.item?.strategy === 'realtime')

const STATUS_LABEL: Record<string, string> = {
  queued: '排队中',
  running: '执行中',
  done: '完成',
  failed: '失败',
}

const STRATEGY_LABEL: Record<string, string> = {
  incremental: '增量采集',
  full: '全量覆盖',
}

// ── 当前任务状态（轮询维护） ─────────────
const task = ref<CollectTaskState | null>(null)
const running = ref(false)
let timer: ReturnType<typeof setInterval> | null = null
let lastPayload: CollectStartPayload | null = null

/** 当前任务的采集方式（优先 strategy，回退 kind） */
const taskStrategy = computed<CollectStrategy | ''>(() => {
  const t = task.value
  if (!t) return ''
  return (t.strategy || t.kind || '') as CollectStrategy
})

/**
 * 进度百分比。
 *
 * ★ 优先用服务端算好的 `progress`（= 已完成步数 / 总步数 * 100），
 *   兜底用本地算的 done/total —— 两端口径一致，服务端是权威值。
 */
const progressPct = computed(() => {
  const t = task.value
  if (!t) return 0
  if (typeof t.progress === 'number' && t.progress > 0) {
    return Math.min(100, Math.round(t.progress))
  }
  if (!t.total) return 0
  return Math.min(100, Math.round(((t.done || 0) / t.total) * 100))
})

const progressStatus = computed(() => {
  const s = task.value?.status
  if (s === 'done') return 'success'
  if (s === 'failed') return 'exception'
  return undefined
})

const taskColor = computed(() => {
  const s = task.value?.status
  if (s === 'failed') return '#ef4444'
  if (s === 'done') return '#22c55e'
  return '#3b82f6'
})

const taskIcon = computed(() => {
  const s = task.value?.status
  if (s === 'failed') return CircleClose
  if (s === 'done') return CircleCheck
  if (s === 'running' || s === 'queued') return Loading
  return InfoFilled
})

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

async function tick(taskId: string) {
  try {
    const state = await getCollectTask(taskId)
    task.value = state
    if (state.status === 'done' || state.status === 'failed') {
      stopPolling()
      running.value = false
      if (state.status === 'done') ElMessage.success(state.message || '采集完成')
      else ElMessage.error(state.message || '采集失败')
    }
  } catch (e: any) {
    stopPolling()
    running.value = false
    ElMessage.error(e?.message || '查询任务进度失败')
  }
}

/** 开始采集：建任务 → 1s 轮询进度 */
async function startTask(serviceName: string, payload: CollectStartPayload) {
  console.log('[CollectTaskPane] createTask', serviceName, payload)
  stopPolling()
  running.value = true
  lastPayload = payload
  try {
    const created = await createCollectTask(serviceName, payload)
    ElMessage.info(`任务已创建 ${created.task_id}，共 ${created.total} 步`)
    await tick(created.task_id)
    stopPolling()
    if (task.value && task.value.status !== 'done' && task.value.status !== 'failed') {
      running.value = true
      timer = setInterval(() => tick(created.task_id), 1000)
    }
  } catch (e: any) {
    running.value = false
    task.value = null
    ElMessage.error(e?.response?.data?.message || e?.message || '创建任务失败')
  }
}

/**
 * 重跑：同参数再建一次（upsert 幂等，安全）。
 *
 * ★ 带上 trigger_source='retry' + parent_task_id（指原任务），
 *   审计日志能追出「这次是重跑哪次」的链路。
 */
function retry() {
  if (!lastPayload) return
  startTask(props.serviceName, {
    ...lastPayload,
    trigger_source: 'retry',
    parent_task_id: task.value?.task_id,
  })
}

// 切 service 时清掉旧任务状态 + 停轮询
watch(
  () => props.serviceName,
  () => {
    stopPolling()
    running.value = false
    task.value = null
    lastPayload = null
  },
)

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.task-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.task-pane__scroll {
  flex: 1;
  min-height: 0;
}

.tip {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

/* ── 任务进度卡片 ── */
.result-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  flex-shrink: 0;
}

.result-card__title {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.task-progress {
  margin-bottom: 8px;
}

.result-card__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #475569;
  margin-bottom: 8px;
}

.result-card__stats .stat b {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px;
  margin-right: 2px;
}

.result-card__msg {
  font-size: 12px;
  color: #64788b;
  background: #f8fafc;
  padding: 6px 10px;
  border-radius: 4px;
  border-left: 3px solid #94a3b8;
}

.result-card__actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
</style>
