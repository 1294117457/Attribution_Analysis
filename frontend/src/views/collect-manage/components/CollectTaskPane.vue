<!--
  CollectTaskPane.vue — 采集管理右侧主区（v3 自管协议适配）

  v2 新增功能：
    - 触发采集后立即返回 log_id，前端开始轮询进度
    - 实时显示采集进度条、已保存数、失败数
    - 日志列表展示历史采集记录

  v3（2026-10-22）适配后端「自管协议」：
    - daily 路由不再返回 log_id（log_id 不透出边界），改由前端按
      service_name 轮询 GET /collect/logs/{service_name} 定位新日志
    - 触发后先快照旧日志 id 集合，再轮询找「新增的 init/running」日志，
      避免误把上一轮任务当成本轮进度

  v4（2026-10-26）后端日志状态机简化：
    - status: init（已创建）→ running（采集中）→ success/partial_fail/failed
    - DB 侧创建后停在 init，实时进度以 Redis 为准，读接口会合并

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
        :saved-label="savedLabel"
        :total-label="totalLabel"
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
import { runService, listCollectLogs, describeCollectError } from '../api'

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

/**
 * daily 的 saved_count 语义 = 成功采集的天数/单元数（不是入库行数），
 * total_count = 区间自然日总数。其它 service 语义与后端一致。
 */
const isDaily = computed(() => props.serviceName === 'daily')
const savedLabel = computed(() => (isDaily.value ? '已采集' : '已保存'))
const totalLabel = computed(() => (isDaily.value ? '总天数' : '预估总数'))

// ── 轮询控制 ──────────────────────────────────────────────
let pollTimer: ReturnType<typeof setTimeout> | null = null
const polling = ref(false)

/**
 * 本轮触发前的日志 id 快照（后端不返回 log_id 时用来定位「新增的那条」）
 */
let knownLogIds = new Set<string>()

/** 本轮触发时刻（毫秒）——用于按 started_at 兜底定位 */
let triggeredAt = 0

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

/** 记录当前已知日志 id（触发前调用） */
function snapshotLogIds() {
  knownLogIds = new Set(logs.value.map(l => l.id))
}

/**
 * 定位本轮采集的日志
 *
 * ★ 后端 v4 自管协议不再返回 log_id（daily 路由 response 是 ApiResponse[None]），
 *   所以只能按 service_name 查日志列表，找出「快照之后新增的那条」。
 */
function findTriggeredLog(latestLogs: CollectLog[]): CollectLog | undefined {
  // 1) 优先：快照之后新增的日志
  const fresh = latestLogs.find(l => !knownLogIds.has(l.id))
  if (fresh) return fresh
  // 2) 兜底：按 started_at 判断是本轮触发的（快照后没新增 → 列表可能已刷新过）
  const byTime = latestLogs.find(l => {
    if (!l.started_at) return false
    const t = new Date(l.started_at).getTime()
    return Number.isFinite(t) && t >= triggeredAt - 1000
  })
  if (byTime) return byTime
  // 3) 最后兜底：仍在进行中的日志
  return latestLogs.find(
    l => l.status === 'init' || l.status === 'running',
  )
}

/** 如果有待采集的日志（init/running），恢复轮询 */
async function resumePollingIfNeeded() {
  const active = logs.value.find(
    l => l.status === 'init' || l.status === 'running'
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

    // ★ 没有 log_id 时（daily 等自管协议路由）自动定位本轮日志
    if (!activeLogId.value) {
      const triggered = findTriggeredLog(latestLogs)
      if (triggered) {
        activeLogId.value = triggered.id
        console.log(LOG_PREFIX, '定位到本轮采集日志:', triggered.id, triggered.status)
      }
    }

    // 找到当前 activeLogId 对应的最新状态
    const currentLog = latestLogs.find(l => l.id === activeLogId.value)

    // 终态停止轮询
    if (currentLog && ['success', 'partial_fail', 'failed', 'skipped'].includes(currentLog.status)) {
      console.log(LOG_PREFIX, '采集完成，停止轮询:', currentLog.status)
      stopPolling()

      // 提示用户（daily 的 saved_count 是「成功单元数」，非入库行数）
      const unit = isDaily.value ? '个采集单元' : '条'
      if (currentLog.status === 'success') {
        ElMessage.success(`采集完成：已保存 ${currentLog.saved_count} ${unit}`)
      } else if (currentLog.status === 'partial_fail') {
        ElMessage.warning(`采集完成：成功 ${currentLog.saved_count} ${unit}，失败 ${currentLog.fail_count} 个`)
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
  if (log.status === 'init' || log.status === 'running') {
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

  // ★ 快照当前日志 id：后端不返回 log_id 时靠它定位本轮新增日志
  snapshotLogIds()
  triggeredAt = Date.now()
  activeLogId.value = null

  try {
    const res = await runService(serviceName, payload)
    console.log(LOG_PREFIX, 'runService result:', res)

    // 后端 v4 自管协议可能不返回 log_id（daily 路由 → ApiResponse[None]）
    if (res.log_id) {
      activeLogId.value = res.log_id
    } else {
      ElMessage.info(res.message || '采集任务派发成功')
    }

    // 重新加载日志列表（把新日志加进去）
    await loadLogs()

    // 开始轮询（无 log_id 时由 pollProgress 自动定位本轮日志）
    startPolling()
  } catch (e: any) {
    console.error(LOG_PREFIX, 'runService error:', e)
    ElMessage.error(describeCollectError(e))
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
