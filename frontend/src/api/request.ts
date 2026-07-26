import axios, { type AxiosInstance, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '@/types'

// ============================================
// Axios 实例配置
// ============================================

const service: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token 存储键名
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

// 是否正在刷新 Token
let isRefreshing = false
// 等待 Token 刷新的请求队列
let requestsQueue: Array<(token: string) => void> = []

/** 登录和令牌刷新必须保持匿名，避免失效旧令牌阻断重新登录。 */
export function isPublicAuthRequest(url?: string): boolean {
  const path = (url || '').split('?')[0].replace(/\/+$/, '')
  return path.endsWith('/auth/login') || path.endsWith('/auth/refresh')
}

/** 获取 Access Token */
export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

/** 获取 Refresh Token */
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

/** 设置 Token */
export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access)
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
}

/** 清除 Token */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

/** 清理失效会话并进入独立登录页。 */
function redirectToLogin(): void {
  clearTokens()
  if (window.location.pathname !== '/login') {
    const redirect = `${window.location.pathname}${window.location.search}`
    window.location.href = `/login?redirect=${encodeURIComponent(redirect)}`
  }
}

/** 刷新 Token */
export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return null
  }
  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_BASE_URL}/auth/refresh/`,
      { refresh: refreshToken }
    )
    const { access } = response.data
    localStorage.setItem(ACCESS_TOKEN_KEY, access)
    return access
  } catch {
    return null
  }
}

// ============================================
// 请求拦截器
// ============================================

service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 注入 Bearer Token
    const token = getAccessToken()
    if (token && config.headers && !isPublicAuthRequest(config.url)) {
      config.headers.Authorization = `Bearer ${token}`
    } else if (config.headers && isPublicAuthRequest(config.url)) {
      delete config.headers.Authorization
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// ============================================
// 响应拦截器
// ============================================

export function isApiResponse(payload: unknown): payload is ApiResponse {
  if (typeof payload !== 'object' || payload === null) return false

  const candidate = payload as Record<string, unknown>
  return (
    typeof candidate.code === 'number' &&
    typeof candidate.message === 'string' &&
    Object.prototype.hasOwnProperty.call(candidate, 'data')
  )
}

export function unwrapResponseData<T>(payload: ApiResponse<T> | T): T {
  return isApiResponse(payload) ? payload.data : payload
}

service.interceptors.response.use(
  async (response) => {
    const payload: unknown = response.data

    // 处理 Blob 类型响应（文件下载）
    if (response.config.responseType === 'blob') {
      return response.data
    }

    // 统一响应格式处理：code !== 0 表示业务错误
    if (isApiResponse(payload) && payload.code !== 0) {
      ElMessage.error(payload.message || '请求失败')
      // 401 未授权
      if (payload.code === 401) {
        redirectToLogin()
      }
      return Promise.reject(new Error(payload.message || 'Error'))
    }

    // 自定义接口使用统一响应信封，DRF 默认 retrieve 则直接返回业务对象。
    return unwrapResponseData(payload) as any
  },
  async (error) => {
    const { response, config } = error

    // 401 错误：尝试刷新 Token
    if (response && response.status === 401) {
      // 登录失败由登录页直接展示；刷新失败才需要清理会话。
      if (isPublicAuthRequest(config.url)) {
        if (config.url && config.url.includes('/auth/refresh')) {
          redirectToLogin()
        }
        return Promise.reject(error)
      }

      // 如果正在刷新 Token，将请求加入队列
      if (isRefreshing) {
        return new Promise((resolve) => {
          requestsQueue.push((token: string) => {
            if (config.headers) {
              config.headers.Authorization = `Bearer ${token}`
            }
            resolve(service(config))
          })
        })
      }

      // 开始刷新 Token
      isRefreshing = true
      const newToken = await refreshAccessToken()
      isRefreshing = false

      if (newToken) {
        // 刷新成功，重新发送队列中的请求
        requestsQueue.forEach((cb) => cb(newToken))
        requestsQueue = []
        // 重新发送当前请求
        if (config.headers) {
          config.headers.Authorization = `Bearer ${newToken}`
        }
        return service(config)
      } else {
        // 刷新失败，跳转登录
        redirectToLogin()
        return Promise.reject(error)
      }
    }

    // 403 权限不足
    if (response && response.status === 403) {
      ElMessage.error('权限不足，无法执行此操作')
      return Promise.reject(error)
    }

    // 500 服务器错误
    if (response && response.status >= 500) {
      ElMessage.error('服务器内部错误，请稍后重试')
      return Promise.reject(error)
    }

    // 其他错误，提取后端错误消息
    const errorMessage = response?.data?.message || response?.data?.detail || error.message || '网络异常'
    ElMessage.error(errorMessage)
    return Promise.reject(error)
  }
)

// ============================================
// 封装请求方法
// ============================================

/** GET 请求 */
export function get<T = unknown>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
  return service.get(url, { params, ...config }) as Promise<T>
}

/** POST 请求 */
export function post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return service.post(url, data, config) as Promise<T>
}

/** PUT 请求 */
export function put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return service.put(url, data, config) as Promise<T>
}

/** PATCH 请求 */
export function patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return service.patch(url, data, config) as Promise<T>
}

/** DELETE 请求 */
export function del<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return service.delete(url, config) as Promise<T>
}

/** 文件上传 */
export function upload<T = unknown>(url: string, formData: FormData, config?: AxiosRequestConfig): Promise<T> {
  return service.post(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...config,
  }) as Promise<T>
}

/** 文件下载 */
export function download(url: string, config?: AxiosRequestConfig): Promise<Blob> {
  return service.get(url, { responseType: 'blob', ...config }) as Promise<unknown> as Promise<Blob>
}

export default service
