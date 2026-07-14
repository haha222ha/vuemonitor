import { createRouter, createWebHistory } from "vue-router";
import { ElMessage } from "element-plus";

const BASE_PATH = import.meta.env.BASE_URL || "/";

const routes = [
  { path: "/", redirect: `${BASE_PATH}dashboard` },
  { path: `${BASE_PATH}login`, component: () => import("../views/LoginView.vue") },
  {
    path: BASE_PATH.slice(0, -1) || "/",
    component: () => import("../layouts/AdminLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "dashboard", component: () => import("../views/DashboardView.vue") },
      { path: "users", component: () => import("../views/UsersView.vue") },
      { path: "licenses", component: () => import("../views/LicensesView.vue") },
      { path: "intel-codes", component: () => import("../views/IntelCodesView.vue") },
      { path: "pick-member", component: () => import("../views/PickMemberView.vue") },
      { path: "insight-llm", component: () => import("../views/InsightLlmConfigView.vue") },
      { path: "ab-test", component: () => import("../views/AbTestView.vue") },
      { path: "member-contact", component: () => import("../views/MemberContactView.vue") },
      { path: "member-feedback", component: () => import("../views/MemberFeedbackView.vue") },
      { path: "collect", component: () => import("../views/CollectView.vue") },
      { path: "proxies", component: () => import("../views/ProxiesView.vue") },
      { path: "risk-events", component: () => import("../views/RiskEventsView.vue") },
      { path: "audit-logs", component: () => import("../views/AuditLogsView.vue") },
      { path: "system-monitor", component: () => import("../views/SystemMonitorView.vue") },
      { path: "alert-config", component: () => import("../views/AlertConfigView.vue") },
      { path: "security-audit", component: () => import("../views/SecurityAuditView.vue") },
      { path: "gdpr", component: () => import("../views/GdprView.vue") },
      { path: "benchmarks", component: () => import("../views/BenchmarkView.vue") },
    ],
  },
  { path: `${BASE_PATH}:pathMatch(.*)*`, redirect: `${BASE_PATH}dashboard` },
];

const router = createRouter({ history: createWebHistory(BASE_PATH), routes });

function decodeJWTPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function isTokenValid(token: string): boolean {
  const payload = decodeJWTPayload(token);
  if (!payload || !payload.exp) return false;
  return (payload.exp as number) * 1000 > Date.now();
}

function hasAdminRole(token: string): boolean {
  const payload = decodeJWTPayload(token);
  if (!payload) return false;
  const role = payload.role as string || "";
  return ["admin", "super_admin"].includes(role);
}

const loginPath = `${BASE_PATH}login`.replace(/\/+/g, "/");

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("admin_token");

  if (to.path === loginPath) {
    if (token && isTokenValid(token)) {
      next(`${BASE_PATH}dashboard`.replace(/\/+/g, "/"));
      return;
    }
    next();
    return;
  }

  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!token || !isTokenValid(token)) {
      localStorage.removeItem("admin_token");
      localStorage.removeItem("admin_refresh_token");
      localStorage.removeItem("admin_username");
      next({ path: loginPath, query: { redirect: to.fullPath } });
      return;
    }

    if (!hasAdminRole(token)) {
      ElMessage.error("无管理员权限");
      localStorage.removeItem("admin_token");
      next({ path: loginPath });
      return;
    }
  }

  next();
});

export default router;
export { BASE_PATH };
