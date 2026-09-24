<template>
  <el-drawer
    :model-value="modelValue"
    :title="stock?.name || '股票详情'"
    size="480px"
    direction="rtl"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template v-if="stock">
      <div class="px-1">
        <div class="detail-header mb-4">
          <div class="text-xl font-bold text-gray-900">
            {{ stock.symbol }}
            <el-tag size="small" class="ml-2">{{ stock.name }}</el-tag>
          </div>
          <div class="text-xs text-gray-500 mt-1">
            {{ stock.ts_code }} · {{ stock.market }} · {{ stock.industry || '—' }}
          </div>
        </div>

        <el-tabs v-model="activeTab" class="drawer-tabs">
          <el-tab-pane label="基本信息" name="info">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="TS代码">{{ stock.ts_code }}</el-descriptions-item>
              <el-descriptions-item label="交易所">{{ exchangeLabel(stock.exchange) }}</el-descriptions-item>
              <el-descriptions-item label="市场">{{ stock.market || '—' }}</el-descriptions-item>
              <el-descriptions-item label="行业">{{ stock.industry || '—' }}</el-descriptions-item>
              <el-descriptions-item label="地域">{{ stock.area || '—' }}</el-descriptions-item>
              <el-descriptions-item label="上市日期">{{ formatDate(stock.list_date) }}</el-descriptions-item>
              <el-descriptions-item label="实控人">{{ stock.act_name || '—' }}</el-descriptions-item>
              <el-descriptions-item label="企业性质">{{ stock.act_ent_type || '—' }}</el-descriptions-item>
            </el-descriptions>

            <div class="mt-4 space-y-2">
              <el-button type="success" class="w-full" @click="$emit('addToPool')">
                <el-icon class="mr-1"><Folder /></el-icon>
                加入操作池
              </el-button>
              <el-button type="primary" class="w-full" @click="$emit('goAnalysis')">
                <el-icon class="mr-1"><DataLine /></el-icon>
                打开 K 线分析页
              </el-button>
            </div>
          </el-tab-pane>

          <el-tab-pane label="K 线图" name="kline">
            <KLineDrawerTab :symbol="stock.symbol" />
          </el-tab-pane>

          <el-tab-pane label="概念" name="concepts">
            <ConceptTab
              v-if="stock"
              :symbol="stock.symbol"
              :stock-name="stock.name"
              @concept-click="onConceptClick"
            />
          </el-tab-pane>

          <el-tab-pane label="归因分析" name="analysis">
            <div class="flex flex-col items-center justify-center py-8 gap-4">
              <div class="text-gray-500 text-sm text-center">
                完整归因分析需要更多数据支持,<br>点击下方按钮进入分析页。
              </div>
              <el-button type="primary" @click="$emit('goAnalysis')">
                <el-icon class="mr-1"><DataLine /></el-icon>
                打开分析页
              </el-button>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Folder, DataLine } from '@element-plus/icons-vue'
import KLineDrawerTab from './KLineDrawerTab.vue'
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

const activeTab = ref('info')

watch(() => props.modelValue, (visible) => {
  if (visible) activeTab.value = 'info'
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
.detail-header {
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
</style>
