import axios, { type AxiosInstance, type AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

/**
 * 统一 API 响应包装
 *
 * 对应后端设计文档 docs/design/api/03-api-response.md §2.1：
 *   { code: 0, data: ..., msg: 'ok' }
 *
 * code 语义：
 *   - 0      = 业务成功
 *   - 1xxxx  = 客户端错误（HTTP 4xx 同步）
 *   - 2xxxx  = 业务错误（通常 HTTP 200）
 *   - 3xxxx  = 第三方 / 外部错误（HTTP 502）
 *   - 5xxxx  = 服务端内部错误（HTTP 500）
 */
export interface ApiResponse<T = unknown> {
  code: number
  message?: string
  data: T
  msg: string
}

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 60_000,
})

// ── 请求拦截器 ────────────────────────────────────────────
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── 响应拦截器 ────────────────────────────────────────────
http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse>) => {
    const status = error.response?.status
    const data = error.response?.data
    // 业务码（2xxxx/5xxxx 等）走 msg，HTTP 协议错误走 detail
    const msg =
      data?.msg ||
      data?.message ||
      (data as any)?.detail ||
      error.message ||
      '网络异常'

    if (status === 401) {
      localStorage.removeItem('access_token')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else if (status === 403) {
      ElMessage.error('没有权限访问')
    } else if (status && status >= 500) {
      ElMessage.error(msg || '服务器错误')
    }

    return Promise.reject(new Error(msg))
  }
)

// ── 统一解包 data（规范化字段） ────────────────────────────
/**
 * 解包后端 ApiResponse。
 *
 * 兼容两种返回：
 *   - 新版（规范）：{ code, data, msg }
 *   - 旧版（过渡期）：{ code, data, message }
 */
export function unwrap<T>(res: { data: ApiResponse<T> }): T {
  const d = res.data
  if (d.code !== undefined && d.code !== 0) {
    throw new Error(d.msg || d.message || '请求失败')
  }
  return d.data as T
}

export default http
