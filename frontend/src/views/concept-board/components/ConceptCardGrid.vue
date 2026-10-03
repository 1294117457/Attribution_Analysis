<template>
  <div class="grid-card">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold">🗂️ 概念卡片</span>
          <span class="text-xs text-gray-500">共 {{ props.items.length }} 个</span>
        </div>
      </template>

      <div v-loading="loading" class="grid-body">
        <div v-for="group in grouped" :key="group.type" class="type-group">
          <!-- 单 type 模式隐藏分组标题（避免"行业概念（N）"下面全是同 type 的视觉冗余） -->
          <div v-if="grouped.length > 1" class="type-group__title">
            {{ group.label }}（{{ group.items.length }}）
          </div>
          <div class="type-grid">
            <div
              v-for="item in group.items"
              :key="item.concept_id"
              class="concept-tile"
              :class="`concept-tile--${item.color}`"
              @click="$emit('pick', item)"
            >
              <div class="concept-tile__name" :title="item.name">
                {{ item.name }}
              </div>
              <div class="concept-tile__pct">
                {{ formatPct(item.pct_change) }}
              </div>
              <div class="concept-tile__count">
                {{ item.stock_count }} 成分
                <span v-if="item.stale" class="stale-tag">STALE</span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="!grouped.length" class="text-center text-gray-400 py-8">
          暂无数据
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ConceptBoardItem } from '../../api'

const props = defineProps<{
  items: ConceptBoardItem[]
  loading: boolean
}>()
defineEmits<{ (e: 'pick', c: ConceptBoardItem): void }>()

const TYPE_LABELS: Record<string, string> = {
  industry: '行业概念',
  theme: '主题概念',
  style: '风格概念',
  region: '地域概念',
  event: '事件概念',
  other: '其他概念',
}
const TYPE_ORDER = ['industry', 'theme', 'style', 'region', 'event', 'other']

/**
 * 分组逻辑
 * - 单 type（用户已筛选某一 type）：不再分组，直接平铺；分组标题隐藏
 * - 多 type（type_filter=all）：按 TYPE_ORDER 分组；每组最多 8 个
 *
 * 单 type 模式去掉 .slice(0, 8) 限制，确保用户能看到所有该 type 的概念
 */
const grouped = computed(() => {
  const typeSet = new Set(props.items.map((i) => i.concept_type))
  if (typeSet.size <= 1) {
    // 单 type 模式：平铺, 无 .slice
    const t = props.items[0]?.concept_type ?? 'all'
    return [{
      type: t,
      label: TYPE_LABELS[t] ?? '全部',
      items: [...props.items]
        .sort((a, b) => (b.pct_change ?? -999) - (a.pct_change ?? -999)),
    }]
  }
  // 多 type 模式：按 type 分组, 每组 .slice(0, 8)
  return TYPE_ORDER.map((t) => ({
    type: t,
    label: TYPE_LABELS[t],
    items: props.items
      .filter((i) => i.concept_type === t)
      .sort((a, b) => (b.pct_change ?? -999) - (a.pct_change ?? -999))
      .slice(0, 8),
  })).filter((g) => g.items.length > 0)
})

function formatPct(p: number | null): string {
  if (p == null) return '—'
  const sign = p > 0 ? '+' : ''
  return `${sign}${p.toFixed(2)}%`
}
</script>

<style scoped>
.grid-card { height: 100%; }
.grid-card :deep(.el-card) { height: 100%; }
.grid-card :deep(.el-card__body) { height: calc(100% - 56px); padding: 0.75rem; overflow: auto; }
.grid-body { padding: 0.25rem; }

.type-group { margin-bottom: 1rem; }
.type-group__title {
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.5rem;
}

.concept-tile {
  padding: 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  border-left: 4px solid #94a3b8;
  background: #f8fafc;
  transition: transform 0.15s, box-shadow 0.15s;
}
.concept-tile:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.concept-tile--up {
  border-left-color: #ef4444;
  background: linear-gradient(135deg, #fef2f2, #fff);
}
.concept-tile--down {
  border-left-color: #16a34a;
  background: linear-gradient(135deg, #f0fdf4, #fff);
}
.concept-tile--flat { border-left-color: #94a3b8; background: #f8fafc; }
.concept-tile__name {
  font-weight: 600;
  font-size: 0.875rem;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.concept-tile__pct {
  font-family: ui-monospace;
  font-weight: 700;
  font-size: 1.125rem;
  margin: 0.25rem 0;
}
.concept-tile--up .concept-tile__pct { color: #dc2626; }
.concept-tile--down .concept-tile__pct { color: #16a34a; }
.concept-tile--flat .concept-tile__pct { color: #94a3b8; }
.concept-tile__count {
  font-size: 0.75rem;
  color: #94a3b8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stale-tag {
  font-size: 0.625rem;
  padding: 0 0.25rem;
  border-radius: 2px;
  background: #fee2e2;
  color: #dc2626;
}
</style>
