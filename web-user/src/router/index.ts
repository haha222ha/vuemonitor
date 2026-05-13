import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useI18n } from "../i18n";

const routes = [
  { path: "/", name: "Landing", component: () => import("../views/LandingView.vue") },
  { path: "/pricing", name: "Pricing", component: () => import("../views/PricingView.vue") },
  { path: "/download", name: "Download", component: () => import("../views/DownloadView.vue") },
  { path: "/login", name: "Login", component: () => import("../views/LoginView.vue") },
  { path: "/register", name: "Register", component: () => import("../views/RegisterView.vue") },
  {
    path: "/dashboard",
    component: () => import("../layouts/DashboardLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "", name: "Dashboard", component: () => import("../views/dashboard/DashboardHome.vue") },
      { path: "monitor", name: "MonitorList", component: () => import("../views/dashboard/MonitorList.vue") },
      { path: "collect", name: "CollectCenter", component: () => import("../views/dashboard/CollectCenter.vue") },
      { path: "ai", name: "AIAnalysis", component: () => import("../views/dashboard/AIAnalysis.vue") },
      { path: "ai/reports", name: "AIReports", component: () => import("../views/dashboard/AIReportView.vue") },
      { path: "team", name: "Team", component: () => import("../views/dashboard/TeamView.vue") },
      { path: "notifications", name: "Notifications", component: () => import("../views/dashboard/NotificationsView.vue") },
      { path: "product/:id", name: "ProductDetail", component: () => import("../views/dashboard/ProductDetailView.vue") },
      { path: "settings", name: "Settings", component: () => import("../views/dashboard/SettingsView.vue") },
      { path: "admin/monitor", name: "AdminMonitor", component: () => import("../views/dashboard/AdminMonitorView.vue"), meta: { requiresAdmin: true } },
    ],
  },
  { path: "/:pathMatch(.*)*", name: "NotFound", component: () => import("../views/NotFoundView.vue") },
];

const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) });

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();
  const token = localStorage.getItem("access_token");

  if (auth.isLoggedIn && (to.name === "Login" || to.name === "Register")) {
    next({ name: "Dashboard" });
    return;
  }

  if (token && !auth.isLoggedIn) {
    auth.initFromStorage();
  }

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next({ name: "Login", query: { redirect: to.fullPath } });
    return;
  }

  const { t } = useI18n();
  const routeName = to.name as string;
  const pageTitle = t(`route.${routeName}`) || routeName;
  document.title = pageTitle + " - VueMonitor";

  next();
});

export default router;
