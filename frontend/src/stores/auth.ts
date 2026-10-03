/**
 * Auth Pinia store
 *
 * 暴露:
 * - accessToken / refreshToken / userInfo (state)
 * - isLoggedIn / isAdmin / hasRole / hasPermission (getter)
 * - login(email, password)
 * - register(payload)
 * - logout()
 * - fetchMe()
 * - refreshTokens()
 * - clear()
 *
 * 双 token 持久化在 localStorage;userInfo 每次刷新通过 /auth/me 重新拉取
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import http, { unwrap, clearAuthTokens } from '@/common/utils/http'
import { generateCaptcha, type CaptchaImage } from '@/views/auth/api'

const TOKEN_KEYS = {
  access: 'access_token',
  refresh: 'refresh_token',
} as const

// ═══════════════════════════════════════════════════════════════
//  Types
// ═══════════════════════════════════════════════════════════════

export interface RoleBrief {
  id: number
  code: string
  name: string
}

export interface UserInfo {
  id: number
  email: string
  nickname: string | null
  avatar_url: string | null
  is_active: boolean
  is_verified: boolean
  roles: RoleBrief[]
  role_codes: string[]
  permissions: string[]
  created_at: string | null
  last_login_at: string | null
}

export interface LoginPayload {
  email: string
  password: string
  captcha_id: string
  captcha_code: string
}

export interface RegisterPayload {
  email: string
  password: string
  nickname?: string
  code: string
}

export interface SendCodePayload {
  email: string
  purpose?: 'register' | 'reset_password'
  captcha_id: string
  captcha_code: string
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user_info: UserInfo
}

// ═══════════════════════════════════════════════════════════════
//  Store
// ═══════════════════════════════════════════════════════════════

export const useAuthStore = defineStore('auth', () => {
  // ── State ─────────────────────────────────────────────────
  const accessToken = ref<string | null>(localStorage.getItem(TOKEN_KEYS.access))
  const refreshToken = ref<string | null>(localStorage.getItem(TOKEN_KEYS.refresh))
  const userInfo = ref<UserInfo | null>(null)
  const initializing = ref(false)

  // ── Getters ───────────────────────────────────────────────
  const isLoggedIn = computed(() => Boolean(accessToken.value))
  const roles = computed(() => userInfo.value?.roles ?? [])
  const roleCodes = computed(() => userInfo.value?.role_codes ?? [])
  const permissions = computed(() => userInfo.value?.permissions ?? [])
  const isAdmin = computed(() => roleCodes.value.includes('admin'))

  function hasRole(code: string): boolean {
    return roleCodes.value.includes(code)
  }

  function hasPermission(code: string): boolean {
    return permissions.value.includes(code)
  }

  // ── Actions ───────────────────────────────────────────────

  function persistTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem(TOKEN_KEYS.access, access)
    localStorage.setItem(TOKEN_KEYS.refresh, refresh)
  }

  async function login(payload: LoginPayload) {
    const data = await http
      .post<{ code: number; message: string; data: LoginResponse }>('/auth/login', payload)
      .then(unwrap)
    persistTokens(data.access_token, data.refresh_token)
    userInfo.value = data.user_info
  }

  async function register(payload: RegisterPayload) {
    await http.post('/auth/register', payload).then(unwrap)
  }

  async function sendVerificationCode(payload: SendCodePayload) {
    return http
      .post<
        { code: number; message: string; data: { expire_seconds: number; purpose: string } }
      >('/auth/send-verification-code', payload)
      .then(unwrap)
  }

  async function logout() {
    try {
      if (accessToken.value) {
        await http.post('/auth/logout').then(unwrap).catch(() => undefined)
      }
    } finally {
      clear()
    }
  }

  async function fetchMe() {
    const data = await http
      .get<{ code: number; message: string; data: UserInfo }>('/auth/me')
      .then(unwrap)
    userInfo.value = data
  }

  async function refreshTokens(): Promise<boolean> {
    if (!refreshToken.value) return false
    try {
      const res = await http
        .post<
          {
            code: number
            message: string
            data: { access_token: string; refresh_token: string; expires_in: number }
          }
        >('/auth/refresh', { refresh_token: refreshToken.value })
        .then(unwrap)
      persistTokens(res.access_token, res.refresh_token)
      return true
    } catch {
      clear()
      return false
    }
  }

  function clear() {
    accessToken.value = null
    refreshToken.value = null
    userInfo.value = null
    clearAuthTokens()
  }

  /** 应用启动时调用:有 token 但无 userInfo 时拉一次 */
  async function bootstrap() {
    if (!accessToken.value) return
    if (userInfo.value) return
    initializing.value = true
    try {
      await fetchMe()
    } catch {
      clear()
    } finally {
      initializing.value = false
    }
  }

  return {
    // state
    accessToken,
    refreshToken,
    userInfo,
    initializing,
    // getters
    isLoggedIn,
    roles,
    roleCodes,
    permissions,
    isAdmin,
    // actions
    hasRole,
    hasPermission,
    login,
    register,
    sendVerificationCode,
    logout,
    fetchMe,
    refreshTokens,
    clear,
    bootstrap,
  }
})