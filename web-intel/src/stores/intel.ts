import { defineStore } from "pinia"
import { ref } from "vue"
import api from "@/utils/api"
import { getCached, setCache, clearCache } from "@/utils/intel"

export interface TrendItem {
  id: string
  title: string
  category: string
  platform: string
  opportunity_score: number
  lifecycle: string
  direction: string
  risk_level: string
  user_emotion: string
  actionable_insight?: string
  evidence?: string
}

export interface OpportunityItem {
  id: string
  name: string
  category: string
  verdict_score: number
  verdict?: string
  difficulty: string
  startup_cost: string
  monthly_ceiling: string
  persona_fit: string
  commercial_paths: string[]
}

export interface RiskItem {
  id: string
  name: string
  severity: string
  status: string
  reason: string
  alternative: string
  risk_type: string
}

export interface DashboardSummary {
  plan: string
  summary: {
    active_trends: number
    recommended_opportunities: number
    active_risks: number
  }
  top_trends: TrendItem[]
  top_opportunities: OpportunityItem[]
  top_risks: RiskItem[]
}

export const useIntelStore = defineStore("intel", () => {
  const dashboard = ref<DashboardSummary | null>(null)
  const loading = ref(false)
  const error = ref("")

  async function fetchDashboard(): Promise<void> {
    const cached = getCached<DashboardSummary>("dashboard")
    if (cached) {
      dashboard.value = cached
      return
    }
    loading.value = true
    error.value = ""
    try {
      const { data } = await api.get("/intel/dashboard")
      dashboard.value = data
      setCache("dashboard", data)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "加载失败"
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  function invalidateCache(): void {
    clearCache()
  }

  return { dashboard, loading, error, fetchDashboard, invalidateCache }
})