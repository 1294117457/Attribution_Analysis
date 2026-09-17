<!--
  操作池详情 — 左右分栏布局 (1 : 4)
  - 左侧 (~20%)：成员列表（可点击切换右侧分析）
  - 右侧 (~80%)：完整 K 线分析面板（复用 AnalysisDetailPanel）
-->
<template>
  <div class="pool-detail" v-loading="store.loading && !pool">
    <!-- 顶部信息 -->
    <header class="top-bar flex items-center gap-4 px-5 py-3 border-b bg-white">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>

      <div v-if="pool" class="flex items-center gap-3 flex-1 min-w-0">
        <span class="text-2xl">{{ pool.icon || '📂' }}</span>
        <h2 class="text-lg font-bold text-gray-900 !mb-0 truncate">{{ pool.name }}</h2>
        <el-tag v-if="pool.is_default" type="warning" size="small">默认池</el-tag>
        <span class="text-xs text-gray-500 truncate">
          {{ pool.description || '暂无描述' }}
          · {{ pool.member_count }} 只股票
        </span>
      </div>

      <div v-if="pool" class="flex gap-2">
        <el-button type="primary" @click="showCollectDialog">
          <el-icon class="mr-1"><Download /></el-icon>
          批量采集 K 线
        </el-button>
        <el-button @click="showEditDialog">
          <el-icon class="mr-1"><Edit /></el-icon>
          编辑
        </el-button>
      </div>
    </header>

    <!-- 主体：左 1 : 右 4 -->
    <main class="body flex-1 min-h-0 flex gap-3 p-3 overflow-hidden">
      <!-- 左：成员列表 -->
      <aside class="left-card flex flex-col min-h-0 overflow-hidden bg-white rounded-md">
        <div class="left-toolbar flex items-center gap-2 px-3 py-2 border-b">
          <el-input
            v-model="memberSearch"
            placeholder="搜索成员"
            clearable
            size="small"
            :prefix-icon="Search"
          />
          <el-button size="small" type="primary" @click="showAddMemberDialog">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>

        <div class="left-list flex-1 overflow-auto" v-loading="loadingMembers">
          <div
            v-if="filteredMembers.length === 0 && !loadingMembers"
            class="empty-hint flex items-center justify-center h-full text-xs text-gray-400"
          >
            池内还没有成员
          </div>

          <ul class="member-list">
            <li
              v-for="m in filteredMembers"
              :key="m.symbol"
              class="member-row"
              :class="{ active: m.symbol === selectedSymbol }"
              :data-symbol="m.symbol"
              @click="selectMember(m)"
            >
              <div class="flex items-center justify-between gap-1">
                <span class="font-mono font-semibold text-sm">{{ m.symbol }}</span>
                <el-tooltip v-if="!m.is_valid" content="该股票可能已退市" placement="top">
                  <el-icon class="text-amber-500"><Warning /></el-icon>
                </el-tooltip>
              </div>
              <div class="text-xs text-gray-500 truncate">
                {{ m.name || '—' }}
              </div>
              <div v-if="m.memo" class="text-[11px] text-gray-400 truncate">
                {{ m.memo }}
              </div>
            </li>
          </ul>
        </div>

        <!-- 选中成员的快捷操作 -->
        <div
          v-if="selectedMember"
          class="left-actions flex items-center justify-between gap-1 px-3 py-2 border-t text-xs"
        >
          <span class="text-gray-500 truncate">
            已选：<span class="font-mono font-semibold">{{ selectedMember.symbol }}</span>
          </span>
          <div class="flex gap-1">
            <el-button
              size="small"
              link
              type="danger"
              @click="removeOne(selectedMember.symbol)"
            >
              移除
            </el-button>
          </div>
        </div>
      </aside>

      <!-- 右：完整 K 线分析 -->
      <section class="right-card flex flex-col min-h-0 overflow-hidden bg-white rounded-md">
        <AnalysisDetailPanel
          v-if="selectedSymbol"
          :symbol="selectedSymbol"
          :days="365"
          class="flex-1 min-h-0 overflow-hidden"
        />
        <el-empty
          v-else
          class="h-full flex items-center justify-center"
          description="从左侧选择一只股票查看完整分析"
        />
      </section>
    </main>

    <!-- 编辑池弹窗 -->
    <PoolCreateDialog
      v-model="editDialogVisible"
      :pool="pool"
      @saved="onPoolEdited"
    />

    <!-- 批量采集 K 线 弹窗 -->
    <el-dialog v-model="collectDialogVisible" title="批量采集 K 线" width="420px">
      <el-form label-width="80px">
        <el-form-item label="回溯天数">
          <el-input-number
            v-model="collectDays"
            :min="1"
            :max="3650"
            :step="30"
          />
          <span class="ml-2 text-xs text-gray-500">默认 365 天</span>
        </el-form-item>
        <el-form-item>
          <el-alert
            :title="`将对池内 ${pool?.member_count ?? 0} 只股票依次采集`"
            type="info"
            :closable="false"
            show-icon
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="collectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="collecting" @click="startCollect">
          开始采集
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加成员 弹窗 -->
    <el-dialog v-model="addMemberDialogVisible" title="添加股票到池" width="500px">
      <el-form>
        <el-form-item label="股票代码">
          <el-input
            v-model="addSymbolsText"
            type="textarea"
            :rows="5"
            placeholder="每行一个 6 位股票代码，例如：&#10;600000&#10;600016"
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="addValidateExists">
            校验股票是否存在（取消后可加入退市股票）
          </el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addMemberDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="addMembers">
          添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Search,
  Plus,
  Download,
  Edit,
  Warning,
} from '@element-plus/icons-vue'
import { usePoolStore } from '@/stores/pool'
import PoolCreateDialog from '@/views/stock-pool/components/PoolCreateDialog.vue'
import AnalysisDetailPanel from './AnalysisDetailPanel.vue'
import type { PoolMember } from '@/views/stock-pool/api'

