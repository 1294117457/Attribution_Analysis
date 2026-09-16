<template>
  <el-dialog
    v-model="visible"
    :title="pool ? '编辑操作池' : '新建操作池'"
    width="500px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
      label-position="right"
    >
      <el-form-item label="名称" prop="name">
        <el-input
          v-model="form.name"
          placeholder="如：银行股组合"
          maxlength="64"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="类型">
        <el-select v-model="form.pool_type" style="width: 100%" :disabled="!!pool">
          <el-option label="自选股" value="watchlist">
            <span>⭐ 自选股</span>
          </el-option>
          <el-option label="行业" value="industry">
            <span>🏦 行业</span>
          </el-option>
          <el-option label="策略" value="strategy">
            <span>📈 策略</span>
          </el-option>
          <el-option label="自定义" value="custom">
            <span>📂 自定义</span>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="图标">
        <el-input
          v-model="form.icon"
          placeholder="emoji 或留空"
          maxlength="32"
        />
      </el-form-item>

      <el-form-item label="颜色">
        <el-color-picker v-model="form.color" />
        <span class="ml-3 text-xs text-gray-500">留空使用默认色</span>
      </el-form-item>

      <el-form-item label="描述">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          maxlength="255"
          show-word-limit
          placeholder="可选：池的用途和说明"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { usePoolStore } from '@/stores/pool'
import type { Pool, PoolCreateRequest, PoolUpdateRequest } from '@/views/stock-pool/api'

const props = defineProps<{
  modelValue: boolean
  pool?: Pool | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [pool: Pool]
}>()

const store = usePoolStore()

const visible = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  pool_type: 'custom' as PoolCreateRequest['pool_type'],
  icon: '',
  color: undefined as string | undefined,
  description: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入池名称', trigger: 'blur' },
    { min: 1, max: 64, message: '长度 1-64 字符', trigger: 'blur' },
  ],
}

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val) resetForm()
  },
)

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function resetForm() {
  if (props.pool) {
    form.name = props.pool.name
    form.pool_type = props.pool.pool_type
    form.icon = props.pool.icon ?? ''
    form.color = props.pool.color ?? undefined
    form.description = props.pool.description ?? ''
  } else {
    form.name = ''
    form.pool_type = 'custom'
    form.icon = ''
    form.color = undefined
    form.description = ''
  }
}

async function handleSave() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    let result: Pool
    if (props.pool) {
      const updateData: PoolUpdateRequest = {
        name: form.name,
        icon: form.icon || undefined,
        color: form.color || undefined,
        description: form.description || undefined,
      }
      result = await store.updatePool(props.pool.id, updateData)
    } else {
      const createData: PoolCreateRequest = {
        name: form.name,
        pool_type: form.pool_type,
        icon: form.icon || undefined,
        color: form.color || undefined,
        description: form.description || undefined,
      }
      result = await store.createPool(createData)
    }
    ElMessage.success('保存成功')
    emit('saved', result)
    visible.value = false
  } catch (e) {
    ElMessage.error('保存失败: ' + (e as Error).message)
  } finally {
    saving.value = false
  }
}

function handleClose() {
  formRef.value?.resetFields()
}
</script>

<style scoped>
.ml-3 {
  margin-left: 12px;
}
</style>
