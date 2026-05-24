import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios"
import { ElMessage } from "element-plus"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1"

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

let isRefreshing = false
let pendingRequests: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processPendingRequests(token: string | null, error: unknown = null) {
  pendingRequests.forEach(({ resolve, reject }) => {
    if (token) {
      resolve(token)
    } else {
      reject(error)
    }
  })
  pendingRequests = []
}

async function refreshToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("intel_refresh_token")
  if (!refreshToken) return null

  try {
    const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    })
    const newAccessToken = data?.access_token || data?.data?.access_token
    const newRefreshToken = data?.refresh_token || data?.data?.refresh_token

    if (newAccessToken) {
      localStorage.setItem("intel_token", newAccessToken)
      if (newRefreshToken) {
        localStorage.setItem("intel_refresh_token", newRefreshToken)
      }
      return newAccessToken
    }
    return null
  } catch {
    return null
  }
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("intel_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    if (response.data && typeof response.data === "object" && "data" in response.data && "code" in response.data) {
      response.data = response.data.data
    }
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: number; _auth_retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._auth_retry) {
      const detail = (error.response?.data as { detail?: string })?.detail
      if (detail === "账号已在其他设备登录，请重新授权") {
        clearAuthAndRedirect("账号已在其他设备登录")
        return Promise.reject(error)
      }

      if (originalRequest.url?.includes("/auth/")) {
        clearAuthAndRedirect()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingRequests.push({
            resolve: (newToken: string) => {
              originalRequest.headers.Authorization = `Bearer ${newToken}`
              resolve(api(originalRequest))
            },
            reject,
          })
        })
      }

      originalRequest._auth_retry = true
      isRefreshing = true

      try {
        const newToken = await refreshToken()
        if (newToken) {
          processPendingRequests(newToken)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return api(originalRequest)
        } else {
          processPendingRequests(null, error)
          clearAuthAndRedirect()
          return Promise.reject(error)
        }
      } catch (refreshError) {
        processPendingRequests(null, refreshError)
        clearAuthAndRedirect()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    const retryCount = originalRequest._retry || 0

    if (!error.response && retryCount < 2 && !originalRequest.url?.includes("/auth/")) {
      originalRequest._retry = retryCount + 1
      await new Promise((resolve) => setTimeout(resolve, 1000 * Math.pow(2, retryCount)))
      return api(originalRequest)
    }

    if (error.response?.status === 403) {
      const detail = (error.response?.data as { detail?: string })?.detail
      ElMessage.error(detail || "无访问权限，请检查会员状态")
    } else if (error.response?.status === 429) {
      ElMessage.warning("请求过于频繁，请稍后再试")
    } else if ((error.response?.data as { message?: string })?.message && error.response?.status !== 401) {
      ElMessage.error((error.response!.data as { message: string }).message)
    } else if (!error.response) {
      ElMessage.error("网络连接异常，请检查网络后重试")
    }

    return Promise.reject(error)
  }
)

function clearAuthAndRedirect(reason?: string) {
  localStorage.removeItem("intel_token")
  localStorage.removeItem("intel_refresh_token")
  localStorage.removeItem("intel_auth_code")
  localStorage.removeItem("intel_username")
  localStorage.removeItem("intel_membership")
  if (!window.location.pathname.endsWith("/login")) {
    const params = new URLSearchParams()
    if (reason) params.set("reason", reason)
    const query = params.toString()
    window.location.href = `/login${query ? `?${query}` : ""}`
  }
}

export default api
export { API_BASE_URL }