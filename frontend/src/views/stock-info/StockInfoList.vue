<template>
  <div class="stock-info-page">
  <PageWrapper>
    <!-- ═══ Top Area — Row 1: 标题 ═══ -->
    <template #title>📋 股票信息</template>

    <!-- ═══ Top Area — Row 2: 搜索 + 操作按钮 ═══ -->
    <template #toolbar>
      <div class="toolbar-row">
        <!-- 左侧：主搜索 + 高级展开 -->
        <div class="toolbar-search">
          <el-input
            v-model="filters.q"
            placeholder="代码 / 名称 / 拼音"
            clearable
            style="width: 260px"
            :prefix-icon="Search"
            @input="onSearchInput"
            @clear="onFilterChange"
          />
          <el-button
            :type="showAdvanced ? 'primary' : 'default'"
            :text="!showAdvanced"
            @click="showAdvanced = !showAdvanced"
          >
            <el-icon class="mr-1"><ArrowDown v-if="!showAdvanced" /><ArrowUp v-else /></el-icon>
            高级筛选
            <el-badge v-if="advancedFilterCount > 0 && !showAdvanced" :value="advancedFilterCount" class="ml-1" />
          </el-button>
          <el-button v-if="hasActiveFilters" type="danger" link @click="resetFilters">重置</el-button>
        </div>

        <!-- 右侧：操作按钮 -->
        <div class="toolbar-actions">
          <el-button type="success" :disabled="selectedStocks.length === 0" @click="addToPoolVisible = true">
            <el-icon class="mr-1"><Folder /></el-icon>
            加入操作池
          </el-button>
          <el-button type="primary" :loading="syncing" @click="syncStocksHandler">
            <el-icon class="mr-1"><Refresh /></el-icon>
            同步最新数据
          </el-button>
        </div>
      </div>

      <!-- 高级筛选展开区（grid-rows 动画，避免 max-height 重排） -->
      <div class="advanced-wrapper" :class="{ open: showAdvanced }">
        <div class="advanced-filters">
          <el-select v-model="filters.industry" placeholder="行业" clearable style="width: 130px" @change="onFilterChange">
            <el-option v-for="v in meta.industries" :key="v" :label="v" :value="v" />
          </el-select>
          <el-select v-model="filters.market" placeholder="市场" clearable style="width: 130px" @change="onFilterChange">
            <el-option v-for="v in meta.markets" :key="v" :label="v" :value="v" />
          </el-select>
          <el-select v-model="filters.exchange" placeholder="交易所" clearable style="width: 110px" @change="onFilterChange">
            <el-option label="上交所" value="SSE" />
            <el-option label="深交所" value="SZSE" />
            <el-option label="北交所" value="BSE" />
          </el-select>
          <el-select v-model="filters.is_hs" placeholder="沪深港通" clearable style="width: 110px" @change="onFilterChange">
            <el-option label="否" value="N" />
            <el-option label="沪股通" value="H" />
            <el-option label="深股通" value="S" />
          </el-select>
          <el-select v-model="filters.list_status" placeholder="状态" style="width: 110px" @change="onFilterChange">
            <el-option label="上市" value="L" />
            <el-option label="退市" value="D" />
            <el-option label="暂停上市" value="P" />
            <el-option label="全部" value="" />
          </el-select>
          <el-select v-model="filters.st_filter" placeholder="ST筛选" clearable style="width: 110px" @change="onFilterChange">
            <el-option label="排除ST" value="exclude" />
            <el-option label="仅ST" value="only" />
          </el-select>
          <el-input-number
            v-model="filters.min_total_mv"
            placeholder="最低市值(亿)"
            :min="0"
            :precision="0"
            :controls="false"
            style="width: 130px"
            @change="onFilterChange"
          />
        </div>
      </div>
    </template>

    <!-- ═══ Middle Area ═══ -->
    <!-- 选中提示 -->
    <div v-if="selectedStocks.length > 0" class="selection-bar">
      已选 <span class="font-semibold text-blue-600">{{ selectedStocks.length }}</span> 只股票
      <el-button text type="primary" size="small" @click="clearSelection">清除选择</el-button>
    </div>

    <!-- 表格 -->
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="stocks"
      stripe
      class="flex-1"
      highlight-current-row
      empty-text="没有匹配的股票"
      row-key="symbol"
      @row-click="openDetailDrawer"
      @selection-change="onSelectionChange"
    >
      <!-- 展开第二行（K线图）：点击 chevron 触发，行点击不会触发展开 -->
      <el-table-column type="expand" width="48">
        <template #default="{ row }">
          <StockExpandRow :symbol="row.symbol" />
        </template>
      </el-table-column>

      <!-- 固定列（左侧钉住） -->
      <el-table-column type="selection" width="50" fixed="left" />
      <el-table-column prop="symbol" label="代码" width="90" fixed="left">
        <template #default="{ row }">
          <span class="mono font-semibold">{{ row.symbol }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" width="100" fixed="left">
        <template #default="{ row }">
          <span class="font-medium">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="已加入池" width="160" fixed="left">
        <template #default="{ row }">
          <div v-if="getStockPools(row.symbol).length > 0" class="flex flex-wrap gap-1">
            <el-tag
              v-for="p in getStockPools(row.symbol).slice(0, 3)"
              :key="p.pool_id"
              size="small"
              :type="poolTypeTag(p.pool_type) as 'primary' | 'success' | 'warning' | 'info'"
              effect="plain"
              class="cursor-pointer"
              @click.stop="router.push(`/home/pool/${p.pool_id}`)"
            >
              {{ p.name }}
            </el-tag>
            <el-tooltip
              v-if="getStockPools(row.symbol).length > 3"
              :content="getStockPools(row.symbol).slice(3).map(p => p.name).join(', ')"
              placement="top"
            >
              <span class="text-xs text-gray-500">+{{ getStockPools(row.symbol).length - 3 }}</span>
            </el-tooltip>
          </div>
          <span v-else class="text-xs text-gray-400">未加入</span>
        </template>
      </el-table-column>

      <!-- 滚动列（按重要性从左到右排列） -->
      <el-table-column label="最新价" width="90" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.latest_close != null" class="mono font-medium">{{ row.latest_close.toFixed(2) }}</span>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column label="总市值" width="110" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.total_mv != null" class="mono">{{ formatMv(row.total_mv) }}</span>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column label="PE(TTM)市盈率" width="120" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.pe_ttm != null" :class="peClass(row.pe_ttm)" class="mono">{{ row.pe_ttm.toFixed(1) }}</span>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column label="净利润率%" width="100" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.profit_margin != null" :class="row.profit_margin >= 0 ? 'text-red-500' : 'text-green-600'" class="mono">{{ row.profit_margin.toFixed(1) }}%</span>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="industry" label="行业" width="120">
        <template #default="{ row }">{{ row.industry || '—' }}</template>
      </el-table-column>
      <el-table-column prop="market" label="市场" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="marketType(row.market)" effect="light">
            {{ row.market || '—' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="exchange" label="交易所" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="exchangeType(row.exchange)" effect="plain">
            {{ exchangeLabel(row.exchange) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上市日期" width="110">
        <template #default="{ row }">{{ formatDate(row.list_date) }}</template>
      </el-table-column>
      <el-table-column prop="area" label="地域" width="80">
        <template #default="{ row }">{{ row.area || '—' }}</template>
      </el-table-column>
      <el-table-column label="沪深港通" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_hs === 'H'" type="danger" size="small">沪</el-tag>
          <el-tag v-else-if="row.is_hs === 'S'" type="success" size="small">深</el-tag>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="act_name" label="实控人" width="120">
        <template #default="{ row }">
          <span class="text-sm">{{ row.act_name || '—' }}</span>
        </template>
      </el-table-column>

      <!-- 行末「详情」按钮列已移除：改为整行 hover pointer + chevron 触发展开/抽屉 -->
    </el-table>

    <!-- ═══ Bottom Area ═══ -->
    <template #bottom>
      <el-row justify="end">
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
    </template>
  </PageWrapper>

  <AddToPoolDialog
    v-model="addToPoolVisible"
    :stocks="selectedStocks"
    @done="onPoolDone"
  />

  <!-- 详情抽屉 -->
  <StockDetailDrawer
    v-model="detailDrawerVisible"
    :stock="detailDrawerStock"
    @add-to-pool="onDrawerAddToPool"
    @go-analysis="onDrawerGoAnalysis"
    @close="closeDetailDrawer"
  />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Search, Refresh, Folder, ArrowDown, ArrowUp,
} from '@element-plus/icons-vue'

import PageWrapper from '@/components/PageWrapper.vue'
import StockExpandRow from './components/StockExpandRow.vue'
import AddToPoolDialog from './components/AddToPoolDialog.vue'
import StockDetailDrawer from './components/StockDetailDrawer.vue'
import { useStockDetailDrawer } from './composables/useStockDetailDrawer'
import {
  queryStocks,
  getStockMeta,
  syncStocks,
} from '@/views/stock-info/api'
import type {
  StockInfo,
  StockMeta,
  StockQueryParams,
  PoolMembership,
} from '@/views/stock-info/api'

const router = useRouter()

// ── 列表状态 ──────────────────────────────────────────────
const stocks = ref<StockInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const syncing = ref(false)
const meta = ref<StockMeta>({ industries: [], markets: [], exchanges: [] })
const selectedStocks = ref<StockInfo[]>([])

// ── 弹窗 / 抽屉 ─────────────────────────────────────────
const tableRef = ref()
const addToPoolVisible = ref(false)

// 🆕 详情抽屉（composable 接管状态）
const {
  visible: detailDrawerVisible,
  currentStock: detailDrawerStock,
  open: openDetailDrawer,
  close: closeDetailDrawer,
} = useStockDetailDrawer()

// ── 筛选 ──────────────────────────────────────────────────
const showAdvanced = ref(false)

const filters = ref({
  q: '',
  industry: '',
  market: '',
  exchange: '',
  is_hs: '',
  list_status: 'L',
  st_filter: '' as string,
  min_total_mv: undefined as number | undefined,
})

const advancedFilterCount = computed(() => {
  let count = 0
  if (filters.value.industry) count++
  if (filters.value.market) count++
  if (filters.value.exchange) count++
  if (filters.value.is_hs) count++
  if (filters.value.list_status !== 'L') count++
  if (filters.value.st_filter) count++
  if (filters.value.min_total_mv != null) count++
  return count
})

const hasActiveFilters = computed(() =>
  !!filters.value.q || advancedFilterCount.value > 0
)

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; loadStocks() }, 300)
}

function onFilterChange() {
  page.value = 1
  loadStocks()
}

function resetFilters() {
  filters.value = { q: '', industry: '', market: '', exchange: '', is_hs: '', list_status: 'L', st_filter: '', min_total_mv: undefined }
  page.value = 1
  loadStocks()
}

// ── 数据加载 ──────────────────────────────────────────────
/**
 * 加载股票面板列表（with_pools=true + with_concepts=true）
 *
 * - pools：内嵌池信息，避免 N+1
 * - concepts：内嵌概念简略版（详情抽屉预热用），需后端 ConceptFetcher 已注册
 */
async function loadStocks() {
  loading.value = true
  try {
    const params: StockQueryParams = {
      page: page.value,
      page_size: pageSize.value,
      with_pools: true,    // 一次性返回所属池
      with_concepts: true, // 详情抽屉预热（仅简略 ConceptBrief[]）
    }
    if (filters.value.q) params.q = filters.value.q
    if (filters.value.industry) params.industry = filters.value.industry
    if (filters.value.market) params.market = filters.value.market
    if (filters.value.exchange) params.exchange = filters.value.exchange
    if (filters.value.is_hs) params.is_hs = filters.value.is_hs
    if (filters.value.list_status) params.list_status = filters.value.list_status
    if (filters.value.st_filter === 'exclude') params.exclude_st = true
    else if (filters.value.st_filter === 'only') params.exclude_st = false
    if (filters.value.min_total_mv != null) params.min_total_mv = filters.value.min_total_mv * 10000

    const data = await queryStocks(params)
    stocks.value = data.items || []
    total.value = data.total || 0
  } catch {
    stocks.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  try { meta.value = await getStockMeta() } catch { /* silent */ }
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

// ── 分页 ──────────────────────────────────────────────────
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

// ── 选择 ──────────────────────────────────────────────────
function onSelectionChange(rows: StockInfo[]) {
  selectedStocks.value = rows
}

function clearSelection() {
  selectedStocks.value = []
}

// ── 详情抽屉事件 ────────────────────────────────────────
function onDrawerAddToPool() {
  // 把当前股票作为唯一选中项
  if (detailDrawerStock.value) {
    selectedStocks.value = [detailDrawerStock.value]
    addToPoolVisible.value = true
    closeDetailDrawer()
  }
}

function onDrawerGoAnalysis() {
  if (detailDrawerStock.value) {
    router.push(`/home/stock/${detailDrawerStock.value.symbol}/analysis`)
    closeDetailDrawer()
  }
}

// ── 池操作完成回调 ────────────────────────────────────────
/**
 * 加池完成后：直接重载列表（池已内嵌到 row.pools，无需额外加载）
 */
async function onPoolDone() {
  clearSelection()
  await loadStocks()
}

// ── 工具函数 ──────────────────────────────────────────────
/**
 * 直接从 row.pools 读取所属池信息（由后端 with_pools=true 一次性下发）
 */
function getStockPools(symbol: string): PoolMembership[] {
  const stock = stocks.value.find(s => s.symbol === symbol)
  return stock?.pools ?? []
}

function formatDate(v?: string) {
  if (!v) return ''
  return String(v).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

function formatMv(v: number): string {
  if (v >= 10000_0000) return (v / 10000_0000).toFixed(1) + ' 万亿'
  if (v >= 10000) return (v / 10000).toFixed(1) + ' 亿'
  return v.toFixed(0) + ' 万'
}

function peClass(v: number): string {
  if (v < 0) return 'text-gray-400'
  if (v <= 20) return 'text-green-600'
  if (v <= 50) return 'text-orange-500'
  return 'text-red-500'
}

function exchangeLabel(v?: string) {
  const map: Record<string, string> = { SSE: '上交所', SZSE: '深交所', BSE: '北交所' }
  return map[v || ''] || v || '—'
}

function exchangeType(v?: string): 'primary' | 'success' | 'warning' | 'info' {
  return ({ SSE: 'primary', SZSE: 'success', BSE: 'warning' } as const)[v || ''] || 'info'
}

function marketType(v?: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  if (!v) return 'info'
  if (v.includes('科创')) return 'danger'
  if (v.includes('创业')) return 'warning'
  if (v.includes('北交')) return 'success'
  return 'primary'
}

function poolTypeTag(type: string) {
  return ({ watchlist: 'warning', industry: 'success', strategy: 'primary', custom: 'info' } as const)[type] || 'info'
}

// ── 生命周期 ──────────────────────────────────────────────
onMounted(async () => {
  // 🆕 不再调用 poolStore.fetchPools 和 loadAllStockPools
  // 池信息由 loadStocks(with_pools=true) 一次性下发，零 N+1
  // 概念简略版由 with_concepts=true 一次性下发，供详情抽屉预热
  await Promise.all([loadMeta(), loadStocks()])
})
</script>

<style scoped>
.stock-info-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

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

/* 高级筛选：grid-rows 展开动画（不触发 layout 重排） */
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
  background: var(--color-admin-bg);
  border-radius: 8px;
  transition: padding 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.advanced-wrapper.open > .advanced-filters {
  padding: 12px 16px;
}

.selection-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  color: #475569;
  background: #eff6ff;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
}

/* 表格数据行 hover：强调可点击 */
:deep(.el-table__row) {
  cursor: pointer;
  transition: background-color 0.18s ease;
}

:deep(.el-table__row:hover > td) {
  background-color: #f0f9ff !important;
}

/* 展开按钮（chevron）悬浮强化：scale + 阴影 + 渐变背景 */
:deep(.el-table__expand-icon) {
  position: relative;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              background-color 0.2s ease;
  border-radius: 50%;
}

:deep(.el-table__expand-icon .el-icon) {
  transition: color 0.2s ease;
}

:deep(.el-table__expand-icon:hover) {
  transform: scale(1.4);
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  box-shadow:
    0 4px 12px rgba(59, 130, 246, 0.35),
    0 0 0 3px rgba(99, 102, 241, 0.15);
}

:deep(.el-table__expand-icon:hover .el-icon),
:deep(.el-table__expand-icon.expanded:hover .el-icon) {
  color: #ffffff;
}

/* 展开态自身：轻微 scale，保持阴影反馈 */
:deep(.el-table__expand-icon.expanded) {
  transform: scale(1.1);
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  box-shadow:
    0 2px 8px rgba(59, 130, 246, 0.3),
    0 0 0 2px rgba(99, 102, 241, 0.12);
}

:deep(.el-table__expand-icon.expanded .el-icon) {
  color: #ffffff;
}
</style>
