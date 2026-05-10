import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import axios from "axios";
import App from "./App.vue";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const BASE_PATH = import.meta.env.BASE_URL || "/admin/";

const routes = [
  { path: "/", redirect: `${BASE_PATH}dashboard` },
  { path: `${BASE_PATH}login`, component: () => import("./views/LoginView.vue") },
  {
    path: BASE_PATH.slice(0, -1) || "/",
    component: () => import("./layouts/AdminLayout.vue"),
    children: [
      { path: "dashboard", component: () => import("./views/DashboardView.vue") },
      { path: "users", component: () => import("./views/UsersView.vue") },
      { path: "licenses", component: () => import("./views/LicensesView.vue") },
      { path: "collect", component: () => import("./views/CollectView.vue") },
      { path: "proxies", component: () => import("./views/ProxiesView.vue") },
      { path: "risk-events", component: () => import("./views/RiskEventsView.vue") },
      { path: "audit-logs", component: () => import("./views/AuditLogsView.vue") },
    ],
  },
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

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(ElementPlus);
app.config.errorHandler = (err) => {
  console.error("[Vue Error]", err);
};
app.mount("#app");
