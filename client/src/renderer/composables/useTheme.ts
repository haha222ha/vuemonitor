import { ref, watch, onMounted } from "vue";

export type ThemeMode = "light" | "dark" | "system";

const STORAGE_KEY = "xhs365_theme";

const mode = ref<ThemeMode>("system");
const isDark = ref(false);

function getSystemPreference(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyTheme(dark: boolean) {
  isDark.value = dark;
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
}

function resolveTheme() {
  if (mode.value === "system") {
    applyTheme(getSystemPreference());
  } else {
    applyTheme(mode.value === "dark");
  }
}

let mediaQuery: MediaQueryList | null = null;

function handleMediaChange(e: MediaQueryListEvent) {
  if (mode.value === "system") {
    applyTheme(e.matches);
  }
}

export function useTheme() {
  function setMode(newMode: ThemeMode) {
    mode.value = newMode;
    localStorage.setItem(STORAGE_KEY, newMode);
    resolveTheme();
  }

  function toggle() {
    if (mode.value === "light") setMode("dark");
    else if (mode.value === "dark") setMode("system");
    else setMode("light");
  }

  onMounted(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
    if (saved && ["light", "dark", "system"].includes(saved)) {
      mode.value = saved;
    }
    resolveTheme();

    if (!mediaQuery) {
      mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      mediaQuery.addEventListener("change", handleMediaChange);
    }
  });

  watch(mode, resolveTheme);

  return { mode, isDark, setMode, toggle };
}
