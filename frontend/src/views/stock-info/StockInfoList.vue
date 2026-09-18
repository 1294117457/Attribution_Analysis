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
          <el-button :loading="syncingBasic" @click="syncDailyBasicHandler">
            <el-icon class="mr-1"><TrendCharts /></el-icon>
            同步估值
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
      :expand-row-keys="expandedRows"
      @row-click="toggleExpand"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="expand">
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
              :key="p.id"
              size="small"
              :type="poolTypeTag(p.pool_type) as 'primary' | 'success' | 'warning' | 'info'"
              effect="plain"
              class="cursor-pointer"
              @click.stop="router.push(`/home/pool/${p.id}`)"
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
      <el-table-column label="PE(TTM)" width="100" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.pe_ttm != null" :class="peClass(row.pe_ttm)" class="mono">{{ row.pe_ttm.toFixed(1) }}</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Folder, ArrowDown, ArrowUp, TrendCharts } from '@element-plus/icons-vue'

import PageWrapper from '@/components/PageWrapper.vue'
import StockExpandRow from './components/StockExpandRow.vue'
import AddToPoolDialog from './components/AddToPoolDialog.vue'
import { usePoolStore } from '@/stores/pool'
import {
  queryStocks,
  getStockMeta,
  syncStocks,
  syncDailyBasic,
} from '@/views/stock-info/api'
import type { StockInfo, StockMeta, StockQueryParams } from '@/views/stock-info/api'
import type { Pool } from '@/views/stock-pool/api'

const router = useRouter()
const poolStore = usePoolStore()

// ── 列表状态 ──────────────────────────────────────────────
const stocks = ref<StockInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const syncing = ref(false)
const syncingBasic = ref(false)
const meta = ref<StockMeta>({ industries: [], markets: [], exchanges: [] })
const selectedStocks = ref<StockInfo[]>([])
const symbolPoolsMap = ref<Record<string, Pool[]>>({})

// ── 展开行 / 弹窗 ────────────────────────────────────────
const tableRef = ref()
const expandedRows = ref<string[]>([])
const addToPoolVisible = ref(false)

// ── 筛选 ──────────────────────────────────────────────────
const showAdvanced = ref(false)

const filters = ref({
  q: '',
  industry: '',
  market: '',
  exchange: '',
  is_hs: '',
  list_status: 'L',
})

const advancedFilterCount = computed(() => {
  let count = 0
  if (filters.value.industry) count++
  if (filters.value.market) count++
  if (filters.value.exchange) count++
  if (filters.value.is_hs) count++
  if (filters.value.list_status !== 'L') count++
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
  filters.value = { q: '', industry: '', market: '', exchange: '', is_hs: '', list_status: 'L' }
  page.value = 1
  loadStocks()
}

// ── 数据加载 ──────────────────────────────────────────────
async function loadStocks() {
  loading.value = true
  try {
    const params: StockQueryParams = { page: page.value, page_size: pageSize.value }
    if (filters.value.q) params.q = filters.value.q
    if (filters.value.industry) params.industry = filters.value.industry
    if (filters.value.market) params.market = filters.value.market
    if (filters.value.exchange) params.exchange = filters.value.exchange
    if (filters.value.is_hs) params.is_hs = filters.value.is_hs
    if (filters.value.list_status) params.list_status = filters.value.list_status

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

async function syncDailyBasicHandler() {
  syncingBasic.value = true
  try {
    const res = await syncDailyBasic(3)
    ElMessage.success(res.message || `同步完成，共 ${res.synced_count} 条`)
    await loadStocks()
  } catch (e) {
    ElMessage.error('估值同步失败: ' + (e as Error).message)
  } finally {
    syncingBasic.value = false
  }
}

async function loadAllStockPools() {
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

// ── 展开行 ──────────────────────────────────────────────
function toggleExpand(row: StockInfo) {
  const idx = expandedRows.value.indexOf(row.symbol)
  if (idx >= 0) {
    expandedRows.value.splice(idx, 1)
  } else {
    expandedRows.value = [row.symbol]
  }
}

// ── 池操作完成回调 ────────────────────────────────────────
async function onPoolDone() {
  clearSelection()
  await loadAllStockPools()
}

// ── 工具函数 ──────────────────────────────────────────────
function getStockPools(symbol: string): Pool[] {
  return symbolPoolsMap.value[symbol] ?? []
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
  return ({ watchlist: 'warning', industry: 'success', strategy: 'primary', custom: 'info' })[type] || 'info'
}

// ── 生命周期 ──────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadMeta(), loadStocks(), poolStore.fetchPools()])
  await loadAllStockPools()
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
</style>
