import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Pool,
  PoolDetail,
  PoolOperation,
  PoolMember,
  OperationProgress,
} from '@/views/stock-pool/api'
import * as poolApi from '@/views/stock-pool/api'

export const usePoolStore = defineStore('pool', () => {
  // ── State ─────────────────────────────────────────────────────────────

  const pools = ref<Pool[]>([])
  const currentPool = ref<PoolDetail | null>(null)
  const operations = ref<PoolOperation[]>([])
  const currentOperation = ref<PoolOperation | null>(null)
  const loading = ref(false)

  // ── Getters ──────────────────────────────────────────────────────────

  const defaultPool = computed(() =>
    pools.value.find((p) => p.is_default) ?? null,
  )

  // ── Actions ───────────────────────────────────────────────────────────

  /** 拉取所有池（仅元信息，不含成员） */
  async function fetchPools() {
    loading.value = true
    try {
      const res = await poolApi.listPools({ limit: 100 })
      pools.value = res.items
    } finally {
      loading.value = false
    }
  }

  /** 拉取池详情（含成员） */
  async function fetchPoolDetail(poolId: number) {
    loading.value = true
    try {
      currentPool.value = await poolApi.getPool(poolId)
    } finally {
      loading.value = false
    }
  }

  /** 创建池 */
  async function createPool(data: poolApi.PoolCreateRequest) {
    const pool = await poolApi.createPool(data)
    pools.value.push(pool)
    return pool
  }

  /** 更新池 */
  async function updatePool(
    poolId: number,
    data: poolApi.PoolUpdateRequest,
  ) {
    const updated = await poolApi.updatePool(poolId, data)
    const idx = pools.value.findIndex((p) => p.id === poolId)
    if (idx >= 0) {
      pools.value[idx] = { ...pools.value[idx], ...updated }
    }
    if (currentPool.value?.id === poolId) {
      currentPool.value = { ...currentPool.value, ...updated }
    }
    return updated
  }

  /** 删除池 */
  async function deletePool(poolId: number) {
    await poolApi.deletePool(poolId)
    pools.value = pools.value.filter((p) => p.id !== poolId)
    if (currentPool.value?.id === poolId) {
      currentPool.value = null
    }
  }

  /** 添加成员 */
  async function addMembers(
    poolId: number,
    symbols: string[],
    validateExists = true,
  ) {
    if (typeof poolId !== 'number' || Number.isNaN(poolId)) {
      const display = typeof poolId === 'number' ? String(poolId) : typeof poolId
      throw new Error(`[addMembers] poolId 必须是有效数字，实际类型: ${display}`)
    }
    const result = await poolApi.addMembers(poolId, {
      symbols,
      validate_exists: validateExists,
    })
    await fetchPoolDetail(poolId)
    return result
  }

  /** 移除成员 */
  async function removeMembers(poolId: number, symbols: string[]) {
    await poolApi.removeMembers(poolId, symbols)
    if (currentPool.value?.id === poolId) {
      currentPool.value.members = currentPool.value.members.filter(
        (m) => !symbols.includes(m.symbol),
      )
      currentPool.value.member_count = currentPool.value.members.length
    }
  }

  /** 更新成员备注 */
  async function updateMemberMemo(
    poolId: number,
    symbol: string,
    memo: string,
  ) {
    const updated = await poolApi.updateMemberMemo(poolId, symbol, memo)
    if (currentPool.value?.id === poolId) {
      const m = currentPool.value.members.find((m) => m.symbol === symbol)
      if (m) m.memo = updated.memo
    }
  }

  /** 反向查询 */
  async function findPoolsBySymbol(symbol: string) {
    return await poolApi.findPoolsBySymbol(symbol)
  }

  /** 拉取操作历史 */
  async function fetchOperations(poolId: number, limit = 20) {
    const res = await poolApi.listOperations(poolId, { limit })
    operations.value = res.items
    return res.items
  }

  /** 发起 K 线采集操作 */
  async function startKlineCollect(
    poolId: number,
    days = 365,
  ) {
    const result = await poolApi.createOperation(poolId, {
      operation_type: 'kline_collect',
      days,
    })

    const newOp: PoolOperation = {
      id: result.operation_id,
      pool_id: poolId,
      operation_type: 'kline_collect',
      status: result.status,
      params: { days },
      progress: { done: 0, total: result.total, failed: 0 },
      created_at: new Date().toISOString(),
    }
    operations.value.unshift(newOp)
    currentOperation.value = newOp
    return result
  }

  /** 轮询单个操作的进度 */
  async function pollProgress(opId: number): Promise<OperationProgress> {
    const progress = await poolApi.getOperationProgress(opId)
    const op = operations.value.find((o) => o.id === opId)
    if (op) {
      op.progress = progress
      if (progress.done === progress.total && progress.total > 0) {
        op.status = progress.failed > 0 ? 'partial' : 'success'
      } else if (progress.done > 0) {
        op.status = 'running'
      }
    }
    return progress
  }

  /** 刷新单个操作（详情） */
  async function refreshOperation(opId: number) {
    const op = await poolApi.getOperation(opId)
    const idx = operations.value.findIndex((o) => o.id === opId)
    if (idx >= 0) operations.value[idx] = op
    return op
  }

  /** 取消操作 */
  async function cancelOperation(opId: number) {
    await poolApi.cancelOperation(opId)
    await refreshOperation(opId)
  }

  return {
    // state
    pools,
    currentPool,
    operations,
    currentOperation,
    loading,
    // getters
    defaultPool,
    // actions
    fetchPools,
    fetchPoolDetail,
    createPool,
    updatePool,
    deletePool,
    addMembers,
    removeMembers,
    updateMemberMemo,
    findPoolsBySymbol,
    fetchOperations,
    startKlineCollect,
    pollProgress,
    refreshOperation,
    cancelOperation,
  }
})
