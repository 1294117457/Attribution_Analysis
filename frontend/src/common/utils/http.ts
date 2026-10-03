import axios, {
  type AxiosInstance,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

/** 统一 API 响应包装 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/** 后端 auth 接口的 data 解包后形状 */
export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

const TOKEN_KEYS = {
  access: 'access_token',
  refresh: 'refresh_token',
} as const

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 60_000,
})

// ── 请求拦截器 ────────────────────────────────────────────
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEYS.access)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ── refresh 单飞:避免 401 风暴时并发请求重复触发刷新 ────────
let refreshing: Promise<string | null> | null = null
let refreshSubscribers: Array<(token: string | null) => void> = []

async function doRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem(TOKEN_KEYS.refresh)
  if (!refreshToken) return null
  try {
    // 直接用裸 axios,不走 http 实例(避免再触发拦截器)
    const res = await axios.post<ApiResponse<AuthTokens>>(
      '/api/v1/auth/refresh',
      { refresh_token: refreshToken },
      { timeout: 15_000 },
    )
    if (res.data.code !== 0 && res.data.code >= 400) {
      return null
    }
    const data = res.data.data
    localStorage.setItem(TOKEN_KEYS.access, data.access_token)
    localStorage.setItem(TOKEN_KEYS.refresh, data.refresh_token)
    return data.access_token
  } catch {
    return null
  }
}

function onRefreshed(token: string | null) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(cb: (token: string | null) => void) {
  refreshSubscribers.push(cb)
}

// ── 响应拦截器 ────────────────────────────────────────────
http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse>) => {
    const status = error.response?.status
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined
    const msg =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      '网络异常'

    // 401 → 尝试用 refresh_token 换新,排除 /auth/login 与 /auth/refresh 自身
    const url = originalRequest?.url || ''
    const isAuthEndpoint =
      url.includes('/auth/login') ||
      url.includes('/auth/register') ||
      url.includes('/auth/refresh')

    if (status === 401 && originalRequest && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true

      // 单飞:把并发 401 的请求挂起,等本次 refresh 完成
      if (!refreshing) {
        refreshing = doRefresh().then((token) => {
          onRefreshed(token)
          refreshing = null
          return token
        })
      }
      const newToken = await new Promise<string | null>((resolve) => {
        addRefreshSubscriber(resolve)
        refreshing!.then((t) => {
          // refreshing 期间被挂起的请求统一 resolve
          // doRefresh 已经 onRefreshed 过了,这里再 resolve 一次也安全(会拿到同样的 t)
          resolve(t)
        })
      })

      if (newToken) {
        originalRequest.headers = originalRequest.headers ?? {}
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return http(originalRequest)
      }

      // refresh 失败 → 清 token + 跳登录
      localStorage.removeItem(TOKEN_KEYS.access)
      localStorage.removeItem(TOKEN_KEYS.refresh)
      ElMessage.error('登录已过期,请重新登录')
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
      return Promise.reject(new Error('登录已过期'))
    }

    if (status === 401) {
      // login / register / refresh 失败时直接弹错,不要再跳 login
      ElMessage.error(msg)
    } else if (status === 403) {
      ElMessage.error('没有权限访问')
    } else if (status && status >= 500) {
      ElMessage.error('服务器错误')
    }

    return Promise.reject(new Error(msg))
  },
)

// ── 统一解包 data ────────────────────────────────────────
export function unwrap<T>(res: { data: ApiResponse<T> }): T {
  const d = res.data
  if (d.code >= 400) {
    throw new Error(d.message || '请求失败')
  }
  return d.data
}

/** 清空 token(登出场景) */
export function clearAuthTokens() {
  localStorage.removeItem(TOKEN_KEYS.access)
  localStorage.removeItem(TOKEN_KEYS.refresh)
}

export default http