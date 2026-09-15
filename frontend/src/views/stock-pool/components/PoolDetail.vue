<template>
  <div class="admin-page flex flex-col gap-5 h-full" v-loading="store.loading">
    <!-- 顶部信息 -->
    <div class="flex items-start gap-4">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>

      <div v-if="pool" class="flex-1">
        <div class="flex items-center gap-3">
          <span class="text-3xl">{{ pool.icon || '📂' }}</span>
          <h2 class="page-title !mb-0">{{ pool.name }}</h2>
          <el-tag v-if="pool.is_default" type="warning" size="small">默认池</el-tag>
        </div>
        <div class="text-sm text-gray-500 mt-1">
          {{ pool.description || '暂无描述' }}
          · {{ pool.member_count }} 只股票
          · 创建于 {{ formatDate(pool.created_at) }}
        </div>
      </div>

      <div v-if="pool" class="flex gap-2">
        <el-button type="primary" @click="showCollectDialog">
          <el-icon class="mr-1"><Download /></el-icon>
          采集 K 线
        </el-button>
        <el-button @click="showEditDialog">
          <el-icon class="mr-1"><Edit /></el-icon>
          编辑
        </el-button>
      </div>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="flex-1">
      <!-- 成员 Tab -->
      <el-tab-pane label="成员列表" name="members">
        <div class="flex flex-col gap-3 h-full">
          <div class="flex items-center gap-2">
            <el-input
              v-model="memberSearch"
              placeholder="搜索成员"
              clearable
              style="width: 240px"
              :prefix-icon="Search"
              @input="onMemberSearch"
            />
            <el-button type="primary" @click="showAddMemberDialog">
              <el-icon class="mr-1"><Plus /></el-icon>
              添加股票
            </el-button>
            <el-button
              type="danger"
              :disabled="selectedMembers.length === 0"
              @click="batchRemove"
            >
              批量移除 ({{ selectedMembers.length }})
            </el-button>
          </div>

          <el-table
            :data="filteredMembers"
            stripe
            height="calc(100vh - 380px)"
            highlight-current-row
            empty-text="池内还没有成员"
            @selection-change="onSelectionChange"
          >
            <el-table-column type="selection" width="50" />
            <el-table-column prop="symbol" label="代码" width="100">
              <template #default="{ row }">
                <span class="mono font-semibold">{{ row.symbol }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" width="120">
              <template #default="{ row }">
                <span v-if="row.is_valid" class="font-medium">{{ row.name }}</span>
                <el-tooltip v-else content="该股票可能已退市" placement="top">
                  <span class="text-gray-400">{{ row.name || row.symbol }} ⚠️</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="industry" label="行业" min-width="120">
              <template #default="{ row }">{{ row.industry || '—' }}</template>
            </el-table-column>
            <el-table-column prop="market" label="市场" width="100">
              <template #default="{ row }">{{ row.market || '—' }}</template>
            </el-table-column>
            <el-table-column label="备注" min-width="160">
              <template #default="{ row }">
                <el-input
                  v-if="editingMemo === row.symbol"
                  v-model="memoDraft"
                  size="small"
                  maxlength="255"
                  @blur="saveMemo(row.symbol)"
                  @keyup.enter="saveMemo(row.symbol)"
                  ref="memoInput"
                />
                <span
                  v-else
                  class="cursor-pointer hover:bg-gray-100 px-2 py-1 rounded"
                  @click="startEditMemo(row)"
                >
                  {{ row.memo || '—' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="加入时间" width="110">
              <template #default="{ row }">{{ formatDate(row.added_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button text type="danger" size="small" @click="removeOne(row.symbol)">
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 操作历史 Tab -->
      <el-tab-pane :label="`操作历史 (${store.operations.length})`" name="operations">
        <PoolOperations :pool-id="poolId" />
      </el-tab-pane>
    </el-tabs>

    <!-- 编辑池弹窗 -->
    <PoolCreateDialog
      v-model="editDialogVisible"
      :pool="pool"
      @saved="onPoolEdited"
    />

    <!-- 采集 K 线弹窗 -->
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
        <el-form-item label="数据源">
          <el-select v-model="collectSource" placeholder="默认" clearable>
            <el-option label="AkShare" value="akshare" />
            <el-option label="Tushare" value="tushare" />
          </el-select>
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

    <!-- 添加成员弹窗 -->
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
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Search, Plus, Download, Edit } from '@element-plus/icons-vue'
import { usePoolStore } from '@/stores/pool'
import PoolCreateDialog from '@/views/stock-pool/popup/PoolCreateDialog.vue'
import PoolOperations from '@/views/stock-pool/components/PoolOperations.vue'

const route = useRoute()
const router = useRouter()
const store = usePoolStore()

const poolId = computed(() => Number(route.params.poolId))
const pool = computed(() => store.currentPool)

const activeTab = ref('members')
const memberSearch = ref('')
const selectedMembers = ref<{ symbol: string }[]>([])

// 编辑备注
const editingMemo = ref<string | null>(null)
const memoDraft = ref('')

// 弹窗
const editDialogVisible = ref(false)
const collectDialogVisible = ref(false)
const collectDays = ref(365)
const collectSource = ref<string | undefined>(undefined)
const collecting = ref(false)

const addMemberDialogVisible = ref(false)
const addSymbolsText = ref('')
const addValidateExists = ref(true)
const adding = ref(false)

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
let memberSearchTimer: ReturnType<typeof setTimeout> | null = null
function onMemberSearch() {
  if (memberSearchTimer) clearTimeout(memberSearchTimer)
  memberSearchTimer = setTimeout(() => {}, 200)
}

function onSelectionChange(rows: { symbol: string }[]) {
  selectedMembers.value = rows
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

async function batchRemove() {
  const symbols = selectedMembers.value.map((m) => m.symbol)
  if (symbols.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定移除选中的 ${symbols.length} 个成员？`,
      '确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await store.removeMembers(poolId.value, symbols)
    ElMessage.success(`成功移除 ${symbols.length} 个成员`)
    selectedMembers.value = []
  } catch (e) {
    ElMessage.error('移除失败: ' + (e as Error).message)
  }
}

async function removeOne(symbol: string) {
  try {
    await store.removeMembers(poolId.value, [symbol])
    ElMessage.success('已移除')
  } catch (e) {
    ElMessage.error('移除失败: ' + (e as Error).message)
  }
}

function startEditMemo(row: { symbol: string; memo?: string | null }) {
  editingMemo.value = row.symbol
  memoDraft.value = row.memo ?? ''
  nextTick(() => {
    const inputs = document.querySelectorAll<HTMLInputElement>(
      '.el-table .el-input__inner',
    )
    inputs[inputs.length - 1]?.focus()
  })
}

async function saveMemo(symbol: string) {
  if (editingMemo.value !== symbol) return
  try {
    await store.updateMemberMemo(poolId.value, symbol, memoDraft.value)
  } catch (e) {
    ElMessage.error('更新失败: ' + (e as Error).message)
  } finally {
    editingMemo.value = null
  }
}

// ── 采集 K 线 ────────────────────────────────────────────────────────
function showCollectDialog() {
  collectDays.value = 365
  collectSource.value = undefined
  collectDialogVisible.value = true
}

async function startCollect() {
  collecting.value = true
  try {
    const result = await store.startKlineCollect(
      poolId.value,
      collectDays.value,
      collectSource.value,
    )
    ElMessage.success(result.message)
    collectDialogVisible.value = false
    activeTab.value = 'operations'
    // 启动进度轮询
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

// ── 工具 ─────────────────────────────────────────────────────────────
function formatDate(v?: string | null) {
  if (!v) return ''
  const d = new Date(v)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleDateString('zh-CN')
}

// ── 生命周期 ─────────────────────────────────────────────────────────
watch(
  poolId,
  async (id) => {
    if (id) {
      await store.fetchPoolDetail(id)
      await store.fetchOperations(id)
    }
  },
  { immediate: true },
)

onMounted(() => {
  stopProgressPolling()
})

// 切换 tab 时如果是 operations 则拉取最新
watch(activeTab, async (val) => {
  if (val === 'operations') {
    await store.fetchOperations(poolId.value)
  }
})
</script>

<style scoped>
.admin-page {
  min-height: 100%;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, monospace;
}
</style>
