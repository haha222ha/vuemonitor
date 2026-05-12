import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";
import { useI18n } from "./i18n";
import { useAuthStore } from "./stores/auth";

// Set up i18n and set initial language
const { locale, setLocale } = useI18n();
// Ensure the html lang attribute is set for initial load
document.documentElement.setAttribute("lang", locale.value);

// Watch for locale changes to update html lang attribute
locale.value; // Trigger the watcher? Actually, we can't watch because it's a ref from reactive.
// Instead, we'll set it in setLocale? But we cannot modify the i18n index.ts.
// We'll do a workaround: set it initially and then rely on the user changing locale via the UI calling setLocale.
// For now, we set it once and hope the UI calls setLocale when changing language.
// Alternatively, we can create a watcher in main.ts if we have access to the locale ref.
// Since we have the locale ref, we can watch it.
import { watch } from "vue";
watch(locale, (newLocale) => {
  document.documentElement.setAttribute("lang", newLocale);
});

const routes = [
  { path: "/", name: "Landing", component: () => import("./views/LandingView.vue") },
  { path: "/pricing", name: "Pricing", component: () => import("./views/PricingView.vue") },
  { path: "/download", name: "Download", component: () => import("./views/DownloadView.vue") },
  { path: "/login", name: "Login", component: () => import("./views/LoginView.vue") },
  { path: "/register", name: "Register", component: () => import("./views/RegisterView.vue") },
  {
    path: "/dashboard",
    component: () => import("./layouts/DashboardLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "", name: "Dashboard", component: () => import("./views/dashboard/DashboardHome.vue") },
      { path: "monitor", name: "MonitorList", component: () => import("./views/dashboard/MonitorList.vue") },
      { path: "collect", name: "CollectCenter", component: () => import("./views/dashboard/CollectCenter.vue") },
      { path: "ai", name: "AIAnalysis", component: () => import("./views/dashboard/AIAnalysis.vue") },
      { path: "team", name: "Team", component: () => import("./views/dashboard/TeamView.vue") },
      { path: "notifications", name: "Notifications", component: () => import("./views/dashboard/NotificationsView.vue") },
      { path: "product/:id", name: "ProductDetail", component: () => import("./views/dashboard/ProductDetailView.vue") },
      { path: "settings", name: "Settings", component: () => import("./views/dashboard/SettingsView.vue") },
    ],
  },
  // 404 catch-all route
  { path: "/:pathMatch(.*)*", name: "NotFound", component: () => import("./views/NotFoundView.vue") },
];

const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) });

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();
  const token = localStorage.getItem("access_token");

  // If user is logged in and tries to visit login/register, redirect to dashboard
  if (auth.isLoggedIn && (to.name === "Login" || to.name === "Register")) {
    next({ name: "Dashboard" });
    return;
  }

  // If token exists but user is not initialized (e.g., page refresh), try to init from storage
  if (token && !auth.isLoggedIn) {
    auth.initFromStorage();
  }

  // Auth guard for routes requiring authentication
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next({ name: "Login", query: { redirect: to.fullPath } });
    return;
  }

  // Set document title based on route name and i18n
  const { t } = useI18n();
  const routeName = to.name as string;
  // Try to get title from i18n using route name as key, fallback to route name
  const pageTitle = t(`route.${routeName}`) || routeName;
  document.title = pageTitle + " - VueMonitor";

  next();
});

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(ElementPlus);
app.config.errorHandler = (err) => {
  console.error("[Vue Error]", err);
};
app.mount("#app");