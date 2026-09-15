<template>
  <div class="admin-page flex flex-col gap-5 h-full">
    <div class="flex items-center justify-between">
      <h2 class="page-title">📋 股票信息</h2>
      <el-button type="primary" :loading="syncing" @click="syncStocksHandler">
        <el-icon class="mr-1"><Refresh /></el-icon>
        同步最新数据
      </el-button>
    </div>

    <!-- 搜索 + 筛选卡 -->
    <el-card shadow="never">
      <el-form :inline="true" class="!flex !flex-wrap !items-center !gap-x-3 !gap-y-2 !m-0">
        <div class="btn-group">
          <el-input
            v-model="filters.q"
            placeholder="代码 / 名称 / 拼音"
            clearable
            style="width: 240px"
            :prefix-icon="Search"
            @input="onSearchInput"
            @clear="onFilterChange"
          />
        </div>

        <div class="search-group">
          <el-select
            v-model="filters.industry"
            placeholder="行业"
            clearable
            style="width: 130px"
            @change="onFilterChange"
          >
            <el-option
              v-for="v in meta.industries"
              :key="v"
              :label="v"
              :value="v"
            />
          </el-select>

          <el-select
            v-model="filters.market"
            placeholder="市场"
            clearable
            style="width: 130px"
            @change="onFilterChange"
          >
            <el-option
              v-for="v in meta.markets"
              :key="v"
              :label="v"
              :value="v"
            />
          </el-select>

          <el-select
            v-model="filters.exchange"
            placeholder="交易所"
            clearable
            style="width: 110px"
            @change="onFilterChange"
          >
            <el-option label="上交所" value="SSE" />
            <el-option label="深交所" value="SZSE" />
            <el-option label="北交所" value="BSE" />
          </el-select>

          <el-select
            v-model="filters.is_hs"
            placeholder="沪深港通"
            clearable
            style="width: 110px"
            @change="onFilterChange"
          >
            <el-option label="否" value="N" />
            <el-option label="沪股通" value="H" />
            <el-option label="深股通" value="S" />
          </el-select>

          <el-select
            v-model="filters.list_status"
            placeholder="状态"
            style="width: 110px"
            @change="onFilterChange"
          >
            <el-option label="上市" value="L" />
            <el-option label="退市" value="D" />
            <el-option label="暂停上市" value="P" />
            <el-option label="全部" value="" />
          </el-select>

          <el-button v-if="hasActiveFilters" type="danger" link @click="resetFilters">
            重置
          </el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 列表 -->
    <el-card shadow="never" class="flex-1">
      <div class="flex items-center justify-between mb-3">
        <div class="text-sm text-gray-600">
          已选 <span class="font-semibold text-blue-600">{{ selectedStocks.length }}</span> 只股票
          <el-button
            v-if="selectedStocks.length > 0"
            text
            type="primary"
            size="small"
            @click="clearSelection"
          >
            清除选择
          </el-button>
        </div>
        <div class="flex gap-2">
          <el-button
            type="success"
            :disabled="selectedStocks.length === 0"
            @click="showAddToPoolDialog"
          >
            <el-icon class="mr-1"><Folder /></el-icon>
            加入操作池
          </el-button>
          <el-button type="primary" :loading="syncing" @click="syncStocksHandler">
            <el-icon class="mr-1"><Refresh /></el-icon>
            同步最新数据
          </el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="stocks"
        stripe
        height="calc(100vh - 400px)"
        highlight-current-row
        empty-text="没有匹配的股票"
        @row-click="selectStock"
        @selection-change="onTableSelectionChange"
      >
        <el-table-column type="selection" width="50" :selectable="rowSelectable" />
        <el-table-column prop="symbol" label="代码" width="90" fixed>
          <template #default="{ row }">
            <span class="mono font-semibold">{{ row.symbol }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="100" fixed>
          <template #default="{ row }">
            <span class="font-medium">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="已加入池" min-width="160">
          <template #default="{ row }">
            <div v-if="getStockPools(row.symbol).length > 0" class="flex flex-wrap gap-1">
              <el-tag
                v-for="p in getStockPools(row.symbol).slice(0, 3)"
                :key="p.id"
                size="small"
                :type="poolTypeTag(p.pool_type) as 'primary' | 'success' | 'warning' | 'info'"
                effect="plain"
                @click.stop="goToPool(p.id)"
                class="cursor-pointer"
              >
                {{ p.name }}
              </el-tag>
              <el-tooltip
                v-if="getStockPools(row.symbol).length > 3"
                :content="getStockPools(row.symbol).slice(3).map(p => p.name).join(', ')"
                placement="top"
              >
                <span class="text-xs text-gray-500">
                  +{{ getStockPools(row.symbol).length - 3 }}
                </span>
              </el-tooltip>
            </div>
            <span v-else class="text-xs text-gray-400">未加入</span>
          </template>
        </el-table-column>
        <el-table-column prop="ts_code" label="TS代码" width="100">
          <template #default="{ row }">
            <span class="mono text-gray-500 text-xs">{{ row.ts_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="exchange" label="交易所" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="exchangeType(row.exchange)" effect="plain">
              {{ exchangeLabel(row.exchange) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="market" label="市场" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="marketType(row.market)" effect="light">
              {{ row.market || '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="industry" label="行业" min-width="120">
          <template #default="{ row }">
            {{ row.industry || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="area" label="地域" width="80">
          <template #default="{ row }">
            {{ row.area || '—' }}
          </template>
        </el-table-column>
        <el-table-column label="上市日期" width="110">
          <template #default="{ row }">{{ formatDate(row.list_date) }}</template>
        </el-table-column>
        <el-table-column label="沪深港通" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_hs === 'H'" type="danger" size="small">沪</el-tag>
            <el-tag v-else-if="row.is_hs === 'S'" type="success" size="small">深</el-tag>
            <span v-else class="text-gray-400 text-xs">—</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-row justify="end" class="mt-4">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </el-row>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailVisible"
      :title="selectedStock?.name || '股票详情'"
      size="400px"
      direction="rtl"
    >
      <template v-if="selectedStock">
        <div class="px-1">
          <div class="detail-header">
            <div class="text-xl font-bold text-gray-900">
              {{ selectedStock.symbol }}
              <el-tag size="small" class="ml-2">{{ selectedStock.name }}</el-tag>
            </div>
            <div class="text-xs text-gray-500 mt-1">
              {{ selectedStock.ts_code }} · {{ selectedStock.market }}
            </div>
          </div>

          <el-descriptions :column="1" border class="mt-4">
            <el-descriptions-item label="TS代码">{{ selectedStock.ts_code }}</el-descriptions-item>
            <el-descriptions-item label="交易所">{{ exchangeLabel(selectedStock.exchange) }}</el-descriptions-item>
            <el-descriptions-item label="市场">{{ selectedStock.market || '—' }}</el-descriptions-item>
            <el-descriptions-item label="行业">{{ selectedStock.industry || '—' }}</el-descriptions-item>
            <el-descriptions-item label="地域">{{ selectedStock.area || '—' }}</el-descriptions-item>
            <el-descriptions-item label="上市日期">{{ formatDate(selectedStock.list_date) }}</el-descriptions-item>
            <el-descriptions-item label="退市日期">{{ formatDate(selectedStock.delist_date) || '—' }}</el-descriptions-item>
            <el-descriptions-item label="实控人">{{ selectedStock.act_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="企业性质">{{ selectedStock.act_ent_type || '—' }}</el-descriptions-item>
            <el-descriptions-item label="英文名">{{ selectedStock.enname || '—' }}</el-descriptions-item>
            <el-descriptions-item label="拼音缩写">{{ selectedStock.cnspell || '—' }}</el-descriptions-item>
          </el-descriptions>

          <div class="mt-6 space-y-2">
            <!-- 加入操作池 -->
            <el-dropdown
              trigger="click"
              :disabled="poolStore.pools.length === 0"
            >
              <el-button type="success" class="w-full">
                <el-icon class="mr-1"><Folder /></el-icon>
                加入操作池
                <el-icon class="ml-1"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="pool in activePools"
                    :key="pool.id"
                    :data-pool-id="pool.id"
                    :disabled="currentStockInPool(pool.id as number)"
                    @click="(e: Event) => onPoolDropdownClick(e, pool.id as number)"
                  >
                    {{ pool.icon || '📂' }} {{ pool.name }}
                    <span v-if="currentStockInPool(pool.id)" class="text-xs text-green-500 ml-2">已在池中</span>
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="onNewPoolClick">
                    <el-icon><Plus /></el-icon> 新建池...
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>

            <!-- 跳转操作池（采集 K 线） -->
            <el-button
              type="primary"
              class="w-full"
              @click="goToPoolPage"
            >
              <el-icon class="mr-1"><FolderOpened /></el-icon>
              在操作池中采集 K 线
            </el-button>
          </div>
        </div>
      </template>
    </el-drawer>

    <!-- 加入操作池弹窗 -->
    <el-dialog
      v-model="addToPoolDialogVisible"
      :title="`将 ${selectedStocks.length} 只股票加入操作池`"
      width="520px"
      @close="resetAddToPool"
    >
      <div v-if="createNewPool" class="space-y-3">
        <el-form label-width="80px">
          <el-form-item label="池名称" required>
            <el-input
              v-model="newPoolName"
              placeholder="如：银行股组合"
              maxlength="64"
              clearable
            />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="newPoolType" style="width: 100%">
              <el-option label="⭐ 自选股" value="watchlist" />
              <el-option label="🏦 行业" value="industry" />
              <el-option label="📈 策略" value="strategy" />
              <el-option label="📂 自定义" value="custom" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <div v-else class="space-y-3">
        <p class="text-sm text-gray-600">
          选中 <strong>{{ selectedStocks.length }}</strong> 只股票：
          <span class="mono">{{ selectedStocks.map(s => s.symbol).slice(0, 10).join(', ') }}{{ selectedStocks.length > 10 ? '...' : '' }}</span>
        </p>

        <el-form label-width="80px">
          <el-form-item label="选择操作池" required>
            <el-select
              v-model="selectedPoolId"
              placeholder="请选择一个操作池"
              style="width: 100%"
              filterable
            >
              <el-option
                v-for="pool in activePools"
                :key="pool.id"
                :label="`${pool.icon || '📂'} ${pool.name} (${pool.member_count}只)`"
                :value="pool.id"
              />
            </el-select>
          </el-form-item>
        </el-form>

        <div class="text-xs text-gray-400 flex items-center justify-between">
          <span>
            {{ selectedPoolId ? `已选: ${getPoolName(selectedPoolId)}` : '请选择操作池' }}
          </span>
          <el-button
            text
            type="primary"
            size="small"
            @click="createNewPool = true"
          >
            + 新建池
          </el-button>
        </div>
      </div>

      <template #footer>
        <div class="flex gap-2">
          <el-button @click="addToPoolDialogVisible = false">取消</el-button>
          <el-button
            v-if="createNewPool"
            text
            type="primary"
            @click="createNewPool = false; selectedPoolId = null"
          >
            返回选择池
          </el-button>
          <el-button
            type="primary"
            :loading="addToPoolLoading"
            :disabled="!canSubmitPool"
            class="flex-1"
            @click="submitAddToPool"
          >
            {{ createNewPool ? '创建并加入' : '确认加入' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Download, FolderOpened, Folder, ArrowDown, Plus } from '@element-plus/icons-vue'
import {
  queryStocks,
  getStockMeta,
  syncStocks,
} from '@/views/stock-info/api'
import { usePoolStore } from '@/stores/pool'
import type { StockInfo, StockMeta, StockQueryParams } from '@/views/stock-info/api'
import type { Pool } from '@/views/stock-pool/api'

// ── State ───────────────────────────────────────────────
const router = useRouter()
const stocks = ref<StockInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const syncing = ref(false)
const detailVisible = ref(false)
const selectedStock = ref<StockInfo | null>(null)
const meta = ref<StockMeta>({ industries: [], markets: [], exchanges: [] })
const poolStore = usePoolStore()

// 选中股票
const selectedStocks = ref<StockInfo[]>([])

// 加入池弹窗
const addToPoolDialogVisible = ref(false)
const addToPoolLoading = ref(false)
const selectedPoolId = ref<number | null>(null)
const newPoolName = ref('')
const createNewPool = ref(false)
const newPoolType = ref<'watchlist' | 'industry' | 'strategy' | 'custom'>('custom')

// 选中股票所在池的缓存（symbol -> Pool[]）
const symbolPoolsMap = ref<Record<string, Pool[]>>({})

const filters = ref({
  q: '' as string,
  industry: '' as string,
  market: '' as string,
  exchange: '' as string,
  is_hs: '' as string,
  list_status: 'L' as string,
})

const hasActiveFilters = computed(
  () =>
    !!filters.value.q ||
    !!filters.value.industry ||
    !!filters.value.market ||
    !!filters.value.exchange ||
    !!filters.value.is_hs ||
    filters.value.list_status !== 'L'
)

// ── 防抖搜索 ─────────────────────────────────────────────
let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadStocks()
  }, 300)
}

function onFilterChange() {
  page.value = 1
  loadStocks()
}

function resetFilters() {
  filters.value = {
    q: '',
    industry: '',
    market: '',
    exchange: '',
    is_hs: '',
    list_status: 'L',
  }
  page.value = 1
  loadStocks()
}

// ── 加载数据 ─────────────────────────────────────────────
async function loadStocks() {
  loading.value = true
  try {
    const params: StockQueryParams = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filters.value.q)          params.q          = filters.value.q
    if (filters.value.industry)   params.industry    = filters.value.industry
    if (filters.value.market)     params.market      = filters.value.market
    if (filters.value.exchange)   params.exchange    = filters.value.exchange
    if (filters.value.is_hs)      params.is_hs       = filters.value.is_hs
    if (filters.value.list_status) params.list_status = filters.value.list_status

    const data = await queryStocks(params)
    stocks.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    stocks.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  try {
    meta.value = await getStockMeta()
  } catch (_) {
    /* 静默失败 */
  }
}

async function syncStocksHandler() {
  syncing.value = true
  try {
    const res = await syncStocks()
    ElMessage.success(`同步成功，共 ${res.synced_count ?? '—'} 只股票`)
    await loadMeta()
    await loadStocks()
  } catch (e) {
    ElMessage.error('同步失败: ' + (e as Error).message)
  } finally {
    syncing.value = false
  }
}

// ── 详情抽屉 ─────────────────────────────────────────────
function selectStock(row: StockInfo) {
  selectedStock.value = row
  detailVisible.value = true
}

// ── 分页 ────────────────────────────────────────────────
function onPageChange(p: number) {
  page.value = p
  clearSelection()
  loadStocks()
}
function onPageSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  clearSelection()
  loadStocks()
}

function onTableSelectionChange(rows: StockInfo[]) {
  selectedStocks.value = rows
}

// ── 工具 ────────────────────────────────────────────────
function formatDate(v?: string) {
  if (!v) return ''
  return String(v).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

function exchangeLabel(v?: string) {
  const map: Record<string, string> = { SSE: '上交所', SZSE: '深交所', BSE: '北交所' }
  return map[v || ''] || v || '—'
}

function exchangeType(v?: string): 'primary' | 'success' | 'warning' | 'info' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
    SSE: 'primary',
    SZSE: 'success',
    BSE: 'warning',
  }
  return map[v || ''] || 'info'
}

function marketType(v?: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  if (!v) return 'info'
  if (v.includes('科创')) return 'danger'
  if (v.includes('创业')) return 'warning'
  if (v.includes('北交')) return 'success'
  return 'primary'
}

// ── 生命周期 ─────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadMeta(), loadStocks(), poolStore.fetchPools()])
  // 预加载所有股票所在池
  await loadAllStockPools()
})

// ═══════════════════════════════════════════════════════════════════════════════
//  操作池集成
// ═══════════════════════════════════════════════════════════════════════════════

// 仅显示未归档的池
const activePools = computed(() =>
  poolStore.pools.filter((p) => !p.is_archived)
)

function rowSelectable(_row: StockInfo, _idx: number) {
  return true
}

function clearSelection() {
  selectedStocks.value = []
}

function getStockPools(symbol: string): Pool[] {
  return symbolPoolsMap.value[symbol] ?? []
}

function getPoolName(poolId: number): string {
  return poolStore.pools.find((p) => p.id === poolId)?.name ?? ''
}

const canSubmitPool = computed(() => {
  if (createNewPool.value) {
    return newPoolName.value.trim().length > 0
  }
  return selectedPoolId.value !== null
})

function showAddToPoolDialog() {
  if (selectedStocks.value.length === 0) return
  selectedPoolId.value = poolStore.defaultPool?.id ?? null
  addToPoolDialogVisible.value = true
}

function resetAddToPool() {
  createNewPool.value = false
  newPoolName.value = ''
  newPoolType.value = 'custom'
  selectedPoolId.value = null
}

async function loadAllStockPools() {
  // 对当前页所有股票并行查询所在池
  const symbols = stocks.value.map((s) => s.symbol)
  await Promise.all(
    symbols.map(async (symbol) => {
      try {
        const result = await poolStore.findPoolsBySymbol(symbol)
        symbolPoolsMap.value[symbol] = result.pools
      } catch {
        symbolPoolsMap.value[symbol] = []
      }
    })
  )
}

async function submitAddToPool() {
  if (!canSubmitPool.value) return

  addToPoolLoading.value = true
  try {
    const symbols = selectedStocks.value.map((s) => s.symbol)
    let targetPoolId: number

    if (createNewPool.value) {
      // 创建新池
      const newPool = await poolStore.createPool({
        name: newPoolName.value.trim(),
        pool_type: newPoolType.value,
      })
      targetPoolId = typeof newPool.id === 'number' ? newPool.id : NaN
    } else {
      // 必须用 .value 取 ref 内的原始数字；裸 ref 对象 typeof 为 'object'
      targetPoolId = typeof selectedPoolId.value === 'number'
        ? selectedPoolId.value
        : NaN
    }

    if (Number.isNaN(targetPoolId)) {
      ElMessage.error('池 ID 无效')
      addToPoolLoading.value = false
      return
    }

    const result = await poolStore.addMembers(targetPoolId, symbols)
    ElMessage.success(
      `已成功添加 ${result.total_added} 只，跳过 ${result.total_skipped} 只`
    )

    // 更新缓存
    for (const sym of symbols) {
      const pools = await poolStore.findPoolsBySymbol(sym)
      symbolPoolsMap.value[sym] = pools.pools
    }

    addToPoolDialogVisible.value = false
    clearSelection()

    // 提示可去操作池
    const targetPool = poolStore.pools.find((p) => p.id === targetPoolId)
    if (targetPool) {
      ElMessage({
        type: 'success',
        message: `已加入「${targetPool.name}」，点击跳转到操作池`,
        duration: 4000,
        onClose: () => router.push(`/home/pool/${targetPoolId}`),
      })
    }
  } catch (e) {
    ElMessage.error('加入失败: ' + (e as Error).message)
  } finally {
    addToPoolLoading.value = false
  }
}

function goToPool(poolId: number) {
  router.push({ path: `/home/pool/${poolId}` })
}

function goToPoolPage() {
  if (selectedStock.value) {
    // 从详情抽屉：用当前选中的股票跳转到默认池
    const defaultId = poolStore.defaultPool?.id ?? poolStore.pools[0]?.id
    if (defaultId) {
      router.push({ path: `/home/pool/${defaultId}` })
    } else {
      router.push({ path: '/home/pool' })
    }
  }
}

// ── 详情抽屉中的池操作 ─────────────────────────────────────

function currentStockInPool(poolId: unknown): boolean {
  if (!selectedStock.value) return false
  const id = typeof poolId === 'number' ? poolId : null
  if (id === null) return false
  return symbolPoolsMap.value[selectedStock.value.symbol]?.some((p) => p.id === id) ?? false
}

// 点击已有池项 → 直接加入（绕过 el-dropdown command 机制）
function onPoolDropdownClick(_e: Event, poolId: unknown) {
  // 强制转为原始数字，防御 Vue Proxy 包装
  const id = poolId == null ? NaN : Number(poolId)
  addCurrentToPool(id)
}

// 点击"新建池"项
function onNewPoolClick() {
  if (!selectedStock.value) return
  selectedStocks.value = [selectedStock.value]
  createNewPool.value = true
  newPoolName.value = ''
  addToPoolDialogVisible.value = true
}

async function addCurrentToPool(poolId: unknown) {
  if (!selectedStock.value) return

  // 安全转为数字（Number() 会强制 unwrap Vue Proxy）
  const id = typeof poolId === 'number' && !Number.isNaN(poolId)
    ? poolId
    : NaN
  if (Number.isNaN(id)) {
    console.error('[addCurrentToPool] poolId 无效:', poolId, typeof poolId)
    ElMessage.error('池 ID 无效')
    return
  }

  try {
    const result = await poolStore.addMembers(id, [selectedStock.value.symbol])
    // 更新缓存
    const pools = await poolStore.findPoolsBySymbol(selectedStock.value.symbol)
    symbolPoolsMap.value[selectedStock.value.symbol] = pools.pools
    ElMessage.success(
      result.total_added > 0
        ? `已加入「${poolStore.pools.find(p => p.id === id)?.name}」`
        : `${selectedStock.value.symbol} 已在该池中`
    )
  } catch (e) {
    ElMessage.error('加入失败: ' + (e as Error).message)
  }
}

// 池类型标签
function poolTypeTag(type: string) {
  const map: Record<string, string> = {
    watchlist: 'warning',
    industry: 'success',
    strategy: 'primary',
    custom: 'info',
  }
  return map[type] || 'info'
}
</script>

<style scoped>
.admin-page {
  min-height: 100%;
}

.detail-header {
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
</style>
