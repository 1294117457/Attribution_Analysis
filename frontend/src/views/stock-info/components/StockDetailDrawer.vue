<!--
 * components/StockDetailDrawer.vue
 *
 * 股票详情抽屉（骨架见 components/DetailDrawer.vue 与 docs/frontend-docs/detail-drawer-guide.md）
 *
 *   top-button-area  加入操作池 / K线分析
 *   baseinfo-area    「基本信息」：股票名称 / 股票代码 / 市场 / 行业 / 交易所 / 地域 / 上市日 / 实控人 / 企业性质
 *   main-area        「数据面」：技术面 / 资金面 / 基本面 / 新闻面 / 概念（Tab）
 *                    4 个数据面复用 data-board-tabs/*，columns=1（480px 抽屉强制单列）
 -->
<template>
  <DetailDrawer
    v-model="visible"
    v-model:active="activeTab"
    :actions="actions"
    :fields="fields"
    main-title="数据面"
    :panels="PANELS"
    @action="onAction"
  >
    <template #panel-tech>
      <TechPanel
        v-if="stock"
        :symbol="stock.symbol"
        :columns="1"
        :kline-height="180"
        :kline-sub="false"
      />
    </template>
    <template #panel-capital>
      <CapitalPanel v-if="stock" :symbol="stock.symbol" :columns="1" />
    </template>
    <template #panel-fundamental>
      <FundamentalPanel v-if="stock" :symbol="stock.symbol" :columns="1" />
    </template>
    <template #panel-news>
      <NewsPanel />
    </template>
    <template #panel-concepts>
      <ConceptTab
        v-if="stock"
        :symbol="stock.symbol"
        :stock-name="stock.name"
        @concept-click="onConceptClick"
      />
    </template>
  </DetailDrawer>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Folder, DataLine } from '@element-plus/icons-vue'
import DetailDrawer, {
  type DetailDrawerAction,
  type DetailDrawerField,
  type DetailDrawerPanel,
} from '@/components/DetailDrawer.vue'
import TechPanel from './data-board-tabs/TechPanel.vue'
import CapitalPanel from './data-board-tabs/CapitalPanel.vue'
import FundamentalPanel from './data-board-tabs/FundamentalPanel.vue'
import NewsPanel from './data-board-tabs/NewsPanel.vue'
import ConceptTab from './ConceptTab.vue'
import type { StockInfo, ConceptGroupedVO } from '@/views/stock-info/api'

const props = defineProps<{
  stock: StockInfo | null
  /** 抽屉首次打开时是否立即加载「概念」Tab 数据（默认 true） */
  prefetchConcepts?: boolean
}>()

const emit = defineEmits<{
  addToPool: []
  goAnalysis: []
}>()

const visible = defineModel<boolean>({ required: true })
const activeTab = ref('tech')

const PANELS: DetailDrawerPanel[] = [
  { name: 'tech', label: '📈 技术面' },
  { name: 'capital', label: '💰 资金面' },
  { name: 'fundamental', label: '📊 基本面' },
  { name: 'news', label: '📰 新闻面' },
  { name: 'concepts', label: '概念' },
]

const actions: DetailDrawerAction[] = [
  { key: 'addToPool', label: '加入操作池', icon: Folder, type: 'success' },
  { key: 'goAnalysis', label: 'K线分析', icon: DataLine, type: 'primary' },
]

const fields = computed<DetailDrawerField[]>(() => {
  const s = props.stock
  if (!s) return []
  return [
    { label: '股票名称', value: s.name || '—' },
    { label: '股票代码', value: s.ts_code || s.symbol || '—' },
    { label: '市场', value: s.market || '—' },
    { label: '行业', value: s.industry || '—' },
    { label: '交易所', value: exchangeLabel(s.exchange) },
    { label: '地域', value: s.area || '—' },
    { label: '上市日', value: formatDate(s.list_date) || '—' },
    { label: '实控人', value: s.act_name || '—' },
    { label: '企业性质', value: s.act_ent_type || '—' },
  ]
})

function onAction(key: string) {
  if (key === 'addToPool') emit('addToPool')
  else if (key === 'goAnalysis') emit('goAnalysis')
}

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