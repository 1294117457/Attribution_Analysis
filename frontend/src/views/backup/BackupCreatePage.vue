<!--
  BackupCreatePage · 子页 1
  - 4 步骤卡片：粒度 / 表 / 路径 / 命名
  - "开始备份" 按钮
  - el-progress 进度区
  - 启动后调用 store.startPolling(record_id, ...) 轮询
-->
<template>
  <div class="bkup-create">
    <el-card class="bkup-step" shadow="never">
      <template #header><span class="bkup-step__title">① 备份粒度</span></template>
      <el-radio-group v-model="form.backup_type">
        <el-radio-button value="full">full · 结构 + 数据</el-radio-button>
        <el-radio-button value="schema">schema · 仅结构</el-radio-button>
        <el-radio-button value="data">data · 仅数据</el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card class="bkup-step" shadow="never">
      <template #header><span class="bkup-step__title">② 备份范围</span></template>
      <el-radio-group v-model="form.scope" @change="onScopeChange">
        <el-radio-button value="all">all · 全表</el-radio-button>
        <el-radio-button value="partial">partial · 选子集</el-radio-button>
      </el-radio-group>

      <div v-if="form.scope === 'partial'" class="bkup-tablepicker">
        <el-input
          v-model="tableFilter"
          placeholder="按表名过滤..."
          clearable
          size="default"
          style="max-width: 280px; margin-bottom: 0.5rem"
        />
        <el-table
          ref="tablePickerRef"
          :data="filteredTables"
          height="240px"
          @selection-change="onSelectionChange"
          :style="{ '--el-table-cell-padding-x': '8px', '--el-table-cell-padding-y': '4px' }"
        >
          <el-table-column type="selection" width="44" />
          <el-table-column prop="name" label="表名" />
          <el-table-column label="分类" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="categoryTagType(row.category)">{{ row.category }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="行数(估)" width="100" prop="row_count" />
          <el-table-column label="大小(MB)" width="100" prop="size_mb" />
        </el-table>
        <div class="bkup-tablepicker__tip">
          已选 {{ form.tables.length }} 张表
          <el-button text @click="onSelectAll" v-if="filteredTables.length">全选当前</el-button>
          <el-button text @click="form.tables = []">清空</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="bkup-step" shadow="never">
      <template #header><span class="bkup-step__title">③ 输出路径</span></template>
      <div class="bkup-path-select">
        <el-input
          :model-value="form.output_dir || backupConfig?.default_output_dir || './backups'"
          readonly
          placeholder="点击选择输出路径"
        >
          <template #append>
            <el-button :icon="FolderOpened" @click="showPathDialog = true">选择</el-button>
          </template>
        </el-input>
      </div>

      <el-dialog v-model="showPathDialog" title="选择备份输出路径" width="480px" :close-on-click-modal="false">
        <el-radio-group v-model="selectedPath" class="bkup-path-radio">
          <el-radio
            v-for="root in allowedRoots"
            :key="root"
            :value="root"
            class="bkup-path-radio__item"
          >
            <code>{{ root }}</code>
          </el-radio>
        </el-radio-group>
        <div v-if="!allowedRoots.length" class="bkup-path-empty">
          未获取到服务端白名单路径，将使用默认路径
        </div>
        <template #footer>
          <el-button @click="showPathDialog = false">取消</el-button>
          <el-button type="primary" @click="onConfirmPath">确定</el-button>
        </template>
      </el-dialog>
    </el-card>

    <el-card class="bkup-step" shadow="never">
      <template #header><span class="bkup-step__title">④ 文件名（选填）</span></template>
      <el-input
        v-model="form.name"
        placeholder="留空按 backup_type_yyyymmdd_hhmmss_<随机8>.sql 命名"
        clearable
        maxlength="120"
      />
    </el-card>

    <div class="bkup-actions">
      <el-button
        type="primary"
        :icon="VideoPlay"
        :loading="submitting"
        :disabled="!canSubmit"
        @click="onCreate"
      >
        开始备份
      </el-button>
      <el-text v-if="!canSubmit" type="warning" size="small">
        {{ submitHint }}
      </el-text>
    </div>

    <!-- 进度区：有 running 任务时显示 -->
    <el-card v-if="currentRecord" class="bkup-progress" shadow="never">
      <template #header>
        <span class="bkup-step__title">实时进度</span>
        <el-tag
          :type="statusTagType(currentRecord.status)"
          size="small"
          style="margin-left: 0.5rem"
        >
          {{ currentRecord.status }}
        </el-tag>
      </template>
      <el-progress
        :percentage="currentRecord.progress"
        :status="currentRecord.status === 'failed' ? 'exception' : ''"
      />
      <div class="bkup-progress__msg">{{ currentRecord.progress_msg || '准备中...' }}</div>
      <div v-if="currentRecord.status === 'success'" class="bkup-progress__success">
        文件：<code>{{ currentRecord.file_path }}</code>
        （共 {{ formatBytes(currentRecord.file_size) }}）
        <el-link
          type="primary"
          style="margin-left: 1rem"
          @click="onDownloadCurrent"
        >下载 .sql</el-link>
      </div>
      <div v-if="currentRecord.status === 'failed'" class="bkup-progress__err">
        {{ currentRecord.error_message }}
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, FolderOpened } from '@element-plus/icons-vue'
import {
  createBackup,
  listTables,
  getBackupConfig,
  downloadBackup,
  type CreateBackupRequest,
  type TableInfo,
  type BackupConfig,
  type BackupRecord,
} from '@/api/backup'
import { useBackupStore } from '@/stores/backup'

const store = useBackupStore()

const form = ref<CreateBackupRequest & { tables: string[] }>({
  backup_type: 'full',
  scope: 'all',
  tables: [],
  output_dir: store.pathConfig.outputDir || '',
  name: '',
})

