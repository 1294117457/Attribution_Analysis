<template>
  <div class="cm-wrap">
    <!-- 抽屉头部 -->
    <header class="cm-header">
      <button class="cm-close" @click="$emit('close')">×</button>
      <div class="cm-info">
        <div class="cm-name">{{ concept.name }}</div>
        <div class="cm-meta">
          <el-tag size="small" type="info">{{ concept.concept_type_label }}</el-tag>
          <span class="cm-count">{{ concept.stock_count }} 只成分</span>
          <span v-if="realtime" :class="realtimeColor" class="cm-realtime">
            {{ realtime.price != null ? realtime.price.toFixed(2) : '—' }}
            <span class="cm-pct">
              {{ realtime.pct_change != null
                ? (realtime.pct_change > 0 ? '+' : '') + realtime.pct_change.toFixed(2) + '%'
                : '' }}
            </span>
            <el-tag v-if="realtime.stale" type="warning" size="small" effect="plain">STALE</el-tag>
            <el-tag v-else type="success" size="small" effect="plain">实时</el-tag>
          </span>
          <span v-else class="text-gray-400 text-xs">行情暂无</span>
        </div>
      </div>
    </header>

    <!-- K 线 + 成分股表格 -->
    <ConceptKlineCard
      class="cm-kline"
      :concept-name="concept.name"
      :index-code="concept.index_code"
      :data="klineData"
      :loading="klineLoading"
      :height="200"
      :hint="klineHint"
    />

    <el-table
      :data="rows"
      v-loading="loading"
      class="cm-table"
      stripe
      size="small"
    >
      <el-table-column prop="symbol" label="代码" width="100" fixed>
        <template #default="{ row }">
          <a class="cm-link" @click="$emit('pick-stock', row.symbol)">{{ row.symbol }}</a>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" width="120" fixed />
      <el-table-column label="最新价" width="100" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.latest_close != null ? row.latest_close.toFixed(2) : '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="涨跌幅" width="100" align="right">
        <template #default="{ row }">
          <span
            v-if="row.pct_change != null"
            :class="row.color === 'up' ? 'text-red-500' : row.color === 'down' ? 'text-green-600' : ''"
            class="mono"
          >
            {{ row.pct_change > 0 ? '+' : '' }}{{ row.pct_change.toFixed(2) }}%
          </span>
          <span v-else class="text-gray-400">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="industry" label="行业" width="120" show-overflow-tooltip />
      <el-table-column label="总市值(亿)" width="100" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.total_mv != null ? (row.total_mv / 10000).toFixed(1) : '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="PE(TTM)" width="80" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.pe_ttm != null ? row.pe_ttm.toFixed(1) : '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="已加入池" min-width="180">
        <template #default="{ row }">
          <div v-if="row.pools.length" class="cm-pools">
            <el-tag
              v-for="p in row.pools.slice(0, 3)"
              :key="p.pool_id"
              size="small"
              effect="plain"
            >
              {{ p.name }}
            </el-tag>
            <span v-if="row.pools.length > 3" class="text-xs text-gray-400">
              +{{ row.pools.length - 3 }}
            </span>
          </div>
          <span v-else class="text-xs text-gray-400">—</span>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      small
      background
      class="cm-pagination"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  getConceptBoardMembers,
  type ConceptKlineResponse,
  type ConceptMemberItem,
} from '../api'
import type { ConceptBoardItem } from '../api'
import ConceptKlineCard from './ConceptKlineCard.vue'

const props = defineProps<{
  concept: ConceptBoardItem
  klineData: ConceptKlineResponse | null
  klineLoading: boolean
  klineHint?: string
}>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'pick-stock', symbol: string): void
}>()

const rows = ref<ConceptMemberItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const loading = ref(false)

const realtime = computed(() => props.klineData?.realtime ?? null)
const realtimeColor = computed(() => {
  const c = realtime.value?.color
  if (c === 'up') return 'text-red-500 font-bold'
  if (c === 'down') return 'text-green-600 font-bold'
  return 'text-gray-400'
})

async function load() {
  loading.value = true
  try {
    const res = await getConceptBoardMembers({
      concept_id: props.concept.concept_id,
      sort_by: 'pct_change',
      order: 'desc',
      with_pools: true,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = res.items
    total.value = res.total
  } catch (e) {
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

watch(() => props.concept.concept_id, () => {
  page.value = 1
  load()
}, { immediate: true })

watch([page, pageSize], load)
onMounted(load)
</script>

<style scoped>
.cm-wrap { display: flex; flex-direction: column; height: 100vh; }

.cm-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.cm-close {
  font-size: 1.5rem;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: #64748b;
  border-radius: 4px;
}
.cm-close:hover { background: #e2e8f0; color: #0f172a; }
.cm-info { flex: 1; }
.cm-name { font-size: 1rem; font-weight: 700; color: #0f172a; }
.cm-meta { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem; font-size: 0.8rem; flex-wrap: wrap; }
.cm-count { color: #64748b; }
.cm-realtime { display: inline-flex; align-items: center; gap: 0.25rem; font-family: ui-monospace, monospace; }
.cm-pct { margin-left: 0.25rem; font-size: 0.75rem; }

.cm-kline { margin: 0.5rem; flex: 0 0 auto; }
.cm-table { flex: 1; overflow: auto; }
.mono { font-family: ui-monospace, monospace; font-weight: 600; }
.cm-link { color: #2563eb; cursor: pointer; text-decoration: none; }
.cm-link:hover { text-decoration: underline; }
.cm-pools { display: flex; flex-wrap: wrap; gap: 0.25rem; align-items: center; }

.cm-pagination {
  padding: 0.5rem;
  justify-content: flex-end;
  border-top: 1px solid #e2e8f0;
}
</style>
