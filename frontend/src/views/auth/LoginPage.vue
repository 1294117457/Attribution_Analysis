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
          <el-tab-pane label="忘记密码" name="forgot" />
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
            <el-link type="primary" :underline="false" @click="activeTab = 'forgot'">
              忘记密码？
            </el-link>
            <span class="auth-foot-sep">·</span>
            <span>还没有账号？</span>
            <el-link type="primary" :underline="false" @click="switchToRegister">
              立即注册
            </el-link>
          </div>
        </el-form>

        <!-- 注册 -->
        <el-form
          v-if="activeTab === 'register'"
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

        <!-- 忘记密码(三 tab 平铺,与登录/注册并列;两步流程用 el-steps 表达) -->
        <el-form
          v-if="activeTab === 'forgot'"
          ref="forgotFormRef"
          :model="forgotForm"
          :rules="forgotRules"
          size="large"
          label-position="top"
          @submit.prevent
        >
          <el-steps
            :active="forgotStep"
            finish-status="success"
            simple
            class="forgot-steps"
          >
            <el-step title="验证邮箱" />
            <el-step title="设置新密码" />
          </el-steps>

          <!-- Step 1: 邮箱 + 图形验证码 + 发送 -->
          <template v-if="forgotStep === 1">
            <el-alert
              class="forgot-tip"
              type="info"
              show-icon
              :closable="false"
              description="请输入注册时使用的邮箱，我们会向该邮箱发送 6 位验证码。"
            />
            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="forgotForm.email"
                placeholder="请输入注册邮箱"
                :prefix-icon="Message"
                clearable
              />
            </el-form-item>
            <el-form-item label="图形验证码">
              <CaptchaInput
                ref="forgotCaptchaRef"
                v-model="forgotForm.captcha"
              />
            </el-form-item>
            <el-button
              type="primary"
              class="submit-btn"
              :loading="forgotSending"
              @click="handleForgotSendCode"
            >
              发送验证码
            </el-button>
          </template>

          <!-- Step 2: 邮箱验证码 + 新密码 -->
          <template v-else>
            <el-alert
              class="forgot-tip"
              type="success"
              show-icon
              :closable="false"
              :title="`验证码已发送至 ${forgotForm.email}`"
            />
            <el-form-item label="邮箱验证码" prop="code">
              <div class="code-row">
                <el-input
                  v-model="forgotForm.code"
                  placeholder="6 位数字"
                  maxlength="6"
                  :prefix-icon="Key"
                  clearable
                />
                <el-button
                  class="send-code-btn"
                  :disabled="forgotCodeCooldown > 0 || forgotSending"
                  :loading="forgotSending"
                  @click="handleResendForgotCode"
                >
                  {{ forgotCodeCooldown > 0 ? `${forgotCodeCooldown}s 后重发` : '重新发送' }}
                </el-button>
              </div>
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="forgotForm.new_password"
                type="password"
                placeholder="8-64 位"
                :prefix-icon="Lock"
                show-password
                clearable
              />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirm_password">
              <el-input
                v-model="forgotForm.confirm_password"
                type="password"
                placeholder="再次输入新密码"
                :prefix-icon="Lock"
                show-password
                clearable
              />
            </el-form-item>
            <div class="forgot-actions">
              <el-button @click="forgotStep = 1">上一步</el-button>
              <el-button
                type="primary"
                :loading="forgotSubmitting"
                @click="handleForgotReset"
              >
                重置密码
              </el-button>
            </div>
          </template>

          <div class="auth-foot">
            <span>想起密码了？</span>
            <el-link type="primary" :underline="false" @click="switchToLogin">
              去登录
            </el-link>
            <span class="auth-foot-sep">·</span>
            <span>还没有账号？</span>
            <el-link type="primary" :underline="false" @click="switchToRegister">
              立即注册
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
import {
  forgotPasswordReset as apiForgotReset,
  forgotPasswordSendCode as apiForgotSendCode,
} from '@/views/auth/api'
import CaptchaInput from '@/components/CaptchaInput.vue'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref<'login' | 'register' | 'forgot'>('login')

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

/**
 * 登录失败的错误细分:
 * - 后端 code=CAPTCHA_INVALID / CAPTCHA_REQUIRED   → 图形验证码错:前端高亮 + 后端 message
 * - 后端 code=USER_INACTIVE                       → 账号禁用:明确文案
 * - 其它(账号不存在/密码错等)                       → 统一文案"登录失败,请检查账号密码是否正确",防账号枚举
 */
