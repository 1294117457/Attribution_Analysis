<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- 左侧品牌 -->
      <div class="auth-brand">
        <div class="brand-icon">📈</div>
        <h1 class="brand-title">智能金融归因分析平台</h1>
        <p class="brand-subtitle">
          A 股全维度数据 · 归因分析 · 操作池联动
        </p>
        <ul class="brand-features">
          <li><el-icon><CircleCheckFilled /></el-icon> 实时行情 + 历史日线 + 分钟线</li>
          <li><el-icon><CircleCheckFilled /></el-icon> 板块成分 + 资金面 + 基本面</li>
          <li><el-icon><CircleCheckFilled /></el-icon> 操作池跟踪 + 归因可视化</li>
        </ul>
      </div>

      <!-- 右侧表单 -->
      <div class="auth-form">
        <el-tabs v-model="activeTab" class="auth-tabs" stretch>
          <el-tab-pane label="登录" name="login" />
          <el-tab-pane label="注册" name="register" />
        </el-tabs>

        <!-- 登录 -->
        <el-form
          v-if="activeTab === 'login'"
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          size="large"
          label-position="top"
          @keyup.enter="handleLogin"
        >
          <el-form-item label="邮箱" prop="email">
            <el-input
              v-model="loginForm.email"
              placeholder="请输入邮箱"
              :prefix-icon="Message"
              clearable
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>
          <el-form-item label="图形验证码" prop="captcha_code">
            <CaptchaInput
              ref="loginCaptchaRef"
              v-model="loginForm.captcha"
              :error="!!loginCaptchaError"
            />
          </el-form-item>
          <el-button
            type="primary"
            class="submit-btn"
            :loading="loginLoading"
            @click="handleLogin"
          >
            登录
          </el-button>

          <div class="auth-foot">
            <span>还没有账号？</span>
            <el-link type="primary" :underline="false" @click="switchToRegister">
              立即注册
            </el-link>
          </div>

          <el-alert
            class="hint"
            type="info"
            show-icon
            :closable="false"
            title="初始管理员"
            description="邮箱：admin@local · 密码：admin123（首次登录后请尽快修改）"
          />
        </el-form>

        <!-- 注册 -->
        <el-form
          v-else
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          size="large"
          label-position="top"
          @keyup.enter="handleRegister"
        >
          <el-form-item label="邮箱" prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="任意邮箱（会收到验证码）"
              :prefix-icon="Message"
              clearable
            />
          </el-form-item>
          <el-form-item label="图形验证码" prop="send_captcha_code">
            <CaptchaInput
              ref="sendCaptchaRef"
              v-model="registerForm.sendCaptcha"
              :error="!!sendCaptchaError"
            />
          </el-form-item>
          <el-form-item label="邮箱验证码" prop="code">
            <div class="code-row">
              <el-input
                v-model="registerForm.code"
                placeholder="6 位数字"
                maxlength="6"
                :prefix-icon="Key"
                clearable
              />
              <el-button
                class="send-code-btn"
                :disabled="codeCooldown > 0 || sendingCode"
                :loading="sendingCode"
                @click="handleSendCode"
              >
                {{ codeCooldown > 0 ? `${codeCooldown}s 后重发` : '发送验证码' }}
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="8-64 位"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="再次输入密码"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>
          <el-button
            type="primary"
            class="submit-btn"
            :loading="registerLoading"
            @click="handleRegister"
          >
            创建账号
          </el-button>

          <div class="auth-foot">
            <span>已有账号？</span>
            <el-link type="primary" :underline="false" @click="switchToLogin">
              去登录
            </el-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Message as Message, Lock, Key, CircleCheckFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import CaptchaInput from '@/components/CaptchaInput.vue'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref<'login' | 'register'>('login')

// ── 登录 ─────────────────────────────────────────────────
const loginFormRef = ref<FormInstance>()
const loginCaptchaRef = ref<InstanceType<typeof CaptchaInput> | null>(null)
const loginForm = reactive({
  email: '',
  password: '',
  captcha: { captcha_id: '', captcha_code: '' },
  // 镜像字段:el-form 的 prop 走顶层路径,这里保持同步
  captcha_code: '',
})
watch(
  () => loginForm.captcha.captcha_code,
  (v) => {
    loginForm.captcha_code = v
  },
)
const loginRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度 8-64 位', trigger: 'blur' },
  ],
  captcha_code: [
    {
      validator(_rule, value, cb) {
        if (!value || !value.trim()) {
          cb(new Error('请输入图形验证码'))
        } else {
          cb()
        }
      },
      trigger: 'blur',
    },
  ],
}
const loginLoading = ref(false)
const loginCaptchaError = ref(false)

async function handleLogin() {
  if (!loginFormRef.value) return
  try {
    await loginFormRef.value.validate()
  } catch {
    return
  }
  if (!loginForm.captcha.captcha_id || !loginForm.captcha.captcha_code) {
    ElMessage.warning('请先完成图形验证码')
    return
  }
  loginLoading.value = true
  loginCaptchaError.value = false
  try {
    await authStore.login({
      email: loginForm.email,
      password: loginForm.password,
      captcha_id: loginForm.captcha.captcha_id,
      captcha_code: loginForm.captcha.captcha_code,
    })
    ElMessage.success('登录成功')
    const redirect = (router.currentRoute.value.query.redirect as string) || '/home/index'
    router.push(redirect)
  } catch (e: any) {
    // 登录失败(密码错 / 验证码错 / 账号禁用):后端会回 400,刷新图形验证码
    loginCaptchaError.value = true
    loginCaptchaRef.value?.refresh()
    console.warn('login failed', e)
  } finally {
    loginLoading.value = false
  }
}

