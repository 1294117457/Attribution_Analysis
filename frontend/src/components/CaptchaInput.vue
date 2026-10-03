<!--
  CaptchaInput.vue
  ─────────────────────────────────────────────────────────────
  图形验证码输入组件(基于 /api/v1/auth/captcha/generate)

  行为:
  - 挂载时自动拉取一张新验证码
  - 点击图片 / 文字"换一张"按钮 / 父组件调用 refresh() 时重新拉取
  - 父组件通过 v-model 拿到 { captcha_id, captcha_code } 对象
  - 通过 prop :error="true" 把"后端校验失败"的红框状态传给子组件
-->
<template>
  <div class="captcha-row">
    <el-input
      v-model="inputText"
      :placeholder="placeholder"
      :maxlength="6"
      :prefix-icon="Picture"
      :status="error ? 'error' : undefined"
      clearable
      @input="emitChange"
    />
    <div
      class="captcha-img-box"
      :class="{ 'is-loading': loading }"
      @click="refresh"
      role="button"
      tabindex="0"
      :aria-label="'点击刷新图形验证码'"
      @keyup.enter="refresh"
    >
      <img
        v-if="imageBase64"
        :src="imageBase64"
        alt="图形验证码"
        class="captcha-img"
        draggable="false"
      />
      <div v-else-if="loading" class="captcha-placeholder">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中</span>
      </div>
      <div v-else class="captcha-placeholder">
        <span>点击获取</span>
      </div>
    </div>
    <el-button
      link
      type="primary"
      class="refresh-btn"
      :disabled="loading"
      @click="refresh"
    >
      <el-icon><Refresh /></el-icon>
      <span>换一张</span>
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Picture, Refresh } from '@element-plus/icons-vue'
import { generateCaptcha } from '@/views/auth/api'

const props = withDefaults(
  defineProps<{
    placeholder?: string
    error?: boolean
  }>(),
  {
    placeholder: '请输入图形验证码',
    error: false,
  },
)
// 触发 props 解构(避免 unused-var 警告):保留 props 占位,用于将来扩展
void props

const emit = defineEmits<{
  (e: 'update:modelValue', value: { captcha_id: string; captcha_code: string }): void
  (e: 'refreshed', captchaId: string): void
}>()

const inputText = ref('')
const captchaId = ref('')
const imageBase64 = ref('')
const loading = ref(false)

function emitChange() {
  emit('update:modelValue', {
    captcha_id: captchaId.value,
    captcha_code: inputText.value.trim(),
  })
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  try {
    const data = await generateCaptcha()
    captchaId.value = data.captcha_id
    imageBase64.value = data.base64
    inputText.value = ''
    emit('update:modelValue', { captcha_id: captchaId.value, captcha_code: '' })
    emit('refreshed', captchaId.value)
  } catch (e) {
    console.warn('captcha load failed', e)
    ElMessage.error('图形验证码加载失败,请稍后重试')
  } finally {
    loading.value = false
  }
}

defineExpose({ refresh })

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.captcha-row {
  display: flex;
  gap: 8px;
  width: 100%;
  align-items: stretch;
}

.captcha-row :deep(.el-input) {
  flex: 1;
  min-width: 0;
}

.captcha-img-box {
  flex-shrink: 0;
  width: 120px;
  height: 40px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafbfc;
  transition: border-color 0.2s, transform 0.1s;
  user-select: none;
}

.captcha-img-box:hover {
  border-color: var(--el-color-primary, #409eff);
}

.captcha-img-box:active {
  transform: scale(0.98);
}

.captcha-img-box.is-loading {
  cursor: wait;
}

.captcha-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  pointer-events: none;
}

.captcha-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #909399;
  font-size: 12px;
}

.refresh-btn {
  flex-shrink: 0;
  white-space: nowrap;
  padding-left: 4px;
  padding-right: 4px;
  font-size: 12px;
}
</style>
