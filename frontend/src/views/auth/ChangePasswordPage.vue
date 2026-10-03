<template>
  <div class="cp-page page-wrapper">
    <header class="page-header">
      <div>
        <h1 class="page-title">修改密码</h1>
        <p class="page-subtitle">
          当前账号：{{ authStore.userInfo?.email || '—' }}
        </p>
      </div>
    </header>

    <el-card class="cp-card" shadow="never">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        size="large"
        @keyup.enter="submit"
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password clearable />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password clearable />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" show-password clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="submit">
            提交
          </el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        type="warning"
        show-icon
        :closable="false"
        title="注意"
        description="修改密码将撤销您所有未过期的登录会话，提交后需重新登录。"
        class="tip"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import http, { unwrap } from '@/common/utils/http'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度 8-64 位', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度 8-64 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator(_r, v, cb) {
        if (v !== form.new_password) cb(new Error('两次输入的新密码不一致'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

async function submit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await http
      .post('/auth/change-password', {
        old_password: form.old_password,
        new_password: form.new_password,
      })
      .then(unwrap)
    ElMessage.success('密码已修改，请重新登录')
    await authStore.logout()
    router.push('/login')
  } catch {
    // http 拦截器已弹错
  } finally {
    loading.value = false
  }
}

function reset() {
  form.old_password = ''
  form.new_password = ''
  form.confirm_password = ''
  formRef.value?.clearValidate()
}
</script>

<style scoped>
.cp-page {
  padding: var(--density-card-padding);
  background: var(--color-admin-bg);
  display: flex;
  flex-direction: column;
  gap: var(--density-gap-xl);
  min-height: 100%;
  max-width: 720px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: var(--density-title-min);
}

.page-title {
  font-size: 1.25rem;
  font-weight: 700;
}

.page-subtitle {
  font-size: 0.85rem;
  color: var(--color-admin-muted);
  margin-top: 4px;
}

.cp-card {
  border-radius: 12px;
}

.tip {
  margin-top: 12px;
}
</style>