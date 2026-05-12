import { ipcRenderer } from "electron";

const SHORTCUTS_KEY = "keyboard-shortcuts";

interface ShortcutBinding {
  key: string;
  action: string;
  label: string;
  enabled: boolean;
}

const DEFAULT_SHORTCUTS: ShortcutBinding[] = [
  { key: "Ctrl+K", action: "search", label: "全局搜索", enabled: true },
  { key: "Ctrl+N", action: "new-monitor", label: "新建监控", enabled: true },
  { key: "Ctrl+E", action: "export", label: "导出数据", enabled: true },
  { key: "Ctrl+1", action: "nav-dashboard", label: "切换到看板", enabled: true },
  { key: "Ctrl+2", action: "nav-products", label: "切换到商品", enabled: true },
  { key: "Ctrl+3", action: "nav-monitor", label: "切换到监控", enabled: true },
  { key: "Ctrl+4", action: "nav-ai", label: "切换到AI", enabled: true },
  { key: "Ctrl+5", action: "nav-settings", label: "切换到设置", enabled: true },
  { key: "Ctrl+Shift+A", action: "start-collect", label: "开始采集", enabled: true },
  { key: "Ctrl+Shift+S", action: "stop-collect", label: "停止采集", enabled: true },
  { key: "F5", action: "refresh", label: "刷新数据", enabled: true },
  { key: "Ctrl+,", action: "open-settings", label: "打开设置", enabled: true },
];

function loadShortcuts(): ShortcutBinding[] {
  try {
    const saved = localStorage.getItem(SHORTCUTS_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      const savedMap = new Map(parsed.map((s: ShortcutBinding) => [s.action, s]));
      return DEFAULT_SHORTCUTS.map((d) => savedMap.get(d.action) || d);
    }
  } catch {}
  return [...DEFAULT_SHORTCUTS];
}

function saveShortcuts(shortcuts: ShortcutBinding[]): void {
  localStorage.setItem(SHORTCUTS_KEY, JSON.stringify(shortcuts));
}

function resetShortcuts(): ShortcutBinding[] {
  localStorage.removeItem(SHORTCUTS_KEY);
  return [...DEFAULT_SHORTCUTS];
}

type ShortcutHandler = (action: string) => void;

class ShortcutManager {
  private shortcuts: ShortcutBinding[] = loadShortcuts();
  private handlers: Map<string, ShortcutHandler> = new Map();
  private bound = false;

  getShortcuts(): ShortcutBinding[] {
    return this.shortcuts;
  }

  registerHandler(action: string, handler: ShortcutHandler): void {
    this.handlers.set(action, handler);
  }

  updateShortcut(action: string, newKey: string): void {
    const idx = this.shortcuts.findIndex((s) => s.action === action);
    if (idx !== -1) {
      this.shortcuts[idx].key = newKey;
      saveShortcuts(this.shortcuts);
    }
  }

  toggleShortcut(action: string, enabled: boolean): void {
    const idx = this.shortcuts.findIndex((s) => s.action === action);
    if (idx !== -1) {
      this.shortcuts[idx].enabled = enabled;
      saveShortcuts(this.shortcuts);
    }
  }

  reset(): ShortcutBinding[] {
    this.shortcuts = resetShortcuts();
    return this.shortcuts;
  }

  bind(): void {
    if (this.bound) return;
    this.bound = true;
    document.addEventListener("keydown", (e) => {
      const parts: string[] = [];
      if (e.ctrlKey || e.metaKey) parts.push("Ctrl");
      if (e.shiftKey) parts.push("Shift");
      if (e.altKey) parts.push("Alt");

      const key = e.key;
      if (!["Control", "Shift", "Alt", "Meta"].includes(key)) {
        parts.push(key.length === 1 ? key.toUpperCase() : key);
      }

      const combo = parts.join("+");

      for (const shortcut of this.shortcuts) {
        if (shortcut.enabled && shortcut.key === combo) {
          e.preventDefault();
          e.stopPropagation();
          const handler = this.handlers.get(shortcut.action);
          if (handler) {
            handler(shortcut.action);
          }
          break;
        }
      }
    });
  }
}

export const shortcutManager = new ShortcutManager();
export type { ShortcutBinding };
export { DEFAULT_SHORTCUTS };
