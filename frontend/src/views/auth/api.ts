/**
 * Auth API 封装
 *
 * 暴露与后端 /api/v1/auth/* 和 /api/v1/users/* 匹配的 TypeScript 接口与请求方法。
 * 业务逻辑 / token 持久化全部走 stores/auth.ts,本文件只做 HTTP 拼装。
 */
import http, { unwrap } from '@/common/utils/http'

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

export interface CaptchaImage {
  captcha_id: string
  base64: string
}

export interface AuthTokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user_info?: UserInfo
}

export interface RefreshTokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserListResponse {
  items: UserInfo[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Role {
  id: number
  code: string
  name: string
  description: string | null
  is_system: boolean
  sort_order: number
}

export interface Permission {
  id: number
  code: string
  resource: string
  action: string
  name: string
  description: string | null
}

export interface UpdateUserStatusPayload {
  is_active: boolean
}

export interface ResetPasswordPayload {
  new_password: string
}

export interface AssignRolePayload {
  role_id: number
}

// ═══════════════════════════════════════════════════════════════
//  Auth endpoints
// ═══════════════════════════════════════════════════════════════

/** 获取一张图形验证码(后端返回 base64 + captcha_id) */
export const generateCaptcha = () =>
  http
    .get<{ code: number; message: string; data: CaptchaImage }>('/auth/captcha/generate')
    .then(unwrap)

export const register = (payload: RegisterPayload) =>
  http
    .post<{ code: number; message: string; data: UserInfo }>('/auth/register', payload)
    .then(unwrap)

export const sendVerificationCode = (payload: SendCodePayload) =>
  http
    .post<
      {
        code: number
        message: string
        data: { expire_seconds: number; purpose: string }
      }
    >('/auth/send-verification-code', payload)
    .then(unwrap)

export const login = (payload: LoginPayload) =>
  http
    .post<{ code: number; message: string; data: AuthTokenResponse }>('/auth/login', payload)
    .then(unwrap)

export const refresh = (refresh_token: string) =>
  http
    .post<{ code: number; message: string; data: RefreshTokenResponse }>(
      '/auth/refresh',
      { refresh_token },
    )
    .then(unwrap)

export const logout = () =>
  http.post<{ code: number; message: string; data: null }>('/auth/logout').then(unwrap)

export const me = () =>
  http
    .get<{ code: number; message: string; data: UserInfo }>('/auth/me')
    .then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  User management endpoints
// ═══════════════════════════════════════════════════════════════

export const listUsers = (params: {
  page?: number
  page_size?: number
  keyword?: string
  is_active?: boolean
}) =>
  http
    .get<{ code: number; message: string; data: UserListResponse }>('/users/', { params })
    .then(unwrap)

export const updateUserStatus = (userId: number, payload: UpdateUserStatusPayload) =>
  http
    .patch<{ code: number; message: string; data: { id: number; is_active: boolean } }>(
      `/users/${userId}/status`,
      payload,
    )
    .then(unwrap)

export const resetUserPassword = (userId: number, payload: ResetPasswordPayload) =>
  http
    .post<{ code: number; message: string; data: null }>(
      `/users/${userId}/reset-password`,
      payload,
    )
    .then(unwrap)

export const assignRole = (userId: number, payload: AssignRolePayload) =>
  http
    .post<{ code: number; message: string; data: null }>(
      `/users/${userId}/roles`,
      payload,
    )
    .then(unwrap)

export const removeRole = (userId: number, roleId: number) =>
  http
    .delete<{ code: number; message: string; data: null }>(
      `/users/${userId}/roles/${roleId}`,
    )
    .then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  Role / Permission (read-only)
// ═══════════════════════════════════════════════════════════════

export const listRoles = () =>
  http
    .get<{ code: number; message: string; data: Role[] }>('/roles/')
    .then(unwrap)

export const listPermissions = () =>
  http
    .get<{ code: number; message: string; data: Permission[] }>('/permissions/')
    .then(unwrap)