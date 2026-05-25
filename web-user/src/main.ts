import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import { ElNotification } from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";
import router from "./router";
import { useI18n } from "./i18n";
import { initWebVitals } from "./utils/webVitals";
import { watch } from "vue";

const i18n = useI18n();
document.documentElement.setAttribute("lang", i18n.getLocale());

watch(() => i18n.getLocale(), (newLocale) => {
  document.documentElement.setAttribute("lang", newLocale);
});

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(ElementPlus);
app.config.errorHandler = (err, _instance, info) => {
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

app.mount("#app");
initWebVitals();
