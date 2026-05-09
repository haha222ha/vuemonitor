import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const routes = [
  { path: "/", redirect: "/admin/dashboard" },
  { path: "/admin/login", component: () => import("./views/LoginView.vue") },
  {
    path: "/admin",
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

const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem("admin_token");

  if (to.path === "/admin/login") {
    next();
    return;
  }

  if (!token) {
    next("/admin/login");
    return;
  }

  try {
    await axios.get(`${API_BASE_URL}/admin/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    next();
  } catch {
    localStorage.removeItem("admin_token");
    next("/admin/login");
  }
});

const app = createApp({ template: "<router-view />" });
app.use(createPinia());
app.use(router);
app.use(ElementPlus);
app.mount("#app");
