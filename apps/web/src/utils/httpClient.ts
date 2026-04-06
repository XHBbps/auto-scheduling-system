import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { clearAuthSession } from './authSession'

export interface RequestConfig extends AxiosRequestConfig {
  silentError?: boolean
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const PROTECTED_API_PREFIXES = [
  '/api/admin',
  '/api/dashboard',
  '/api/data',
  '/api/exports',
  '/api/issues',
  '/api/part-schedules',
  '/api/schedules',
  '/admin',
  '/dashboard',
  '/data',
  '/exports',
  '/issues',
  '/part-schedules',
  '/schedules',
] as const

const isAbsoluteUrl = (value: string) => /^https?:\/\//i.test(value)

const normalizeRequestUrl = (baseURL: string, requestUrl: string) => {
  if (!requestUrl || isAbsoluteUrl(requestUrl) || !baseURL || isAbsoluteUrl(baseURL)) {
    return requestUrl
  }

  const normalizedBasePath = baseURL.startsWith('/') ? baseURL : `/${baseURL}`
  if (requestUrl === normalizedBasePath) {
    return '/'
  }
  if (requestUrl.startsWith(`${normalizedBasePath}/`)) {
    return requestUrl.slice(normalizedBasePath.length) || '/'
  }
  return requestUrl
}

const matchesProtectedPrefix = (requestUrl: string, prefix: string) =>
  requestUrl === prefix || requestUrl.startsWith(`${prefix}/`)

const request: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true,
})

const isSilentErrorRequest = (config?: AxiosRequestConfig) =>
  Boolean((config as RequestConfig | undefined)?.silentError)

const isProtectedApiRequest = (config?: AxiosRequestConfig) => {
  const requestUrl = normalizeRequestUrl(
    typeof config?.baseURL === 'string' ? config.baseURL : API_BASE_URL,
    config?.url || '',
  )
  return PROTECTED_API_PREFIXES.some((prefix) => matchesProtectedPrefix(requestUrl, prefix))
}

request.interceptors.request.use((config) => {
  config.url = normalizeRequestUrl(
    typeof config.baseURL === 'string' ? config.baseURL : API_BASE_URL,
    config.url || '',
  )
  config.withCredentials = true
  return config
})

const MAX_RETRIES = 2
const RETRY_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504])
const RETRY_BACKOFF_MS = 1000

request.interceptors.response.use(undefined, async (error) => {
  if (axios.isCancel(error)) return Promise.reject(error)
  const config = error.config as RequestConfig & { _retryCount?: number }
  if (!config) return Promise.reject(error)

  const status = error.response?.status
  const isRetryable = !status || RETRY_STATUS_CODES.has(status)
  config._retryCount = config._retryCount ?? 0

  if (isRetryable && config._retryCount < MAX_RETRIES) {
    config._retryCount += 1
    const delay = RETRY_BACKOFF_MS * Math.pow(2, config._retryCount - 1)
    await new Promise((resolve) => setTimeout(resolve, delay))
    return request(config)
  }

  return Promise.reject(error)
})

request.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response
    }
    const { code, message, data } = response.data
    if (code !== 0) {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message || '请求失败'))
    }
    return data
  },
  (error) => {
    if (axios.isCancel(error)) return Promise.reject(error)
    const response = error?.response
    const message = response?.data?.message || response?.data?.detail || error?.message || '网络请求失败'
    const normalizedError = new Error(message) as Error & { status?: number }
    normalizedError.status = response?.status

    if ((response?.status === 401 || response?.status === 403) && isProtectedApiRequest(error?.config)) {
      clearAuthSession()
      if (!isSilentErrorRequest(error?.config)) {
        ElMessage.error(response?.status === 403 ? '当前账号无权访问该页面' : '登录状态已失效，请重新登录')
      }
      return Promise.reject(normalizedError)
    }

    if (!isSilentErrorRequest(error?.config)) {
      ElMessage.error(message)
    }
    return Promise.reject(normalizedError)
  },
)

const http = {
  get: <T = any>(url: string, config?: RequestConfig) => request.get(url, config) as Promise<T>,
  post: <T = any>(url: string, data?: any, config?: RequestConfig) => request.post(url, data, config) as Promise<T>,
  put: <T = any>(url: string, data?: any, config?: RequestConfig) => request.put(url, data, config) as Promise<T>,
  patch: <T = any>(url: string, data?: any, config?: RequestConfig) => request.patch(url, data, config) as Promise<T>,
  delete: <T = any>(url: string, config?: RequestConfig) => request.delete(url, config) as Promise<T>,
}

export default http
