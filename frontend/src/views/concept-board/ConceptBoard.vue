<template>
  <PageWrapper class="cb-page">
    <!-- ═══ Title Area ═══ -->
    <template #title>
      <el-icon class="mr-1"><DataAnalysis /></el-icon>
      概念大盘
      <span class="page-title-text">概念涨幅实时榜 + 概念日 K</span>
      <span class="ml-2 text-xs text-gray-400">v2 · 实验性</span>
    </template>

    <!-- ═══ Top Area ═══ -->
    <template #toolbar>
      <div class="toolbar-row">
        <div class="toolbar-search">
          <el-select
            v-model="filters.type_filter"
            placeholder="类型"
            style="width: 160px"
            @change="reload"
          >
            <el-option label="全部" value="all" />
            <el-option label="行业概念" value="industry" />
            <el-option label="主题概念" value="theme" />
            <el-option label="风格概念" value="style" />
            <el-option label="地域概念" value="region" />
            <el-option label="事件概念" value="event" />
            <el-option label="其他概念" value="other" />
          </el-select>
        </div>
        <div class="toolbar-actions">
          <el-tag :type="autoRefresh ? 'success' : 'info'" size="small" class="mr-2">
            {{ autoRefresh ? '🟢 自动刷新 15s' : '⏸ 已暂停' }}
          </el-tag>
          <el-button @click="reload" :loading="loading" size="small">
            <el-icon class="mr-1"><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button
            @click="autoRefresh = !autoRefresh"
            :type="autoRefresh ? 'warning' : 'primary'"
            size="small"
          >
            {{ autoRefresh ? '暂停' : '开启' }} 自动刷新
          </el-button>
        </div>
      </div>
    </template>

    <!-- ═══ Middle Area ═══ -->
    <div class="cb-middle">
      <div class="cb-row1">
        <ConceptRankBoard
          class="cb-rank"
          :items="boardItems"
          :loading="loading"
          @pick="onPickConcept"
        />
        <ConceptCardGrid
          class="cb-grid"
          :items="boardItems"
          :loading="loading"
          @pick="onPickConcept"
        />
      </div>
      <div v-if="pickedConcept" class="cb-row2">
        <ConceptKlineCard
          :concept-name="pickedConcept.name"
          :index-code="pickedConcept.index_code"
          :data="klineData"
          :loading="klineLoading"
          :height="240"
          :hint="klineHint"
        />
      </div>
    </div>

    <!-- ═══ 成分股抽屉 ═══ -->
    <el-drawer
      v-model="drawerVisible"
      :size="720"
      :with-header="false"
      direction="rtl"
    >
      <ConceptMembersList
        v-if="drawerVisible && pickedConcept"
        :concept="pickedConcept"
        :kline-data="klineData"
        :kline-loading="klineLoading"
        @close="drawerVisible = false"
        @pick-stock="onPickStock"
      />
    </el-drawer>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Refresh } from '@element-plus/icons-vue'
import PageWrapper from '@/components/PageWrapper.vue'
import {
  getConceptBoard,
  getConceptKline,
  type ConceptBoardItem,
  type ConceptKlineResponse,
} from './api'
import ConceptRankBoard from './components/ConceptRankBoard.vue'
import ConceptCardGrid from './components/ConceptCardGrid.vue'
import ConceptKlineCard from './components/ConceptKlineCard.vue'
import ConceptMembersList from './components/ConceptMembersList.vue'

const router = useRouter()

// ── 业务状态 ──
const filters = ref<{ type_filter: 'all' | 'industry' | 'theme' | 'style' | 'region' | 'event' | 'other' }>({
  type_filter: 'all',
})
const boardItems = ref<ConceptBoardItem[]>([])
const loading = ref(false)
const autoRefresh = ref(true)
const drawerVisible = ref(false)
const pickedConcept = ref<ConceptBoardItem | null>(null)

// ── K 线（选中概念时加载） ──
const klineData = ref<ConceptKlineResponse | null>(null)
const klineLoading = ref(false)
const klineHint = ref<string>('')

// ── 数据加载 ──
async function load() {
  loading.value = true
  try {
    const res = await getConceptBoard({
      type_filter: filters.value.type_filter,
      sort_by: 'pct_change',
      order: 'desc',
      page: 1,
      page_size: 500,
    })
    boardItems.value = res.items
    // 如果选中的概念还在新结果里,K 线不重新拉
    // 否则清空 picked
    if (pickedConcept.value) {
      const still = boardItems.value.find(
        (i) => i.concept_id === pickedConcept.value!.concept_id,
      )
      if (!still) {
        pickedConcept.value = null
        klineData.value = null
      } else {
        pickedConcept.value = still
      }
    }
  } catch (e) {
    ElMessage.error('加载概念大盘失败: ' + (e as Error).message)
  } finally {
    loading.value = false
  }
}
function reload() { load() }

async function loadKline(indexCode: string, conceptName: string) {
  klineLoading.value = true
  klineHint.value = ''
  try {
    const res = await getConceptKline({ index_code: indexCode, days: 250 })
    klineData.value = res
    if (!res.kline.length) {
      klineHint.value = '提示:此概念暂无日 K 数据,可前往 /collect 采集指数后重试'
    }
  } catch (e) {
    klineData.value = null
    klineHint.value = '加载失败: ' + (e as Error).message
  } finally {
    klineLoading.value = false
    void conceptName
  }
}

// ── 自动刷新（15s）──
let pollTimer: ReturnType<typeof setInterval> | null = null
function startPolling() {
  stopPolling()
  if (!autoRefresh.value) return
  pollTimer = setInterval(() => {
    if (!loading.value) load()
  }, 15000)
}
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}
watch(autoRefresh, () => { startPolling() })

// ── 交互 ──
function onPickConcept(c: ConceptBoardItem) {
  pickedConcept.value = c
  drawerVisible.value = true
  loadKline(c.index_code, c.name)
}
function onPickStock(symbol: string) {
  router.push(`/home/stock-panel?q=${symbol}`)
  drawerVisible.value = false
}

onMounted(() => { load(); startPolling() })
onUnmounted(() => { stopPolling() })
</script>

<style scoped>
.cb-page { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.page-title-text { font-size: 0.75rem; color: #94a3b8; margin-left: 0.5rem; font-weight: 400; }

.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.toolbar-search { display: flex; gap: 0.5rem; align-items: center; }
.toolbar-actions { display: flex; gap: 0.5rem; align-items: center; }

.cb-middle {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem 0;
  overflow: hidden;
}
.cb-row1 {
  flex: 1 1 0;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(320px, 0.5fr) 1fr;
  gap: 0.75rem;
}
.cb-row2 {
  flex: 0 0 auto;
  max-height: 38%;
  min-height: 280px;
}
.cb-rank, .cb-grid { min-width: 0; min-height: 0; }

.cb-page :deep(.top-area__header) { min-height: 2.5rem; height: 2.5rem; max-height: 2.5rem; }
.cb-page :deep(.top-area__title) { min-width: 0; }
</style>
