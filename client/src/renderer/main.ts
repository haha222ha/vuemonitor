import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import { ElNotification } from "element-plus";
import "element-plus/dist/index.css";
import "./styles/global.css";
import App from "./App.vue";
import router from "./router";
import { vPermission } from "./directives/permission";
import { useI18n } from "./i18n";
import { shortcutManager } from "./composables/shortcuts";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);
app.use(ElementPlus);
app.directive("permission", vPermission);

app.config.globalProperties.$t = useI18n().t;
app.config.globalProperties.$i18n = useI18n();

app.config.errorHandler = (err, instance, info) => {
  console.error("[Vue Error]", info, err);
  const message = err instanceof Error ? err.message : String(err);
  if (!message.includes("ResizeObserver") && !message.includes("Non-Error promise rejection")) {
    ElNotification({
      title: "运行时错误",
      message,
      type: "error",
      duration: 5000,
    });
  }
};

window.addEventListener("unhandledrejection", (event) => {
  const err = event.reason;
  console.error("[Unhandled Rejection]", err);
  const message = err instanceof Error ? err.message : String(err);
  if (message.includes("Network Error") || message.includes("ERR_NETWORK")) {
    ElNotification({
      title: "网络错误",
      message: "无法连接到服务器，请检查网络连接",
      type: "warning",
      duration: 4000,
    });
  }
});

shortcutManager.registerHandler("nav-dashboard", () => router.push("/dashboard"));
shortcutManager.registerHandler("nav-products", () => router.push("/products"));
shortcutManager.registerHandler("nav-monitor", () => router.push("/monitor"));
shortcutManager.registerHandler("nav-ai", () => router.push("/ai"));
shortcutManager.registerHandler("nav-settings", () => router.push("/settings"));
shortcutManager.registerHandler("open-settings", () => router.push("/settings"));
shortcutManager.registerHandler("search", () => {
  const event = new CustomEvent("shortcut:search");
  window.dispatchEvent(event);
});
shortcutManager.registerHandler("refresh", () => window.location.reload());
shortcutManager.bind();

app.mount("#app");
