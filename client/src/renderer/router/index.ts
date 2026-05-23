import { createRouter, createWebHashHistory } from "vue-router";

const routes = [
  {
    path: "/",
    redirect: "/dashboard",
  },
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/LoginView.vue"),
  },
  {
    path: "/",
    component: () => import("../layouts/MainLayout.vue"),
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("../views/DashboardView.vue"),
      },
      {
        path: "products",
        name: "Products",
        component: () => import("../views/ProductsView.vue"),
      },
      {
        path: "products/:id",
        name: "ProductDetail",
        component: () => import("../views/ProductDetailView.vue"),
      },
      {
        path: "monitor",
        name: "Monitor",
        component: () => import("../views/MonitorView.vue"),
      },
      {
        path: "notifications",
        name: "Notifications",
        component: () => import("../views/NotificationsView.vue"),
      },
      {
        path: "ai",
        name: "AIAnalysis",
        component: () => import("../views/AIView.vue"),
      },
      {
        path: "settings",
        name: "Settings",
        component: () => import("../views/SettingsView.vue"),
      },
      {
        path: "license",
        name: "License",
        component: () => import("../views/LicenseView.vue"),
      },
      {
        path: "compare",
        name: "Compare",
        component: () => import("../views/CompareView.vue"),
      },
      {
        path: "category-insight",
        name: "CategoryInsight",
        component: () => import("../views/CategoryInsightView.vue"),
      },
      {
        path: "discovery",
        name: "Discovery",
        component: () => import("../views/DiscoveryView.vue"),
      },
      {
        path: "hot-insight",
        name: "HotInsight",
        component: () => import("../views/HotInsightView.vue"),
      },
      {
        path: "scheduler",
        name: "Scheduler",
        component: () => import("../views/SchedulerView.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

router.beforeEach(async (to, _from, next) => {
  let token: string | null = null;
  if (window.electronAPI) {
    token = await window.electronAPI.invoke("secure-storage:get", "access_token");
  } else {
    token = localStorage.getItem("access_token");
  }
  if (to.name !== "Login" && !token) {
    next({ name: "Login" });
  } else {
    next();
  }
});

export default router;
