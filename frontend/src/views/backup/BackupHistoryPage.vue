<!--
  BackupHistoryPage · 子页 2
  - 状态筛选 + 刷新
  - el-table 列表（9 列，用 colW(px) 控列宽）
  - 分页
  - 行操作：下载、删除
-->
<template>
  <div class="bkup-history">
    <div class="bkup-history__toolbar">
      <el-select
        v-model="filter.status"
        placeholder="全部状态"
        clearable
        style="width: 160px"
        @change="loadList(1)"
      >
        <el-option label="pending" value="pending" />
        <el-option label="running" value="running" />
        <el-option label="success" value="success" />
        <el-option label="failed" value="failed" />
        <el-option label="interrupted" value="interrupted" />
      </el-select>
      <el-button :icon="RefreshIcon" @click="loadList()">刷新</el-button>
      <el-text type="info" size="small" class="bkup-history__count">
        共 {{ total }} 条
      </el-text>
    </div>

    <el-table
      v-loading="loading"
      :data="items"
      :style="{ '--el-table-cell-padding-x': '10px', '--el-table-cell-padding-y': '5px' }"
      size="default"
      class="bkup-history__table"
      :default-sort="{ prop: 'id', order: 'descending' }"
    >
      <el-table-column prop="id" label="ID" :width="colW(60)" sortable />
      <el-table-column prop="name" label="文件名" :width="colW(280)" show-overflow-tooltip>
        <template #default="{ row }">
          <code class="bkup-history__filename">{{ row.name }}</code>
        </template>
      </el-table-column>
      <el-table-column prop="backup_type" label="粒度" :width="colW(80)">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.backup_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="tables_count" label="表数" :width="colW(70)" />
      <el-table-column label="行数" :width="colW(100)">
        <template #default="{ row }">
          {{ formatNumber(row.row_count) }}
        </template>
      </el-table-column>
      <el-table-column label="大小" :width="colW(100)">
        <template #default="{ row }">
          {{ row.file_size ? formatBytes(row.file_size) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" :width="colW(110)">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
          <el-progress
            v-if="row.status === 'running' || row.status === 'pending'"
            :percentage="row.progress"
            :stroke-width="4"
            style="margin-top: 4px"
          />
        </template>
      </el-table-column>
      <el-table-column label="创建时间" :width="colW(170)" prop="created_at" sortable>
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" :width="colW(160)" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'success' && row.file_path"
            size="small"
            link
            type="primary"
            @click="onDownload(row)"
          >下载</el-button>
          <el-button
            size="small"
            link
            type="danger"
            :disabled="row.status === 'running' || row.status === 'pending'"
            @click="onDelete(row)"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="bkup-history__pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        background
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="(p) => loadList(p)"
        @size-change="() => loadList(1)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh as RefreshIcon } from '@element-plus/icons-vue'
import {
  listBackups,
  deleteBackup,
  downloadBackup,
  type BackupRecord,
  type BackupStatus,
} from '@/api/backup'
import { useBackupDensity } from '@/composables/useBackupDensity'

const { colW } = useBackupDensity()

const filter_ = reactive<{ status: BackupStatus | '' }>({ status: '' })
const items = ref<BackupRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const filter = filter_

// 轮询 running 任务
const pollers: Record<number, number> = {}
function pollIfRunning(rows: BackupRecord[]) {
  // 清掉已不在跑中的
  for (const idStr of Object.keys(pollers)) {
    const id = Number(idStr)
    if (!rows.find((r) => r.id === id && (r.status === 'running' || r.status === 'pending'))) {
      window.clearInterval(pollers[id])
      delete pollers[id]
    }
  }
  // 给新进入 running/pending 的加轮询
  for (const r of rows) {
    if ((r.status === 'running' || r.status === 'pending') && !pollers[r.id]) {
      pollers[r.id] = window.setInterval(async () => {
        try {
          const updated = await (await import('@/api/backup')).getBackup(r.id)
          const idx = items.value.findIndex((x) => x.id === r.id)
          if (idx >= 0) items.value.splice(idx, 1, updated)
          if (updated.status !== 'running' && updated.status !== 'pending') {
            window.clearInterval(pollers[r.id])
            delete pollers[r.id]
          }
        } catch {
          /* ignore */
        }
      }, 2000)
    }
  }
}

onBeforeUnmount(() => {
  for (const id of Object.keys(pollers)) window.clearInterval(pollers[Number(id)])
})

function statusTagType(s: BackupStatus): 'success' | 'warning' | 'danger' | 'info' {
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

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} MB`
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function formatNumber(n: number): string {
  if (n < 1000) return String(n)
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}K`
  return `${(n / 1_000_000).toFixed(2)}M`
}

function formatDate(s: string): string {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadList(targetPage?: number) {
  if (targetPage) page.value = targetPage
  loading.value = true
  try {
    const res = await listBackups({
      page: page.value,
      page_size: pageSize.value,
      status: (filter.value.status || undefined) as BackupStatus | undefined,
    })
    items.value = res.items
    total.value = res.total
    pollIfRunning(res.items)
  } catch (e) {
    ElMessage.error((e as Error).message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function onDownload(row: BackupRecord) {
  try {
    await downloadBackup(row.id)
  } catch (e) {
    ElMessage.error((e as Error).message || '下载失败')
  }
}

async function onDelete(row: BackupRecord) {
  try {
    await ElMessageBox.confirm(`确认删除备份 "${row.name}"？文件将一并删除`, '危险操作', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteBackup(row.id)
    ElMessage.success('已删除')
    await loadList()
  } catch (e) {
    ElMessage.error((e as Error).message || '删除失败')
  }
}

onMounted(() => loadList(1))
</script>

<style scoped>
.bkup-history {
  display: flex;
  flex-direction: column;
  gap: var(--bkup-gap-md);
  padding: 0 var(--bkup-card-padding);
  height: 100%;
}
.bkup-history__toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.bkup-history__count {
  margin-left: auto;
}
.bkup-history__table {
  flex: 1;
  min-height: 0;
}
.bkup-history__filename {
  font-family: ui-monospace, monospace;
  font-size: 0.82rem;
  color: #475569;
}
.bkup-history__pagination {
  display: flex;
  justify-content: flex-end;
}
</style>