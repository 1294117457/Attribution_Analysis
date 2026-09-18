<template>
  <div class="mini-kline">
    <div v-if="title || loading || klines.length" class="mini-kline-header">
      <span v-if="title" class="mini-kline-title">{{ title }}</span>
      <span v-if="loading" class="text-xs text-gray-400">加载中...</span>
      <span v-else-if="klines.length" class="text-xs text-gray-400">{{ klines.length }} 根</span>
    </div>
    <div v-if="loading" class="mini-kline-placeholder" :style="{ height: `${height}px` }">
      <el-icon class="is-loading text-gray-300"><Loading /></el-icon>
    </div>
    <CandleChart
      v-else-if="klines.length"
      :klines="chartData"
      :show-main="showMain"
      :show-sub="showSub"
      :height="height"
    />
    <div v-else class="mini-kline-placeholder" :style="{ height: `${height}px` }">
      <span class="text-xs text-gray-400">暂无数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import CandleChart from '@/components/kline/CandleChart.vue'
import type { Kline } from '@/views/stock-info/api'

const props = withDefaults(defineProps<{
  title: string
  klines: Kline[]
  loading?: boolean
  height?: number
  showMain?: string[]
  showSub?: string
}>(), {
  loading: false,
  height: 160,
  showMain: () => [],
  showSub: '',
})

const chartData = computed(() => {
  return [...props.klines].sort((a, b) => a.date.localeCompare(b.date))
})
</script>

<style scoped>
.mini-kline {
  flex: 1;
  min-width: 0;
}

.mini-kline-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.mini-kline-title {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.mini-kline-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px dashed #e5e7eb;
}
</style>
