<!--
  RestorePage · 独立恢复页
  - 2 步骤卡片：来源 / 模式
  - "确认恢复" 危险按钮（ElMessageBox 二次确认）
  - 上传文件方式：el-upload
  - history 模式：选历史备份
  - file 模式：手填路径
  - el-progress 进度区
-->
<template>
  <PageWrapper :style="densityStyle" class="bkup-page">
    <template #title>
      <el-icon class="bkup-title-icon"><RefreshLeft /></el-icon>
      <span class="bkup-page-title">数据恢复</span>

      <BackupDensityPanel :show="showDensity" />
      <button
        class="bkup-density-toggle"
        :class="{ active: showDensity }"
        title="页面密度"
        @click="showDensity = !showDensity"
      >
        <el-icon><Setting /></el-icon>
      </button>
    </template>

    <div class="bkup-restore">
      <el-alert
        type="error"
        :closable="false"
        show-icon
        title="危险操作提示"
        description="cover 模式将执行 DROP + CREATE + COPY；upsert 模式执行 INSERT ON CONFLICT DO NOTHING。请确认你知道自己在做什么。"
        style="margin-bottom: 0.6rem"
      />

      <el-card class="bkup-step" shadow="never">
        <template #header><span class="bkup-step__title">① 来源</span></template>
        <el-radio-group v-model="form.source_type" @change="onSourceTypeChange">
          <el-radio-button value="upload">upload · 上传 .sql</el-radio-button>
          <el-radio-button value="file">file · 服务端路径</el-radio-button>
        </el-radio-group>

        <!-- upload 模式 -->
        <div v-if="form.source_type === 'upload'" class="bkup-step__body">
          <el-upload
            v-if="!uploadResult"
            :auto-upload="true"
            :show-file-list="false"
            :before-upload="onBeforeUpload"
            :http-request="customUpload"
            drag
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">拖拽或点击上传 .sql 文件（≤ 500MB）</div>
          </el-upload>
          <div v-else class="bkup-upload-info">
            <el-icon><DocumentChecked /></el-icon>
            <div class="bkup-upload-info__meta">
              <div><strong>{{ uploadResult.filename }}</strong> ({{ formatBytes(uploadResult.size) }})</div>
              <div v-if="uploadResult.header?.backup_name">
                备份名：<code>{{ uploadResult.header.backup_name }}</code>
              </div>
              <div v-if="uploadResult.header?.tables_count">
                表数：{{ uploadResult.header.tables_count }}
              </div>
              <div v-if="uploadResult.header?.generator">
                生成器：{{ uploadResult.header.generator }} v{{ uploadResult.header.generator_version }}
              </div>
            </div>
            <el-button text type="danger" @click="uploadResult = null">移除</el-button>
          </div>
        </div>

        <!-- file 模式 -->
        <div v-else-if="form.source_type === 'file'" class="bkup-step__body">
          <el-input
            v-model="form.source_path"
            placeholder="服务端 .sql 绝对路径，例如 D:/backups/db.sql"
            clearable
          />
          <div class="bkup-path-tip">
            服务端会做白名单校验；路径必须落在 <code>BACKUP_ALLOWED_ROOTS</code> 下
          </div>
        </div>
      </el-card>

      <el-card class="bkup-step" shadow="never">
        <template #header><span class="bkup-step__title">② 恢复模式</span></template>
        <el-radio-group v-model="form.restore_mode">
          <el-radio-button value="cover">
            cover（破坏性，覆盖已有表）
          </el-radio-button>
          <el-radio-button value="upsert">
            upsert（保留已有数据，INSERT ... ON CONFLICT DO NOTHING）
          </el-radio-button>
        </el-radio-group>
      </el-card>

      <div class="bkup-actions">
        <el-button
          type="danger"
          :icon="RefreshLeft"
          :loading="submitting"
          :disabled="!canSubmit"
          @click="onConfirm"
        >
          确认恢复
        </el-button>
        <el-text v-if="!canSubmit" type="warning" size="small">{{ submitHint }}</el-text>
      </div>

      <el-card v-if="currentRecord" class="bkup-progress" shadow="never">
        <template #header>
          <span class="bkup-step__title">恢复进度</span>
          <el-tag
            :type="statusTagType(currentRecord.status)"
            size="small"
            style="margin-left: 0.5rem"
          >{{ currentRecord.status }}</el-tag>
        </template>
        <el-progress
          :percentage="currentRecord.progress"
          :status="currentRecord.status === 'failed' ? 'exception' : ''"
        />
        <div class="bkup-progress__msg">{{ currentRecord.progress_msg || '准备中...' }}</div>
        <div v-if="currentRecord.status === 'failed'" class="bkup-progress__err">
          {{ currentRecord.error_message }}
        </div>
      </el-card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DocumentChecked, RefreshLeft, Setting, UploadFilled } from '@element-plus/icons-vue'
