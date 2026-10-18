<!--
  CollectActionCard — 批量采集 service 的采集卡片（step7 重构 + param_schema 驱动）

  行 1：title + description
  行 2：默认参数摘要（只读，从 service.default_params 来）
  行 3：附加参数 —— 按 service.param_schema 动态渲染（后端推导每个 param 的 ui 控件）
  底部：并发度 + 开始采集

  配套：backend/src/contexts/collect/interface/route/manage.py
-->
<template>
  <CollectCard :title="item.label" :description="item.description">
    <!-- 采集模式：全量 / 条件 -->
    <CollectCardRow label="采集模式">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button label="full">全量采集</el-radio-button>
        <el-radio-button label="condition">条件采集</el-radio-button>
      </el-radio-group>
      <span class="hint" :class="{ 'hint--strong': mode === 'full' }">
        {{ mode === 'full'
            ? '⚡ 全量采集：拉取全市场数据，参数已锁定'
            : '请填写采集条件（留空则使用默认参数）' }}
      </span>
    </CollectCardRow>

    <CollectCardRow label="默认参数">
      <el-form :inline="true" size="small" class="form-row">
        <el-form-item v-for="(v, k) in defaultParams" :key="String(k)" :label="`${k}`" class="form-row__item">
          <span class="form-row__value">{{ formatValue(v) }}</span>
        </el-form-item>
        <el-form-item v-if="Object.keys(defaultParams).length === 0" label="-">
          <span class="hint">无</span>
        </el-form-item>
      </el-form>
    </CollectCardRow>

    <!-- 全量模式横幅：提示用户参数已锁定 + 描述默认行为 + 并发可调 -->
    <div v-if="mode === 'full'" class="full-mode-banner">
      <div>将以 <strong>默认参数</strong> 拉取全市场数据，{{ defaultParamsHint }}</div>
      <div class="mt-1 flex items-center gap-2 flex-wrap">
        <span v-if="rateLimitHint">限速：<code>{{ rateLimitHint }}</code></span>
        <span class="inline-flex items-center gap-1">
          并发
          <el-input-number
            v-model="form.concurrency"
            :min="1" :max="32" :step="1"
            size="small"
            controls-position="right"
            class="!w-20"
          />
        </span>
      </div>
    </div>

    <CollectCardRow v-if="mode === 'condition'" label="调整参数">
      <el-form :inline="true" size="small" class="form-row">
        <!-- 并发（固定字段，单独抽出） -->
        <el-form-item label="并发">
          <el-input-number v-model="form.concurrency" :min="1" :max="32" :step="1" class="!w-24" />
        </el-form-item>

        <!-- ── 按 param_schema 动态渲染所有可调参数 ── -->
        <el-form-item
          v-for="p in paramSchema"
          :key="p.key"
          :label="p.label"
          :required="p.required"
        >
          <!-- 列表类：symbols / index_codes -->
          <template v-if="p.ui === 'symbols_list' || p.ui === 'index_codes_list' || p.ui === 'str_list'">
            <el-input
              v-model="form[p.key + '_text']"
              type="textarea"
              :rows="2"
              class="!w-64"
              :placeholder="p.placeholder"
            />
            <span class="hint">{{ formatListCount(form[p.key]) }} 项</span>
          </template>

          <!-- 日期类：YYYY-MM-DD -->
          <template v-else-if="p.ui === 'date_str'">
            <el-input v-model="form[p.key]" :placeholder="p.placeholder" class="!w-36" />
          </template>

          <!-- 上市状态：L/D/P -->
          <template v-else-if="p.ui === 'list_status'">
            <el-select v-model="form[p.key]" class="!w-28">
              <el-option label="上市中 L" value="L" />
              <el-option label="已退市 D" value="D" />
              <el-option label="暂停 P" value="P" />
            </el-select>
          </template>

          <!-- 交易所多选 -->
          <template v-else-if="p.ui === 'exchange_multi'">
            <el-select v-model="form[p.key]" multiple clearable placeholder="全部" class="!w-48">
              <el-option label="上交所 SSE" value="SSE" />
              <el-option label="深交所 SZSE" value="SZSE" />
              <el-option label="北交所 BSE" value="BSE" />
            </el-select>
          </template>

          <!-- K 线周期（分钟） -->
          <template v-else-if="p.ui === 'interval_kline'">
            <el-select v-model="form[p.key]" class="!w-24">
              <el-option label="1m" value="1" />
              <el-option label="5m" value="5" />
              <el-option label="15m" value="15" />
              <el-option label="30m" value="30" />
              <el-option label="60m" value="60" />
            </el-select>
          </template>

          <!-- K 线周期（日/周/月） -->
          <template v-else-if="p.ui === 'period_kline'">
            <el-select v-model="form[p.key]" class="!w-24">
              <el-option label="日" value="D" />
              <el-option label="周" value="W" />
              <el-option label="月" value="M" />
            </el-select>
          </template>

          <!-- 布尔开关 -->
          <template v-else-if="p.ui === 'bool_flag'">
            <el-switch v-model="form[p.key]" />
          </template>

          <!-- 整数（minutes / days / years / limit） -->
          <template v-else-if="['minutes_int', 'days_int', 'years_int', 'limit_int', 'int'].includes(p.ui)">
            <el-input-number
              v-model="form[p.key]"
              :min="p.ui === 'limit_int' ? 0 : 1"
              :step="1"
              class="!w-28"
            />
            <span v-if="p.ui === 'limit_int'" class="hint">0 = 不限</span>
          </template>

          <!-- 字符串（ts_code / symbol / index_code） -->
          <template v-else-if="['ts_code_str', 'symbol_str', 'index_code_str', 'str'].includes(p.ui)">
            <el-input v-model="form[p.key]" :placeholder="p.placeholder" class="!w-40" />
          </template>

          <!-- 兜底：原始字符串 -->
          <template v-else>
            <el-input v-model="form[p.key]" class="!w-40" />
          </template>
        </el-form-item>
      </el-form>
      <div v-if="paramSchema.length === 0" class="hint">无可调整参数（无 default_params）</div>
    </CollectCardRow>

    <template #footer>
      <el-button
        type="primary"
        size="small"
        :loading="starting"
        :disabled="starting"
        @click="start"
      >{{ mode === 'full' ? '开始全量采集' : '开始条件采集' }}</el-button>
    </template>
  </CollectCard>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import CollectCard from './CollectCard.vue'
