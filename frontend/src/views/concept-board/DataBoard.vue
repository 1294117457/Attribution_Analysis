<!--
  四数据面数据看板 — 单页面（4 Tab 整合）
  业务模块：四数据面（tech / capital / fundamental / news）
  配套设计文档：docs/overview/数据面与采集总览.md

  2026-10-06 改：4 个 Tab 内容抽到 stock-info/components/data-board-tabs/ 复用，
  本页只保留路由 / symbol 切换 / 概览 header / 错误汇总。
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
        <div class="toolbar-search">
          <el-input
            v-model="symbol"
            placeholder="股票代码 6 位 (如 000001 / 600519)"
            style="width: 220px"
            clearable
            @keyup.enter="reload"
          />
          <el-button type="primary" :loading="loading" @click="reload">
            <el-icon class="mr-1"><Search /></el-icon>
            查询
          </el-button>
        </div>
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
        <div class="toolbar-quick">
          <span class="text-xs text-gray-500">快捷</span>
          <el-button
            v-for="q in QUICK_SYMBOLS"
            :key="q.symbol"
            size="small"
            :type="symbol === q.symbol ? 'primary' : 'default'"
            plain
            @click="switchQuickSymbol(q.symbol)"
          >{{ q.label }}</el-button>
        </div>
        <div class="toolbar-meta">
          <el-tag v-if="lastFetchAt" size="small" type="info" effect="plain" title="上次拉取时间">
            🕐 {{ lastFetchAt }} · {{ fmtMs(fetchElapsed) }}
          </el-tag>
          <el-tag v-if="errorCount > 0" size="small" type="danger" effect="dark" title="失败接口数">
            ⚠ {{ errorCount }} 个失败
          </el-tag>
        </div>
      </div>
    </template>

    <!-- 4 Tab 内容 -->
    <el-tabs v-model="activeTab" class="db-tabs">
      <el-tab-pane label="📈 技术面" name="tech">
        <TechPanel :symbol="symbol" :columns="2" :kline-height="320" />
      </el-tab-pane>

      <el-tab-pane label="💰 资金面" name="capital">
        <CapitalPanel :symbol="symbol" :columns="2" />
      </el-tab-pane>

      <el-tab-pane label="📊 基本面" name="fundamental">
        <div class="grid-2">
          <!-- 看板特有：股票基本信息（详情抽屉里已放 header 不重复） -->
          <el-card shadow="never">
            <template #header><span class="font-bold">股票基本信息</span></template>
            <div v-loading="loadingStock" class="info-grid">
              <template v-if="stockInfo">
                <div class="info-row"><label>代码</label><span class="mono">{{ stockInfo.symbol }}</span></div>
                <div class="info-row"><label>名称</label><span class="font-bold">{{ stockInfo.name }}</span></div>
                <div class="info-row"><label>行业</label>{{ stockInfo.industry || '—' }}</div>
                <div class="info-row"><label>市场</label>{{ stockInfo.market || '—' }}</div>
                <div class="info-row"><label>交易所</label>{{ stockInfo.exchange || '—' }}</div>
                <div class="info-row"><label>地域</label>{{ stockInfo.area || '—' }}</div>
                <div class="info-row"><label>上市日</label><span class="mono">{{ stockInfo.list_date || '—' }}</span></div>
                <div class="info-row"><label>沪深港通</label>{{ stockInfo.is_hs === 'N' ? '否' : stockInfo.is_hs }}</div>
                <div class="info-row"><label>法人</label>{{ stockInfo.act_name || '—' }}</div>
              </template>
              <div v-else-if="!loadingStock" class="text-gray-400 text-sm">暂无数据</div>
            </div>
          </el-card>

          <FundamentalPanel :symbol="symbol" :columns="2" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="📰 新闻面" name="news">
        <NewsPanel />
      </el-tab-pane>
    </el-tabs>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Search } from '@element-plus/icons-vue'
import PageWrapper from '@/components/PageWrapper.vue'
import TechPanel from '@/views/stock-info/components/data-board-tabs/TechPanel.vue'
import CapitalPanel from '@/views/stock-info/components/data-board-tabs/CapitalPanel.vue'
import FundamentalPanel from '@/views/stock-info/components/data-board-tabs/FundamentalPanel.vue'
import NewsPanel from '@/views/stock-info/components/data-board-tabs/NewsPanel.vue'
import * as API from './api-data-board'

