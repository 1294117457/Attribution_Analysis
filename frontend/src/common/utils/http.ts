import axios, { type AxiosInstance, type AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

/** 统一 API 响应包装 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
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
    const msg =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      '网络异常'

    if (status === 401) {
      localStorage.removeItem('access_token')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else if (status === 403) {
      ElMessage.error('没有权限访问')
    } else if (status && status >= 500) {
      ElMessage.error('服务器错误')
    }

    return Promise.reject(new Error(msg))
  }
)

// ── 统一解包 data ────────────────────────────────────────
export function unwrap<T>(res: { data: ApiResponse<T> }): T {
  const d = res.data
  if (d.code >= 400) {
    throw new Error(d.message || '请求失败')
  }
  return d.data
}

export default http