function resolveLoginError(e: any): { msg: string; highlightCaptcha: boolean } {
  const backendMsg = e?.response?.data?.message as string | undefined
  const backendCode = e?.response?.data?.code as string | undefined
  const status = e?.response?.status

  if (backendCode === 'CAPTCHA_INVALID' || backendCode === 'CAPTCHA_REQUIRED') {
    return { msg: backendMsg || '图形验证码错误', highlightCaptcha: true }
  }
  if (backendCode === 'USER_INACTIVE' || status === 403) {
    return { msg: '账号已被禁用,请联系管理员', highlightCaptcha: false }
  }
  // 其它:账号不存在 / 密码错 / 网络错 — 统一文案(不区分防枚举)
  return {
    msg: backendMsg || '登录失败,请检查账号密码是否正确',
    highlightCaptcha: false,
  }
}

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
    const { msg, highlightCaptcha } = resolveLoginError(e)
    ElMessage.error(msg)
    // 图形验证码错:刷新 + 高亮;其它失败也刷新(防重放)
    loginCaptchaError.value = highlightCaptcha
    loginCaptchaRef.value?.refresh()
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
    // 方案A:统一友好提示
    const backendMsg = e?.response?.data?.message as string | undefined
    const msg = backendMsg || '验证码发送失败，请重试'
    ElMessage.error(msg)
    // 图形验证码错 / 限流 / 邮箱占用:刷新图形验证码
    sendCaptchaError.value = true
    sendCaptchaRef.value?.refresh()
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
  } catch (e: any) {
    // 方案A:统一友好提示
    const backendMsg = e?.response?.data?.message as string | undefined
    const msg = backendMsg || '注册失败，请重试'
    ElMessage.error(msg)
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

// 监听 activeTab 切到 forgot:预填邮箱 + 刷新图形验证码
watch(activeTab, async (newTab) => {
  if (newTab === 'forgot') {
    await switchToForgot()
  }
})

// ═════════════════════════════════════════════════════════════
//  忘记密码(第三个 tab,两步流程)
// ═════════════════════════════════════════════════════════════

const forgotStep = ref<1 | 2>(1)

// tab 内独立的表单实例(避免和登录/注册表单冲突)
const forgotFormRef = ref<FormInstance>()
const forgotCaptchaRef = ref<InstanceType<typeof CaptchaInput> | null>(null)
const forgotSending = ref(false)
const forgotSubmitting = ref(false)
const forgotCodeCooldown = ref(0)
let forgotCooldownTimer: ReturnType<typeof setInterval> | null = null

const forgotForm = reactive({
  email: '',
  code: '',
  new_password: '',
  confirm_password: '',
  captcha: { captcha_id: '', captcha_code: '' },
})
const forgotRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入邮箱验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度 8-64 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator(_r, v, cb) {
        if (v !== forgotForm.new_password) cb(new Error('两次输入的新密码不一致'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

function startForgotCooldown(seconds: number) {
  forgotCodeCooldown.value = seconds
  if (forgotCooldownTimer) clearInterval(forgotCooldownTimer)
  forgotCooldownTimer = setInterval(() => {
    forgotCodeCooldown.value -= 1
    if (forgotCodeCooldown.value <= 0) {
      forgotCodeCooldown.value = 0
      if (forgotCooldownTimer) {
        clearInterval(forgotCooldownTimer)
        forgotCooldownTimer = null
      }
    }
  }, 1000)
}

/**
 * 找回密码 step1 失败的错误细分:
 * - 图形验证码错 (CAPTCHA_INVALID)            → 高亮图形验证码 + 后端 message
 * - 账号不存在 (ACCOUNT_NOT_FOUND)            → "请检查账号是否正确"(用户明确感知)
 * - 限流 (EMAIL_CODE_RATE_LIMITED)            → 用后端 message
 * - 其它                                       → 兜底
 */
function resolveForgotSendError(e: any): { msg: string; highlightCaptcha: boolean } {
  const backendMsg = e?.response?.data?.message as string | undefined
  const backendCode = e?.response?.data?.code as string | undefined
  if (backendCode === 'CAPTCHA_INVALID' || backendCode === 'CAPTCHA_REQUIRED') {
    return { msg: backendMsg || '图形验证码错误', highlightCaptcha: true }
  }
  if (backendCode === 'ACCOUNT_NOT_FOUND') {
    return { msg: '账号不存在，请检查账号是否正确', highlightCaptcha: false }
  }
  if (backendCode === 'EMAIL_CODE_RATE_LIMITED' && backendMsg) {
    return { msg: backendMsg, highlightCaptcha: false }
  }
  return { msg: backendMsg || '验证码发送失败，请重试', highlightCaptcha: false }
}

async function handleForgotSendCode() {
  if (!forgotForm.email) {
    ElMessage.warning('请先填写邮箱')
    return
  }
  const emailOk = /[^\s@]+@[^\s@]+\.[^\s@]+$/.test(forgotForm.email)
  if (!emailOk) {
    ElMessage.warning('邮箱格式不正确')
    return
  }
  if (!forgotForm.captcha.captcha_id || !forgotForm.captcha.captcha_code) {
    ElMessage.warning('请先完成图形验证码')
    await nextTick()
    forgotCaptchaRef.value?.refresh()
    return
  }
  forgotSending.value = true
  try {
    await apiForgotSendCode({
      email: forgotForm.email,
      captcha_id: forgotForm.captcha.captcha_id,
      captcha_code: forgotForm.captcha.captcha_code,
    })
    ElMessage.success('验证码已发送，请查收邮箱')
    startForgotCooldown(60)
    forgotStep.value = 2
  } catch (e: any) {
    const { msg } = resolveForgotSendError(e)
    ElMessage.error(msg)
    await nextTick()
    forgotCaptchaRef.value?.refresh()
  } finally {
    forgotSending.value = false
  }
}

/** 在 step2 中重新发送验证码(强制刷一张新图形验证码) */
async function handleResendForgotCode() {
  if (forgotCodeCooldown.value > 0) return
  if (!forgotForm.email) {
    ElMessage.warning('请先填写邮箱')
    return
  }
  // 强制刷一张新图形验证码
  await nextTick()
  forgotCaptchaRef.value?.refresh()
  // 等验证码加载完成
  await new Promise((r) => setTimeout(r, 400))
  if (!forgotForm.captcha.captcha_id) {
    ElMessage.warning('图形验证码加载失败，请稍后再试')
    return
  }
  forgotSending.value = true
  try {
    await apiForgotSendCode({
      email: forgotForm.email,
      captcha_id: forgotForm.captcha.captcha_id,
      captcha_code: forgotForm.captcha.captcha_code,
    })
    ElMessage.success('验证码已重新发送，请查收邮箱')
    startForgotCooldown(60)
  } catch (e: any) {
    const { msg } = resolveForgotSendError(e)
    ElMessage.error(msg)
    await nextTick()
    forgotCaptchaRef.value?.refresh()
  } finally {
    forgotSending.value = false
  }
}

/**
 * 找回密码 step2 失败的错误细分:
 * - 邮箱验证码错/过期 → 直接展示后端 message
 * - 账号不存在 (ACCOUNT_NOT_FOUND) → "请检查账号是否正确"
 * - 其它 → 兜底
 */
function resolveForgotResetError(e: any): string {
  const backendMsg = e?.response?.data?.message as string | undefined
  const backendCode = e?.response?.data?.code as string | undefined
  if (backendCode === 'ACCOUNT_NOT_FOUND') {
    return '账号不存在，请检查账号是否正确'
  }
  return backendMsg || '密码重置失败，请重试'
}

async function handleForgotReset() {
  if (!forgotFormRef.value) return
  try {
    await forgotFormRef.value.validate()
  } catch {
    return
  }
  forgotSubmitting.value = true
  try {
    await apiForgotReset({
      email: forgotForm.email,
      code: forgotForm.code,
      new_password: forgotForm.new_password,
    })
    ElMessage.success('密码已重置，请使用新密码登录')
    // 把邮箱填到登录表单 + 跳回登录 tab
    loginForm.email = forgotForm.email
    activeTab.value = 'login'
    await nextTick()
    loginCaptchaRef.value?.refresh()
  } catch (e: any) {
    ElMessage.error(resolveForgotResetError(e))
  } finally {
    forgotSubmitting.value = false
  }
}

/** 切到 forgot tab 时:预填邮箱、刷新图形验证码、重置 step */
async function switchToForgot() {
  if (!forgotForm.email) {
    forgotForm.email = loginForm.email || ''
  }
  forgotStep.value = 1
  forgotForm.code = ''
  forgotForm.new_password = ''
  forgotForm.confirm_password = ''
  await nextTick()
  forgotCaptchaRef.value?.refresh()
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

.auth-foot-sep {
  color: var(--color-admin-muted);
  margin: 0 2px;
  opacity: 0.5;
}

.forgot-steps {
  margin-bottom: 16px;
}

.forgot-tip {
  margin-bottom: 16px;
}

.forgot-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
</style>