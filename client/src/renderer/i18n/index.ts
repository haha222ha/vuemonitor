import { reactive } from "vue";
import { zh } from "./zh";
import { en } from "./en";
import type { LocaleMessages } from "./zh";

export type Locale = "zh" | "en";

const messages: Record<Locale, LocaleMessages> = { zh, en };

const state = reactive({
  locale: (localStorage.getItem("locale") || "zh") as Locale,
});

function t(key: string): string {
  const keys = key.split(".");
  let result: unknown = messages[state.locale];
  for (const k of keys) {
    if (result && typeof result === "object" && k in result) {
      result = (result as Record<string, unknown>)[k];
    } else {
      result = key;
      break;
    }
  }
  return typeof result === "string" ? result : key;
}

function setLocale(locale: Locale) {
  state.locale = locale;
  localStorage.setItem("locale", locale);
  document.documentElement.setAttribute("lang", locale);
}

function getLocale(): Locale {
  return state.locale;
}

export function useI18n() {
  return { t, setLocale, getLocale, locale: state };
}
