<!--
  CollectGroups.vue — 采集任务组

  列表 + 编辑弹窗（名称 / 按顺序选择接口并填参数 / cron / 失败即停止）+ 执行 + 最近一次执行记录。
  执行规则（后端）：按 items 顺序串行；某项已在运行则跳过；stop_on_fail 时某项失败/取消后停止后续项。
  配套：docs/dev/step2/04采集管理优化/04-修订方案.md §4.4
-->
<template>
  <div class="groups-pane">
    <div class="groups-toolbar">
      <span class="text-sm text-gray-500">一个任务组按顺序执行多个采集接口，可手动执行，也可定时</span>
      <span class="ml-auto">
        <el-button size="small" text @click="load"><el-icon class="mr-1"><Refresh /></el-icon>刷新</el-button>
        <el-button size="small" type="primary" @click="openEditor()"><el-icon class="mr-1"><Plus /></el-icon>新建任务组</el-button>
      </span>
    </div>

    <el-table :data="groups" v-loading="loading" size="small" stripe empty-text="暂无任务组">
      <el-table-column label="名称" prop="name" min-width="120" />
      <el-table-column label="执行顺序" min-width="260">
        <template #default="{ row }">
          <span v-for="(item, i) in row.items" :key="i" class="item-chain">
            <el-tag size="small" effect="plain">{{ i + 1 }}. {{ labelOf(item.task_type) }}</el-tag>
            <el-icon v-if="i < row.items.length - 1" class="chain-arrow"><Right /></el-icon>
          </span>
        </template>
      </el-table-column>
      <el-table-column label="定时" min-width="150">
        <template #default="{ row }">
          <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
            {{ row.enabled ? cronLabel(row.cron) : '仅手动' }}
          </el-tag>
          <div v-if="row.next_run_at" class="text-xs text-gray-400 mono">下次 {{ fmt(row.next_run_at) }}</div>
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
      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" text :loading="runningId === row.id" @click="run(row)">执行</el-button>
          <el-button size="small" text :disabled="!row.last_group_run_id" @click="openRecords(row)">执行记录</el-button>
          <el-button size="small" text @click="openEditor(row)">编辑</el-button>
          <el-button size="small" type="danger" text @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editorOpen" :title="editingId ? '编辑任务组' : '新建任务组'" width="680px" append-to-body>
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="64" placeholder="如：盘后同步" />
        </el-form-item>
        <el-form-item label="执行顺序" required>
          <div class="items-editor">
            <div v-for="(item, i) in form.items" :key="item.key" class="item-row">
              <span class="item-no mono">{{ i + 1 }}</span>
              <el-select v-model="item.task_type" filterable placeholder="选择采集接口" class="item-select">
                <el-option v-for="t in readyTasks" :key="t.task_type" :label="t.label" :value="t.task_type" />
              </el-select>
              <el-input
                v-model="item.paramsText"
                class="item-params mono"
                :placeholder="paramsPlaceholder(item.task_type)"
              />
              <el-button text size="small" :disabled="i === 0" @click="move(i, -1)"><el-icon><Top /></el-icon></el-button>
              <el-button text size="small" :disabled="i === form.items.length - 1" @click="move(i, 1)"><el-icon><Bottom /></el-icon></el-button>
              <el-button text size="small" type="danger" @click="form.items.splice(i, 1)"><el-icon><Delete /></el-icon></el-button>
            </div>
            <el-button size="small" text type="primary" @click="addItem"><el-icon class="mr-1"><Plus /></el-icon>添加一项</el-button>
            <div class="form-hint">参数为 JSON 对象，留空 = 用该接口的采集方案 / 默认参数；前一项结束才开始下一项</div>
          </div>
        </el-form-item>
        <el-form-item label="定时执行">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="cron">
          <el-select
            v-model="form.cron"
            filterable
            allow-create
            clearable
            default-first-option
            placeholder="选择预设或输入 5 段 cron"
            class="w-full"
          >
            <el-option v-for="p in CRON_PRESETS" :key="p.value" :label="`${p.label}　${p.value}`" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="选项">
          <el-checkbox v-model="form.trading_day_only">仅交易日（周六日不执行）</el-checkbox>
          <el-checkbox v-model="form.stop_on_fail">某项失败 / 取消后停止后续项</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editorOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 执行记录 -->
    <el-drawer v-model="recordsOpen" :title="`执行记录 · ${recordsGroup?.name ?? ''}`" size="720px" append-to-body>
      <div class="text-sm text-gray-500 mb-2">
        最近一次执行（group_run_id = {{ recordsGroup?.last_group_run_id }}）
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
          <template #default="{ row }"><span class="mono text-sm">{{ row.started_at ? fmt(row.started_at) : '-' }}</span></template>
        </el-table-column>
        <el-table-column label="日志" min-width="160" show-overflow-tooltip prop="message" />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bottom, Delete, Plus, Refresh, Right, Top } from '@element-plus/icons-vue'
