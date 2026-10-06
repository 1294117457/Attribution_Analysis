<template>
  <div class="stock-info-page" :style="densityStyle">
  <PageWrapper>
    <!-- ═══ Top Area — Row 1: 标题 + 唯一折叠按钮 + 内联展开的密度设置 ═══ -->
    <template #title>
      <span class="page-title-text">📋 股票信息</span>

      <!-- 唯一折叠按钮：标题旁的"页面设置"开关 -->
      <el-tooltip
        :content="showDensityPanel ? '收起页面设置' : '页面设置（密度 / 字号）'"
        placement="bottom"
      >
        <button
          class="density-toggle"
          :class="{ active: showDensityPanel }"
          :aria-pressed="showDensityPanel"
          @click="showDensityPanel = !showDensityPanel"
        >
          <el-icon :size="14">
            <Setting />
          </el-icon>
        </button>
      </el-tooltip>

      <!-- 展开后才出现的内联面板：与标题同一行横排 -->
      <transition name="density-inline">
        <div v-if="showDensityPanel" class="density-inline">
          <span class="density-inline__label">⚙️ 页面设置</span>
          <span class="density-inline__divider"></span>

          <div class="density-inline__group">
            <span>页面</span>
            <el-slider v-model="pageDensity" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
            <span class="density-inline__value">{{ pageDensity.toFixed(2) }}</span>
          </div>

          <div class="density-inline__group">
            <span>顶部</span>
            <el-slider v-model="topDensityProxy" :min="0.6" :max="1.5" :step="0.05" :show-tooltip="false" />
            <span class="density-inline__value">{{ topDensityProxy.toFixed(2) }}</span>
          </div>

          <div class="density-inline__group">
            <span>表格</span>
            <el-slider v-model="middleDensityProxy" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
            <span class="density-inline__value">{{ middleDensityProxy.toFixed(2) }}</span>
          </div>

          <div class="density-inline__group">
            <span>分页</span>
            <el-slider v-model="bottomDensityProxy" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
            <span class="density-inline__value">{{ bottomDensityProxy.toFixed(2) }}</span>
          </div>

          <el-button
            size="small"
            :disabled="pageDensity === 1 && allSynced"
            @click="syncAreasToPage"
          >
            区域跟随
          </el-button>

          <el-button
            size="small"
            type="primary"
            :disabled="pageDensity === 1 && allSynced"
            @click="resetDensities"
          >
            全部还原
          </el-button>
        </div>
      </transition>
    </template>

    <!-- ═══ Top Area — Row 2: 搜索 + 操作按钮（不包含密度面板） ═══ -->
    <template #toolbar>
      <div class="toolbar-row">
        <!-- 左侧：主搜索 + 高级展开 -->
        <div class="toolbar-search">
          <el-input
            v-model="filters.q"
            placeholder="代码 / 名称 / 拼音"
            clearable
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
          <el-select
            v-model="filters.concept_id"
            placeholder="概念"
            clearable
            filterable
            remote
            :remote-method="onConceptSearch"
            :loading="conceptLoading"
            :style="{ width: topDensityProxy * 150 + 'px' }"
            @visible-change="onConceptDropdownVisible"
            @change="onFilterChange"
          >
            <el-option
              v-for="c in conceptOptions"
              :key="c.concept_id"
              :label="c.name"
              :value="c.concept_id"
            >
              <span class="concept-opt-name">{{ c.name }}</span>
              <span v-if="c.stock_count != null" class="concept-opt-count">
                {{ c.stock_count }} 只
              </span>
            </el-option>
          </el-select>
          <el-select v-model="filters.industry" placeholder="行业" clearable :style="{ width: topDensityProxy * 130 + 'px' }" @change="onFilterChange">
            <el-option v-for="v in meta.industries" :key="v" :label="v" :value="v" />
          </el-select>
          <el-select v-model="filters.market" placeholder="市场" clearable :style="{ width: topDensityProxy * 130 + 'px' }" @change="onFilterChange">
            <el-option v-for="v in meta.markets" :key="v" :label="v" :value="v" />
          </el-select>
          <el-select v-model="filters.exchange" placeholder="交易所" clearable :style="{ width: topDensityProxy * 110 + 'px' }" @change="onFilterChange">
            <el-option label="上交所" value="SSE" />
            <el-option label="深交所" value="SZSE" />
            <el-option label="北交所" value="BSE" />
          </el-select>
          <el-select v-model="filters.is_hs" placeholder="沪深港通" clearable :style="{ width: topDensityProxy * 110 + 'px' }" @change="onFilterChange">
            <el-option label="否" value="N" />
            <el-option label="沪股通" value="H" />
            <el-option label="深股通" value="S" />
          </el-select>
          <el-select v-model="filters.list_status" placeholder="状态" :style="{ width: topDensityProxy * 110 + 'px' }" @change="onFilterChange">
            <el-option label="上市" value="L" />
            <el-option label="退市" value="D" />
            <el-option label="暂停上市" value="P" />
            <el-option label="全部" value="" />
          </el-select>
          <el-select v-model="filters.st_filter" placeholder="ST筛选" clearable :style="{ width: topDensityProxy * 110 + 'px' }" @change="onFilterChange">
            <el-option label="排除ST" value="exclude" />
            <el-option label="仅ST" value="only" />
          </el-select>
          <el-input-number
            v-model="filters.min_total_mv"
            placeholder="最低市值(亿)"
            :min="0"
            :precision="0"
            :controls="false"
            align="left"
            :style="{ width: topDensityProxy * 110 + 'px' }"
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
      class="sil-table flex-1"
      highlight-current-row
      empty-text="没有匹配的股票"
      row-key="symbol"
      @row-click="openDetailDrawer"
      @selection-change="onSelectionChange"
    >
      <!-- 固定列（左侧钉住） -->
      <el-table-column type="selection" :width="colW(50)" fixed="left" />
      <el-table-column prop="symbol" label="代码" :width="colW(90)" fixed="left">
        <template #default="{ row }">
          <span class="mono font-semibold">{{ row.symbol }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" :width="colW(100)" fixed="left">
        <template #default="{ row }">
          <span class="font-medium">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="已加入池" :width="colW(110)" fixed="left">
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

      <!-- 滚动列（按重要性从左到右排列）；概念只在详情抽屉「概念」Tab 展示 -->
      <el-table-column label="最新价" :width="colW(90)" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.latest_close != null" class="mono font-medium">{{ row.latest_close.toFixed(2) }}</span>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column label="总市值" :width="colW(110)" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.total_mv != null" class="mono">{{ formatMv(row.total_mv) }}</span>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column label="PE(TTM)市盈率" :width="colW(120)" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.pe_ttm != null" :class="peClass(row.pe_ttm)" class="mono">{{ row.pe_ttm.toFixed(1) }}</span>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column label="净利润率%" :width="colW(100)" align="right" sortable>
        <template #default="{ row }">
          <span v-if="row.profit_margin != null" :class="row.profit_margin >= 0 ? 'text-red-500' : 'text-green-600'" class="mono">{{ row.profit_margin.toFixed(1) }}%</span>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="industry" label="行业" :width="colW(120)">
        <template #default="{ row }">{{ row.industry || '—' }}</template>
      </el-table-column>
      <el-table-column prop="market" label="市场" :width="colW(100)">
        <template #default="{ row }">
          <el-tag size="small" :type="marketType(row.market)" effect="light">
            {{ row.market || '—' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="exchange" label="交易所" :width="colW(80)">
        <template #default="{ row }">
          <el-tag size="small" :type="exchangeType(row.exchange)" effect="plain">
            {{ exchangeLabel(row.exchange) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上市日期" :width="colW(110)">
        <template #default="{ row }">{{ formatDate(row.list_date) }}</template>
      </el-table-column>
      <el-table-column prop="area" label="地域" :width="colW(80)">
        <template #default="{ row }">{{ row.area || '—' }}</template>
      </el-table-column>
      <el-table-column label="沪深港通" :width="colW(90)" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_hs === 'H'" type="danger" size="small">沪</el-tag>
          <el-tag v-else-if="row.is_hs === 'S'" type="success" size="small">深</el-tag>
          <span v-else class="text-gray-400 text-xs">—</span>
        </template>
      </el-table-column>
      <!-- 末列：不设 width，给一个 min-width，table-layout:fixed 时自动吸满剩余到容器边缘 -->
      <el-table-column prop="act_name" label="实控人" :min-width="colW(120)">
        <template #default="{ row }">
          <span class="text-sm">{{ row.act_name || '—' }}</span>
        </template>
      </el-table-column>

      <!-- 折叠展开按钮列：固定到「已加入池」右侧（左侧固定列的最后） -->
      <el-table-column type="expand" :width="colW(48)" fixed="left">
        <template #default="{ row }">
          <StockExpandRow :symbol="row.symbol" />
        </template>
      </el-table-column>

      <!-- 行末「详情」按钮列已移除：改为整行 hover pointer + chevron 触发展开/抽屉 -->
    </el-table>

    <!-- ═══ Bottom Area ═══ -->
    <template #bottom>
      <div class="bottom-area-inner">
        <el-pagination
          class="sil-pagination"
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          small
          background
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </div>
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Search, Refresh, Folder, ArrowDown, ArrowUp, Setting,
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
  listConceptOptions,
} from '@/views/stock-info/api'
import type {
  StockInfo,
  StockMeta,
  StockQueryParams,
  PoolMembership,
  ConceptOption,
} from '@/views/stock-info/api'

const router = useRouter()

// ════════════════════════════════════════════════════════════════
// 两层密度锚点状态（局部 CSS 变量驱动）
// ════════════════════════════════════════════════════════════════
//
// 设计原则：
// 1. 页面整体缩放 → 改 pageDensity，top/middle/bottom 默认跟随
// 2. 单区域独立缩放 → 改对应 areaDensity，覆盖默认跟随
// 3. JS 只管传值，CSS calc 自动派生所有 rem 派生量
//
// 持久化：localStorage key = 'sil-density'，刷新后恢复
// ════════════════════════════════════════════════════════════════

const DENSITY_STORAGE_KEY = 'sil-density'

type DensityShape = {
  page: number
  top: number
  middle: number
  bottom: number
}

function loadDensity(): DensityShape {
  try {
    const raw = localStorage.getItem(DENSITY_STORAGE_KEY)
    if (!raw) return { page: 1, top: 1, middle: 1, bottom: 1 }
    const parsed = JSON.parse(raw) as Partial<DensityShape>
    return {
      page:   clamp01(Number(parsed.page   ?? 1)),
      top:    clamp01(Number(parsed.top    ?? 1)),
      middle: clamp01(Number(parsed.middle ?? 1)),
      bottom: clamp01(Number(parsed.bottom ?? 1)),
    }
  } catch {
    return { page: 1, top: 1, middle: 1, bottom: 1 }
  }
}

/** 密度值范围限制：4 个锚点的安全区间（防止 localStorage 脏数据炸裂布局）
 *  - 页面：0.7 ~ 1.4
 *  - 顶部：0.6 ~ 1.5（顶部基础量大，范围更宽以提升缩小时的可见变化）
 *  - 中部 / 底部：0.7 ~ 1.4
 */
function clamp01(v: number) {
  const n = Math.max(0.6, Math.min(1.5, Number.isFinite(v) ? v : 1))
  return Math.round(n * 100) / 100
}

/** 区域密度 ref：null = 未独立设置（CSS calc 自动跟随 --sil-page-density） */
const pageDensity   = ref<number>(loadDensity().page)
const topDensity    = ref<number | null>(loadDensity().top === 1 ? null : loadDensity().top)
const middleDensity = ref<number | null>(loadDensity().middle === 1 ? null : loadDensity().middle)
const bottomDensity = ref<number | null>(loadDensity().bottom === 1 ? null : loadDensity().bottom)

/**
 * 把四个密度值注入为 CSS 变量
 * - 页面层（--sil-page-density）总是注入
 * - 区域层（--sil-top/middle/bottom-density）仅在用户主动设置时才注入
 *   未设置时不写，CSS 内的 calc(var(--sil-page-density)) 自动接管 → 区域跟随页面
 */
const densityStyle = computed<Record<string, string>>(() => {
  const style: Record<string, string> = {
    '--sil-page-density': String(pageDensity.value),
  }
  if (topDensity.value    != null) style['--sil-top-density']    = String(topDensity.value)
  if (middleDensity.value != null) style['--sil-middle-density'] = String(middleDensity.value)
  if (bottomDensity.value != null) style['--sil-bottom-density'] = String(bottomDensity.value)
  return style
})

/** 持久化到 localStorage（区域层为 null 时存 1，load 时识别为跟随） */
watch(
  [pageDensity, topDensity, middleDensity, bottomDensity],
  ([p, t, m, b]) => {
    try {
      localStorage.setItem(DENSITY_STORAGE_KEY, JSON.stringify({
        page: p,
        top:    t    ?? 1,
        middle: m    ?? 1,
        bottom: b    ?? 1,
      }))
    } catch { /* quota 等异常静默 */ }
  },
  { deep: false },
)

/** 一键还原：所有锚点回到 page=1，区域全部回到跟随 */
function resetDensities() {
  pageDensity.value   = 1
  topDensity.value    = null
  middleDensity.value = null
  bottomDensity.value = null
}

/** "区域跟随页面"开关：把区域锚点设为 null（CSS calc 会自动重新跟随 page） */
function syncAreasToPage() {
  topDensity.value    = null
  middleDensity.value = null
  bottomDensity.value = null
}

/** 是否所有区域都已"还原跟随"（用于 UI 状态提示） */
const allSynced = computed(() =>
  topDensity.value    === null
  && middleDensity.value === null
  && bottomDensity.value === null,
)

/**
 * 区域滑块的代理 computed
 * - 显示：null 时显示 pageDensity（视觉上"跟随"）
 * - 写入：用户主动拖动即设为独立值，断开跟随
 */
const topDensityProxy = computed<number>({
  get: () => topDensity.value ?? pageDensity.value,
  set: (v) => { topDensity.value = v },
})
const middleDensityProxy = computed<number>({
  get: () => middleDensity.value ?? pageDensity.value,
  set: (v) => { middleDensity.value = v },
})
const bottomDensityProxy = computed<number>({
  get: () => bottomDensity.value ?? pageDensity.value,
  set: (v) => { bottomDensity.value = v },
})

/**
 * 表格列宽缩放函数：px * middleDensityProxy
 * 用于 el-table-column :width，跟随"表格"锚点缩放
 */
function colW(px: number): number {
  return Math.round(px * middleDensityProxy.value)
}

// ════════════════════════════════════════════════════════════════

// ── 列表状态 ──────────────────────────────────────────────
const stocks = ref<StockInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const syncing = ref(false)
const meta = ref<StockMeta>({ industries: [], markets: [], exchanges: [] })
const selectedStocks = ref<StockInfo[]>([])

/** 概念下拉选项（高级筛选用；展开时懒加载，输入关键词走服务端 remote 搜索） */
const conceptOptions = ref<ConceptOption[]>([])
const conceptLoading = ref(false)

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

/** 密度锚点控制面板折叠状态（默认 false = 收起）
 * 持久化到 localStorage，刷新后保留用户偏好
 */
const DENSITY_PANEL_KEY = 'sil-density-panel'
const showDensityPanel = ref(
  (() => {
    try {
      return localStorage.getItem(DENSITY_PANEL_KEY) === '1'
    } catch { return false }
  })(),
)

watch(showDensityPanel, (v) => {
  try { localStorage.setItem(DENSITY_PANEL_KEY, v ? '1' : '0') } catch { /* quota */ }
})

const filters = ref({
  q: '',
  industry: '',
  market: '',
  exchange: '',
  is_hs: '',
  list_status: 'L',
  st_filter: '' as string,
  min_total_mv: undefined as number | undefined,
  concept_id: undefined as number | undefined,
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
  if (filters.value.concept_id != null) count++
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

/** 展开高级筛选时懒加载概念选项（首屏不拉，避免多余请求） */
watch(showAdvanced, (v) => {
  if (v) loadConceptOptions()
}, { immediate: false })

function resetFilters() {
  filters.value = { q: '', industry: '', market: '', exchange: '', is_hs: '', list_status: 'L', st_filter: '', min_total_mv: undefined, concept_id: undefined }
  page.value = 1
  loadStocks()
}

// ── 数据加载 ──────────────────────────────────────────────
/**
 * 加载股票面板列表（with_pools=true，内嵌池信息，避免 N+1）
 */
async function loadStocks() {
  loading.value = true
  try {
    const params: StockQueryParams = {
      page: page.value,
      page_size: pageSize.value,
      with_pools: true,    // 一次性返回所属池
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
    if (filters.value.concept_id != null) params.concept_id = filters.value.concept_id

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

/** 加载概念下拉选项
 *
 * 概念总数约 390（> 后端 page_size 上限 100），所以用「服务端搜索」：
 *  - 首次展开 / 清空关键词 → 取成分股最多的前 100 个作快捷项
 *  - 输入关键词 → remote-method 调后端 q 搜索，覆盖全部概念
 * 失败静默：概念下拉不可用不影响主列表。
 */
async function loadConceptOptions(q = '') {
  conceptLoading.value = true
  try {
    const list = await listConceptOptions({ q: q || undefined })
    conceptOptions.value = Array.isArray(list) ? list : []
  } catch {
    conceptOptions.value = []
  } finally {
    conceptLoading.value = false
  }
}

/** el-select remote-method：防抖 300ms，避免逐字符打后端 */
let conceptSearchTimer: ReturnType<typeof setTimeout> | null = null
function onConceptSearch(q: string) {
  if (conceptSearchTimer) clearTimeout(conceptSearchTimer)
  conceptSearchTimer = setTimeout(() => loadConceptOptions(q.trim()), 300)
}

/** 下拉展开时兜底加载（remote 模式下 EP 不会自动填初始选项） */
function onConceptDropdownVisible(visible: boolean) {
  if (visible && conceptOptions.value.length === 0) loadConceptOptions()
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
  await Promise.all([loadMeta(), loadStocks()])
})
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════════
 * StockInfoList · 两层密度锚点架构（样板）
 * ════════════════════════════════════════════════════════════════
 *
 * 设计思路
 * ───────
 * 第一层（页面锚点）：--sil-page-density = 用户在顶部滑块控制
 *   │
 *   ├─ 第二层（区域锚点）：--sil-top-density / --sil-middle-density / --sil-bottom-density
 *   │     默认 = calc(var(--sil-page-density) × 1)，
 *   │     也可被 JS 独立覆盖（如 "顶部紧凑 / 表格宽松"）
 *   │
 *   └─ 第三层（元素 token）：每个元素的值 = calc(rem × var(--sil-xxx-density))
 *
 * 作用域
 * ─────
 * 所有变量声明在 .stock-info-page 内，CSS 变量沿 DOM 子树继承，
 * 不会渗透到 .shell / .topbar / .leftbar / 其他页面。
 *
 * 修改规则
 * ───────
 * 1. 想让整页放大/缩小 → JS 改 --sil-page-density（其他自动跟随）
 * 2. 想让某区域单独放大/缩小 → JS 改 --sil-{top|middle|bottom}-density
 * 3. 想改某元素的默认尺寸 → 改 CSS 里 calc() 中的 rem 值
 * 4. 想加新元素跟锚点走 → 用 calc(rem × var(--sil-xxx-density))，xxx 是元素所在区域
 *
 * ⚠️ 标题样式（.top-area__title）在 PageWrapper.vue 里，本文件未动，保持原样。
 * ════════════════════════════════════════════════════════════════ */

.stock-info-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;

  /* ── 第一层：页面锚点（影响整页字号 / 控件密度） ── */
  --sil-page-density: 1;

  /* ── 第二层：三个区域的锚点（默认跟随页面，可被 JS 独立覆盖） ── */
  --sil-top-density:    calc(var(--sil-page-density));
  --sil-middle-density: calc(var(--sil-page-density));
  --sil-bottom-density: calc(var(--sil-page-density));

  /* ── 派生 token：top-area（搜索栏 / 按钮 / 高级筛选）
   * 顶部基础量加大（2rem 起步）→ topDensity=0.6 时缩到 1.2rem，调小幅度更明显 */
  --sil-top-gap:        calc(0.6rem   * var(--sil-top-density));
  --sil-top-button-h:   calc(2rem     * var(--sil-top-density));
  --sil-top-button-fs:  calc(0.95rem * var(--sil-top-density));
  --sil-top-button-px:  calc(0.75rem * var(--sil-top-density));
  --sil-top-icon-fs:    calc(0.95rem * var(--sil-top-density));
  --sil-top-icon-mr:    calc(0.25rem * var(--sil-top-density));
  --sil-top-filter-py:  calc(0.55rem * var(--sil-top-density));
  --sil-top-filter-px:  calc(0.85rem * var(--sil-top-density));
  --sil-top-control-h:  calc(2rem    * var(--sil-top-density));
  /* 字号 token：覆盖 el-input / el-select / el-input-number / placeholder */
  --sil-top-input-fs:    calc(0.95rem * var(--sil-top-density));
  --sil-top-input-w:     calc(220px   * var(--sil-top-density));
  --sil-top-select-fs:   calc(0.95rem * var(--sil-top-density));
  --sil-top-select-w:    calc(130px   * var(--sil-top-density));
  --sil-top-input-num-fs: calc(0.95rem * var(--sil-top-density));
  --sil-top-input-num-w:  calc(130px   * var(--sil-top-density));

  /* ── 派生 token：middle-area（表格） ── */
  --sil-middle-row-h:        calc(2.5rem    * var(--sil-middle-density));
  --sil-middle-cell-pad-y:   calc(0.375rem  * var(--sil-middle-density));
  --sil-middle-cell-pad-x:   calc(0.5rem    * var(--sil-middle-density));
  --sil-middle-table-fs:     calc(0.857rem  * var(--sil-middle-density));
  --sil-middle-sel-fs:       calc(0.857rem  * var(--sil-middle-density));
  --sil-middle-sel-py:       calc(0.357rem  * var(--sil-middle-density));
  --sil-middle-sel-px:       calc(0.625rem  * var(--sil-middle-density));
  --sil-middle-sel-gap:      calc(0.357rem  * var(--sil-middle-density));

  /* ── 派生 token：bottom-area（分页器） ── */
  --sil-bottom-pagination-fs:    calc(0.857rem * var(--sil-bottom-density));
  --sil-bottom-pagination-btn-w: calc(1.857rem * var(--sil-bottom-density));
  --sil-bottom-pagination-btn-h: calc(1.857rem * var(--sil-bottom-density));
  --sil-bottom-pagination-pt:    calc(0.5rem   * var(--sil-bottom-density));
}

/* ════════════════════════════════════════════════
 * 「页面设置」折叠按钮（位于 title slot 内，紧贴标题）
 * ──────────────────────────────────────────────── */
.density-toggle {
  /* reset native button */
  appearance: none;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;

  /* 锁定固定尺寸，不随 top-density 变化（避免放大后比标题文字还大） */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.625rem;
  height: 1.625rem;
  border-radius: 6px;
  color: #64748b;
  transition: all 0.18s ease;
  flex-shrink: 0;
}

.density-toggle:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
  color: #1e293b;
}

.density-toggle.active {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  border-color: #60a5fa;
  color: #1e40af;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.18);
}

/* ════════════════════════════════════════════════
 * 内联密度设置面板（与标题同一行，展开后出现在按钮右侧）
 * ──────────────────────────────────────────────── */
.density-inline {
  /* 锁定高度 32px：≤ header(40px) × 80%，给上下各留 4px 居中 padding，
   * 防止 slider/button 高度变化反向撑高 title 行（详见 .top-area__header 锁死 40px） */
  height: 2rem;
  max-height: 2rem;
  display: flex;
  align-items: center;
  /* 不设 flex-shrink:0，让 .density-inline 自身能被父级（.top-area__title）压缩到容器宽度内
   * —— 内部 .density-inline__group 仍设 flex-shrink:0，所以被压缩后会触发 overflow-x:auto 滚动
   *    满足"内部锚点设置超出时滚动查看，而不是遮盖"的需求 */
  align-self: center;          /* 在 .top-area__header 里锁定 cross-axis 位置 */

  /* 宽度约束：不超出 main-container（继承自 .top-area__title → .top-area__header → .main-container） */
  width: auto;                 /* 由父级分配剩余空间，不撑开 */
  min-width: 0;                /* 允许收缩到内容 min-content 以下，触发 overflow-x:auto */
  flex-grow: 1;                /* 在父级剩余空间里尽可能占满 */
  flex-basis: 0;               /* 与 grow:1 配合：忽略内容本来的尺寸，按比例分配 */
  flex-wrap: nowrap;
  overflow-x: auto;            /* 内部超出时横向滚动（按需求"内容超出滚动查看"） */
  overflow-y: hidden;          /* 垂直硬切断 */

  scrollbar-width: thin;
  scrollbar-color: #93c5fd transparent;
  gap: 0.5rem;
  padding: 0 0.625rem;
  margin-left: 0.357rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px dashed #93c5fd;
  border-radius: 6px;
  font-size: 0.857rem;
  color: #1e40af;
}

/* 本页面内的 .top-area__header：高度锁死 40px
 *
 * 关键不变式：density-inline 出现/消失不引起整页布局抖动。
 *   - 旧方案：height:auto（被 .density-inline 40px 撑高到 40px）→ 展开时 header 32→40，整页上移 8px
 *   - 新方案：height:40px 锁死 + .density-inline 32px（header 内居中）→ 展开/收起 header 恒 40px
 * PageWrapper.vue 全局样式保留不变（其它页面继续按原规则自适应）。 */
.stock-info-page :deep(.top-area__header) {
  height: 2.5rem;              /* 40px 锁死 */
  max-height: 2.5rem;
  min-height: 2.5rem;
}

/* 防止 .top-area__title 这个 flex 容器内的子项（特别是 .density-inline 的 min-content）
 * 反向撑开 .top-area__header → .main-container。
 * min-width:0 是关键：默认 flex 子项的 min-width = min-content，
 * 设为 0 后子项才能被压缩到容器宽度以下、触发 overflow-x:auto 滚动。 */
.stock-info-page :deep(.top-area__title) {
  min-width: 0;
}

.density-inline__label {
  font-weight: 600;
  white-space: nowrap;
  color: #1e40af;
  flex-shrink: 0;
}

.density-inline__divider {
  width: 1px;
  height: 1rem;
  background: #93c5fd;
  flex-shrink: 0;
}

.density-inline__group {
  display: inline-flex;
  align-items: center;
  gap: 0.357rem;
  white-space: nowrap;
  color: #475569;
  flex-shrink: 0;
}

.density-inline__value {
  display: inline-block;
  min-width: 2.25rem;
  text-align: center;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-weight: 600;
  color: #1d4ed8;
}

/* 滑块锁死尺寸 + 垂直居中（ep 默认 vertical-align 会导致高度计算异常） */
.density-inline :deep(.el-slider) {
  width: 60px;
  height: 16px;
  margin: 0;
}

.density-inline :deep(.el-slider__runway) {
  height: 4px;
}

.density-inline :deep(.el-slider__bar) {
  height: 4px;
}

.density-inline :deep(.el-slider__button) {
  width: 12px;
  height: 12px;
}

/* WebKit 滚动条：扁平、细，配合顶栏主题 */
.density-inline::-webkit-scrollbar {
  height: 4px;
}
.density-inline::-webkit-scrollbar-track {
  background: transparent;
}
.density-inline::-webkit-scrollbar-thumb {
  background: #93c5fd;
  border-radius: 2px;
}
.density-inline::-webkit-scrollbar-thumb:hover {
  background: #60a5fa;
}

/* 内联面板内的 el-button 锁死尺寸，避免被 density 放大 */
.density-inline :deep(.el-button) {
  height: 22px;
  padding: 0 10px;
  font-size: 0.78rem;
  margin: 0;
}

/* 内部图标尺寸 */
.density-inline :deep(.el-button .el-icon) {
  font-size: 0.78rem;
}

/* Vue transition for show/hide inline panel */
.density-inline-enter-active,
.density-inline-leave-active {
  transition: opacity 0.22s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}
.density-inline-enter-from,
.density-inline-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

/* 标题文字保持不换行 */
.page-title-text {
  white-space: nowrap;
}

/* ════════════════════════════════════════════════
 * Top Area · 搜索栏 + 按钮 + 高级筛选
 * ════════════════════════════════════════════════ */
.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sil-top-gap);
}

.toolbar-search {
  display: flex;
  align-items: center;
  gap: var(--sil-top-gap);
}

/* 搜索框：宽度 + 高度 + 字号 同步缩放
 * ⚠️ EP 的 el-input font-size 同样 sass 固化，必须 :deep() 强覆盖 */
.toolbar-search :deep(.el-input) {
  --el-input-width: var(--sil-top-input-w);
  --el-input-height: var(--sil-top-control-h);
  --el-component-size: var(--sil-top-control-h);
  --el-input-font-size: var(--sil-top-input-fs);
  width: var(--sil-top-input-w);
  font-size: var(--sil-top-input-fs);
}

.toolbar-search :deep(.el-input__wrapper),
.toolbar-search :deep(.el-input__wrapper .el-input__inner),
.toolbar-search :deep(.el-input__inner) {
  font-size: var(--sil-top-input-fs);
}

/* 搜索框 placeholder 字号 */
.toolbar-search :deep(.el-input__inner::placeholder),
.toolbar-search :deep(.el-input__inner::-webkit-input-placeholder),
.toolbar-search :deep(.el-input__inner::-moz-placeholder),
.toolbar-search :deep(.el-input__inner:-ms-input-placeholder) {
  font-size: var(--sil-top-input-fs);
  color: #a8abb2;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--sil-top-gap);
  flex-shrink: 0;
}

/* 按钮：用 top-area 派生 token
 * ⚠️ EP 的 .el-button font-size / height 是 sass 编译时固化进 CSS 的，
 *   不响应 --el-button-size / --el-button-font-size 这两个 token。
 *   必须直接用 :deep(...) 强制覆盖。 */
.toolbar-row :deep(.el-button) {
  --el-button-size:      var(--sil-top-button-h);
  --el-button-font-size: var(--sil-top-button-fs);
  height:   var(--sil-top-button-h);
  font-size: var(--sil-top-button-fs);
  padding-left:  var(--sil-top-button-px);
  padding-right: var(--sil-top-button-px);
  /* 兜底：覆盖按钮内所有 span 的字号（包括默认 slot 文字） */
  line-height: 1;
}

.toolbar-row :deep(.el-button span),
.toolbar-row :deep(.el-button) {
  font-size: var(--sil-top-button-fs);
}

.toolbar-row :deep(.el-button .el-icon) {
  font-size: var(--sil-top-icon-fs);
  margin-right: var(--sil-top-icon-mr);
}

/* 高级筛选：grid-rows 展开动画 */
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
  gap: var(--sil-top-gap);
  padding: 0 var(--sil-top-filter-px);
  background: var(--color-admin-bg);
  border-radius: 8px;
  transition: padding 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.advanced-wrapper.open > .advanced-filters {
  padding: var(--sil-top-filter-py) var(--sil-top-filter-px);
}

/* 高级筛选内部 select / input-number 同步紧凑
 * 注意：不能用 --el-font-size-base（会影响全局），用 EP 内部精确 token */
.advanced-filters :deep(.el-select),
.advanced-filters :deep(.el-input-number) {
  --el-input-height: var(--sil-top-control-h);
  --el-component-size: var(--sil-top-control-h);
  --el-input-font-size: var(--sil-top-select-fs);
  --el-select-font-size: var(--sil-top-select-fs);
  font-size: var(--sil-top-select-fs);
}

.advanced-filters :deep(.el-select__wrapper),
.advanced-filters :deep(.el-select__placeholder),
.advanced-filters :deep(.el-input-number__input),
.advanced-filters :deep(.el-input-number .el-input__inner),
.advanced-filters :deep(.el-input-number .el-input__wrapper) {
  font-size: var(--sil-top-select-fs);
}

/* el-input-number / el-select 的 placeholder 字号
 * （sass 默认 14px 写死，必须强覆盖） */
.advanced-filters :deep(.el-select .el-input__inner::placeholder),
.advanced-filters :deep(.el-select .el-select__placeholder),
.advanced-filters :deep(.el-select input::placeholder),
.advanced-filters :deep(.el-input-number .el-input__inner::placeholder),
.advanced-filters :deep(.el-input-number input::placeholder),
.advanced-filters :deep(.el-input-number input::-webkit-input-placeholder),
.advanced-filters :deep(.el-input-number input::-moz-placeholder),
.advanced-filters :deep(.el-input-number input:-ms-input-placeholder) {
  font-size: var(--sil-top-select-fs);
  color: #a8abb2;
}

/* ── el-select / el-input-number 盒模型归一化（「最低市值」与其它筛选对齐）──
 *
 * 根因：两者内部「可见盒子」不是同一个元素，原生盒模型基准也不同——
 *   el-select       可见盒子 = .el-select__wrapper （border + padding 4px 11px）
 *   el-input-number 可见盒子 = .el-input__wrapper （box-shadow 画边框，
 *                                           EP 原生 padding 1px 11px）
 * 只给两者套同一组 padding 会让边框盒差 2px，且内层原生 <input> 被二次压缩，
 * 视觉上「矮一截 + 文字居中 + 占位符偏深」——与左侧 7 个 select 明显不齐。
 *
 * 归一化策略：
 *   1. 边框盒统一交给两者的 wrapper：height / padding / line-height / 字号完全一致
 *   2. 内层原生 input 只负责填满剩余空间（height:100%），不再写死 -8px 二次压缩
 *   3. 占位符颜色 / 字重与 .el-select__placeholder 一致（浅灰 #a8abb2）
 *   4. 文字左对齐（模板上 align="left"，让 EP 输出 is-left 类）
 */

/* 边框盒：两个组件共用同一组规格 */
.advanced-filters :deep(.el-select__wrapper),
.advanced-filters :deep(.el-input-number .el-input__wrapper) {
  height: var(--sil-top-control-h);
  min-height: var(--sil-top-control-h);
  padding: 4px 11px;
  line-height: calc(var(--sil-top-control-h) - 8px);
  box-sizing: border-box;
}

/* 内层原生 input：填满剩余高度，不再写死 -8px 造成二次压缩 */
.advanced-filters :deep(.el-input-number .el-input__inner) {
  height: 100%;
  line-height: calc(var(--sil-top-control-h) - 8px);
}

/* 占位符与 select 的 .el-select__placeholder 视觉对齐：
 * select 占位符是 <span>（字号可继承），input-number 是原生 placeholder
 *（EP sass 单独写死），这里显式补齐字号 + 颜色 + 字重。
 * ⚠️ 不要用 var(--el-color-text-color-placeholder)：EP 没有这个变量
 *    （实测解析为空串会让 color 失效并回退到深色），统一用字面量 #a8abb2。 */
.advanced-filters :deep(.el-input-number .el-input__inner::placeholder) {
  font-size: var(--sil-top-select-fs);
  font-weight: 400;
  color: #a8abb2;
}

/* 概念下拉：名称左对齐 + 成分股数量右对齐灰显
 * （EP 选项行默认 list-item / 居中，长短不一时视觉参差）
 *
 * ⚠️ el-select 下拉是 **teleport 到 body** 的，不在 .advanced-filters 子树内，
 *    `:deep()` 选不中（实测 item 的祖先链是 el-popper → body）。
 *    但选项内容仍带本组件的 data-v-xxx 属性，所以用 `:global()` 按属性选，
 *    既能穿透 teleport 又只作用于本页的概念下拉。 */
:global(.el-select-dropdown__item:has(.concept-opt-count)) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sil-top-gap);
}

.concept-opt-name {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.concept-opt-count {
  flex: 0 0 auto;
  font-size: var(--sil-top-select-fs);
  color: #a8abb2;
  font-variant-numeric: tabular-nums;
}

/* ════════════════════════════════════════════════
 * Middle Area · 选中提示条 + 表格
 * ════════════════════════════════════════════════ */
.selection-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--sil-middle-sel-gap);
  padding: var(--sil-middle-sel-py) var(--sil-middle-sel-px);
  font-size: var(--sil-middle-sel-fs);
  color: #475569;
  background: #eff6ff;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
}

/* 表格 EP 主题变量重声明（在 .stock-info-page 作用域内，仅本页生效）
 *
 * ⚠️ 注意：不能用 --el-font-size-base，那是 EP 全局字号源，会反向影响
 *    顶部区域的 el-button / el-select 等组件。这里只覆盖表格自身的 token。
 */
.stock-info-page :deep(.el-table) {
  --el-table-row-height:          var(--sil-middle-row-h);
  --el-table-cell-padding-block:  var(--sil-middle-cell-pad-y);
  --el-table-cell-padding-inline: var(--sil-middle-cell-pad-x);
  --el-table-font-size:           var(--sil-middle-table-fs);
  --el-table-header-font-size:    var(--sil-middle-table-fs);
  /* EP 表格 cell 内部用 --el-font-size-base 做兜底，限定在表格范围内 */
  --el-table-cell-font-size:      var(--sil-middle-table-fs);
}

/* ═══════════════════════════════════════════════════════════════
 * 表格整体宽度 = 容器宽度（绝不超出视区）
 *
 * 关键不变式：
 *   outer(<el-table>) 宽度  ≡  inner-wrapper 父容器宽度  ≡  视区宽度
 *   inner-wrapper 宽度    ≡  body-table 真实列宽之和（可能 > outer）
 *   body-table 在 .el-table__inner-wrapper 内 overflow-x: auto 滚动
 * ══════════════════════════════════════════════════════════════ */

/* (1) flex 子项必须 min-width:0，否则被 inner 撑爆 */
.sil-table {
  min-width: 0;
  width: 100%;
  max-width: 100%;
}

/* (2) outer <el-table>：宽度严格 = 父宽，不让 inner 撑出去
 *   ⚠ 关键：body-table 的真实宽度 ≤ outer 宽。
 *   当列宽总和 > outer 时，body-table 的"超出部分"会触发 outer 自身 overflow-x:auto
 *   即 body wrapper 滚动而非外层 overflow 滚动 */
.sil-table :deep(.el-table) {
  display: block;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: hidden;
}

/* (3) inner-wrapper 维持外层滚动控制 (不能用 max-width 截断 body-table，
 *     否则 colspan 后的 expand cell 反而被压窄) */
.sil-table :deep(.el-table__inner-wrapper) {
  width: 100%;
  max-width: 100%;
  overflow: visible;
}

/* (4) body / header table：table-layout:fixed + max-width:100% 强制列宽总和 ≤ outer
 *     这是 EP 在用户设了 table-layout:fixed 后的实际行为 */
.sil-table :deep(.el-table__header),
.sil-table :deep(.el-table__body) {
  table-layout: fixed;
  width: 100%;
  max-width: 100%;
}

/* (5) header-wrapper 也跟着 100% */
.sil-table :deep(.el-table__header-wrapper) {
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}



/* ═════ EP 内部"写死 px"逐项覆盖（不靠主题变量） ═════
 * EP 表格大量 padding/line-height/宽度 是直接写死的 px，
 * 这里用 calc(px × density) 包装，让它们跟着 middle 锚点走。
 * 标记类 .sil-table 是模板里加的，用于精准锁定（不影响其他页面的 .el-table）。
 */

/* cell 垂直 padding：EP 默认 8px，small 4px；用 calc 包密度 */
.sil-table :deep(.el-table__cell) {
  padding-block:  calc(8px  * var(--sil-middle-density));
  padding-inline: 0;
}

/* cell 内 .cell 容器：水平 padding 12px / line-height 23px */
.sil-table :deep(.el-table .cell) {
  padding-inline: calc(12px * var(--sil-middle-density));
  line-height:   calc(23px * var(--sil-middle-density));
}

/* 展开按钮尺寸：EP 写死 23×23，跟着 density */
.sil-table :deep(.el-table__expand-icon) {
  width:  calc(23px * var(--sil-middle-density));
  height: calc(23px * var(--sil-middle-density));
}

/* 展开内容 cell：EP 写死 padding 20px 50px
 * 这里的 50px 横向 padding 会显著占用展开行宽度，我们改成更小且跟密度
 * 但不强制 0，避免无 padding 导致内容贴到边缘。 */
.sil-table :deep(.el-table__expanded-cell) {
  padding: calc(16px * var(--sil-middle-density)) calc(20px * var(--sil-middle-density));
  background: #f8fafc;
}

/* 表头排序图标区域 */
.sil-table :deep(.el-table .sort-caret) {
  border-width: calc(5px * var(--sil-middle-density));
}

.sil-table :deep(.el-table .caret-wrapper) {
  width:  calc(24px * var(--sil-middle-density));
  height: calc(14px * var(--sil-middle-density));
}

/* 列筛选图标字号（14px 写死） */
.sil-table :deep(.el-table__column-filter-trigger i) {
  font-size: calc(14px * var(--sil-middle-density));
}

/* 空状态行高（60px 写死） */
.sil-table :deep(.el-table__empty-block),
.sil-table :deep(.el-table__empty-text) {
  min-height: calc(60px * var(--sil-middle-density));
  line-height: calc(60px * var(--sil-middle-density));
}

/* 表格数据行 hover：强调可点击 */
:deep(.el-table__row) {
  cursor: pointer;
  transition: background-color 0.18s ease;
}

:deep(.el-table__row:hover > td) {
  background-color: #f0f9ff !important;
}

/* 展开按钮（chevron）悬浮岛效果 */
:deep(.el-table__expand-icon) {
  cursor: pointer;
  transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-table__expand-icon:hover) {
  transform: scale(1.35);
}

:deep(.el-table__expand-icon--expanded) {
  transform: rotate(90deg) scale(1.15);
}

:deep(.el-table__expand-icon--expanded:hover) {
  transform: rotate(90deg) scale(1.35);
  box-shadow:
    0 6px 16px rgba(15, 23, 42, 0.14),
    0 2px 6px rgba(15, 23, 42, 0.08);
}

/* ════════════════════════════════════════════════
 * Bottom Area · 分页器
 * ════════════════════════════════════════════════ */
.bottom-area-inner {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-top: var(--sil-bottom-pagination-pt);
}

/* 分页器 EP 主题变量重声明 */
.stock-info-page :deep(.el-pagination) {
  --el-pagination-font-size:      var(--sil-bottom-pagination-fs);
  --el-pagination-button-width:   var(--sil-bottom-pagination-btn-w);
  --el-pagination-button-height:  var(--sil-bottom-pagination-btn-h);
  /* small 模式（<el-pagination small>）专用变量 */
  --el-pagination-font-size-small:     var(--sil-bottom-pagination-fs);
  --el-pagination-button-width-small:  var(--sil-bottom-pagination-btn-w);
  --el-pagination-button-height-small: var(--sil-bottom-pagination-btn-h);
  /* item 间距：EP 默认 16px */
  --el-pagination-item-gap: calc(16px * var(--sil-bottom-density));
}

/* ═════ EP 分页器内部"写死 px"逐项覆盖 ═════
 * 分页器在 .sil-pagination 标记类内精准覆盖（不影响其他页面）。
 * 涉及 padding / margin / font-size / 宽度 等。
 */
.sil-pagination :deep(.btn-prev),
.sil-pagination :deep(.btn-next),
.sil-pagination :deep(.el-pager li) {
  padding: 0 calc(4px * var(--sil-bottom-density));
  font-size: var(--sil-bottom-pagination-fs);
}

.sil-pagination :deep(.btn-prev .el-icon),
.sil-pagination :deep(.btn-next .el-icon),
.sil-pagination :deep(.el-pager li .el-icon) {
  font-size: var(--sil-bottom-pagination-fs);
}

/* background 模式的左右 margin */
.sil-pagination :deep(.el-pagination.is-background .btn-prev),
.sil-pagination :deep(.el-pagination.is-background .btn-next),
.sil-pagination :deep(.el-pagination.is-background .el-pager li) {
  margin: 0 calc(4px * var(--sil-bottom-density));
}

/* 跳转输入框宽度 56px */
.sil-pagination :deep(.el-pagination__editor.el-input) {
  width: calc(56px * var(--sil-bottom-density));
}

/* select 宽度（默认 128px，跟着密度缩放） */
.sil-pagination :deep(.el-pagination .el-select) {
  width: calc(128px * var(--sil-bottom-density));
}

/* classifier 与 goto 间距 */
.sil-pagination :deep(.el-pagination__classifier),
.sil-pagination :deep(.el-pagination__goto) {
  margin-left: calc(8px * var(--sil-bottom-density));
  margin-right: calc(8px * var(--sil-bottom-density));
}

/* small 模式 select 宽度 100px */
.sil-pagination :deep(.el-pagination--small .el-select) {
  width: calc(100px * var(--sil-bottom-density));
}

/* small 模式 prev/next/pager li 字号 */
.sil-pagination :deep(.el-pagination--small span:not([class*="suffix"])),
.sil-pagination :deep(.el-pagination--small button) {
  font-size: var(--sil-bottom-pagination-fs);
}
</style>