import CollectCardRow from './CollectCardRow.vue'
import type { CatalogItem, ParamSchema, CollectStartPayload } from '../api'

const props = defineProps<{
  serviceName: string
  item: CatalogItem
  starting?: boolean
}>()

const emit = defineEmits<{
  (e: 'start', payload: CollectStartPayload): void
}>()

/** 采集模式：full = 全量采集 / condition = 条件采集 */
const mode = ref<'full' | 'condition'>('condition')

// ── 派生 ──────────────────────────────────────────────
const defaultParams = computed<Record<string, any>>(() => props.item.default_params || {})

/** 全量模式横幅：人类可读描述 "全市场（list_status=L）" */
const defaultParamsHint = computed<string>(() => {
  const p = defaultParams.value
  const bits: string[] = []
  if ('list_status' in p) bits.push(`list_status=${p.list_status}`)
  if ('exchange' in p) {
    const v = p.exchange
    bits.push(Array.isArray(v) && v.length ? v.join('/') : (v || '全部'))
  }
  if ('trade_date' in p) bits.push('按当日')
  if ('start_date' in p || 'end_date' in p) {
    const s = p.start_date || '不限'
    const e = p.end_date || '今天'
    bits.push(`${s} → ${e}`)
  }
  if ('symbols' in p) bits.push(Array.isArray(p.symbols) && p.symbols.length ? `${p.symbols.length} 只` : '全 A')
  if ('index_codes' in p) bits.push(Array.isArray(p.index_codes) && p.index_codes.length ? `${p.index_codes.length} 个` : '全概念')
  if ('days' in p) bits.push(`回溯 ${p.days} 天`)
  if ('years' in p) bits.push(`近 ${p.years} 年`)
  if (bits.length === 0) bits.push(props.item.description || '使用 service 默认行为')
  return bits.join(' · ')
})

/** 后端限速描述 "tushare 200 次/60s" */
const rateLimitHint = computed<string | null>(() => {
  const r = props.item.rate_limit
  if (!r || !Array.isArray(r) || r.length < 3) return null
  const [src, cnt, win] = r
  return `${src} ${cnt} 次/${win}s`
})

/** param_schema：来自后端（每个 param 的 ui / required / description） */
const paramSchema = computed<Array<ParamSchema & { label: string; placeholder: string }>>(() => {
  const schema = props.item.param_schema || []
  return schema.map((p) => ({
    ...p,
    label: PARAM_LABEL[p.key] || p.key,
    placeholder: PARAM_PLACEHOLDER[p.key] || p.description || `请输入 ${p.key}`,
  }))
})

// ── 控件 label / placeholder 映射 ───────────────────────
const PARAM_LABEL: Record<string, string> = {
  symbols: '股票代码',
  symbol: '股票代码',
  index_codes: '概念代码',
  index_code: '概念代码',
  ts_code: 'Tushare 代码',
  trade_date: '交易日期',
  start_date: '开始日期',
  end_date: '结束日期',
  list_status: '上市状态',
  list_date: '上市日期',
  exchange: '交易所',
  interval: '分钟周期',
  period: '日/周/月',
  minutes: '回溯分钟',
  days: '回溯天数',
  years: '回溯年数',
  limit: '限制条数',
  full: '全量重写',
  only_missing: '仅缺失',
}