const tables = ref<TableInfo[]>([])
const tableFilter = ref('')
const tablePickerRef = ref()
const backupConfig = ref<BackupConfig | null>(null)
const submitting = ref(false)
const showPathDialog = ref(false)
const selectedPath = ref('')
const allowedRoots = ref<string[]>([])

const currentRecordId = ref<number | null>(null)
const currentRecord = ref<BackupRecord | null>(null)

const filteredTables = computed(() => {
  const kw = tableFilter.value.trim().toLowerCase()
  if (!kw) return tables.value
  return tables.value.filter((t) => t.name.includes(kw))
})

const canSubmit = computed(() => {
  if (submitting.value) return false
  if (form.value.scope === 'partial' && form.value.tables.length === 0) return false
  return true
})

const submitHint = computed(() => {
  if (form.value.scope === 'partial' && form.value.tables.length === 0) {
    return '请至少选择一张表'
  }
  return ''
})

onMounted(async () => {
  try {
    const [tbl, cfg] = await Promise.all([listTables(), getBackupConfig().catch(() => null)])
    tables.value = tbl
    backupConfig.value = cfg
    if (cfg) {
      allowedRoots.value = cfg.allowed_roots || []
      if (!form.value.output_dir && cfg.default_output_dir) {
        form.value.output_dir = cfg.default_output_dir
        selectedPath.value = cfg.default_output_dir
      }
    }
  } catch (e) {
    ElMessage.error((e as Error).message || '加载表列表失败')
  }
})

function onConfirmPath() {
  if (selectedPath.value) {
    form.value.output_dir = selectedPath.value
  }
  showPathDialog.value = false
}

onBeforeUnmount(() => {
  if (currentRecordId.value) store.stopPolling(currentRecordId.value)
})

function onScopeChange(scope: 'all' | 'partial') {
  if (scope === 'all') form.value.tables = []
}

function onSelectionChange(rows: TableInfo[]) {
  form.value.tables = rows.map((r) => r.name)
}

function onSelectAll() {
  // 触发 Element Plus el-table 全选
  if (!tablePickerRef.value) return
  tablePickerRef.value.toggleAllSelection()
}

function categoryTagType(c: TableInfo['category']): 'success' | 'primary' | 'warning' | 'info' | 'danger' {
  return (
    {
      system: 'danger',
      market: 'primary',
      financial: 'warning',
      concept: 'success',
      business: 'info',
    } as const
  )[c]
}

function statusTagType(s: BackupRecord['status']): 'success' | 'warning' | 'danger' | 'info' {
  return (
    {
      pending: 'info',
      running: 'warning',
      success: 'success',
      failed: 'danger',
      interrupted: 'info',
    } as const
  )[s]
}

function formatBytes(b: number | null | undefined): string {
  if (!b) return '0 B'
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} MB`
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} GB`
}

async function onDownloadCurrent() {
  if (!currentRecord.value) return
  try {
    await downloadBackup(currentRecord.value.id)
  } catch (e) {
    ElMessage.error((e as Error).message || '下载失败')
  }
}

async function onCreate() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    // 提交前同步一次本地路径
    if (form.value.output_dir !== store.pathConfig.outputDir) {
      store.setOutputDir(form.value.output_dir)
    }

    const req: CreateBackupRequest = {
      backup_type: form.value.backup_type,
      scope: form.value.scope,
      tables: form.value.scope === 'partial' ? form.value.tables : undefined,
      output_dir: form.value.output_dir || null,
      name: form.value.name || null,
    }

    const { id } = await createBackup(req)
    currentRecordId.value = id
    ElMessage.success(`已创建备份任务 #${id}`)

    // 启动轮询；首次拉一次作为 currentRecord 初值
    const initial = await store.fetchBackup(id).catch(() => null)
    currentRecord.value = initial

    store.startPolling(
      id,
      store.fetchBackup,
      (r) => {
        currentRecord.value = r
        if (r.status === 'success') {
          ElMessage.success('备份完成')
          submitting.value = false
        } else if (r.status === 'failed') {
          ElMessage.error(r.error_message || '备份失败')
          submitting.value = false
        }
      },
    )
  } catch (e) {
    ElMessage.error((e as Error).message || '创建失败')
    submitting.value = false
  }
}
</script>

<style scoped>
.bkup-create {
  display: flex;
  flex-direction: column;
  gap: var(--bkup-gap-xl);
  padding: 0 var(--bkup-card-padding);
}
.bkup-step {
  --el-card-padding: calc(0.7rem * var(--bkup-page-density));
  --el-card-border-radius: 10px;
}
.bkup-step__title {
  font-weight: 700;
  color: #1e293b;
}
.bkup-tablepicker {
  margin-top: 0.6rem;
}
.bkup-tablepicker__tip {
  margin-top: 0.4rem;
  font-size: 0.85rem;
  color: #475569;
}
.bkup-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0 var(--bkup-card-padding);
}
.bkup-progress {
  margin: 0 var(--bkup-card-padding);
}
.bkup-progress__msg {
  margin-top: 0.5rem;
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
  color: #475569;
}
.bkup-progress__success {
  margin-top: 0.6rem;
  font-size: 0.9rem;
}
.bkup-progress__err {
  margin-top: 0.6rem;
  color: #dc2626;
  font-size: 0.9rem;
}
.bkup-path-select {
  max-width: 500px;
}
.bkup-path-radio {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.bkup-path-radio__item {
  height: auto !important;
}
.bkup-path-radio__item code {
  font-size: 0.9rem;
}
.bkup-path-empty {
  color: #94a3b8;
  font-size: 0.9rem;
  padding: 1rem 0;
}
</style>