// ── 注册 ─────────────────────────────────────────────────
const registerFormRef = ref<FormInstance>()
const sendCaptchaRef = ref<InstanceType<typeof CaptchaInput> | null>(null)
const registerForm = reactive({
  email: '',
  code: '',
  password: '',
  confirmPassword: '',
  sendCaptcha: { captcha_id: '', captcha_code: '' },
  // 镜像字段:el-form prop 走顶层,这里保持同步
  send_captcha_code: '',
})
watch(
  () => registerForm.sendCaptcha.captcha_code,
  (v) => {
    registerForm.send_captcha_code = v
  },
)
const registerRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  send_captcha_code: [
    {
      validator(_rule, value, cb) {
        if (!value || !value.trim()) {
          cb(new Error('请输入图形验证码'))
        } else {
          cb()
        }
      },
      trigger: 'blur',
    },
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度 8-64 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator(_rule, value, cb) {
        if (value !== registerForm.password) {
          cb(new Error('两次输入的密码不一致'))
        } else {
          cb()
        }
      },
      trigger: 'blur',
    },
  ],
}
const registerLoading = ref(false)
const sendCaptchaError = ref(false)

const sendingCode = ref(false)
const codeCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

function startCooldown(seconds: number) {
  codeCooldown.value = seconds
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    codeCooldown.value -= 1
    if (codeCooldown.value <= 0) {
      codeCooldown.value = 0
      if (cooldownTimer) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }
  }, 1000)
}

async function handleSendCode() {
  if (!registerForm.email) {
    ElMessage.warning('请先填写邮箱')
    return
  }
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerForm.email)
  if (!emailOk) {
    ElMessage.warning('邮箱格式不正确')
    return
  }
  if (!registerForm.sendCaptcha.captcha_id || !registerForm.sendCaptcha.captcha_code) {
    ElMessage.warning('请先完成图形验证码')
    sendCaptchaRef.value?.refresh()
    return
  }
  sendingCode.value = true
  sendCaptchaError.value = false
  try {
    await authStore.sendVerificationCode({
      email: registerForm.email,
      purpose: 'register',
      captcha_id: registerForm.sendCaptcha.captcha_id,
      captcha_code: registerForm.sendCaptcha.captcha_code,
    })
    ElMessage.success('验证码已发送,请查收邮箱')
    startCooldown(60)
  } catch (e: any) {
    // 图形验证码错 / 限流 / 邮箱占用:刷新图形验证码
    sendCaptchaError.value = true
    sendCaptchaRef.value?.refresh()
    console.warn('send code failed', e)
  } finally {
    sendingCode.value = false
  }
}

async function handleRegister() {
  if (!registerFormRef.value) return
  try {
    await registerFormRef.value.validate()
  } catch {
    return
  }
  registerLoading.value = true
  try {
    await authStore.register({
      email: registerForm.email,
      code: registerForm.code,
      password: registerForm.password,
    })
    ElMessage.success('注册成功,请登录')
    const registeredEmail = registerForm.email
    registerForm.email = ''
    registerForm.code = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    activeTab.value = 'login'
    loginForm.email = registeredEmail
    await nextTick()
    loginCaptchaRef.value?.refresh()
  } catch (e) {
    console.warn('register failed', e)
  } finally {
    registerLoading.value = false
  }
}

// ── 切 tab 时刷新对应验证码 ───────────────────────────────
async function switchToRegister() {
  activeTab.value = 'register'
  await nextTick()
  sendCaptchaRef.value?.refresh()
}
async function switchToLogin() {
  activeTab.value = 'login'
  await nextTick()
  loginCaptchaRef.value?.refresh()
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(at 20% 30%, rgba(37, 99, 235, 0.18), transparent 60%),
    radial-gradient(at 80% 70%, rgba(99, 102, 241, 0.18), transparent 60%),
    linear-gradient(135deg, #0f172a, #1e293b 60%, #312e81);
}

.auth-card {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  width: min(960px, 100%);
  min-height: 540px;
  background: var(--color-admin-surface);
  border-radius: 16px;
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.4);
  overflow: hidden;
}

@media (max-width: 720px) {
  .auth-card {
    grid-template-columns: 1fr;
  }
  .auth-brand {
    display: none !important;
  }
}

/* ── 左侧品牌 ─────────────────────────────────── */
.auth-brand {
  position: relative;
  padding: 48px 32px;
  color: #f8fafc;
  background:
    radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.45), transparent 50%),
    radial-gradient(at 100% 100%, rgba(99, 102, 241, 0.4), transparent 50%),
    linear-gradient(135deg, #1e3a8a, #312e81);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}

.brand-title {
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.brand-subtitle {
  font-size: 0.95rem;
  color: rgba(248, 250, 252, 0.78);
  margin-bottom: 24px;
  line-height: 1.6;
}

.brand-features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.brand-features li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: rgba(248, 250, 252, 0.88);
}

.brand-features li :deep(.el-icon) {
  color: #93c5fd;
  font-size: 1.1rem;
}

/* ── 右侧表单 ─────────────────────────────────── */
.auth-form {
  padding: 40px 36px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.auth-tabs {
  margin-bottom: 16px;
}

.auth-tabs :deep(.el-tabs__item) {
  font-size: 1rem;
  font-weight: 600;
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
}

.code-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.code-row .el-input {
  flex: 1;
}
.send-code-btn {
  flex-shrink: 0;
  white-space: nowrap;
  min-width: 110px;
}

.auth-foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
  font-size: 0.875rem;
  color: var(--color-admin-muted);
}

.hint {
  margin-top: 18px;
}

.hint :deep(.el-alert__title) {
  font-weight: 600;
}
</style>