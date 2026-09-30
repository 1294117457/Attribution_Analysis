<!--
 * components/ConceptTab.vue
 *
 * 详情抽屉「概念」Tab 的内容组件。
 *
 * 数据流：
 *   props.symbol → watch → getConceptTabForSymbol(symbol) → data
 *   data.sections → v-for 渲染分组（组内按当日涨跌幅降序）
 *   交易时段每 15 秒 getConceptQuotes 刷新行情（useRealtimePoll）
 *   ConceptTag 点击 → emit('conceptClick', c) → 由 StockDetailDrawer 上抛
 *
 * 配套设计文档：docs/dev/06gainian/04-frontend-detail-design.md §2.4.2
 *               docs/dev/08concept/04-frontend-stockinfo.md §三
 *
 * 08concept 增量：
 * - 顶部加 "🔄 实时刷新" 按钮，调 getConceptTabForSymbolMerged
 * - 合并状态显示："数据库数据" / "实时数据（已合并 adata）"
 * - 实时数据点击 ConceptTag 时弹入选理由（reason）
 -->
<template>
  <div v-loading="loading" class="concept-tab">
    <!-- 骨架屏：抽屉刚打开、用户尚未看热词时 -->
    <div v-if="!data && loading" class="concept-skeleton">
      <el-skeleton :rows="4" animated />
    </div>

    <!-- 正常渲染 -->
    <template v-else-if="data">
      <!-- 顶部工具栏：数据来源标识 + 实时刷新按钮 -->
      <div class="concept-toolbar">
        <div class="toolbar-left">
          <el-icon class="text-gray-400" :size="14"><DataLine /></el-icon>
          <span class="text-sm text-gray-700">
            {{ merged ? '实时数据（已合并 adata）' : '数据库数据' }}
          </span>
          <el-tag v-if="merged" size="small" type="success" effect="plain">
            ✓ 已合并
          </el-tag>
          <span v-if="merged && data.last_merged_at" class="text-xs text-gray-400">
            {{ formatRelativeTime(data.last_merged_at) }}
          </span>
          <el-tag v-if="trading && !paused" size="small" type="danger" effect="plain">实时 · 15 秒</el-tag>
          <el-tag v-else-if="!trading" size="small" type="info" effect="plain">已收盘</el-tag>
          <el-link v-if="paused" type="warning" :underline="false" class="text-xs" @click="resume">
            实时更新已暂停 · 重试
          </el-link>
        </div>
        <el-button
          size="small"
          type="primary"
          link
          :loading="loading && merged"
          @click="onLiveRefresh"
        >
          <el-icon class="mr-1"><Refresh /></el-icon>
          🔄 实时刷新
        </el-button>
      </div>

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
              v-for="(c, idx) in section.concepts"
              :key="(c.concept_id ?? '') + '-' + c.name + '-' + idx"
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
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, DataLine } from '@element-plus/icons-vue'
import {
  getConceptQuotes,
  getConceptTabForSymbol,
  getConceptTabForSymbolMerged,
  type ConceptTabContentVO,
  type ConceptGroupedVO,
} from '@/views/stock-info/api'
import { useRealtimePoll } from '@/composables/useRealtimePoll'
import ConceptTag from './ConceptTag.vue'

const props = defineProps<{
  symbol: string
  stock_name?: string
}>()

const emit = defineEmits<{
  conceptClick: [c: ConceptGroupedVO]
}>()

const loading = ref(false)
const data = ref<ConceptTabContentVO | null>(null)
// 🆕 跟踪当前数据是否经过实时合并
const merged = ref(false)

async function load() {
  if (!props.symbol) return
  loading.value = true
  try {
    data.value = await getConceptTabForSymbol(props.symbol, {
      stock_name: props.stock_name,
    })
    merged.value = false
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

/** 只刷新行情（15 秒），不重新查概念归属；各分组内按涨跌幅重新排序 */
async function refreshQuotes() {
  const sections = data.value?.sections
  if (!sections?.length) return
  const codes = sections.flatMap((s) => s.concepts.map((c) => c.index_code || c.concept_code || ''))
  const unique = [...new Set(codes.filter(Boolean))]
  if (!unique.length) return
  const quotes = await getConceptQuotes(unique)
  for (const s of sections) {
    for (const c of s.concepts) {
      const q = quotes[c.index_code || c.concept_code || '']
      if (q) c.snapshot = q
    }
    s.concepts.sort((a, b) => {
      const pa = a.snapshot?.pct_change
      const pb = b.snapshot?.pct_change
      if (pa == null && pb == null) return a.name.localeCompare(b.name)
      if (pa == null) return 1
      if (pb == null) return -1
      return pb - pa
    })
  }
}

const { paused, trading, resume } = useRealtimePoll(refreshQuotes, { interval: 15_000 })

/**
 * 🆕 实时刷新：合并 adata 实时数据
 *
 * 数据源优先级：
 * - DB（list_concepts_by_symbol_grouped）
 * - adata（fetch_concepts_by_stock，按股票反查 + 入选理由）
 *
 * 失败容忍：
 * - adata 网络断开 → 仅返回 DB 数据（is_merged=true 但仅 DB 部分）
 * - adata 超时 → ElMessage.error，不重置 merged
 */
async function onLiveRefresh() {
  if (loading.value) return  // 防抖
  loading.value = true
  try {
    data.value = await getConceptTabForSymbolMerged(props.symbol, {
      stock_name: props.stock_name,
    })
    merged.value = true
    ElMessage.success(
      `已合并 ${data.value?.total_count ?? 0} 个概念${data.value?.is_merged ? '（含 adata 入选理由）' : ''}`,
    )
  } catch (e) {
    ElMessage.error('实时刷新失败: ' + (e as Error).message)
  } finally {
    loading.value = false
  }
}

/**
 * Tag 点击：有 reason（库中或实时）时弹入选理由，否则走原有逻辑（emit + toast 占位）
 */
async function onTagClick(c: ConceptGroupedVO & {
  concept_code?: string | null
  is_realtime?: boolean
}) {
  if (c.reason) {
    await ElMessageBox.alert(c.reason, `${c.name} · 入选理由${c.is_realtime ? '（实时）' : ''}`, {
      confirmButtonText: '关闭',
      type: 'info',
    })
  } else {
    emit('conceptClick', c as ConceptGroupedVO)
    ElMessage.info(`点击了概念：${c.name}（${c.source}）`)
  }
}

/**
 * 🆕 相对时间格式化（"3 分钟前"）
 */
function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  const diff = Date.now() - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  return new Date(iso).toLocaleString('zh-CN')
}

watch(() => props.symbol, () => {
  // 🆕 切换股票时重置合并状态
  merged.value = false
  load()
}, { immediate: true })
</script>

<style scoped>
.concept-tab {
  min-height: 200px;
}

.concept-skeleton {
  padding: 8px 0;
}

/* 🆕 顶部工具栏 */
.concept-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0 12px 0;
  margin-bottom: 8px;
  border-bottom: 1px dashed #e5e7eb;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 6px;
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

.concept-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px dashed #e5e7eb;
  margin-top: 8px;
}
</style>
