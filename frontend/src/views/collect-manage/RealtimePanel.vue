<!--
  RealtimePanel.vue — 实时接口面板（采集管理中选中 kind=realtime 的接口时显示）

  实时接口不建任务、不入库：这里只展示基本信息、提供试查、显示今日调用统计。
  配套：backend/docs/dev/step2/04采集管理优化/06实时数据接口.md §7
-->
<template>
  <div class="realtime-panel">
    <header class="panel-block">
      <h3>
        {{ taskDef.label }}
        <el-tag size="small" type="danger" effect="plain" class="ml-1">实时</el-tag>
      </h3>
      <p class="desc">{{ taskDef.description }}</p>
      <el-descriptions :column="3" size="small" border>
        <el-descriptions-item label="数据源">{{ taskDef.source_label || taskDef.source || '—' }}</el-descriptions-item>
        <el-descriptions-item label="缓存策略">
          交易时段 {{ taskDef.ttl_trading ?? 15 }} 秒，非交易时段缓存到开盘
        </el-descriptions-item>
        <el-descriptions-item label="业务调用方">
          {{ taskDef.consumers?.length ? taskDef.consumers.join('、') : '—' }}
        </el-descriptions-item>
      </el-descriptions>
    </header>

    <section class="panel-block">
      <div class="block-title">试查</div>
      <el-form inline size="small" @submit.prevent="runQuery">
        <el-form-item v-for="key in paramKeys" :key="key" :label="key">
          <el-input v-model="form[key]" style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="querying" @click="runQuery">查询</el-button>
        </el-form-item>
      </el-form>

      <el-alert v-if="queryError" :title="queryError" type="error" :closable="false" show-icon />
      <template v-else-if="result">
        <div class="result-meta">
          <span>耗时 <b>{{ result.latency_ms }}</b> ms</span>
          <el-tag size="small" :type="result.cached ? 'success' : 'info'" effect="plain">
            {{ result.cached ? '命中缓存' : '请求数据源' }}
          </el-tag>
          <el-tag v-if="result.stale" size="small" type="warning" effect="plain">降级数据</el-tag>
          <span v-if="result.fetched_at" class="muted">取数时间 {{ result.fetched_at.replace('T', ' ').slice(0, 19) }}</span>
          <span v-if="previewRows.length" class="muted">共 {{ previewTotal }} 行，预览前 {{ previewRows.length }} 行</span>
        </div>
        <pre v-if="headerFields" class="header-json">{{ headerFields }}</pre>
        <el-table v-if="previewRows.length" :data="previewRows" size="small" stripe max-height="360">
          <el-table-column v-for="col in previewColumns" :key="col" :prop="col" :label="col" min-width="90" />
        </el-table>
      </template>
    </section>

    <section class="panel-block">
      <div class="block-title">
        今日调用统计
        <el-button link size="small" type="primary" @click="loadStats">刷新</el-button>
      </div>
      <el-descriptions v-if="stats" :column="4" size="small" border>
        <el-descriptions-item label="调用数">{{ stats.calls }}</el-descriptions-item>
        <el-descriptions-item label="缓存命中率">
          {{ stats.hit_rate == null ? '—' : (stats.hit_rate * 100).toFixed(1) + '%' }}
        </el-descriptions-item>
        <el-descriptions-item label="失败数">{{ stats.errors }}</el-descriptions-item>
        <el-descriptions-item label="平均耗时">
          {{ stats.avg_latency_ms == null ? '—' : stats.avg_latency_ms + ' ms' }}
        </el-descriptions-item>
        <el-descriptions-item label="最近错误" :span="4">
          <span v-if="stats.last_error" class="text-red-500">
            {{ stats.last_error_at?.replace('T', ' ').slice(0, 19) }} · {{ stats.last_error }}
          </span>
          <span v-else class="muted">无</span>
        </el-descriptions-item>
      </el-descriptions>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { getRealtimeStats, queryRealtime, type RealtimeResult, type RealtimeStats, type TaskDef } from './api'

const PREVIEW_ROWS = 20

const props = defineProps<{ taskDef: TaskDef }>()

const form = reactive<Record<string, string>>({})
const paramKeys = computed(() => Object.keys(props.taskDef.default_params || {}))
const querying = ref(false)
const queryError = ref('')
const result = ref<RealtimeResult | null>(null)
const stats = ref<RealtimeStats | null>(null)

const rows = computed<Record<string, any>[]>(() => {
  const d = result.value?.data
  return (d?.items || d?.points || []) as Record<string, any>[]
})
const previewTotal = computed(() => rows.value.length)
const previewRows = computed(() => rows.value.slice(0, PREVIEW_ROWS))
const previewColumns = computed(() => Object.keys(previewRows.value[0] || {}))
const headerFields = computed(() => {
  const d = result.value?.data
  if (!d || typeof d !== 'object') return d == null ? '' : String(d)
  const { items, points, ...rest } = d
  return Object.keys(rest).length ? JSON.stringify(rest, null, 2) : ''
})

async function runQuery() {
  querying.value = true
  queryError.value = ''
  try {
    result.value = await queryRealtime(props.taskDef.task_type, { ...form })
  } catch (e: any) {
    result.value = null
    queryError.value = e?.response?.data?.message || e?.message || '查询失败'
  } finally {
    querying.value = false
    loadStats()
  }
}

async function loadStats() {
  try {
    const list = await getRealtimeStats(props.taskDef.task_type, 1)
    stats.value = list[0] ?? null
  } catch {
    stats.value = null
  }
}

watch(
  () => props.taskDef.task_type,
  () => {
    for (const k of Object.keys(form)) delete form[k]
    for (const [k, v] of Object.entries(props.taskDef.default_params || {})) form[k] = String(v)
    result.value = null
    queryError.value = ''
    loadStats()
  },
  { immediate: true },
)
</script>

<style scoped>
.panel-block {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
}
.panel-block h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #1e293b;
}
.desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: #64748b;
}
.block-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}
.result-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  margin-bottom: 8px;
}
.muted {
  color: #94a3b8;
  font-size: 12px;
}
.header-json {
  background: #f8fafc;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 12px;
  margin: 0 0 8px;
  max-height: 200px;
  overflow: auto;
}
</style>
