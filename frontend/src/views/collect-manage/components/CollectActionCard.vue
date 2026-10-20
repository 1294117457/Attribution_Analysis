<!--
  CollectActionCard — 批量采集 service 的采集卡片（v3：kind 驱动 UI）

  三种 kind 对应三种 UI：
    incremental  → 时间选择器（日期范围）
    full_refresh → 无需参数，全量采集
    realtime     → 不走此卡片（CollectTaskPane 直接走 RealtimePanel）
-->
<template>
  <CollectCard :title="item.label" :description="item.description">
    <!-- 增量采集：时间选择器 -->
    <CollectCardRow v-if="isIncremental" label="时间范围">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="→"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        :shortcuts="dateShortcuts"
        class="!w-96"
      />
      <span class="hint">留空按 service 默认（增量）</span>
    </CollectCardRow>

    <!-- 全量覆盖：无参数，显示采集说明 -->
    <div v-if="isFullRefresh" class="full-mode-banner">
      <div>全量采集（覆盖式刷新）</div>
      <div class="mt-1 muted">每次采集将全量覆盖当前数据，无时间范围参数</div>
    </div>

    <template #footer>
      <el-button
        type="primary"
        size="small"
        :loading="starting"
        :disabled="starting"
        @click="start"
      >开始采集</el-button>
    </template>
  </CollectCard>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import CollectCard from './CollectCard.vue'
import CollectCardRow from './CollectCardRow.vue'
import type { CatalogItem, CollectStartPayload } from '../api'

const props = defineProps<{
  serviceName: string
  item: CatalogItem
  starting?: boolean
}>()

const emit = defineEmits<{
  (e: 'start', payload: CollectStartPayload): void
}>()

// ── Kind 驱动 UI ─────────────────────────────────────────
const isIncremental = computed(() => props.item.kind === 'incremental')
const isFullRefresh = computed(() => props.item.kind === 'full_refresh')

// ── 时间选择器（仅增量采集） ──────────────────────────────
const dateRange = ref<[string, string] | null>(null)

const dateShortcuts = [
  {
    text: '今天',
    value: () => {
      const today = new Date()
      return [today, today]
    },
  },
  {
    text: '近 7 天',
    value: () => {
      const today = new Date()
      const ago = new Date(today.getTime() - 7 * 86400_000)
      return [ago, today]
    },
  },
  {
    text: '近 30 天',
    value: () => {
      const today = new Date()
      const ago = new Date(today.getTime() - 30 * 86400_000)
      return [ago, today]
    },
  },
  {
    text: '近 90 天',
    value: () => {
      const today = new Date()
      const ago = new Date(today.getTime() - 90 * 86400_000)
      return [ago, today]
    },
  },
]

// ── 切 service 时重置 ─────────────────────────────────
watch(
  () => props.serviceName,
  () => {
    dateRange.value = null
  },
)

// ── 提交 ────────────────────────────────────────────────
function start() {
  const params: Record<string, any> = {}

  // 增量采集：传时间范围
  if (isIncremental.value && dateRange.value) {
    const [start, end] = dateRange.value
    if (start) params.start_date = start
    if (end) params.end_date = end
  }

  emit('start', { params })
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
  margin-left: 8px;
}

.full-mode-banner {
  margin-top: 6px;
  padding: 6px 10px;
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 12px;
  color: #92400e;
  line-height: 1.6;
}

.mt-1 {
  margin-top: 4px;
}

.muted {
  color: #92400e;
  opacity: 0.75;
}
</style>
