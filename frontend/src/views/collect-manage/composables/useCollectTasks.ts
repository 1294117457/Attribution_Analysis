/**
 * 采集任务列表 + 进度轮询 composable
 *
 * 抽离自 CollectManage.vue（原 ~660 行中任务相关逻辑）：
 * - 任务列表 + 分页
 * - 进度轮询（每 3s）
 * - 启动任务 / 取消任务
 * - 正在运行任务集合（按钮 loading 反馈）
 *
 * 配套：docs/dev/step2/02datamanage/01-采集管理四维重构方案.md §3.2.2
 */

import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createTask,
  listTasks,
  getTaskProgress,
  cancelTask,
  type CollectTask,
  type CreateTaskResult,
  type TaskProgress,
} from '../api'

const LOG_PREFIX = '[useCollectTasks]'

export function useCollectTasks(currentTaskType: () => string) {
  // ── 列表 ────────────────────────────────────────────────
  const tasks = ref<CollectTask[]>([])
  const taskTotal = ref(0)
  const taskPage = ref(1)
  const taskPageSize = ref(20)
  const tasksLoading = ref(false)

  // ── 启动中任务集合（按钮 loading 反馈） ──────────────
  const startingTasks = reactive<Set<string>>(new Set())

  // ── 进度 ────────────────────────────────────────────────
  const progressMap = reactive<Record<number, TaskProgress>>({})
  const finishedIds = new Set<number>()
  const watchingIds = new Set<number>()
  let pollTimer: ReturnType<typeof setInterval> | null = null
  const expandedRowKeys = ref<number[]>([])

  // ── 列表加载 ────────────────────────────────────────────
  async function loadTasks() {
    tasksLoading.value = true
    try {
      const data = await listTasks({
        task_type: currentTaskType(),
        page: taskPage.value,
        page_size: taskPageSize.value,
      })
      tasks.value = data.items || []
      taskTotal.value = data.total || 0

      const statusSummary = tasks.value.map((t) => `${t.id}:${t.status}`).join(', ')
      console.log(LOG_PREFIX, 'loadTasks', currentTaskType(),
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

  // ── 启动任务 ────────────────────────────────────────────
  /** creator 默认 createTask；按方案执行时传 runPlan（响应形状相同） */
  async function startTask(
    taskType: string,
    params?: Record<string, any>,
    creator: () => Promise<CreateTaskResult> = () => createTask({ task_type: taskType, params }),
  ) {
    console.log(LOG_PREFIX, 'startTask', taskType, params)
    startingTasks.add(taskType)
    try {
      const res = await creator()
      console.log(LOG_PREFIX, 'createTask response:', res)
      if (res.task_id) {
        ElMessage.success(res.message || '任务已创建')
        watchingIds.add(res.task_id)
        console.log(LOG_PREFIX, 'added to watchingIds:', res.task_id)
        if (!pollTimer) startPolling()
      } else {
        ElMessage.warning(res.message || '操作未完成')
      }
      await loadTasks()
      if (res.task_id && !tasks.value.some((t) => t.id === res.task_id)) {
        console.log(LOG_PREFIX, 'new task not in list yet, retry in 500ms')
        setTimeout(() => loadTasks(), 500)
      }
    } catch (e) {
      console.error(LOG_PREFIX, 'startTask error:', e)
      ElMessage.error('创建任务失败: ' + (e as Error).message)
    } finally {
      startingTasks.delete(taskType)
    }
  }

  // ── 取消任务 ────────────────────────────────────────────
  async function handleCancel(row: CollectTask) {
    try {
      await ElMessageBox({
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

  // ── 进度轮询 ────────────────────────────────────────────
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

  // ── 分页 ────────────────────────────────────────────────
  function onPageChange(p: number) {
    taskPage.value = p
    loadTasks()
  }
  function onPageSizeChange(s: number) {
    taskPageSize.value = s
    taskPage.value = 1
    loadTasks()
  }

  // ── 切 task 时清理状态 ────────────────────────────────
  function onTaskTypeChange() {
    console.log(LOG_PREFIX, 'task_type →', currentTaskType())
    stopPolling()
    finishedIds.clear()
    watchingIds.clear()
    taskPage.value = 1
    loadTasks()
  }

  watch(currentTaskType, onTaskTypeChange)

  // ── 生命周期 ────────────────────────────────────────────
  onMounted(() => {
    loadTasks()
  })
  onBeforeUnmount(() => {
    console.log(LOG_PREFIX, 'unmount, stopping poll')
    stopPolling()
  })

  return {
    // 列表状态
    tasks,
    taskTotal,
    taskPage,
    taskPageSize,
    tasksLoading,
    expandedRowKeys,
    // 操作
    loadTasks,
    startTask,
    handleCancel,
    onPageChange,
    onPageSizeChange,
    // 进度
    progressMap,
    startingTasks,
  }
}