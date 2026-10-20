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
        <template v-if="paramDefs.length > 0">
          <div v-for="def in paramDefs" :key="def.key" class="param">
            <span class="param__label">{{ def.label }}</span>
            <el-input
              v-if="def.ui === 'str'"
              v-model="form[def.key]"
              size="small"
              style="width: 200px"
              :placeholder="def.placeholder"
              @keyup.enter="runQuery"
            />
            <el-input-number
              v-else-if="def.ui === 'int'"
              v-model="form[def.key]"
              size="small"
              style="width: 200px"
              :placeholder="def.placeholder"
              @keyup.enter="runQuery"
            />
            <el-select
              v-else-if="def.ui === 'select'"
              v-model="form[def.key]"
              size="small"
              style="width: 200px"
              @change="runQuery"
            >
              <el-option
                v-for="opt in def.options"
                :key="opt"
                :label="opt"
                :value="opt"
              />
            </el-select>
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

// ── 实时 service 的参数定义（按 service_name 硬编码） ──────
interface ParamDef {
  key: string
  label: string
  ui: 'str' | 'int' | 'select'
  placeholder?: string
  default?: any
  options?: string[]
}

const REALTIME_PARAM_DEFS: Record<string, ParamDef[]> = {
  minute_kline: [
    { key: 'symbol', label: '股票代码', ui: 'str', placeholder: '000001' },
    { key: 'interval', label: '分钟周期', ui: 'select', default: '5min', options: ['1min', '5min', '15min', '30min', '60min'] },
    { key: 'days', label: '回溯天数', ui: 'int', default: 1 },
  ],
  concept_minute: [
    { key: 'index_code', label: '概念指数代码', ui: 'str', placeholder: 'BK0001' },
  ],
  concept_snapshot: [
    { key: 'index_code', label: '概念指数代码', ui: 'str', placeholder: 'BK0001' },
  ],
}

const paramDefs = computed<ParamDef[]>(() => REALTIME_PARAM_DEFS[props.serviceName] || [])

const form = reactive<Record<string, any>>({})
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
    // 把 form 表单转成 kwargs（只保留非空值；按 paramDef.ui 做轻量转换）
    const kwargs: Record<string, any> = {}
    for (const def of paramDefs.value) {
      const v = form[def.key]
      if (v == null || v === '') continue
      if (def.ui === 'int') {
        const n = Number(v)
        if (!Number.isNaN(n)) {
          kwargs[def.key] = n
          continue
        }
      }
      kwargs[def.key] = v
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
    // 用 paramDefs 的 default 初始化
    for (const def of paramDefs.value) {
      if (def.default !== undefined) {
        form[def.key] = def.default
      } else {
        form[def.key] = ''
      }
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
