import { createRouter, createWebHistory } from "vue-router";
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const BASE_PATH = import.meta.env.BASE_URL || "/";

const routes = [
  { path: "/", redirect: `${BASE_PATH}dashboard` },
  { path: `${BASE_PATH}login`, component: () => import("../views/LoginView.vue") },
  {
    path: BASE_PATH.slice(0, -1) || "/",
    component: () => import("../layouts/AdminLayout.vue"),
    children: [
      { path: "dashboard", component: () => import("../views/DashboardView.vue") },
      { path: "users", component: () => import("../views/UsersView.vue") },
      { path: "licenses", component: () => import("../views/LicensesView.vue") },
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

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem("admin_token");
  const loginPath = `${BASE_PATH}login`;

  if (to.path === loginPath) {
    next();
    return;
  }

  if (!token) {
    next(loginPath);
    return;
  }

  try {
    await axios.get(`${API_BASE_URL}/admin/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    next();
  } catch {
    localStorage.removeItem("admin_token");
    next(`${BASE_PATH}login`.replace("//", "/"));
  }
});

export default router;
export { BASE_PATH, API_BASE_URL };
