import { defineStore } from "pinia"
import { ref, computed } from "vue"
import api from "@/utils/api"

export interface IntelMembership {
  plan: string
  started_at: string
  expires_at: string
  status: string
  days_remaining: number
}

export const useIntelAuthStore = defineStore("intelAuth", () => {
  const membership = ref<IntelMembership | null>(null)
  const loading = ref(false)
  const error = ref("")

  const isLoggedIn = computed(() => !!localStorage.getItem("intel_token"))
  const hasMembership = computed(() => membership.value?.status === "active" && (membership.value?.days_remaining ?? 0) > 0)
  const planName = computed(() => membership.value?.plan || "免费版")
  const planLabel = computed(() => {
    const map: Record<string, string> = { free: "免费版", pro: "专业版", enterprise: "企业版" }
    return map[membership.value?.plan || ""] || membership.value?.plan || "未知"
  })
  const daysRemaining = computed(() => membership.value?.days_remaining ?? 0)

  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true
    error.value = ""
    try {
      const { data } = await api.post("/auth/login", { username, password })
      const token = data?.access_token || data?.token
      const refreshToken = data?.refresh_token
      if (token) {
        localStorage.setItem("intel_token", token)
        localStorage.setItem("intel_username", username)
        if (refreshToken) localStorage.setItem("intel_refresh_token", refreshToken)
        await fetchMembership()
        return true
      }
      return false
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "登录失败"
      error.value = msg
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchMembership(): Promise<void> {
    try {
      const { data } = await api.get("/intel/auth/me")
      membership.value = data
    } catch {
      membership.value = null
    }
  }

  async function activateCode(code: string): Promise<boolean> {
    loading.value = true
    error.value = ""
    try {
      const { data } = await api.post("/intel/auth/activate", { code: code.trim().toUpperCase() })
      membership.value = data
      return true
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "激活失败"
      error.value = msg
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    localStorage.removeItem("intel_token")
    localStorage.removeItem("intel_refresh_token")
    localStorage.removeItem("intel_username")
    membership.value = null
  }

  return {
    membership,
    loading,
    error,
    isLoggedIn,
    hasMembership,
    planName,
    planLabel,
    daysRemaining,
    login,
    fetchMembership,
    activateCode,
    logout,
  }
})