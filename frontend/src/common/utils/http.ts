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

// ── 客户端 ETag 缓存（K线/复权因子/停复牌/曾用名 准静态） ──
//
// 后端返回 ETag 头 → 下次请求带 If-None-Match → 服务端 304 即可省去 body 传输
// 同时客户端用 etagCache 保留上次响应，再次 304 时直接用本地缓存数据，
// 即使断网/服务端过期也能秒级渲染。
//
// 注：304 的 body 是空的，所以「用不用缓存」的决定权必须在 etagGet 手里，
//     不能让 http 拦截器代劳（否则会被伪造成 data:null 而静默渲染空白）。

interface EtagEntry<T> {
  etag: string
  data: T
}
const etagCache = new Map<string, EtagEntry<any>>()

const etagCacheGet = <T>(key: string) => etagCache.get(key) as EtagEntry<T> | undefined
const etagCacheSet = <T>(key: string, entry: EtagEntry<T>) => etagCache.set(key, entry)

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 60_000,
  // 304 视为合法响应（ETag 协商），不能 reject。
  // 否则 axios 默认 validateStatus（仅 2xx）会把 304 丢进 error 分支，
  // 而 304 本身是"内容未变"的正常语义，必须交由调用方用缓存兜底。
  validateStatus: (s) => (s >= 200 && s < 300) || s === 304,
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
  // 304 Not Modified：内容未变，body 为空。
  // 这里【必须原样透出 status】，绝不能伪造成 { code:0, data:null } 的信封——
  // 因为 unwrap() 只按 code>=400 判错，伪造信封会让调用方静默拿到 null 而渲染成空白面板。
  // 真正要用缓存兜底的是 etagGet()，它自己持有 _etagCache 并判断 status===304。
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

/**
 * ETag 协商：服务端 304（内容未变、body 为空）时用本地缓存兜底。
 *
 * 三种情形都能拿到数据，不会出现 null/空白：
 *  1. 304 且本地有缓存          → 返回缓存 data（省带宽的快路径）
 *  2. 304 但本地无缓存（首屏 / 切股票 / 热重载清空 Map）→ 去掉 If-None-Match 重试一次，
 *     强制拿 200 全量 body
 *  3. 200                        → 正常解包，并回填缓存供下次 304 复用
 */
export async function etagGet<T>(url: string, params?: Record<string, any>): Promise<T> {
  const cacheKey = url + JSON.stringify(params ?? {})
  const cached = etagCacheGet<T>(cacheKey)

  const send = (inm?: string) =>
    http.get<ApiResponse<T>>(url, {
      params,
      headers: inm ? { 'If-None-Match': inm } : {},
    })

  let res = await send(cached?.etag)

  if (res.status === 304) {
    if (cached) return cached.data
    // 兜底重试：本地无缓存时必须拿全量 body，否则组件会渲染空白
    res = await send(undefined)
  }

  const data = unwrap<T>(res)
  const etag = (res.headers as any)?.etag as string | undefined
  if (etag) etagCacheSet(cacheKey, { etag, data })
  return data
}

/** 清空 token(登出场景) */
export function clearAuthTokens() {
  localStorage.removeItem(TOKEN_KEYS.access)
  localStorage.removeItem(TOKEN_KEYS.refresh)
}

export default http