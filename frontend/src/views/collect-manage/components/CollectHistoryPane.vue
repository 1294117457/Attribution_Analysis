<!--
  CollectHistoryPane.vue — 采集历史（Java 查 PG collect_logs，永久审计）

  数据源：GET /collect/logs?facet=&name=&status=&page=&pageSize=
  与轮询进度（Redis 临时）区分：重启丢 Redis 也不影响这里。
-->
<template>
  <div class="history-pane">
    <el-form :inline="true" size="small" class="filter-row" @submit.prevent="reload(1)">
      <el-form-item label="facet">
        <el-select v-model="filter.facet" clearable placeholder="全部" class="!w-32" @change="reload(1)">
          <el-option label="技术面 tech" value="tech" />
          <el-option label="资金面 capital" value="capital" />
          <el-option label="基本面 fundamental" value="fundamental" />
          <el-option label="资讯 news" value="news" />
          <el-option label="情绪 sentiment" value="sentiment" />
        </el-select>
      </el-form-item>
      <el-form-item label="service">
        <el-input v-model="filter.name" clearable placeholder="如 daily_kline" class="!w-44" @keyup.enter="reload(1)" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filter.status" clearable placeholder="全部" class="!w-28" @change="reload(1)">
          <el-option label="排队中" value="queued" />
          <el-option label="执行中" value="running" />
          <el-option label="完成" value="done" />
          <el-option label="失败" value="failed" />
          <el-option label="已中断" value="cancelled" />
        </el-select>
      </el-form-item>
      <el-form-item label="采集类型">
        <el-select v-model="filter.kind" clearable placeholder="全部" class="!w-32" @change="reload(1)">
          <el-option label="增量采集" value="incremental" />
          <el-option label="全量覆盖" value="full" />
        </el-select>
      </el-form-item>
      <el-form-item label="仅看有失败">
        <el-switch v-model="filter.hasFail" @change="reload(1)" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="reload(1)">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="rows" size="small" stripe v-loading="loading" max-height="520">
      <el-table-column prop="task_id" label="task_id" min-width="150" />
      <el-table-column prop="name" label="service" min-width="140" />
      <el-table-column label="采集类型" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="kindType(row.kind)" effect="plain">
            {{ KIND_LABEL[row.kind] || row.kind || '—' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="区间" min-width="190">
        <template #default="{ row }">{{ rangeText(row) }}</template>
      </el-table-column>
      <el-table-column label="步数" width="90">
        <template #default="{ row }">{{ row.done ?? 0 }}/{{ row.total ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="失败" width="70">
        <template #default="{ row }">
          <span v-if="(row.fail ?? 0) > 0" class="text-red-500">{{ row.fail }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="跳过" width="70">
        <template #default="{ row }">
          <span v-if="(row.skip ?? 0) > 0">{{ row.skip }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="saved_total" label="写入行数" width="90" />
      <el-table-column prop="message" label="信息" min-width="220" show-overflow-tooltip />
      <el-table-column label="创建" min-width="160">
        <template #default="{ row }">{{ timeText(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="终态" min-width="160">
        <template #default="{ row }">{{ timeText(row.finished_at) }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next"
      class="pager"
      @current-change="reload"
      @size-change="reload(1)"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listCollectLogs, type CollectLogRow } from '../api'

const STATUS_LABEL: Record<string, string> = {
  queued: '排队中',
  running: '执行中',
  done: '完成',
  failed: '失败',
  cancelled: '已中断',
}

/** ★ 采集类型标签（kind 列承载 strategy：incremental / full） */
const KIND_LABEL: Record<string, string> = {
  incremental: '增量采集',
  full: '全量覆盖',
}

const filter = reactive({ facet: '', name: '', status: '', kind: '', hasFail: false })
const rows = ref<CollectLogRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

function statusType(status: string) {
  if (status === 'done') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  if (status === 'cancelled') return 'info'
  return 'info'
}

function kindType(kind: string) {
  if (kind === 'incremental') return 'success'
  if (kind === 'full') return 'warning'
  return 'info'
}

function rangeText(row: CollectLogRow): string {
  if (row.range_start || row.range_end) return `${row.range_start || '?'} → ${row.range_end || '?'}`
  return '—'
}

/**
 * 时间显示：ISO-8601 带时区 → 本地时间。
 *
 * ⚠️ 后端返回的是 UTC（如 2026-10-29T14:43:27.926076Z），
 * 直接 `prop` 绑定会把 "Z" 串原样显示出来；
 * 用 Date 解析后转本地时区才是人看得懂的时间。
 */
function timeText(v?: string | null): string {
  if (!v) return '—'
  const d = new Date(v)
  if (isNaN(d.getTime())) return v
  return d.toLocaleString('zh-CN', { hour12: false })
}

async function reload(p = page.value) {
  page.value = p
  loading.value = true
  try {
    const res = await listCollectLogs({
      facet: filter.facet || undefined,
      name: filter.name || undefined,
      status: filter.status || undefined,
      kind: filter.kind || undefined,
      hasFail: filter.hasFail || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    rows.value = res.list || []
    total.value = res.total || 0
  } catch (e: any) {
    ElMessage.error(e?.message || '加载采集历史失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => reload(1))
</script>

<style scoped>
.history-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}
</style>
