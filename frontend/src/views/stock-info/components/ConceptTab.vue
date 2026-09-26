<!--
 * components/ConceptTab.vue
 *
 * 详情抽屉「概念」Tab 的内容组件。
 *
 * 数据流：
 *   props.symbol → watch → getConceptTabForSymbol(symbol) → data
 *   data.sections → v-for 渲染分组
 *   ConceptTag 点击 → emit('conceptClick', c) → 由 StockDetailDrawer 上抛
 *
 * 配套设计文档：docs/dev/06gainian/04-frontend-detail-design.md §2.4.2
 -->
<template>
  <div v-loading="loading && !data" class="concept-tab">
    <!-- 骨架屏：抽屉刚打开、用户尚未看热词时 -->
    <div v-if="!data && loading" class="concept-skeleton">
      <el-skeleton :rows="4" animated />
    </div>

    <!-- 正常渲染 -->
    <template v-else-if="data">
      <!-- 空状态 -->
      <el-empty
        v-if="data.sections.length === 0"
        description="该股票暂无概念归属"
        :image-size="80"
      />

      <!-- 分组渲染 -->
      <div v-else>
        <div
          v-for="section in data.sections"
          :key="section.type"
          class="concept-section"
        >
          <div class="section-title">
            <span class="title-text">{{ section.type_label }}</span>
            <el-tag size="small" type="info" effect="plain">
              {{ section.concepts.length }}
            </el-tag>
          </div>
          <div class="concept-list">
            <ConceptTag
              v-for="c in section.concepts"
              :key="c.concept_id"
              :concept="c"
              @click="onTagClick"
            />
          </div>
        </div>

        <!-- 底部汇总 + 刷新 -->
        <div class="concept-footer">
          <span class="text-xs text-gray-500">
            共 <b class="text-gray-900">{{ data.total_count }}</b> 个概念
          </span>
          <el-link type="primary" :underline="false" @click="reload">
            <el-icon class="mr-1"><Refresh /></el-icon>刷新
          </el-link>
        </div>
      </div>
    </template>

    <!-- 🆕 预热简略版：full data 还没回来时，先用 preheat 渲染一组 chip
         命中目标：抽屉打开瞬间不再有「空白骨架屏」，用户立刻看到概念归属 -->
    <div v-else-if="preheatConcepts && preheatConcepts.length > 0" class="concept-section">
      <div class="section-title">
        <span class="title-text">所属概念</span>
        <el-tag size="small" type="info" effect="plain">
          {{ preheatConcepts.length }}
        </el-tag>
        <span class="text-xs text-gray-400 ml-1">（预热数据，加载完成后展示分组）</span>
      </div>
      <div class="concept-list">
        <el-tag
          v-for="c in preheatConcepts"
          :key="`${c.source}:${c.concept_id}`"
          size="small"
          :type="sourceTagType(c.source)"
          effect="plain"
          round
          class="concept-preheat-chip"
        >
          {{ c.name }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  getConceptTabForSymbol,
  type ConceptTabContentVO,
  type ConceptGroupedVO,
  type ConceptBrief,
  type ConceptSource,
} from '@/views/stock-info/api'
import ConceptTag from './ConceptTag.vue'

const props = defineProps<{
  symbol: string
  stock_name?: string
  /**
   * 列表阶段预热的概念简略版（ConceptBrief[]）。
   * 由父组件 StockDetailDrawer 从 useStockDetailDrawer.preheatConcepts 透传。
   * 抽屉打开瞬间即可渲染，无需等待 /concepts/tab-by-symbol 接口。
   */
  preheatConcepts?: ConceptBrief[]
}>()

const emit = defineEmits<{
  conceptClick: [c: ConceptGroupedVO]
}>()

const loading = ref(false)
const data = ref<ConceptTabContentVO | null>(null)

async function load() {
  if (!props.symbol) return
  loading.value = true
  try {
    data.value = await getConceptTabForSymbol(props.symbol, {
      stock_name: props.stock_name,
    })
  } catch (e) {
    ElMessage.error('加载概念失败: ' + (e as Error).message)
    data.value = null
  } finally {
    loading.value = false
  }
}

async function reload() {
  await load()
}

function onTagClick(c: ConceptGroupedVO) {
  emit('conceptClick', c)
  // 占位反馈：未来跳到概念详情页
  ElMessage.info(`点击了概念：${c.name}（${c.source}）`)
}

/** 预热 chip 的染色：与 StockInfoList 表格保持一致 */
function sourceTagType(source: ConceptSource): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  return ({ em: 'primary', ths: 'success' } as const)[source] || 'info'
}

watch(() => props.symbol, load, { immediate: true })
</script>

<style scoped>
.concept-tab {
  min-height: 200px;
}

.concept-skeleton {
  padding: 8px 0;
}

.concept-section {
  margin-bottom: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  border-left: 3px solid #3b82f6;
  padding-left: 8px;
}

.title-text {
  letter-spacing: 0.5px;
}

.concept-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  min-height: 24px;
}

/* 🆕 预热 chip：与正式 ConceptTag 区分透明度，避免视觉混淆 */
.concept-preheat-chip {
  margin: 0 4px 6px 0;
  opacity: 0.85;
  transition: opacity 0.2s ease;
}

.concept-preheat-chip:hover {
  opacity: 1;
}

.concept-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px dashed #e5e7eb;
  margin-top: 8px;
}
</style>
