export interface ShortcutBinding {
  action: string;
  key: string;
  label: string;
  enabled: boolean;
}

const DEFAULT_SHORTCUTS: ShortcutBinding[] = [
  { action: "toggle-sidebar", key: "Ctrl+B", label: "切换侧边栏", enabled: true },
  { action: "search", key: "Ctrl+K", label: "全局搜索", enabled: true },
  { action: "refresh", key: "Ctrl+R", label: "刷新数据", enabled: true },
  { action: "new-collect", key: "Ctrl+N", label: "新建采集", enabled: true },
  { action: "go-dashboard", key: "Ctrl+1", label: "跳转仪表盘", enabled: true },
  { action: "go-products", key: "Ctrl+2", label: "跳转商品列表", enabled: true },
  { action: "go-ai", key: "Ctrl+3", label: "跳转AI分析", enabled: true },
  { action: "go-monitor", key: "Ctrl+4", label: "跳转监控规则", enabled: true },
  { action: "go-scheduler", key: "Ctrl+5", label: "跳转采集调度", enabled: true },
  { action: "go-settings", key: "Ctrl+,", label: "跳转设置", enabled: true },
];

class ShortcutManager {
  private shortcuts: ShortcutBinding[];

  constructor() {
    this.shortcuts = this.loadFromStorage() ?? DEFAULT_SHORTCUTS.map((s) => ({ ...s }));
  }

  getShortcuts(): ShortcutBinding[] {
    return this.shortcuts;
  }

  updateShortcut(action: string, newKey: string): void {
    const item = this.shortcuts.find((s) => s.action === action);
    if (item) {
      item.key = newKey;
      this.saveToStorage();
    }
  }

  toggleShortcut(action: string, enabled: boolean): void {
    const item = this.shortcuts.find((s) => s.action === action);
    if (item) {
      item.enabled = enabled;
      this.saveToStorage();
    }
  }

  reset(): ShortcutBinding[] {
    this.shortcuts = DEFAULT_SHORTCUTS.map((s) => ({ ...s }));
    this.saveToStorage();
    return this.shortcuts;
  }

  private loadFromStorage(): ShortcutBinding[] | null {
    try {
      const raw = localStorage.getItem("vuemonitor:shortcuts");
      if (!raw) return null;
      return JSON.parse(raw) as ShortcutBinding[];
    } catch {
      return null;
    }
  }

  private saveToStorage(): void {
    try {
      localStorage.setItem("vuemonitor:shortcuts", JSON.stringify(this.shortcuts));
    } catch {
      // ignore
    }
  }
}

export const shortcutManager = new ShortcutManager();