import PageWrapper from '@/components/PageWrapper.vue'
import BackupDensityPanel from '@/components/backup/BackupDensityPanel.vue'
import {
  restore,
  uploadBackupFile,
  type RestoreRequest,
  type UploadResponse,
  type RestoreRecord,
} from '@/api/backup'
import { useBackupStore } from '@/stores/backup'
import { useBackupDensity } from '@/composables/useBackupDensity'

const { densityStyle } = useBackupDensity()
const showDensity = ref(false)

const store = useBackupStore()

const form = ref<RestoreRequest>({
  source_type: 'upload',
  source_backup_id: null,
  upload_id: null,
  source_path: '',
  restore_mode: 'cover',
  confirm: false,
})

const uploadResult = ref<UploadResponse | null>(null)
const submitting = ref(false)
const currentRecordId = ref<number | null>(null)
const currentRecord = ref<RestoreRecord | null>(null)

const canSubmit = computed(() => {
  if (submitting.value) return false
  if (form.value.source_type === 'upload' && !uploadResult.value) return false
  if (form.value.source_type === 'file' && !form.value.source_path.trim()) return false
  return true
})

const submitHint = computed(() => {
  if (form.value.source_type === 'upload' && !uploadResult.value) return '请先上传 .sql 文件'
  if (form.value.source_type === 'file' && !form.value.source_path.trim()) return '请填写服务端路径'
  return ''
})

onBeforeUnmount(() => {
  if (currentRecordId.value) store.stopPolling(currentRecordId.value)
})

function statusTagType(s: RestoreRecord['status']): 'success' | 'warning' | 'danger' | 'info' {
  return (
    {
      pending: 'info',
      running: 'warning',
      success: 'success',
      failed: 'danger',
    } as const
  )[s]
}

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1024 * 1024 * 1024) return `${(b / 1024 / 1024).toFixed(1)} MB`
  return `${(b / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function onSourceTypeChange(t: 'upload' | 'file' | 'history') {
  form.value.source_backup_id = null
  form.value.upload_id = null
  form.value.source_path = ''
  if (t !== 'upload') uploadResult.value = null
}

function onBeforeUpload(file: File): boolean {
  if (!file.name.toLowerCase().endsWith('.sql')) {
    ElMessage.error('只支持 .sql 文件')
    return false
  }
  if (file.size > 500 * 1024 * 1024) {
    ElMessage.error('文件超过 500MB')
    return false
  }
  return true
}

async function customUpload(opts: { file: File }) {
  try {
    uploadResult.value = await uploadBackupFile(opts.file)
    ElMessage.success('上传成功')
  } catch (e) {
    ElMessage.error((e as Error).message || '上传失败')
  }
}

async function onConfirm() {
  if (!canSubmit.value) return

  try {
    await ElMessageBox.confirm(
      `即将以 ${form.value.restore_mode} 模式恢复数据库。此操作不可撤销，确认继续？`,
      '危险操作二次确认',
      {
        type: 'error',
        confirmButtonText: '我已了解，确认恢复',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  submitting.value = true
  try {
    const req: RestoreRequest = {
      source_type: form.value.source_type,
      restore_mode: form.value.restore_mode,
      confirm: true,
    }
    if (form.value.source_type === 'upload') {
      req.upload_id = uploadResult.value?.upload_id || null
    } else if (form.value.source_type === 'file') {
      req.source_path = form.value.source_path.trim()
    } else if (form.value.source_type === 'history') {
      req.source_backup_id = form.value.source_backup_id
    }

    const { id } = await restore(req)
    currentRecordId.value = id
    ElMessage.success(`已创建恢复任务 #${id}`)

    const initial = await store.fetchRestore(id).catch(() => null)
    currentRecord.value = initial

    store.startPolling(
      id,
      store.fetchRestore,
      (r) => {
        currentRecord.value = r
        if (r.status === 'success') {
          ElMessage.success('恢复完成')
          submitting.value = false
        } else if (r.status === 'failed') {
          ElMessage.error(r.error_message || '恢复失败')
          submitting.value = false
        }
      },
    )
  } catch (e) {
    ElMessage.error((e as Error).message || '创建恢复任务失败')
    submitting.value = false
  }
}
</script>

<style scoped>
.bkup-restore {
  display: flex;
  flex-direction: column;
  gap: var(--bkup-gap-lg);
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
.bkup-step__body {
  margin-top: 0.6rem;
}
.bkup-path-tip {
  font-size: 0.78rem;
  color: #94a3b8;
  margin-top: 0.25rem;
}
.bkup-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.bkup-upload-info {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.6rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}
.bkup-upload-info__meta {
  flex: 1;
  font-size: 0.88rem;
  line-height: 1.6;
}
.bkup-progress {
  --el-card-padding: calc(0.7rem * var(--bkup-page-density));
}
.bkup-progress__msg {
  margin-top: 0.5rem;
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
  color: #475569;
}
.bkup-progress__err {
  margin-top: 0.6rem;
  color: #dc2626;
  font-size: 0.9rem;
}
</style>