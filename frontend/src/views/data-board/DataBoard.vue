<!--
  四数据面数据看板（单股分析工具）
  业务模块：data-board/
  - 左侧 200px 股票列（全量 5000+ 只，可搜索 + 当前选中高亮）
  - 右侧 4 Tab：技术面 / 资金面 / 基本面 / 新闻面
  - 点击左侧股票自动切换右侧 4 Tab 展示的数据

  配套设计文档：docs/overview/数据面与采集总览.md
-->
<template>
  <PageWrapper class="db-page">
    <template #title>
      <el-icon class="mr-1"><DataAnalysis /></el-icon>
      四数据面看板
      <span class="page-title-text">技术面 · 资金面 · 基本面 · 新闻面</span>
      <span class="ml-2 text-xs text-gray-400">v1 · 2026-10-04</span>
    </template>

    <template #toolbar>
      <div class="toolbar-row">
        <div class="toolbar-tags">
          <el-tag v-if="overview?.stock" size="small" type="info">
            {{ overview.stock.name }} ({{ symbol }})
          </el-tag>
          <el-tag v-if="overview?.stock?.industry" size="small" effect="plain">
            {{ overview.stock.industry }}
          </el-tag>
          <el-tag v-if="overview" size="small" type="success" effect="plain">
            K线 {{ overview.tech.kline_count }} 根
          </el-tag>
          <el-tag v-if="overview" size="small" type="warning" effect="plain">
            资金 {{ overview.capital.moneyflow_count }} 条
          </el-tag>
        </div>
        <div class="toolbar-meta">
          <el-tag v-if="lastFetchAt" size="small" type="info" effect="plain" title="上次拉取时间">
            🕐 {{ lastFetchAt }} · {{ fmtMs(fetchElapsed) }}
          </el-tag>
          <el-button size="small" :icon="Refresh" @click="reload" :loading="loading">刷新</el-button>
        </div>
      </div>
    </template>

    <!-- 主体：左侧股票列 + 右侧 4 Tab -->
    <div class="db-body">
      <!-- 左侧 200px 股票列 -->
      <aside class="db-aside">
        <StockListPanel
          :current-symbol="symbol"
          @select="onSelectStock"
        />
      </aside>

      <!-- 右侧 4 Tab -->
      <main class="db-main">
        <el-tabs v-model="activeTab" class="db-tabs">
          <el-tab-pane label="📈 技术面" name="tech">
            <TechPanel ref="techRef" :symbol="symbol" :stock-name="stockName" />
          </el-tab-pane>
          <el-tab-pane label="💰 资金面" name="capital">
            <CapitalPanel ref="capitalRef" :symbol="symbol" />
          </el-tab-pane>
          <el-tab-pane label="📊 基本面" name="fundamental">
            <FundamentalPanel ref="fundamentalRef" :symbol="symbol" />
          </el-tab-pane>
          <el-tab-pane label="📰 新闻面" name="news">
            <NewsPanel :news="overview?.news" />
          </el-tab-pane>
        </el-tabs>
      </main>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Refresh } from '@element-plus/icons-vue'
import PageWrapper from '@/components/PageWrapper.vue'
import StockListPanel from './StockListPanel.vue'
import TechPanel from './TechPanel.vue'
import CapitalPanel from './CapitalPanel.vue'
import FundamentalPanel from './FundamentalPanel.vue'
import NewsPanel from './NewsPanel.vue'
import * as API from './api'

// ── 路由参数（支持 /data-board/000001 直接进入） ──
const route = useRoute()
const router = useRouter()
const routeSymbol = () => {
  const raw = (route.params.symbol as string | undefined)?.trim()
  if (!raw) return ''
  return raw.padStart(6, '0')
}
const symbol = ref(routeSymbol() || '000001')

const activeTab = ref('tech')
const loading = ref(false)

const overview = ref<API.OverviewPanel | null>(null)
const stockName = ref('')

const techRef = ref<InstanceType<typeof TechPanel> | null>(null)
const capitalRef = ref<InstanceType<typeof CapitalPanel> | null>(null)
const fundamentalRef = ref<InstanceType<typeof FundamentalPanel> | null>(null)

// 拉取耗时
const fetchElapsed = ref(0)
const lastFetchAt = ref<string | null>(null)

function fmtMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}
function fmtNow(): string {
  return new Date().toTimeString().slice(0, 8)
}

// ── 数据加载（拉取所有 4 Tab 数据） ──
async function loadAll() {
  const s = symbol.value.trim().padStart(6, '0')
  if (!/^\d{6}$/.test(s)) {
    ElMessage.warning('请输入 6 位股票代码')
    return
  }
  loading.value = true
  const t0 = performance.now()

  // 概览（4 面综合统计 + 股票名）
  try {
    overview.value = await API.getOverviewPanel(s)
    stockName.value = overview.value?.stock?.name || ''
  } catch (e) {
    console.warn('[DataBoard] getOverviewPanel failed', e)
    stockName.value = ''
  }

  // 4 个 Panel 各自的 load（并行触发，由各自 ref 调用）
  await Promise.all([
    techRef.value?.load() ?? Promise.resolve(),
    capitalRef.value?.load() ?? Promise.resolve(),
    fundamentalRef.value?.load() ?? Promise.resolve(),
  ])

  fetchElapsed.value = Math.round(performance.now() - t0)
  lastFetchAt.value = fmtNow()
  loading.value = false
}

function reload() {
  loadAll()
}

// ── 选股：路由同步 + 重新加载 ──
function onSelectStock(s: string) {
  symbol.value = s.padStart(6, '0')
  if (route.params.symbol !== symbol.value) {
    router.replace({ name: 'DataBoard', params: { symbol: symbol.value } })
  }
  loadAll()
}

// 路由参数变化 → 重新加载
watch(() => routeSymbol(), async (next) => {
  if (next && next !== symbol.value) {
    symbol.value = next
    await nextTick()
    loadAll()
  }
})

// 记住上次选中的 symbol
watch(symbol, (next) => {
  if (next) localStorage.setItem('data_board:last_symbol', next)
})

onMounted(() => {
  // 优先用 localStorage 记忆
  const last = localStorage.getItem('data_board:last_symbol')
  if (last && last !== symbol.value && !routeSymbol()) {
    symbol.value = last
  }
  loadAll()
})
</script>

<style scoped>
.db-page { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.page-title-text {
  font-size: 0.75rem; color: #94a3b8; margin-left: 0.5rem; font-weight: 400;
}

.toolbar-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; flex-wrap: wrap;
}
.toolbar-tags { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.toolbar-meta { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }

/* 主体两栏布局 */
.db-body {
  display: flex;
  flex: 1; min-height: 0;
  gap: 0;
}
.db-aside {
  width: 220px; flex-shrink: 0;
  height: 100%;
}
.db-main {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column;
}
.db-tabs {
  flex: 1; min-height: 0;
  display: flex; flex-direction: column;
}
.db-tabs :deep(.el-tabs__content) {
  flex: 1; min-height: 0; overflow: auto;
}

@media (max-width: 900px) {
  .db-aside { width: 180px; }
}

/* 复用 PageWrapper 的 top-area 高度约束 */
.db-page :deep(.top-area__header) { min-height: 2.5rem; height: 2.5rem; max-height: 2.5rem; }
.db-page :deep(.top-area__title) { min-width: 0; }
</style>