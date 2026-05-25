import { createRouter, createWebHistory } from "vue-router";
import { ElMessage } from "element-plus";
import { useAuthStore } from "../stores/auth";
import { useI18n } from "../i18n";

const routes = [
  { path: "/", name: "Landing", component: () => import(/* webpackChunkName: "landing" */ "../views/LandingView.vue") },
  { path: "/pricing", name: "Pricing", component: () => import(/* webpackChunkName: "pricing" */ "../views/PricingView.vue") },
  { path: "/purchase", name: "Purchase", component: () => import(/* webpackChunkName: "purchase" */ "../views/PurchaseGuideView.vue") },
  { path: "/faq", name: "Faq", component: () => import(/* webpackChunkName: "legal" */ "../views/FaqView.vue") },
  { path: "/terms", name: "Terms", component: () => import(/* webpackChunkName: "legal" */ "../views/LegalTermsView.vue") },
  { path: "/privacy", name: "Privacy", component: () => import(/* webpackChunkName: "legal" */ "../views/LegalPrivacyView.vue") },
  { path: "/download", name: "Download", component: () => import(/* webpackChunkName: "download" */ "../views/DownloadView.vue") },
  { path: "/login", name: "Login", component: () => import(/* webpackChunkName: "auth" */ "../views/LoginView.vue") },
  { path: "/register", name: "Register", component: () => import(/* webpackChunkName: "auth" */ "../views/RegisterView.vue") },
  {
    path: "/dashboard",
    component: () => import(/* webpackChunkName: "dashboard-layout" */ "../layouts/DashboardLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "", name: "Dashboard", component: () => import(/* webpackChunkName: "dashboard-home" */ "../views/dashboard/DashboardHome.vue") },
      { path: "monitor", name: "MonitorList", component: () => import(/* webpackChunkName: "monitor" */ "../views/dashboard/MonitorList.vue") },
      { path: "collect", name: "CollectCenter", component: () => import(/* webpackChunkName: "collect" */ "../views/dashboard/CollectCenter.vue") },
      { path: "ai", name: "AIAnalysis", component: () => import(/* webpackChunkName: "ai" */ "../views/dashboard/AIAnalysis.vue") },
      { path: "ai/reports", name: "AIReports", component: () => import(/* webpackChunkName: "ai-reports" */ "../views/dashboard/AIReportView.vue") },
      { path: "aipic", name: "Aipic", component: () => import(/* webpackChunkName: "aipic" */ "../views/dashboard/AipicView.vue") },
      { path: "discovery", name: "Discovery", component: () => import(/* webpackChunkName: "discovery" */ "../views/dashboard/DiscoveryView.vue") },
      { path: "compare", name: "Compare", component: () => import(/* webpackChunkName: "compare" */ "../views/dashboard/CompareView.vue") },
      { path: "team", name: "Team", component: () => import(/* webpackChunkName: "team" */ "../views/dashboard/TeamView.vue") },
      { path: "notifications", name: "Notifications", component: () => import(/* webpackChunkName: "notifications" */ "../views/dashboard/NotificationsView.vue") },
      { path: "product/:id", name: "ProductDetail", component: () => import(/* webpackChunkName: "product-detail" */ "../views/dashboard/ProductDetailView.vue") },
      { path: "settings", name: "Settings", component: () => import(/* webpackChunkName: "settings" */ "../views/dashboard/SettingsView.vue") },
      { path: "admin/monitor", name: "AdminMonitor", component: () => import(/* webpackChunkName: "admin" */ "../views/dashboard/AdminMonitorView.vue"), meta: { requiresAdmin: true } },
    ],
  },
  { path: "/:pathMatch(.*)*", name: "NotFound", component: () => import(/* webpackChunkName: "not-found" */ "../views/NotFoundView.vue") },
];

const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) });

const ADMIN_ROLES = new Set(["admin", "superadmin"]);

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore();
  const token = localStorage.getItem("access_token");

  if (auth.isLoggedIn && (to.name === "Login" || to.name === "Register")) {
    next({ name: "Dashboard" });
    return;
  }

  if (token && !auth.isLoggedIn) {
    auth.initFromStorage();
  }

  if (to.matched.some((record) => record.meta.requiresAuth) && !auth.isLoggedIn) {
    next({ name: "Login", query: { redirect: to.fullPath } });
    return;
  }

  if (to.matched.some((record) => record.meta.requiresAdmin)) {
    const userRole = (auth.user as { role?: string })?.role || "";
    if (!ADMIN_ROLES.has(userRole)) {
      ElMessage.error("无权访问该页面");
      next({ name: "Dashboard" });
      return;
    }
  }

  const { t } = useI18n();
  const routeName = to.name as string;
  const pageTitle = t(`route.${routeName}`) || routeName;
  document.title = pageTitle + " - VueMonitor";

  next();
});

export default router;
