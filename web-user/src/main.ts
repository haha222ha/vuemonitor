import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";
import router from "./router";
import { useI18n } from "./i18n";
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
app.config.errorHandler = (err) => {
  console.error("[Vue Error]", err);
};
app.mount("#app");
