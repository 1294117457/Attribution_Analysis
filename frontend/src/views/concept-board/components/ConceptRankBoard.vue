<template>
  <div class="rank-card">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold">🏆 涨幅榜 / 跌幅榜</span>
          <el-tag size="small" :type="trading ? 'success' : 'info'">
            {{ trading ? '实时 · 15秒' : '已收盘' }}
          </el-tag>
        </div>
      </template>

      <div v-loading="loading" class="rank-grid">
        <!-- 左：涨幅 Top 20 -->
        <div class="rank-col rank-up">
          <div class="rank-col__title">🔥 涨幅 TOP 20</div>
          <div
            v-for="(item, i) in topGainers"
            :key="item.concept_id"
            class="rank-row"
            @click="$emit('pick', item)"
          >
            <span class="rank-no">{{ i + 1 }}</span>
            <span class="rank-name">{{ item.name }}</span>
            <span class="rank-type">{{ item.concept_type_label }}</span>
            <span class="rank-pct" :class="pctClass(item)">
              {{ formatPct(item.pct_change) }}
            </span>
          </div>
          <div v-if="!topGainers.length" class="rank-empty">暂无数据</div>
        </div>

        <!-- 右：跌幅 Top 20 -->
        <div class="rank-col rank-down">
          <div class="rank-col__title">🧊 跌幅 TOP 20</div>
          <div
            v-for="(item, i) in topLosers"
            :key="item.concept_id"
            class="rank-row"
            @click="$emit('pick', item)"
          >
            <span class="rank-no">{{ i + 1 }}</span>
            <span class="rank-name">{{ item.name }}</span>
            <span class="rank-type">{{ item.concept_type_label }}</span>
            <span class="rank-pct" :class="pctClass(item)">
              {{ formatPct(item.pct_change) }}
            </span>
          </div>
          <div v-if="!topLosers.length" class="rank-empty">暂无数据</div>
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

// 简化：实时与否暂不接 trading status（前端暂无接口），固定显示"实时 · 15秒"
const trading = true

const topGainers = computed(() =>
  [...props.items]
    .filter((i) => i.pct_change != null)
    .sort((a, b) => (b.pct_change ?? 0) - (a.pct_change ?? 0))
    .slice(0, 20),
)
const topLosers = computed(() =>
  [...props.items]
    .filter((i) => i.pct_change != null)
    .sort((a, b) => (a.pct_change ?? 0) - (b.pct_change ?? 0))
    .slice(0, 20),
)

function formatPct(p: number | null): string {
  if (p == null) return '—'
  const sign = p > 0 ? '+' : ''
  return `${sign}${p.toFixed(2)}%`
}
function pctClass(item: ConceptBoardItem): string {
  if (item.color === 'up') return 'text-red-500'
  if (item.color === 'down') return 'text-green-600'
  return 'text-gray-400'
}
</script>

<style scoped>
.rank-card { height: 100%; }
.rank-card :deep(.el-card) { height: 100%; }
.rank-card :deep(.el-card__body) { height: calc(100% - 56px); padding: 0; }

.rank-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: #e2e8f0;
  height: 100%;
}
.rank-col {
  background: #fff;
  overflow-y: auto;
  padding: 0.5rem;
}
.rank-col__title {
  font-weight: 600;
  font-size: 0.85rem;
  color: #475569;
  padding: 0.25rem 0.5rem;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid #f1f5f9;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
}
.rank-row {
  display: grid;
  grid-template-columns: 24px 1fr 64px 64px;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.15s;
}
.rank-row:hover { background: #f1f5f9; }
.rank-no { color: #94a3b8; font-weight: 600; }
.rank-name { color: #0f172a; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-type { color: #94a3b8; font-size: 0.75rem; }
.rank-pct { font-family: ui-monospace; font-weight: 700; text-align: right; }
.rank-empty { text-align: center; color: #94a3b8; padding: 2rem; font-size: 0.85rem; }
</style>
