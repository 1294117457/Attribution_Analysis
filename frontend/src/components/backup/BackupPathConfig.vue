<!--
  BackupPathConfig · 路径配置弹窗
  - 备份输出根（outputDir）
  - 恢复读取根（inputDir）
  - 显示服务端白名单（只读）
  - 保存：写 localStorage + 调用 updateBackupConfig
-->
<template>
  <el-dialog v-model="visible" title="路径配置" :close-on-click-modal="false">
    <el-form label-width="110px">
      <el-form-item label="备份输出根">
        <el-input
          v-model="form.outputDir"
          placeholder="默认 ./backups；留空用服务端默认值"
          clearable
        />
        <div class="bkup-path-tip">
          备份任务完成后 .sql 文件落在此根目录下；服务端会做白名单校验
        </div>
      </el-form-item>

      <el-form-item label="恢复读取根">
        <el-input
          v-model="form.inputDir"
          placeholder="恢复时选择 .sql 的起点目录"
          clearable
        />
        <div class="bkup-path-tip">
          选填，仅作前端默认起点；恢复时仍可手动指定其他路径
        </div>
      </el-form-item>

      <el-form-item label="服务端白名单">
        <div class="bkup-roots">
          <el-tag
            v-for="r in allowedRoots"
            :key="r"
            size="small"
            type="info"
            class="bkup-roots__tag"
          >
            {{ r }}
          </el-tag>
          <div class="bkup-path-tip">
            来自 <code>settings.BACKUP_ALLOWED_ROOTS</code>；所有写入路径必须落在这些目录下
          </div>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useBackupStore } from '@/stores/backup'
import { getBackupConfig, updateBackupConfig } from '@/api/backup'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => (visible.value = v))
watch(visible, (v) => emit('update:modelValue', v))

const store = useBackupStore()
const form = reactive({
  outputDir: '',
  inputDir: '',
})

const allowedRoots = ref<string[]>([])
const saving = ref(false)

// 打开时同步一次本地 + 拉服务端配置
watch(visible, async (open) => {
  if (!open) return
  form.outputDir = store.pathConfig.outputDir
  form.inputDir = store.pathConfig.inputDir
  try {
    const cfg = await getBackupConfig()
    allowedRoots.value = cfg.allowed_roots
  } catch (e) {
    ElMessage.error((e as Error).message || '拉取配置失败')
  }
})

async function onSave() {
  saving.value = true
  try {
    store.setOutputDir(form.outputDir)
    store.setInputDir(form.inputDir)
    await updateBackupConfig({ default_output_dir: form.outputDir || null })
    ElMessage.success('已保存')
    visible.value = false
  } catch (e) {
    ElMessage.error((e as Error).message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.bkup-path-tip {
  font-size: 0.78rem;
  color: #94a3b8;
  margin-top: 0.25rem;
  line-height: 1.4;
}
.bkup-roots {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
}
.bkup-roots__tag {
  font-family: ui-monospace, monospace;
}
</style>