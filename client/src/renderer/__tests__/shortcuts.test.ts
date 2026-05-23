import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("electron", () => ({
  ipcRenderer: { on: vi.fn(), send: vi.fn(), invoke: vi.fn() },
}));

const DEFAULT_SHORTCUTS = [
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

interface ShortcutBinding {
  key: string;
  action: string;
  label: string;
  enabled: boolean;
}

class TestShortcutManager {
  private shortcuts: ShortcutBinding[];
  private handlers: Map<string, (action: string) => void> = new Map();

  constructor(stored?: ShortcutBinding[]) {
    if (stored) {
      const savedMap = new Map(stored.map((s) => [s.action, s]));
      this.shortcuts = DEFAULT_SHORTCUTS.map((d) => savedMap.get(d.action) || { ...d });
    } else {
      this.shortcuts = DEFAULT_SHORTCUTS.map((s) => ({ ...s }));
    }
  }

  getShortcuts(): ShortcutBinding[] {
    return this.shortcuts;
  }

  registerHandler(action: string, handler: (action: string) => void): void {
    this.handlers.set(action, handler);
  }

  updateShortcut(action: string, newKey: string): void {
    const idx = this.shortcuts.findIndex((s) => s.action === action);
    if (idx !== -1) this.shortcuts[idx].key = newKey;
  }

  toggleShortcut(action: string, enabled: boolean): void {
    const idx = this.shortcuts.findIndex((s) => s.action === action);
    if (idx !== -1) this.shortcuts[idx].enabled = enabled;
  }

  reset(): ShortcutBinding[] {
    this.shortcuts = DEFAULT_SHORTCUTS.map((s) => ({ ...s }));
    return this.shortcuts;
  }

  simulateKeyCombo(combo: string): void {
    for (const shortcut of this.shortcuts) {
      if (shortcut.enabled && shortcut.key === combo) {
        const handler = this.handlers.get(shortcut.action);
        if (handler) handler(shortcut.action);
        break;
      }
    }
  }
}

describe("ShortcutManager", () => {
  let manager: TestShortcutManager;

  beforeEach(() => {
    manager = new TestShortcutManager();
  });

  describe("getShortcuts", () => {
    it("returns default shortcuts when no saved data", () => {
      const shortcuts = manager.getShortcuts();
      expect(shortcuts).toHaveLength(DEFAULT_SHORTCUTS.length);
      expect(shortcuts[0].action).toBe("search");
      expect(shortcuts[0].key).toBe("Ctrl+K");
    });

    it("merges saved shortcuts with defaults", () => {
      const saved = [{ ...DEFAULT_SHORTCUTS[0], key: "Ctrl+Shift+K" }];
      const freshManager = new TestShortcutManager(saved);
      const shortcuts = freshManager.getShortcuts();
      expect(shortcuts[0].key).toBe("Ctrl+Shift+K");
      expect(shortcuts).toHaveLength(DEFAULT_SHORTCUTS.length);
    });

    it("preserves defaults for actions not in saved data", () => {
      const saved = [{ ...DEFAULT_SHORTCUTS[0], key: "Ctrl+Shift+K" }];
      const freshManager = new TestShortcutManager(saved);
      const shortcuts = freshManager.getShortcuts();
      expect(shortcuts[1].key).toBe("Ctrl+N");
    });
  });

  describe("updateShortcut", () => {
    it("updates key binding for an action", () => {
      manager.updateShortcut("search", "Ctrl+Shift+F");
      const shortcuts = manager.getShortcuts();
      const search = shortcuts.find((s) => s.action === "search");
      expect(search?.key).toBe("Ctrl+Shift+F");
    });

    it("does nothing for unknown action", () => {
      manager.updateShortcut("nonexistent", "Ctrl+X");
      const shortcuts = manager.getShortcuts();
      expect(shortcuts.find((s) => s.action === "nonexistent")).toBeUndefined();
    });
  });

  describe("toggleShortcut", () => {
    it("disables a shortcut", () => {
      manager.toggleShortcut("search", false);
      const shortcuts = manager.getShortcuts();
      const search = shortcuts.find((s) => s.action === "search");
      expect(search?.enabled).toBe(false);
    });

    it("enables a previously disabled shortcut", () => {
      manager.toggleShortcut("search", false);
      manager.toggleShortcut("search", true);
      const shortcuts = manager.getShortcuts();
      const search = shortcuts.find((s) => s.action === "search");
      expect(search?.enabled).toBe(true);
    });
  });

  describe("reset", () => {
    it("restores default shortcuts", () => {
      manager.updateShortcut("search", "Ctrl+Shift+F");
      manager.toggleShortcut("export", false);
      const result = manager.reset();
      expect(result[0].key).toBe("Ctrl+K");
      expect(result.find((s) => s.action === "export")?.enabled).toBe(true);
    });
  });

  describe("registerHandler + simulateKeyCombo", () => {
    it("calls handler on matching key combo", () => {
      const handler = vi.fn();
      manager.registerHandler("search", handler);
      manager.simulateKeyCombo("Ctrl+K");
      expect(handler).toHaveBeenCalledWith("search");
    });

    it("does not call handler for disabled shortcut", () => {
      const handler = vi.fn();
      manager.toggleShortcut("search", false);
      manager.registerHandler("search", handler);
      manager.simulateKeyCombo("Ctrl+K");
      expect(handler).not.toHaveBeenCalled();
    });

    it("does not call handler for non-matching combo", () => {
      const handler = vi.fn();
      manager.registerHandler("search", handler);
      manager.simulateKeyCombo("Ctrl+L");
      expect(handler).not.toHaveBeenCalled();
    });
  });
});
