import { defineStore } from "pinia"
import { ref, computed } from "vue"
import api from "@/utils/api"
import { planLabel as getPlanLabel, PLAN_TAG_TYPE, upgradeTarget } from "@/utils/plan"

export interface IntelMembership {
  plan: string
  started_at: string
  expires_at: string
  status: string
  days_remaining: number
}

const MEMBERSHIP_KEY = "intel_membership"

function loadMembershipFromStorage(): IntelMembership | null {
  try {
    const raw = localStorage.getItem(MEMBERSHIP_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return null
}

function saveMembershipToStorage(m: IntelMembership | null) {
  if (m) {
    localStorage.setItem(MEMBERSHIP_KEY, JSON.stringify(m))
  } else {
    localStorage.removeItem(MEMBERSHIP_KEY)
  }
}

export const useIntelAuthStore = defineStore("intelAuth", () => {
  const membership = ref<IntelMembership | null>(loadMembershipFromStorage())
  const loading = ref(false)
  const error = ref("")

  const isLoggedIn = computed(() => !!localStorage.getItem("intel_token"))
  const hasMembership = computed(() => membership.value?.status === "active" && (membership.value?.days_remaining ?? 0) > 0)
  const planName = computed(() => membership.value?.plan || "free")
  const planLabel = computed(() => getPlanLabel(membership.value?.plan || "free"))
  const planTagType = computed(() => PLAN_TAG_TYPE[membership.value?.plan || "free"] || "info")
  const needsUpgrade = computed(() => upgradeTarget(planName.value) !== null)
  const daysRemaining = computed(() => membership.value?.days_remaining ?? 0)
  const expiresAt = computed(() => membership.value?.expires_at || "")

  async function codeLogin(code: string): Promise<boolean> {
    loading.value = true
    error.value = ""
    try {
      const { data } = await api.post("/intel/auth/code-login", { code: code.trim().toUpperCase() })
      const token = data?.access_token
      const refreshToken = data?.refresh_token
      const m = data?.membership as IntelMembership | undefined
      if (token) {
        localStorage.setItem("intel_token", token)
        localStorage.setItem("intel_auth_code", code.trim().toUpperCase())
        if (refreshToken) localStorage.setItem("intel_refresh_token", refreshToken)
        if (m) {
          membership.value = m
          saveMembershipToStorage(m)
        } else {
          await fetchMembership()
        }
        return true
      }
      return false
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "授权码登录失败"
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
      saveMembershipToStorage(data)
    } catch {
      membership.value = null
      saveMembershipToStorage(null)
    }
  }

  async function activateCode(code: string): Promise<boolean> {
    loading.value = true
    error.value = ""
    try {
      const { data } = await api.post("/intel/auth/activate", { code: code.trim().toUpperCase() })
      membership.value = data
      saveMembershipToStorage(data)
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
    localStorage.removeItem("intel_auth_code")
    localStorage.removeItem("intel_username")
    saveMembershipToStorage(null)
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
    planTagType,
    needsUpgrade,
    daysRemaining,
    expiresAt,
    codeLogin,
    fetchMembership,
    activateCode,
    logout,
  }
})
