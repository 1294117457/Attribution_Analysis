<!--
  RealtimePanel.vue — 实时接口面板（step7 简化版）

  实时 service（如 minute_kline / concept_minute / concept_snapshot）无 collect 写库逻辑，
  这里只展示基本信息 + 提供试查。
  试查走 GET /collect/query/{name}?params=<JSON>（后端把 params JSON 当 kwargs 传给 service.get()）
-->
<template>
  <div class="realtime-panel">
    <CollectCard :title="item.label" :description="item.description">
      <template #tags>
        <el-tag size="small" :type="isRealtimeOnly ? 'danger' : 'warning'" effect="plain">
          {{ isRealtimeOnly ? '实时' : '可实时试查' }}
        </el-tag>
      </template>

      <CollectCardRow label="接口信息">
        <span class="info-item">
          <span class="muted">service</span>{{ serviceName }}
        </span>
        <span class="info-item">
          <span class="muted">入口</span>GET /collect/query/{{ serviceName }}?params=&lt;JSON&gt;
        </span>
      </CollectCardRow>

      <CollectCardRow label="查询参数">
        <template v-if="paramKeys.length > 0">
          <div v-for="key in paramKeys" :key="key" class="param">
            <span class="param__label">{{ key }}</span>
            <el-input v-model="form[key]" size="small" style="width: 200px" @keyup.enter="runQuery" />
          </div>
        </template>
        <span v-else class="muted">无需参数（直接点试查）</span>
      </CollectCardRow>

      <template #footer>
        <el-button type="primary" size="small" :loading="querying" @click="runQuery">试查</el-button>
      </template>
    </CollectCard>

    <section v-if="queryError || queryResult" class="panel-block">
      <div class="block-title">试查结果</div>
      <el-alert v-if="queryError" :title="queryError" type="error" :closable="false" show-icon />
      <template v-else-if="queryResult">
        <div class="result-meta">
          <span v-if="previewTotal > 0" class="muted">共 {{ previewTotal }} 条，预览前 {{ previewRows.length }} 条</span>
          <span v-else class="muted">无数据</span>
        </div>
        <el-table v-if="previewRows.length" :data="previewRows" size="small" stripe max-height="360">
          <el-table-column v-for="col in previewColumns" :key="col" :prop="col" :label="col" min-width="90" />
        </el-table>
        <pre v-else class="result-json">{{ JSON.stringify(queryResult, null, 2) }}</pre>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { queryService, type CatalogItem } from '../api'
import CollectCard from './CollectCard.vue'
import CollectCardRow from './CollectCardRow.vue'

const PREVIEW_ROWS = 20

const props = defineProps<{
  serviceName: string
  item: CatalogItem
}>()

/** 是否「纯实时」（不写入数据库）：kind=realtime 时显示「实时」红标 */
const isRealtimeOnly = computed(() => props.item.kind === 'realtime')

const form = reactive<Record<string, string>>({})
const paramKeys = computed(() => Object.keys(props.item.default_params || {}))
const querying = ref(false)
const queryError = ref('')
const queryResult = ref<any>(null)

/** 后端 /collect/query/{name} 返回 data：list[dict] | dict | { data: ... } */
const rows = computed<Record<string, any>[]>(() => {
  const r = queryResult.value
  if (Array.isArray(r)) return r
  if (Array.isArray(r?.data)) return r.data
  return []
})
const previewTotal = computed(() => rows.value.length)
const previewRows = computed(() => rows.value.slice(0, PREVIEW_ROWS))
const previewColumns = computed(() =>
  previewRows.value.length ? Object.keys(previewRows.value[0]) : [],
)

async function runQuery() {
  querying.value = true
  queryError.value = ''
  try {
    // 把 form 表单转成 kwargs（只保留非空值；按 param ui 类型做轻量转换）
    const kwargs: Record<string, any> = {}
    for (const [k, v] of Object.entries(form)) {
      if (v == null || v === '') continue
      // 简单按 key 名推断：interval/days/limit/minutes 等转 int
      if (/^(interval|days|limit|minutes|years)$/i.test(k)) {
        const n = Number(v)
        if (!Number.isNaN(n)) { kwargs[k] = n; continue }
      }
      kwargs[k] = v
    }
    queryResult.value = await queryService(props.serviceName, kwargs)
  } catch (e: any) {
    queryResult.value = null
    queryError.value = e?.response?.data?.message || e?.message || '查询失败'
  } finally {
    querying.value = false
  }
}

watch(
  () => props.serviceName,
  () => {
    for (const k of Object.keys(form)) delete form[k]
    for (const [k, v] of Object.entries(props.item.default_params || {})) {
      form[k] = String(v ?? '')
    }
    queryResult.value = null
    queryError.value = ''
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
  margin-top: 12px;
}
.info-item {
  display: inline-flex;
  gap: 6px;
  font-size: 13px;
  color: #334155;
  margin-right: 16px;
}
.param {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.param__label {
  font-size: 13px;
  color: #475569;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  min-width: 100px;
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
.result-json {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  background: #0f172a;
  color: #e2e8f0;
  padding: 8px 10px;
  border-radius: 4px;
  max-height: 320px;
  overflow: auto;
  margin: 0;
}
.muted {
  color: #94a3b8;
  font-size: 12px;
}
</style>
