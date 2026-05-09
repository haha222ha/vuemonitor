import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";

const routes = [
  { path: "/", name: "Landing", component: () => import("./views/LandingView.vue") },
  { path: "/pricing", name: "Pricing", component: () => import("./views/PricingView.vue") },
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
      { path: "settings", name: "Settings", component: () => import("./views/dashboard/SettingsView.vue") },
    ],
  },
];

const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) });

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("access_token");
  if (to.meta.requiresAuth && !token) {
    next({ name: "Login", query: { redirect: to.fullPath } });
    return;
  }
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