const route = useRoute()
const router = useRouter()
const store = usePoolStore()

const poolId = computed(() => Number(route.params.poolId))
const pool = computed(() => store.currentPool)
const loadingMembers = ref(false)

// ── 选中成员 ─────────────────────────────────────────────────────────
const selectedSymbol = ref<string>('')
const selectedMember = ref<PoolMember | null>(null)

function selectMember(m: PoolMember) {
  selectedSymbol.value = m.symbol
  selectedMember.value = m
}

const memberSearch = ref('')
const filteredMembers = computed(() => {
  if (!pool.value) return []
  const q = memberSearch.value.trim()
  if (!q) return pool.value.members
  return pool.value.members.filter(
    (m) =>
      m.symbol.includes(q) ||
      (m.name ?? '').includes(q) ||
      (m.industry ?? '').includes(q),
  )
})

// ── 路由 ─────────────────────────────────────────────────────────────
function goBack() {
  router.push({ path: '/home/pool' })
}

function showEditDialog() {
  editDialogVisible.value = true
}

async function onPoolEdited() {
  await store.fetchPoolDetail(poolId.value)
}

// ── 成员管理 ─────────────────────────────────────────────────────────
const editDialogVisible = ref(false)

const collectDialogVisible = ref(false)
const collectDays = ref(365)
const collecting = ref(false)

const addMemberDialogVisible = ref(false)
const addSymbolsText = ref('')
const addValidateExists = ref(true)
const adding = ref(false)

function showCollectDialog() {
  collectDays.value = 365
  collectDialogVisible.value = true
}

function showAddMemberDialog() {
  addSymbolsText.value = ''
  addMemberDialogVisible.value = true
}

async function addMembers() {
  const symbols = addSymbolsText.value
    .split(/[\s,，\n]+/)
    .map((s) => s.trim())
    .filter((s) => /^\d{6}$/.test(s))

  if (symbols.length === 0) {
    ElMessage.warning('请输入有效的股票代码')
    return
  }

  adding.value = true
  try {
    const result = await store.addMembers(poolId.value, symbols, addValidateExists)
    ElMessage.success(
      `添加完成：成功 ${result.total_added}，跳过 ${result.total_skipped}`,
    )
    addMemberDialogVisible.value = false
  } catch (e) {
    ElMessage.error('添加失败: ' + (e as Error).message)
  } finally {
    adding.value = false
  }
}

async function removeOne(symbol: string) {
  try {
    await ElMessageBox.confirm(`确定从池中移除 ${symbol}？`, '确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await store.removeMembers(poolId.value, [symbol])
    ElMessage.success('已移除')
    if (selectedSymbol.value === symbol) {
      selectedSymbol.value = ''
      selectedMember.value = null
    }
  } catch (e) {
    ElMessage.error('移除失败: ' + (e as Error).message)
  }
}

// ── 采集 K 线 ────────────────────────────────────────────────────────
async function startCollect() {
  collecting.value = true
  try {
    const result = await store.startKlineCollect(poolId.value, collectDays.value)
    ElMessage.success(result.message)
    collectDialogVisible.value = false
    startProgressPolling(result.operation_id)
  } catch (e) {
    ElMessage.error('派发失败: ' + (e as Error).message)
  } finally {
    collecting.value = false
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null
function startProgressPolling(opId: number) {
  stopProgressPolling()
  pollTimer = setInterval(async () => {
    try {
      const progress = await store.pollProgress(opId)
      if (progress.done === progress.total && progress.total > 0) {
        stopProgressPolling()
        await store.refreshOperation(opId)
        ElMessage.success('采集任务完成')
        // 重新拉取成员/分析以反映最新数据
        await store.fetchPoolDetail(poolId.value)
        if (selectedSymbol.value) {
          // 触发 AnalysisDetailPanel 重载（symbol 不变也得重新触发）
          const sym = selectedSymbol.value
          selectedSymbol.value = ''
          await nextTick()
          selectedSymbol.value = sym
        }
      }
    } catch (e) {
      stopProgressPolling()
    }
  }, 2000)
}

function stopProgressPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ── 生命周期 ─────────────────────────────────────────────────────────
watch(
  poolId,
  async (id) => {
    if (id) {
      loadingMembers.value = true
      try {
        await store.fetchPoolDetail(id)
        // 默认选中第一个有效成员
        if (pool.value && pool.value.members.length > 0) {
          const first = pool.value.members[0]
          selectedSymbol.value = first.symbol
          selectedMember.value = first
        } else {
          selectedSymbol.value = ''
          selectedMember.value = null
        }
      } finally {
        loadingMembers.value = false
      }
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  stopProgressPolling()
})
</script>

<style scoped>
.pool-detail {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--color-admin-bg);
}

.top-bar {
  flex-shrink: 0;
}

.body {
  min-height: 0;
  flex: 1;
}

.left-card {
  width: 260px;
  flex-shrink: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.right-card {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.left-toolbar {
  flex-shrink: 0;
}

.left-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.member-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.member-row {
  padding: 8px 12px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  transition: background 0.15s;
  user-select: none;
}

.member-row:hover {
  background: #f9fafb;
}

.member-row.active {
  background: #eef2ff;
  border-left: 3px solid #6366f1;
  padding-left: 9px;
}

.left-actions {
  flex-shrink: 0;
  background: #fafafa;
}

.empty-hint {
  padding: 24px 12px;
}
</style>
