<!--
 * components/StockDetailDrawer.vue
 *
 * 股票详情抽屉
 *
 * 结构（2026-10-06 改）：
 *   header 槽   ── 代码 + 名称 + 副信息（紧凑：6 个关键字段 inline 列出）
 *   tabs         ── 📈 技术面 / 💰 资金面 / 📊 基本面 / 📰 新闻面 / 概念
 *                    （4 个基本面复刻自 DataBoard，详见 data-board-tabs/*）
 *   底部按钮   ── 「加入操作池」+「打开 K 线分析页」
 *
 * 改动要点：
 *   1. 移除原「K线图」Tab —— 完整 CandleChart 在分析页；本抽屉的技术面
 *      MiniKlineChart 已能浏览走势，**不内置「拉取 K 线」**。
 *   2. 原「基本信息」Tab 拆出 → **el-drawer header 槽**（始终可见，无需切 tab）。
 *      header 默认是单行 title + 关闭按钮，最多再塞一行副信息 + 几个 inline 标签。
 *      8 行带边框 el-descriptions 放这里太占地，因此改成 6 字段紧凑列表：
 *        代码 · 名称 · TS代码 · 交易所 · 市场 · 行业 · 地域 · 上市日 · 实控人 · 企业性质
 *      关键 5 项 inline 顶行；剩余 5 项次行 2 列 grid，超出折叠由 header 槽的
 *      `el-drawer__header` 自带 max-height 限制（结合 `header-style`）。
 *   3. 4 个 Tab 内容复用 data-board-tabs/，columns=1（480px 抽屉强制单列）。
 *   4. 保留「概念」Tab（实时刷新 + 选中展开指数 K 线 / 分时）。
 -->
<template>
  <el-drawer
    :model-value="modelValue"
    size="480px"
    direction="rtl"
    :with-header="true"
    :header-style="headerStyle"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <!-- ═══════ el-drawer header 槽（替代原「基本信息」Tab）═══════
     *
     * 默认 el-drawer header 是「title + 关闭按钮」一行；
     * 覆盖成自渲染：
     *   第 1 行：代码 + 名称（大字）+ tag
     *   第 2 行：副信息（TS代码/市场/行业，gray 5 字号）
     *   第 3 行：6 个核心字段 inline（交易所/地域/上市日/实控人/企业性质）
     *            —— 高度控制在 2 行内
     * 不再使用占满 8 行的 el-descriptions，紧凑度 +50%。
     * -->
    <template #header="{ close }">
      <div class="header-content">
        <div class="header-line-1">
          <span class="text-lg font-bold text-gray-900">{{ stock?.symbol }}</span>
          <el-tag size="small" class="ml-2">{{ stock?.name }}</el-tag>
          <el-button
            link
            class="header-close"
            aria-label="关闭"
            @click="close"
          >
            <el-icon :size="18"><Close /></el-icon>
          </el-button>
        </div>
        <div v-if="stock" class="header-line-2 text-xs text-gray-500">
          {{ stock.ts_code }} · {{ stock.market }} · {{ stock.industry || '—' }}
        </div>
        <div v-if="stock" class="header-line-3">
          <span class="kv"><label>交易所</label>{{ exchangeLabel(stock.exchange) }}</span>
          <span class="kv"><label>地域</label>{{ stock.area || '—' }}</span>
          <span class="kv"><label>上市日</label>{{ formatDate(stock.list_date) }}</span>
          <span class="kv"><label>实控人</label>{{ stock.act_name || '—' }}</span>
          <span class="kv"><label>性质</label>{{ stock.act_ent_type || '—' }}</span>
        </div>
      </div>
    </template>

    <template v-if="stock">
      <!-- ═══════ Tab 区：4 面数据 + 概念 ═══════ -->
      <el-tabs v-model="activeTab" class="drawer-tabs">
        <el-tab-pane label="📈 技术面" name="tech">
          <TechPanel :symbol="stock.symbol" :columns="1" :kline-height="240" />
        </el-tab-pane>

        <el-tab-pane label="💰 资金面" name="capital">
          <CapitalPanel :symbol="stock.symbol" :columns="1" />
        </el-tab-pane>

        <el-tab-pane label="📊 基本面" name="fundamental">
          <FundamentalPanel :symbol="stock.symbol" :columns="1" />
        </el-tab-pane>

        <el-tab-pane label="📰 新闻面" name="news">
          <NewsPanel />
        </el-tab-pane>

        <el-tab-pane label="概念" name="concepts">
          <ConceptTab
            v-if="stock"
            :symbol="stock.symbol"
            :stock-name="stock.name"
            @concept-click="onConceptClick"
          />
        </el-tab-pane>
      </el-tabs>

      <!-- ═══════ 底部：操作按钮（始终可见）═══════ -->
      <div class="mt-2 space-y-2 sticky-actions">
        <el-button type="success" class="w-full" @click="$emit('addToPool')">
          <el-icon class="mr-1"><Folder /></el-icon>
          加入操作池
        </el-button>
        <el-button type="primary" class="w-full" @click="$emit('goAnalysis')">
          <el-icon class="mr-1"><DataLine /></el-icon>
          打开 K 线分析页
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Close, Folder, DataLine } from '@element-plus/icons-vue'
import TechPanel from './data-board-tabs/TechPanel.vue'
import CapitalPanel from './data-board-tabs/CapitalPanel.vue'
import FundamentalPanel from './data-board-tabs/FundamentalPanel.vue'
import NewsPanel from './data-board-tabs/NewsPanel.vue'
import ConceptTab from './ConceptTab.vue'
import type { StockInfo, ConceptGroupedVO } from '@/views/stock-info/api'

const props = defineProps<{
  modelValue: boolean
  stock: StockInfo | null
  /** 抽屉首次打开时是否立即加载「概念」Tab 数据（默认 true） */
  prefetchConcepts?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
  addToPool: []
  goAnalysis: []
}>()

