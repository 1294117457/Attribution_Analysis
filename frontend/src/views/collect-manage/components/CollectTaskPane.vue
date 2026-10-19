<!--
  CollectTaskPane.vue — 采集管理右侧主区（v2 采集日志进度优化）

  v2 新增功能：
    - 触发采集后立即返回 log_id，前端开始轮询进度
    - 实时显示采集进度条、已保存数、失败数
    - 日志列表展示历史采集记录

  实时 service（kind=realtime）走 RealtimePanel；其他走 CollectActionCard + 进度展示。
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
        @start="runServiceAndWait(serviceName, $event)"
      />

      <!-- 采集进度卡片（v2 新增） -->
      <CollectProgressCard
        v-if="activeLog"
        :log="activeLog"
        @stop="stopPolling"
      />

      <!-- 采集历史日志列表（v2 新增） -->
      <CollectLogList
        :logs="logs"
        :active-log-id="activeLogId"
        @select="onSelectLog"
      />
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'

import CollectActionCard from './CollectActionCard.vue'
import RealtimePanel from './RealtimePanel.vue'
import CollectProgressCard from './CollectProgressCard.vue'
import CollectLogList from './CollectLogList.vue'
import type { CatalogItem, CollectStartPayload, CollectLog } from '../api'
import { runService, listCollectLogs } from '../api'

const LOG_PREFIX = '[CollectTaskPane]'
const POLL_INTERVAL = 2000  // 轮询间隔 2 秒

const props = defineProps<{
  serviceName: string
  item: CatalogItem | null | undefined
}>()

/** 实时 = kind='realtime'（纯实时，不入库） */
const isRealtime = computed(() => props.item?.kind === 'realtime')

// ── 采集状态 ──────────────────────────────────────────────
const running = ref(false)
const activeLogId = ref<string | null>(null)
const logs = ref<CollectLog[]>([])
const activeLog = computed(() =>
  logs.value.find(l => l.id === activeLogId.value) ?? null
)

// ── 轮询控制 ──────────────────────────────────────────────
let pollTimer: ReturnType<typeof setTimeout> | null = null
const polling = ref(false)

// ── 初始化：加载日志列表 + 恢复轮询 ──────────────────────
onMounted(async () => {
  await loadLogs()
  await resumePollingIfNeeded()
})

// service 切换时重新加载日志
watch(() => props.serviceName, async () => {
  stopPolling()
  activeLogId.value = null
  await loadLogs()
  await resumePollingIfNeeded()
})

/** 加载日志列表 */
async function loadLogs() {
  if (!props.serviceName) return
  try {
    const res = await listCollectLogs(props.serviceName, 20)
    logs.value = res.items || []
  } catch (e) {
    console.error(LOG_PREFIX, 'loadLogs error:', e)
  }
}

/** 如果有待采集的日志（pending/running），恢复轮询 */
async function resumePollingIfNeeded() {
  const active = logs.value.find(
    l => l.status === 'pending' || l.status === 'running'
  )
  if (active) {
    console.log(LOG_PREFIX, '发现进行中的采集任务，恢复轮询:', active.id)
    activeLogId.value = active.id
    startPolling()
  }
}

/** 开始轮询 */
function startPolling() {
  if (polling.value) return
  polling.value = true
  pollProgress()
}

/** 停止轮询 */
function stopPolling() {
  polling.value = false
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

/** 轮询进度 */
async function pollProgress() {
  if (!polling.value || !props.serviceName) return

  try {
    const res = await listCollectLogs(props.serviceName, 50)
    const latestLogs = res.items || []

    // 更新本地日志列表
    for (const log of latestLogs) {
      const idx = logs.value.findIndex(l => l.id === log.id)
      if (idx >= 0) {
        logs.value[idx] = log
      } else {
        // 新日志加入列表
        logs.value.unshift(log)
        if (logs.value.length > 20) logs.value.pop()
      }
    }

    // 找到当前 activeLogId 对应的最新状态
    const currentLog = latestLogs.find(l => l.id === activeLogId.value)

    // 终态停止轮询
    if (currentLog && ['success', 'partial_fail', 'failed', 'skipped'].includes(currentLog.status)) {
      console.log(LOG_PREFIX, '采集完成，停止轮询:', currentLog.status)
      stopPolling()

      // 提示用户
      if (currentLog.status === 'success') {
        ElMessage.success(`采集完成：已保存 ${currentLog.saved_count} 条`)
      } else if (currentLog.status === 'partial_fail') {
        ElMessage.warning(`采集完成：成功 ${currentLog.saved_count} 条，失败 ${currentLog.fail_count} 条`)
      } else if (currentLog.status === 'failed') {
        ElMessage.error(`采集失败：${currentLog.error_message || '未知错误'}`)
      }
    }
  } catch (e) {
    console.error(LOG_PREFIX, 'pollProgress error:', e)
  }

  // 继续轮询
  if (polling.value) {
    pollTimer = setTimeout(pollProgress, POLL_INTERVAL)
  }
}

/** 选择日志 */
function onSelectLog(log: CollectLog) {
  activeLogId.value = log.id
  if (log.status === 'pending' || log.status === 'running') {
    startPolling()
  } else {
    stopPolling()
  }
}

/** 触发采集 */
async function runServiceAndWait(
  serviceName: string,
  payload: CollectStartPayload,
) {
  console.log(LOG_PREFIX, 'runService', serviceName, payload)
  running.value = true
  stopPolling()  // 先停止当前轮询

  try {
    const res = await runService(serviceName, payload)
    console.log(LOG_PREFIX, 'runService result:', res)

    // 设置 activeLogId 开始轮询
    activeLogId.value = res.log_id

    // 重新加载日志列表（把新日志加进去）
    await loadLogs()

    // 开始轮询
    startPolling()
  } catch (e: any) {
    console.error(LOG_PREFIX, 'runService error:', e)
    ElMessage.error(e?.response?.data?.message || e?.message || '采集失败')
  } finally {
    running.value = false
  }
}
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
</style>
