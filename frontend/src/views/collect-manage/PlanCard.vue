<!--
  PlanCard.vue — 当前采集接口的「采集方案」

  一行摘要（定时开关 / cron / 下次 · 上次执行 / 方案参数）+ 编辑弹窗。
  「按方案执行」由父组件走 useCollectTasks.startTask(runPlan)，复用进度轮询。
  参数优先级：手动传入 > 方案 params > default_params
  配套：docs/dev/step2/04采集管理优化/04-修订方案.md §4.3
-->
<template>
  <div class="plan-card">
    <div class="plan-summary">
      <span class="plan-title">采集方案</span>
      <el-switch
        :model-value="plan?.enabled ?? false"
        size="small"
        :disabled="!ready || !plan?.cron || saving"
        :title="plan?.cron ? '启用 / 停用定时' : '先编辑方案填写 cron'"
        @change="toggleEnabled"
      />
      <el-tag size="small" :type="plan?.enabled ? 'success' : 'info'">
        {{ plan?.enabled ? cronLabel(plan?.cron) : (plan?.cron ? `${cronLabel(plan.cron)}（已停用）` : '仅手动') }}
      </el-tag>
      <el-tag v-if="plan?.enabled && plan?.trading_day_only" size="small" type="warning" effect="plain">仅交易日</el-tag>
      <span v-if="plan?.next_run_at" class="plan-meta">下次 {{ fmt(plan.next_run_at) }}</span>
      <span v-if="plan?.last_run_at" class="plan-meta">上次 {{ fmt(plan.last_run_at) }} · #{{ plan.last_task_id }}</span>
      <el-tooltip v-if="paramsText" :content="paramsText" placement="top">
        <span class="plan-meta plan-params mono">参数 {{ paramsText }}</span>
      </el-tooltip>

      <span class="plan-actions">
        <el-button size="small" text :disabled="!plan" @click="openEditor">
          <el-icon class="mr-1"><Setting /></el-icon>编辑方案
        </el-button>
        <el-button
          size="small"
          type="primary"
          plain
          :disabled="!ready || running"
          :loading="running"
          @click="emit('run')"
        >按方案执行</el-button>
      </span>
    </div>

    <el-dialog v-model="editorOpen" :title="`采集方案 · ${taskDef?.label ?? taskType}`" width="560px" append-to-body>
      <el-form label-width="96px" size="default">
        <el-form-item label="定时执行">
          <el-switch v-model="form.enabled" :disabled="!ready" />
          <span v-if="!ready" class="form-hint ml-2">接口待实现，不能启用</span>
        </el-form-item>
        <el-form-item label="cron">
          <el-select
            v-model="form.cron"
            filterable
            allow-create
            clearable
            default-first-option
            placeholder="选择预设或输入 5 段 cron（分 时 日 月 周）"
            class="w-full"
          >
            <el-option v-for="p in CRON_PRESETS" :key="p.value" :label="`${p.label}　${p.value}`" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="仅交易日">
          <el-checkbox v-model="form.trading_day_only">周六日不执行（交易日历接入后按日历）</el-checkbox>
        </el-form-item>
        <el-form-item label="方案参数" :error="paramsError">
          <el-input
            v-model="form.paramsText"
            type="textarea"
            :rows="4"
            class="mono"
            placeholder='JSON，如 {"days": 1}'
          />
          <div class="form-hint">
            接口默认：<code class="mono">{{ JSON.stringify(plan?.default_params ?? {}) }}</code>
            ，方案参数覆盖默认；手动启动时传入的条件再覆盖方案
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editorOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'
import { CRON_PRESETS, cronLabel, getPlan, savePlan, type CollectPlan, type TaskDef } from './api'

const props = defineProps<{
  taskType: string
  taskDef: TaskDef | null
  running: boolean
}>()

const emit = defineEmits<{ (e: 'run'): void }>()

const plan = ref<CollectPlan | null>(null)
const saving = ref(false)
const editorOpen = ref(false)
const paramsError = ref('')
const form = reactive({
  enabled: false,
  cron: '' as string,
  trading_day_only: true,
  paramsText: '{}',
})

const ready = computed(() => props.taskDef?.status === 'ready')
const paramsText = computed(() => {
  const p = plan.value?.params
  return p && Object.keys(p).length ? JSON.stringify(p) : ''
})

async function load() {
  plan.value = null
  try {
    plan.value = await getPlan(props.taskType)
  } catch (e) {
    console.warn('[PlanCard] load plan failed', e)
  }
}

function openEditor() {
  if (!plan.value) return
  form.enabled = plan.value.enabled
  form.cron = plan.value.cron ?? ''
  form.trading_day_only = plan.value.trading_day_only
  form.paramsText = JSON.stringify(plan.value.params ?? {}, null, 2)
  paramsError.value = ''
  editorOpen.value = true
}

function parseParams(): Record<string, any> | null {
  const text = form.paramsText.trim()
  if (!text) return {}
  try {
    const v = JSON.parse(text)
    if (v && typeof v === 'object' && !Array.isArray(v)) return v
  } catch {
    /* fallthrough */
  }
  paramsError.value = '参数必须是 JSON 对象'
  return null
}

async function persist(body: { enabled: boolean; cron: string | null; params: Record<string, any>; trading_day_only: boolean }) {
  saving.value = true
  try {
    plan.value = await savePlan(props.taskType, body)
    return true
  } catch (e) {
    ElMessage.error('保存失败: ' + (e as Error).message)
    return false
  } finally {
    saving.value = false
  }
}

async function save() {
  paramsError.value = ''
  const params = parseParams()
  if (params === null) return
  const ok = await persist({
    enabled: form.enabled,
    cron: form.cron?.trim() || null,
    params,
    trading_day_only: form.trading_day_only,
  })
  if (ok) {
    ElMessage.success('采集方案已保存')
    editorOpen.value = false
  }
}

async function toggleEnabled(value: string | number | boolean) {
  if (!plan.value) return
  const ok = await persist({
    enabled: Boolean(value),
    cron: plan.value.cron,
    params: plan.value.params ?? {},
    trading_day_only: plan.value.trading_day_only,
  })
  if (ok) ElMessage.success(value ? '已启用定时' : '已停用定时')
}

function fmt(v: string): string {
  return v.replace('T', ' ').replace(/(\.\d+)?([+-]\d{2}:\d{2})?$/, '').slice(5, 16)
}

watch(() => props.taskType, load, { immediate: true })
defineExpose({ reload: load })
</script>

<style scoped>
.plan-card {
  margin-top: 10px;
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
}

.plan-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
}

.plan-title {
  font-weight: 600;
  color: #334155;
}

.plan-meta {
  color: #64748b;
}

.plan-params {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-actions {
  margin-left: auto;
  display: flex;
  gap: 4px;
}

.form-hint {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
}

.w-full {
  width: 100%;
}
</style>
