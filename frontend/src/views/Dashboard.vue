<template>
  <PageWrapper>
    <template #title>📊 数据大盘</template>

    <!-- Middle Area -->
    <div class="flex flex-col gap-4 flex-1 min-h-0 overflow-auto">
      <!-- 统计卡片 -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <el-card v-for="card in stats" :key="card.label" class="stat-card" shadow="hover">
          <div class="flex items-center gap-3">
            <div :class="['stat-icon', card.color]">{{ card.icon }}</div>
            <div>
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 双列图表区 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <el-card shadow="never">
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold text-gray-800">📈 K 线采集趋势</span>
              <el-tag size="small" type="info">最近 30 天</el-tag>
            </div>
          </template>
          <div class="chart-placeholder">
            <span>📊</span>
            <p>图表开发中…</p>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="flex justify-between items-center">
              <span class="font-bold text-gray-800">🥧 行业分布 Top 10</span>
              <el-tag size="small" type="info">实时</el-tag>
            </div>
          </template>
          <div class="chart-placeholder">
            <span>🥧</span>
            <p>图表开发中…</p>
          </div>
        </el-card>
      </div>

      <!-- 最近采集 -->
      <el-card shadow="never" class="flex-1">
        <template #header>
          <div class="flex justify-between items-center">
            <span class="font-bold text-gray-800">🕐 最近采集</span>
            <el-button text type="primary" size="small" @click="router.push('/home/stock-panel')">
              查看全部 →
            </el-button>
          </div>
        </template>

        <el-table :data="recentStocks" stripe v-loading="loading" empty-text="暂无采集数据">
          <el-table-column prop="symbol" label="代码" width="100">
            <template #default="{ row }">
              <span class="mono font-semibold">{{ row.symbol }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="industry" label="行业" min-width="120">
            <template #default="{ row }">
              {{ row.industry || '—' }}
            </template>
          </el-table-column>
          <el-table-column label="K 线条数" width="120" align="right">
            <template #default="{ row }">
              <span class="text-blue-600 font-medium">
                {{ row.record_count?.toLocaleString() ?? '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="kline_start" label="起始" width="110">
            <template #default="{ row }">{{ row.kline_start || '—' }}</template>
          </el-table-column>
          <el-table-column prop="kline_end" label="截止" width="110">
            <template #default="{ row }">{{ row.kline_end || '—' }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listStocks } from '@/views/stock-info/api'
import PageWrapper from '@/components/PageWrapper.vue'
import type { StockListItem } from '@/views/stock-info/api'

const router = useRouter()
const loading = ref(false)
const allStocks = ref<StockListItem[]>([])

interface StatCard {
  label: string
  value: string | number
  icon: string
  color: string
}

const stats = computed<StatCard[]>(() => {
  const stocks = allStocks.value
  const totalKlines = stocks.reduce((s, x) => s + (x.record_count || 0), 0)
  const dates = stocks.flatMap((s) => [s.kline_start, s.kline_end]).filter(Boolean) as string[]
  const industries = new Set(stocks.map((s) => s.industry).filter(Boolean))

  let range = '—'
  if (dates.length) {
    dates.sort()
    range = `${dates[0]} ~ ${dates[dates.length - 1]}`
  }

  return [
    // ── 已有 4 张 ──
    { label: '股票数量',  value: stocks.length,                                       icon: '📋', color: 'blue' },
    { label: 'K 线总条数', value: totalKlines.toLocaleString(),                       icon: '📈', color: 'green' },
    { label: '数据覆盖',  value: range,                                                icon: '🕐', color: 'orange' },
    { label: '涉及行业',  value: industries.size,                                     icon: '🏭', color: 'purple' },
    // ── 🆕 新增 4 张（开发指南 §8.5，对应后端 4 类新表，需后端提供聚合 API） ──
    // 待后端实现 dashboard/summary 接口后可填真实值
    { label: '资金流向覆盖', value: '—', icon: '💰', color: 'red' },
    { label: '两融覆盖',     value: '—', icon: '📊', color: 'cyan' },
    { label: '龙虎榜记录',   value: '—', icon: '🏆', color: 'gold' },
    { label: '板块行情',     value: '—', icon: '🗂️', color: 'magenta' },
  ]
})

const recentStocks = computed(() => allStocks.value.slice(0, 8))

onMounted(async () => {
  loading.value = true
  try {
    const data = await listStocks()
    allStocks.value = data.dataList ?? data.items ?? []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-card :deep(.el-card__body) {
  padding: 18px 20px;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
}
.stat-icon.blue   { background: #e8f4fd; }
.stat-icon.green  { background: #e8f6ed; }
.stat-icon.orange { background: #fef3e2; }
.stat-icon.purple { background: #f3effd; }
.stat-icon.red    { background: #fde8e8; }
.stat-icon.cyan   { background: #defaf0; }
.stat-icon.gold   { background: #fef4d8; }
.stat-icon.magenta{ background: #fce8f3; }

.stat-value {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
}
.stat-label {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.chart-placeholder {
  height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  gap: 6px;
  border: 1px dashed #e5e7eb;
  border-radius: 8px;
}
.chart-placeholder span { font-size: 2.5rem; opacity: 0.4; }
.chart-placeholder p { font-size: 12px; }
</style>
