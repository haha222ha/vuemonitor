import { createRouter, createWebHistory } from "vue-router"
import { ElMessage } from "element-plus"
import { canAccessRoute } from "@/utils/plan"

const routes = [
  { path: "/", redirect: "/dashboard" },
  { path: "/login", component: () => import("../views/LoginView.vue") },
  { path: "/activate", component: () => import("../views/ActivateView.vue") },
  {
    path: "/",
    component: () => import("../layouts/IntelLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "dashboard", component: () => import("../views/DashboardView.vue") },
      { path: "trends", component: () => import("../views/TrendsView.vue") },
      { path: "opportunities", component: () => import("../views/OpportunitiesView.vue") },
      { path: "risks", component: () => import("../views/RisksView.vue") },
      { path: "reports", component: () => import("../views/ReportsView.vue") },
      { path: "topics", component: () => import("../views/TopicsView.vue") },
      { path: "signals", component: () => import("../views/SignalsView.vue") },
      { path: "emotions", component: () => import("../views/EmotionsView.vue") },
      { path: "report/:topicId", component: () => import("../views/ReportView.vue") },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/dashboard" },
]

const router = createRouter({ history: createWebHistory(), routes })

function decodeJWTPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1]
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"))
    return JSON.parse(json)
  } catch {
    return null
  }
}

function isTokenValid(token: string): boolean {
  const payload = decodeJWTPayload(token)
  if (!payload || !payload.exp) return false
  return (payload.exp as number) * 1000 > Date.now()
}

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("intel_token")

  if (to.path === "/login") {
    if (token && isTokenValid(token)) {
      next("/dashboard")
      return
    }
    next()
    return
  }

  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!token || !isTokenValid(token)) {
      localStorage.removeItem("intel_token")
      localStorage.removeItem("intel_refresh_token")
      localStorage.removeItem("intel_username")
      next({ path: "/login", query: { redirect: to.fullPath } })
      return
    }
    try {
      const raw = localStorage.getItem("intel_membership")
      const m = raw ? JSON.parse(raw) as { plan?: string } : null
      const plan = m?.plan || "free"
      const pathKey = "/" + (to.path.split("/").filter(Boolean)[0] || "dashboard")
      if (!canAccessRoute(plan, pathKey)) {
        ElMessage.warning("当前套餐无权访问该模块，请升级会员")
        next("/dashboard")
        return
      }
    } catch {
      /* ignore */
    }
  }

  next()
})

export default router