const PARAM_PLACEHOLDER: Record<string, string> = {
  symbols: '每行一只：000001\n000002\n600000',
  symbol: '000001',
  index_codes: '每行一只：BK0001\nBK0002',
  index_code: 'BK0001',
  ts_code: '000001.SZ',
  trade_date: '2025-10-17 或 20251017',
  start_date: '2025-09-17',
  end_date: '2025-10-17',
}

// ── 表单状态 ─────────────────────────────────────────
/** 控件用的 form 字典：所有 key 都在 default_params 里 + 旁路 _text 存多行文本 */
function makeForm(): Record<string, any> {
  const out: Record<string, any> = { concurrency: 5 }
  for (const [k, v] of Object.entries(defaultParams.value)) {
    out[k] = v
    // 列表类需要旁路 _text 给 textarea
    if (Array.isArray(v)) {
      out[k + '_text'] = v.join('\n')
    }
  }
  return out
}

const form = reactive<Record<string, any>>(makeForm())

/** 切 service 时重置 */
watch(
  () => props.serviceName,
  () => {
    mode.value = 'condition'  // 切到新 service 默认进条件模式
    const next = makeForm()
    for (const k of Object.keys(form)) delete (form as any)[k]
    Object.assign(form, next)
  },
)

// ── 多行文本 → 数组（实时同步）────────────────────
watch(
  () => form.symbols_text,
  (v) => { form.symbols = parseList(v) },
)
watch(
  () => form.index_codes_text,
  (v) => { form.index_codes = parseList(v) },
)

function parseList(text: string | undefined): string[] {
  if (!text) return []
  return text
    .split(/[\n,;\s]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

function formatListCount(arr: any): number {
  return Array.isArray(arr) ? arr.length : 0
}

// ── 显示辅助 ───────────────────────────────────────
function formatValue(v: any): string {
  if (v == null) return '-'
  if (Array.isArray(v)) return v.length === 0 ? '[]' : `[${v.join(', ')}]`
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

// ── 提交 ─────────────────────────────────────────
function start() {
  // 全量模式：发 default_params（过滤空 list / 空 string，让 service 走默认全量分支）
  if (mode.value === 'full') {
    const params: Record<string, any> = { concurrency: form.concurrency }
    for (const [k, v] of Object.entries(defaultParams.value)) {
      // 过滤：空 list / 空 string / null 不发（让 service 走默认逻辑）
      if (Array.isArray(v)) {
        if (v.length > 0) params[k] = v
      } else if (v === '' || v == null) {
        // skip
      } else {
        params[k] = v
      }
    }
    emit('start', { mode: 'full', params })
    return
  }

  // 条件模式：发用户填的 params
  const params: Record<string, any> = {}

  for (const p of paramSchema.value) {
    const v = (form as any)[p.key]

    if (p.ui === 'symbols_list' || p.ui === 'index_codes_list' || p.ui === 'str_list') {
      // 列表类：已经实时同步到 form.symbols/index_codes
      if (Array.isArray(v) && v.length > 0) {
        params[p.key] = v
      }
    } else if (p.ui === 'bool_flag') {
      // 布尔：总是传
      params[p.key] = !!v
    } else if (p.ui === 'date_str' || p.ui === 'list_status' || p.ui === 'exchange_multi'
             || p.ui === 'interval_kline' || p.ui === 'period_kline'
             || p.ui.endsWith('_str') || p.ui === 'str') {
      // 字符串类：非空才传
      if (v !== '' && v != null) {
        params[p.key] = v
      }
    } else if (p.ui.endsWith('_int') || p.ui === 'int') {
      // 整数：默认传 0/1 也算
      if (v != null) {
        params[p.key] = Number(v)
      }
    } else {
      // 兜底
      if (v !== '' && v != null) {
        params[p.key] = v
      }
    }
  }

  // 并发总是传
  params.concurrency = (form as any).concurrency

  emit('start', { mode: 'condition', params })
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.hint--strong {
  color: #f59e0b;
  font-weight: 500;
  margin-left: 4px;
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

.full-mode-banner code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #fef3c7;
  padding: 0 4px;
  border-radius: 3px;
  color: #78350f;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.form-row :deep(.el-form-item) {
  margin-bottom: 6px;
  margin-right: 8px;
}

.form-row__item :deep(.el-form-item__label) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #475569;
}

.form-row__value {
  display: inline-block;
  padding: 2px 8px;
  background: #f1f5f9;
  border-radius: 4px;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: #475569;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
