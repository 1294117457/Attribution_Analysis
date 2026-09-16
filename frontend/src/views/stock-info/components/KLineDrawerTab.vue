<!-- 股票详情抽屉 - K 线图 Tab -->
<template>
  <div class="kline-drawer">
    <!-- 顶部控制栏 -->
    <div class="flex items-center justify-between mb-3">
      <!-- 时间范围 -->
      <el-button-group size="small">
        <el-button
          v-for="r in ranges"
          :key="r.value"
          :type="range === r.value ? 'primary' : ''"
          @click="range = r.value"
        >
          {{ r.label }}
        </el-button>
      </el-button-group>

      <!-- 拉取按钮 -->
      <el-button
        size="small"
        type="primary"
        :loading="collecting"
        @click="onCollect"
      >
        <el-icon class="mr-1"><Download /></el-icon>
        拉取 K 线
      </el-button>
    </div>

    <!-- 指标切换 -->
    <IndicatorSwitcher
      v-model:main="mainIndicators"
      v-model:sub="subIndicator"
    />

    <!-- K 线图 -->
    <div v-if="loading" class="flex items-center justify-center" style="height: 380px">
      <el-icon class="is-loading text-2xl text-gray-400"><Loading /></el-icon>
    </div>
    <CandleChart
      v-else-if="klines.length"
      :klines="klines"
      :show-main="mainIndicators"
      :show-sub="subIndicator"
      :height="380"
    />
    <el-empty
      v-else
      description="暂无 K 线数据，点击右上角「拉取 K 线」"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Loading } from '@element-plus/icons-vue'
import CandleChart from '@/components/kline/CandleChart.vue'
import IndicatorSwitcher from '@/components/kline/IndicatorSwitcher.vue'
import {
  getKlines,
  collectKlines,
  type Kline,
} from '@/views/stock-info/api'

const props = defineProps<{ symbol: string }>()

const klines = ref<Kline[]>([])
const loading = ref(false)
const range = ref('90')
const mainIndicators = ref(['MA5', 'MA20'])
const subIndicator = ref('MACD')
const collecting = ref(false)

const ranges = [
  { label: '90日', value: '90' },
  { label: '180日', value: '180' },
  { label: '1年', value: '365' },
  { label: '3年', value: '1095' },
]

async function load() {
  loading.value = true
  try {
    const data = (await getKlines(props.symbol, { limit: Number(range.value) })) as { items?: Kline[] }
    klines.value = data.items || []
  } catch {
    klines.value = []
  } finally {
    loading.value = false
  }
}

async function onCollect() {
  collecting.value = true
  try {
    const r = (await collectKlines({ symbol: props.symbol, days: Number(range.value) })) as unknown as { saved_count: number }
    ElMessage.success(`已采集 ${r.saved_count} 条`)
    await load()
  } catch (e) {
    ElMessage.error('采集失败: ' + (e as Error).message)
  } finally {
    collecting.value = false
  }
}

// 监听 symbol / range 变化时重新加载
watch(() => [props.symbol, range.value], load, { immediate: true })
</script>

<style scoped>
.kline-drawer {
  display: flex;
  flex-direction: column;
  gap: 0;
}
</style>