import {
  CRON_PRESETS,
  createGroup,
  cronLabel,
  deleteGroup,
  listGroups,
  listTasks,
  runGroup,
  updateGroup,
  type CollectGroup,
  type CollectTask,
  type TaskDef,
} from './api'

const props = defineProps<{ readyTasks: TaskDef[] }>()

interface ItemForm {
  key: number
  task_type: string
  paramsText: string
}

const groups = ref<CollectGroup[]>([])
const loading = ref(false)
const runningId = ref<number | null>(null)

const editorOpen = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
let itemKey = 0
const form = reactive({
  name: '',
  items: [] as ItemForm[],
  enabled: false,
  cron: '' as string,
  trading_day_only: true,
  stop_on_fail: true,
})

const recordsOpen = ref(false)
const recordsGroup = ref<CollectGroup | null>(null)
const records = ref<CollectTask[]>([])
const recordsLoading = ref(false)

function labelOf(taskType: string): string {
  return props.readyTasks.find((t) => t.task_type === taskType)?.label ?? taskType
}

function paramsPlaceholder(taskType: string): string {
  const d = props.readyTasks.find((t) => t.task_type === taskType)?.default_params
  return d && Object.keys(d).length ? `默认 ${JSON.stringify(d)}` : '参数 JSON（可空）'
}

async function load() {
  loading.value = true
  try {
    groups.value = (await listGroups()) ?? []
  } catch (e) {
    ElMessage.error('加载任务组失败: ' + (e as Error).message)
  } finally {
    loading.value = false
  }
}

function openEditor(row?: CollectGroup) {
  editingId.value = row?.id ?? null
  form.name = row?.name ?? ''
  form.items = (row?.items ?? []).map((it) => ({
    key: ++itemKey,
    task_type: it.task_type,
    paramsText: it.params && Object.keys(it.params).length ? JSON.stringify(it.params) : '',
  }))
  if (!form.items.length) addItem()
  form.enabled = row?.enabled ?? false
  form.cron = row?.cron ?? ''
  form.trading_day_only = row?.trading_day_only ?? true
  form.stop_on_fail = row?.stop_on_fail ?? true
  editorOpen.value = true
}

function addItem() {
  form.items.push({ key: ++itemKey, task_type: '', paramsText: '' })
}

function move(i: number, delta: number) {
  const [item] = form.items.splice(i, 1)
  form.items.splice(i + delta, 0, item)
}

async function save() {
  const items = []
  for (const [i, it] of form.items.entries()) {
    if (!it.task_type) {
      ElMessage.warning(`第 ${i + 1} 项未选择采集接口`)
      return
    }
    let params: Record<string, any> = {}
    if (it.paramsText.trim()) {
      try {
        params = JSON.parse(it.paramsText)
      } catch {
        params = null as any
      }
      if (!params || typeof params !== 'object' || Array.isArray(params)) {
        ElMessage.warning(`第 ${i + 1} 项参数不是 JSON 对象`)
        return
      }
    }
    items.push({ task_type: it.task_type, params })
  }
  const body = {
    name: form.name.trim(),
    items,
    enabled: form.enabled,
    cron: form.cron?.trim() || null,
    trading_day_only: form.trading_day_only,
    stop_on_fail: form.stop_on_fail,
  }
  saving.value = true
  try {
    if (editingId.value) await updateGroup(editingId.value, body)
    else await createGroup(body)
    ElMessage.success('任务组已保存')
    editorOpen.value = false
    await load()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e as Error).message)
  } finally {
    saving.value = false
  }
}

async function run(row: CollectGroup) {
  runningId.value = row.id
  try {
    const res = await runGroup(row.id)
    ElMessage.success(res.message || '任务组已启动')
    // group_run_id 在第一项创建后才写回，稍后刷新
    setTimeout(load, 1500)
  } catch (e) {
    ElMessage.error('执行失败: ' + (e as Error).message)
  } finally {
    runningId.value = null
  }
}

async function remove(row: CollectGroup) {
  try {
    await ElMessageBox.confirm(`删除任务组「${row.name}」？已产生的任务记录保留。`, '删除任务组', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteGroup(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e as Error).message)
  }
}

async function openRecords(row: CollectGroup) {
  recordsGroup.value = row
  recordsOpen.value = true
  await loadRecords()
}

async function loadRecords() {
  const runId = recordsGroup.value?.last_group_run_id
  if (!runId) return
  recordsLoading.value = true
  try {
    const data = await listTasks({ group_run_id: runId, page_size: 100 })
    records.value = [...(data.items ?? [])].sort((a: CollectTask, b: CollectTask) => a.id - b.id)
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
.groups-toolbar {
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
