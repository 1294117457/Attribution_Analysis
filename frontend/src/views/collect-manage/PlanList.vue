<!--
  PlanList.vue — 采集方案管理

  一个「采集方案」= 触发配置（每日定时 / 固定频率）+ 一组采集接口（按顺序串行执行）。
  列表展示：名称 / 触发方式 / 接口链 / 上次·下次执行；操作：立即执行 / 编辑 / 删除。
  编辑弹窗：名称、触发方式、启用、失败即停、接口编排（选接口 + 填参数 + 排序 + 单项启停）。
  执行规则（后端）：按 items 顺序串行；某项已在运行则跳过；stop_on_fail 时失败/取消后中断后续。
  配套：docs/dev/step3/05采集管理优化/03-三表重构方案.md
-->
<template>
  <div class="plans-pane">
    <div class="plans-toolbar">
      <span class="text-sm text-gray-500">
        采集方案 = 「什么时候触发」+「按顺序跑哪些接口」，可手动执行，也可定时
      </span>
      <span class="ml-auto">
        <el-button size="small" text @click="load"><el-icon class="mr-1"><Refresh /></el-icon>刷新</el-button>
        <el-button size="small" type="primary" @click="openEditor()">
          <el-icon class="mr-1"><Plus /></el-icon>新建方案
        </el-button>
      </span>
    </div>

    <el-table :data="plans" v-loading="loading" size="small" stripe empty-text="暂无采集方案">
      <el-table-column label="名称" prop="name" min-width="120">
        <template #default="{ row }">
          <span class="font-semibold">{{ row.name }}</span>
          <el-tag v-if="!row.schedule_type" size="small" type="info" effect="plain" class="ml-1">仅手动</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="触发方式" min-width="150">
        <template #default="{ row }">
          <el-tag size="small" :type="row.enabled ? 'success' : 'info'" effect="plain">
            {{ scheduleLabel(row) }}{{ row.enabled ? '' : '（已停用）' }}
          </el-tag>
          <div v-if="row.enabled && row.next_run_at" class="text-xs text-gray-400 mono">
            下次 {{ fmt(row.next_run_at) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="执行顺序" min-width="260">
        <template #default="{ row }">
          <span v-for="(item, i) in row.items" :key="item.id" class="item-chain">
            <el-tag
              size="small"
              effect="plain"
              :type="item.enabled ? 'info' : 'warning'"
            >{{ i + 1 }}. {{ item.label || item.task_type }}</el-tag>
            <el-icon v-if="i < row.items.length - 1" class="chain-arrow"><Right /></el-icon>
          </span>
          <span v-if="row.items.length === 0" class="text-xs text-gray-400">未配置接口</span>
        </template>
      </el-table-column>

      <el-table-column label="失败即停" width="80" align="center">
        <template #default="{ row }">{{ row.stop_on_fail ? '是' : '否' }}</template>
      </el-table-column>

      <el-table-column label="上次执行" width="130">
        <template #default="{ row }">
          <span class="mono text-sm">{{ row.last_run_at ? fmt(row.last_run_at) : '-' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" text :loading="runningId === row.id" @click="run(row)">
            执行
          </el-button>
          <el-button size="small" text :disabled="!row.last_task_id" @click="openRecords(row)">
            执行记录
          </el-button>
          <el-button size="small" text @click="openEditor(row)">编辑</el-button>
          <el-button size="small" type="danger" text @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- ═══ 编辑弹窗 ═══ -->
    <el-dialog
      v-model="editorOpen"
      :title="editingId ? '编辑采集方案' : '新建采集方案'"
      width="720px"
      append-to-body
    >
      <el-form label-width="100px">
        <el-form-item label="方案名称" required>
          <el-input v-model="form.name" maxlength="64" placeholder="如：盘后同步" />
        </el-form-item>

        <el-form-item label="启用定时">
          <el-switch v-model="form.enabled" />
          <span class="form-hint ml-2">停用后仅能手动执行</span>
        </el-form-item>

        <el-form-item label="触发方式">
          <el-radio-group v-model="form.schedule_type">
            <el-radio-button label="time">每日定时</el-radio-button>
            <el-radio-button label="interval">固定频率</el-radio-button>
            <el-radio-button label="manual">仅手动</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="form.schedule_type === 'time'" label="触发时间">
          <div class="w-full">
            <div v-if="form.times.length" class="mb-2">
              <el-tag
                v-for="(t, i) in form.times"
                :key="`${t}-${i}`"
                closable
                size="small"
                class="mr-1 mb-1"
                @close="removeTime(i)"
              >{{ t }}</el-tag>
            </div>
            <div class="flex items-center gap-2">
              <el-time-picker
                v-model="newTime"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                class="!w-40"
              />
              <el-button size="small" type="primary" plain @click="addTime" :disabled="!newTime">
                <el-icon class="mr-1"><Plus /></el-icon>添加时间
              </el-button>
            </div>
            <div class="form-hint">至少添加一个触发时间（如 09:30 收盘后、15:00）</div>
          </div>
        </el-form-item>

        <el-form-item v-if="form.schedule_type === 'interval'" label="间隔频率">
          <div class="flex items-center gap-2">
            <el-input-number v-model="form.intervalValue" :min="1" class="!w-32" />
            <el-select v-model="form.intervalUnit" class="!w-24">
              <el-option label="秒" value="s" />
              <el-option label="分钟" value="m" />
              <el-option label="小时" value="h" />
            </el-select>
            <span class="form-hint">最短 30 秒</span>
          </div>
        </el-form-item>

        <el-form-item label="执行接口" required>
          <div class="items-editor">
            <div v-for="(item, i) in form.items" :key="item.key" class="item-row">
              <span class="item-no mono">{{ i + 1 }}</span>
              <el-select
                v-model="item.task_type"
                filterable
                placeholder="选择采集接口"
                class="item-select"
                @change="onItemTaskChange(item)"
              >
                <el-option
                  v-for="t in batchFetchers"
                  :key="t.task_type"
                  :label="t.label"
                  :value="t.task_type"
                />
              </el-select>
              <el-input
                v-model="item.paramsText"
                class="item-params mono"
                :placeholder="paramsPlaceholder(item.task_type)"
              />
              <el-switch v-model="item.enabled" size="small" />
              <el-button text size="small" :disabled="i === 0" @click="move(i, -1)">
                <el-icon><Top /></el-icon>
              </el-button>
              <el-button text size="small" :disabled="i === form.items.length - 1" @click="move(i, 1)">
                <el-icon><Bottom /></el-icon>
              </el-button>
              <el-button text size="small" type="danger" @click="form.items.splice(i, 1)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button size="small" text type="primary" @click="addItem">
              <el-icon class="mr-1"><Plus /></el-icon>添加接口
            </el-button>
            <div class="form-hint">
              参数为 JSON 对象，留空 = 用该接口默认参数；前一项结束才开始下一项；开关可临时跳过某项
            </div>
          </div>
        </el-form-item>

        <el-form-item label="失败处理">
          <el-checkbox v-model="form.stop_on_fail">某项失败 / 取消后停止后续项</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editorOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- ═══ 执行记录 ═══ -->
    <el-drawer
      v-model="recordsOpen"
      :title="`执行记录 · ${recordsPlan?.name ?? ''}`"
      size="720px"
      append-to-body
    >
      <div class="text-sm text-gray-500 mb-2 flex items-center gap-2">
        <span>最近一次执行（plan_run_id = {{ recordsPlan?.last_task_id }}）</span>
        <el-button size="small" text @click="loadRecords"><el-icon class="mr-1"><Refresh /></el-icon>刷新</el-button>
      </div>
      <el-table :data="records" v-loading="recordsLoading" size="small" stripe empty-text="无记录">
        <el-table-column label="#" prop="id" width="60" />
        <el-table-column label="接口" min-width="110">
          <template #default="{ row }">{{ labelOf(row.task_type) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="statusColor(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="成功/失败/总数" width="120">
          <template #default="{ row }">
            <span class="mono text-sm">{{ row.success_count }} / {{ row.fail_count }} / {{ row.total_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="开始" width="110">
          <template #default="{ row }">
            <span class="mono text-sm">{{ row.started_at ? fmt(row.started_at) : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日志" min-width="160" show-overflow-tooltip prop="message" />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bottom, Delete, Plus, Refresh, Right, Top } from '@element-plus/icons-vue'
import {
  createPlan,
  deletePlan,
  listFetchers,
  listPlans,
  listTasks,
  runPlan,
  scheduleLabel,
  updatePlan,
  type CollectFetcher,
  type CollectPlan,
  type CollectTask,
} from './api'

interface ItemForm {
  key: number
  task_type: string
  paramsText: string
  enabled: boolean
}

const plans = ref<CollectPlan[]>([])
const fetchers = ref<CollectFetcher[]>([])
const loading = ref(false)
const runningId = ref<number | null>(null)

const editorOpen = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const newTime = ref<string | null>(null)
let itemKey = 0

const form = reactive({
  name: '',
  items: [] as ItemForm[],
  enabled: false,
  schedule_type: 'time' as 'time' | 'interval' | 'manual',
  times: [] as string[],
  intervalValue: 5,
  intervalUnit: 'm' as 's' | 'm' | 'h',
  stop_on_fail: true,
})

const recordsOpen = ref(false)
const recordsPlan = ref<CollectPlan | null>(null)
const records = ref<CollectTask[]>([])
const recordsLoading = ref(false)

// 只有 batch + ready 的接口可加入方案
const batchFetchers = computed(() =>
  fetchers.value.filter((f) => f.kind === 'batch' && f.status === 'ready'),
)

function labelOf(taskType: string): string {
  return fetchers.value.find((f) => f.task_type === taskType)?.label ?? taskType
}

function paramsPlaceholder(taskType: string): string {
  const d = batchFetchers.value.find((f) => f.task_type === taskType)?.default_params
  return d && Object.keys(d).length ? `默认 ${JSON.stringify(d)}` : '参数 JSON（可空）'
}

function onItemTaskChange(item: ItemForm) {
  // 切接口后 params 可能不适用，提示用户重填（这里只做占位，不自动填）
  item.paramsText = ''
}

async function load() {
  loading.value = true
  try {
    const [ps, fs] = await Promise.all([listPlans(), listFetchers()])
    plans.value = ps ?? []
    fetchers.value = fs ?? []
  } catch (e) {
    ElMessage.error('加载采集方案失败: ' + (e as Error).message)
  } finally {
    loading.value = false
  }
}

function openEditor(row?: CollectPlan) {
  editingId.value = row?.id ?? null
  form.name = row?.name ?? ''
  form.enabled = row?.enabled ?? false
  form.schedule_type =
    row?.schedule_type === 'interval' ? 'interval' : row?.schedule_type === 'time' ? 'time' : 'manual'
  form.times = [...(row?.times ?? [])]
  form.stop_on_fail = row?.stop_on_fail ?? true

  // 秒 → value + unit
  if (row?.interval_seconds) {
    const sec = row.interval_seconds
    if (sec % 3600 === 0) {
      form.intervalValue = sec / 3600
      form.intervalUnit = 'h'
    } else if (sec % 60 === 0) {
      form.intervalValue = sec / 60
      form.intervalUnit = 'm'
    } else {
      form.intervalValue = sec
      form.intervalUnit = 's'
    }
  } else {
    form.intervalValue = 5
    form.intervalUnit = 'm'
  }

  form.items = (row?.items ?? []).map((it) => ({
    key: ++itemKey,
    task_type: it.task_type,
    paramsText: it.params && Object.keys(it.params).length ? JSON.stringify(it.params) : '',
    enabled: it.enabled,
  }))
  if (!form.items.length) addItem()
  newTime.value = ''
  editorOpen.value = true
}

function addItem() {
  form.items.push({ key: ++itemKey, task_type: '', paramsText: '', enabled: true })
}

function move(i: number, delta: number) {
  const [item] = form.items.splice(i, 1)
  form.items.splice(i + delta, 0, item)
}

function addTime() {
  const t = newTime.value
  if (!t) {
    ElMessage.warning('请先选择时间')
    return
  }
  if (!/^\d{2}:\d{2}$/.test(t)) {
    ElMessage.warning('时间格式无效，应为 HH:MM')
    return
  }
  if (form.times.includes(t)) {
    ElMessage.info('该时间点已存在')
    return
  }
  form.times.push(t)
  form.times.sort()
  newTime.value = null
}

function removeTime(i: number) {
  form.times.splice(i, 1)
}

function buildIntervalSeconds(): number {
  const mult = form.intervalUnit === 'h' ? 3600 : form.intervalUnit === 'm' ? 60 : 1
  return Math.max(30, (form.intervalValue || 0) * mult)
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写方案名称')
    return
  }
  if (form.enabled && form.schedule_type === 'manual') {
    ElMessage.warning('启用定时需要选择触发方式（每日定时 / 固定频率）')
    return
  }
  if (form.enabled && form.schedule_type === 'time' && form.times.length === 0) {
    ElMessage.warning('启用每日定时需要至少一个触发时间')
    return
  }

  const items = []
  const seen = new Set<string>()
  for (const [i, it] of form.items.entries()) {
    if (!it.task_type) {
      ElMessage.warning(`第 ${i + 1} 项未选择采集接口`)
      return
    }
    if (seen.has(it.task_type)) {
      ElMessage.warning(`第 ${i + 1} 项接口重复`)
      return
    }
    seen.add(it.task_type)
    let params: Record<string, any> = {}
    if (it.paramsText.trim()) {
      try {
        const v = JSON.parse(it.paramsText)
        if (!v || typeof v !== 'object' || Array.isArray(v)) throw new Error('not object')
        params = v
      } catch {
        ElMessage.warning(`第 ${i + 1} 项参数不是 JSON 对象`)
        return
      }
    }
    items.push({ task_type: it.task_type, params, enabled: it.enabled })
  }
  if (items.length === 0) {
    ElMessage.warning('方案至少需要包含一个采集接口')
    return
  }

  const schedule_type =
    form.schedule_type === 'manual' ? null : form.schedule_type
  const body = {
    name: form.name.trim(),
    enabled: form.enabled,
    schedule_type,
    times: form.schedule_type === 'time' ? form.times : [],
    interval_seconds: form.schedule_type === 'interval' ? buildIntervalSeconds() : null,
    stop_on_fail: form.stop_on_fail,
    items,
  }

  saving.value = true
  try {
    if (editingId.value) await updatePlan(editingId.value, body)
    else await createPlan(body)
    ElMessage.success('采集方案已保存')
    editorOpen.value = false
    await load()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e as Error).message)
  } finally {
    saving.value = false
  }
}

async function run(row: CollectPlan) {
  runningId.value = row.id
  try {
    const res = await runPlan(row.id)
    ElMessage.success(res.message || '采集方案已启动')
    // last_task_id 在第一项创建后才写回，稍后刷新
    setTimeout(load, 1500)
  } catch (e) {
    ElMessage.error('执行失败: ' + (e as Error).message)
  } finally {
    runningId.value = null
  }
}

async function remove(row: CollectPlan) {
  try {
    await ElMessageBox.confirm(
      `删除采集方案「${row.name}」？已产生的任务记录保留。`,
      '删除采集方案',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await deletePlan(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e as Error).message)
  }
}

async function openRecords(row: CollectPlan) {
  recordsPlan.value = row
  recordsOpen.value = true
  await loadRecords()
}

async function loadRecords() {
  const runId = recordsPlan.value?.last_task_id
  if (!runId) return
  recordsLoading.value = true
  try {
    const data = await listTasks({ plan_run_id: runId, page_size: 100 })
    records.value = [...(data.items ?? [])].sort((a, b) => a.id - b.id)
  } finally {
    recordsLoading.value = false
  }
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending: '等待中', running: '采集中', success: '成功', failed: '失败', cancelled: '已取消',
  }
  return map[s] || s
}

function statusColor(s: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    pending: 'info', running: 'primary', success: 'success', failed: 'danger', cancelled: 'info',
  }
  return map[s] || 'info'
}

function fmt(v: string): string {
  return v.replace('T', ' ').replace(/(\.\d+)?([+-]\d{2}:\d{2})?$/, '').slice(5, 16)
}

onMounted(load)
defineExpose({ reload: load })
</script>

<style scoped>
.plans-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.ml-auto {
  margin-left: auto;
}

.item-chain {
  display: inline-flex;
  align-items: center;
  margin: 2px 0;
}

.chain-arrow {
  margin: 0 4px;
  color: #94a3b8;
}

.items-editor {
  width: 100%;
}

.item-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.item-no {
  width: 18px;
  color: #94a3b8;
  text-align: right;
}

.item-select {
  width: 170px;
  flex-shrink: 0;
}

.item-params {
  flex: 1;
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
