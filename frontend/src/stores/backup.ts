/**
 * Backup Pinia Store
 * 持有：路径配置（持久化到 localStorage）+ 轮询任务字典
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { BackupRecord, RestoreRecord } from '@/api/backup'

const PATH_KEY = 'bkup-paths'

interface PathConfig {
  outputDir: string
  inputDir: string
}

function loadPath(): PathConfig {
  try {
    const raw = localStorage.getItem(PATH_KEY)
    if (!raw) return { outputDir: '', inputDir: '' }
    return JSON.parse(raw)
  } catch {
    return { outputDir: '', inputDir: '' }
  }
}

function savePath(cfg: PathConfig) {
  try {
    localStorage.setItem(PATH_KEY, JSON.stringify(cfg))
  } catch {
    /* ignore */
  }
}

export const useBackupStore = defineStore('backup', () => {
  // ── 路径配置（localStorage 持久化） ──
  const pathConfig = ref<PathConfig>(loadPath())

  function setOutputDir(d: string) {
    pathConfig.value = { ...pathConfig.value, outputDir: d }
    savePath(pathConfig.value)
  }
  function setInputDir(d: string) {
    pathConfig.value = { ...pathConfig.value, inputDir: d }
    savePath(pathConfig.value)
  }

  // ── 轮询任务（按 record_id 缓存 intervalId） ──
  const pollers = new Map<number, number>()

  /**
   * 启动轮询；cb 每次收到新记录时被调；当 status 终态时自动停止
   */
  function startPolling<T extends { status: string }>(
    recordId: number,
    fetcher: (id: number) => Promise<T>,
    cb: (record: T) => void,
    intervalMs = 2000,
  ) {
    if (pollers.has(recordId)) return
    let cancelled = false

    const tick = async () => {
      if (cancelled) return
      try {
        const record = await fetcher(recordId)
        cb(record)
        if (
          record.status === 'success' ||
          record.status === 'failed' ||
          record.status === 'interrupted'
        ) {
          stopPolling(recordId)
        }
      } catch {
        /* 接口报错忽略，下一轮继续 */
      }
    }
    void tick() // 立即跑一次
    const id = window.setInterval(tick, intervalMs)
    pollers.set(recordId, id)
  }

  function stopPolling(recordId: number) {
    const id = pollers.get(recordId)
    if (id !== undefined) {
      clearInterval(id)
      pollers.delete(recordId)
    }
  }

  function stopAllPolling() {
    for (const id of pollers.values()) clearInterval(id)
    pollers.clear()
  }

  // ── 工具：BackupRecord / RestoreRecord 共用的 fetcher ──
  async function fetchBackup(id: number) {
    const { getBackup } = await import('@/api/backup')
    return getBackup(id) as Promise<BackupRecord>
  }
  async function fetchRestore(id: number) {
    const { getRestore } = await import('@/api/backup')
    return getRestore(id) as Promise<RestoreRecord>
  }

  return {
    pathConfig,
    setOutputDir,
    setInputDir,
    startPolling,
    stopPolling,
    stopAllPolling,
    fetchBackup,
    fetchRestore,
  }
})