const activeTab = ref('tech')

// 紧凑 header：去掉默认 padding，让 3 行更密；高度由内容驱动（不写死）
const headerStyle = {
  padding: '10px 16px',
  borderBottom: '1px solid #f1f5f9',
}

watch(() => props.modelValue, (visible) => {
  if (visible) activeTab.value = 'tech'
})

function formatDate(v?: string) {
  if (!v) return ''
  return String(v).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
}

function exchangeLabel(v?: string) {
  const map: Record<string, string> = { SSE: '上交所', SZSE: '深交所', BSE: '北交所' }
  return map[v || ''] || v || '—'
}

function onConceptClick(c: ConceptGroupedVO) {
  // 占位：未来跳到概念详情页 / 打开新抽屉
  console.log('[StockDetailDrawer] concept click', c)
}
</script>

<style scoped>
/* ── header 紧凑布局 ─────────────────────────────────── */
.header-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  min-width: 0;
}
.header-line-1 {
  display: flex;
  align-items: center;
  /* 留出右侧 EP 默认关闭按钮的位置，避免被遮挡 */
  padding-right: 32px;
}
.header-line-2 {
  line-height: 1.2;
}
.header-line-3 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px 12px;
  font-size: 12px;
  line-height: 1.4;
  color: #475569;
  margin-top: 2px;
}
.header-line-3 .kv {
  display: flex;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-line-3 .kv label {
  color: #94a3b8;
  flex: 0 0 auto;
}
/* 自渲关闭按钮——让出 header 行内空间 */
:deep(.header-close) {
  position: absolute !important;
  top: 8px;
  right: 8px;
}

/* ── 抽屉体需要内部滚动，sticky 按钮始终可见 ─────────── */
:deep(.el-drawer__body) {
  display: flex;
  flex-direction: column;
  padding-bottom: 0;
}
.drawer-tabs {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.drawer-tabs :deep(.el-tabs__content) {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.sticky-actions {
  position: sticky;
  bottom: 0;
  background: #fff;
  padding: 8px 0 12px 0;
  border-top: 1px solid #f1f5f9;
  z-index: 2;
}
</style>
