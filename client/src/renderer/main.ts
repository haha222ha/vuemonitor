import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
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