// ── 路由参数（支持 /home/data-board/000001 直接进入） ──
const route = useRoute()
const router = useRouter()
const routeSymbol = () => {
  const raw = (route.params.symbol as string | undefined)?.trim()
  if (!raw) return ''
  return raw.padStart(6, '0')
}
const symbol = ref(routeSymbol() || '000001')

// 常用股票快捷切换
const QUICK_SYMBOLS = [
  { symbol: '000001', label: '平安银行' },
  { symbol: '600519', label: '贵州茅台' },
  { symbol: '000858', label: '五粮液' },
  { symbol: '300750', label: '宁德时代' },
  { symbol: '600036', label: '招商银行' },
]
function switchQuickSymbol(s: string) {
  if (s === symbol.value) return
  symbol.value = s
  reload()
}

// 路由变化时重新加载（仅当 symbol 真的变了）
watch(() => routeSymbol(), (next) => {
  if (next && next !== symbol.value) {
    symbol.value = next
    loadAll()
  }
})
const activeTab = ref('tech')
const loading = ref(false)

const overview = ref<API.OverviewPanel | null>(null)

// 基本面「股票基本信息」卡（4 子组件没暴露，保留看板特有的 stock info）
const stockInfo = ref<API.StockInfo | null>(null)
const loadingStock = ref(false)

// 拉取耗时 + 错误计数（顶部显示）
const fetchElapsed = ref(0)  // ms
const lastFetchAt = ref<string | null>(null)
const errorCount = ref(0)

// ── 工具 ──
function fmtMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}
function fmtNow(): string {
  return new Date().toTimeString().slice(0, 8)
}

// ── 加载 ──
async function loadAll() {
  const s = symbol.value.trim().padStart(6, '0')
  if (!/^\d{6}$/.test(s)) {
    ElMessage.warning('请输入 6 位股票代码')
    return
  }
  loading.value = true
  errorCount.value = 0
  const t0 = performance.now()

  // 概览（4 面综合统计）
  try {
    overview.value = await API.getOverviewPanel(s)
  } catch (e) {
    errorCount.value++
    console.warn('[DataBoard] getOverviewPanel failed', e)
  }

  // 基本面里独有的「股票基本信息」卡（抽屉 header 已展示，看板仍要显示）
  loadingStock.value = true
  try {
    stockInfo.value = await API.getStockInfo(s)
  } catch (e) {
    errorCount.value++
    console.warn('[DataBoard] getStockInfo failed', e)
    stockInfo.value = null
  } finally {
    loadingStock.value = false
  }

  // 4 个子组件各自按 watch(symbol) 触发自身加载；这里只汇总耗时
  fetchElapsed.value = Math.round(performance.now() - t0)
  lastFetchAt.value = fmtNow()
  loading.value = false
}

function reload() {
  const s = symbol.value.trim().padStart(6, '0')
  // 同步到路由（这样刷新 / 收藏 / 分享 都能复用）
  if (route.params.symbol !== s) {
    router.replace({ name: 'DataBoard', params: { symbol: s } })
  }
  loadAll()
}

onMounted(loadAll)
</script>

<style scoped>
.db-page { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.page-title-text { font-size: 0.75rem; color: #94a3b8; margin-left: 0.5rem; font-weight: 400; }

.toolbar-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; flex-wrap: wrap;
}
.toolbar-search { display: flex; gap: 0.5rem; align-items: center; }
.toolbar-tags { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.toolbar-quick { display: flex; gap: 0.25rem; align-items: center; flex-wrap: wrap; }
.toolbar-meta { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }

.db-tabs { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.db-tabs :deep(.el-tabs__content) { flex: 1; min-height: 0; overflow: auto; }

.grid-2 {
  display: grid; grid-template-columns: 1fr 2fr;
  gap: 0.75rem; padding: 0.5rem 0;
}
@media (max-width: 1100px) { .grid-2 { grid-template-columns: 1fr; } }

.mono { font-family: ui-monospace, monospace; font-weight: 600; }
.font-bold { font-weight: 700; }

.info-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem 1rem;
  padding: 0.5rem;
}
.info-row { display: flex; gap: 0.5rem; align-items: center; padding: 0.25rem 0; border-bottom: 1px solid #f1f5f9; }
.info-row label { color: #94a3b8; min-width: 70px; font-size: 0.85rem; }

.db-page :deep(.top-area__header) { min-height: 2.5rem; height: 2.5rem; max-height: 2.5rem; }
.db-page :deep(.top-area__title) { min-width: 0; }
</style>
