import { BrowserView, BrowserWindow, session } from "electron";
import * as path from "path";
import { EventEmitter } from "events";
import { buildXHSNoteUrl, parseXHSUrl } from "../../../shared/constants/platforms";

export interface CollectTask {
  id: string;
  targetId: string;
  targetType: "note" | "user" | "search" | "url";
  targetUrl?: string;
}

export interface CollectResult {
  taskId: string;
  targetId: string;
  targetType: string;
  status: "success" | "failed" | "risk_detected";
  data?: Record<string, unknown>;
  error?: string;
  collectedAt: string;
}

const XHS_NOTE_CONFIG = {
  buildUrl: (targetId: string, targetType: string, targetUrl?: string): string => {
    if (targetUrl) {
      const parsed = parseXHSUrl(targetUrl);
      if (parsed.type === "note" && parsed.id && parsed.id !== "short_url") {
        return buildXHSNoteUrl(parsed.id);
      }
      return targetUrl;
    }
    if (targetType === "user") {
      return `https://www.xiaohongshu.com/user/profile/${targetId}`;
    }
    return buildXHSNoteUrl(targetId);
  },
  waitForSelector: ".note-item, .note-container, .content-container, [class*='note'], [class*='feed']",
  timeout: 25000,
  noteExtractScript: `
    (function() {
      const data = { platform: 'xhs' };

      const titleEl = document.querySelector(
        '.title, [class*="title"], h1, [class*="note-content"] [class*="title"]'
      );
      data.product_name = titleEl ? titleEl.textContent.trim().substring(0, 500) : '';

      const authorEl = document.querySelector(
        '.author-wrapper .name, [class*="author"] [class*="name"], .user-nickname, [class*="user-info"] [class*="name"]'
      );
      data.shop_name = authorEl ? authorEl.textContent.trim() : null;

      const likeEl = document.querySelector(
        '.like-wrapper .count, [class*="like"] .count, .engagement-bar .count, [class*="engage"] [class*="like"]'
      );
      data.favorite_count = likeEl ? parseInt(likeEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      const collectEl = document.querySelector(
        '.collect-wrapper .count, [class*="collect"] .count, [class*="engage"] [class*="collect"]'
      );
      data.sales_count = collectEl ? parseInt(collectEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      const commentEl = document.querySelector(
        '.chat-wrapper .count, [class*="comment"] .count, [class*="engage"] [class*="chat"]'
      );
      data.review_count = commentEl ? parseInt(commentEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      const imgEl = document.querySelector(
        '.slide-item img, [class*="image"] img, .carousel-img img, [class*="note-content"] img'
      );
      data.image_url = imgEl ? imgEl.src : null;

      const tagEls = document.querySelectorAll('[class*="tag"] a, .tag, [class*="hash-tag"]');
      data.category = tagEls.length > 0 ? Array.from(tagEls).map(t => t.textContent.trim().replace('#', '')).filter(Boolean).join(',') : null;

      const pathname = window.location.pathname;
      const match = pathname.match(/\\/explore\\/([a-f0-9]+)/) || pathname.match(/\\/discovery\\/item\\/([a-f0-9]+)/);
      data.platform_product_id = match ? match[1] : '';
      data.product_url = window.location.href;

      const dateEl = document.querySelector('[class*="date"], [class*="time"], .bottom-container .date');
      data.publish_date = dateEl ? dateEl.textContent.trim() : null;

      const descEl = document.querySelector('[class*="desc"], [class*="note-content"] span, .content');
      data.description = descEl ? descEl.textContent.trim().substring(0, 1000) : null;

      return data;
    })()
  `,
  userExtractScript: `
    (function() {
      const data = { platform: 'xhs', targetType: 'user' };

      const nameEl = document.querySelector('[class*="user-name"], [class*="nickname"], .user-name');
      data.shop_name = nameEl ? nameEl.textContent.trim() : '';

      const descEl = document.querySelector('[class*="desc"], [class*="bio"], .user-desc');
      data.description = descEl ? descEl.textContent.trim() : null;

      const fansEl = document.querySelector('[class*="fans"] [class*="count"], [class*="follower"]');
      data.fans_count = fansEl ? parseInt(fansEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      const noteCountEl = document.querySelector('[class*="note-count"], [class*="notes"]');
      data.note_count = noteCountEl ? parseInt(noteCountEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      const pathname = window.location.pathname;
      const match = pathname.match(/\\/user\\/profile\\/([a-f0-9]+)/);
      data.platform_product_id = match ? match[1] : '';
      data.product_url = window.location.href;
      data.product_name = data.shop_name + '的主页';

      return data;
    })()
  `,
};

const RISK_KEYWORDS = [
  "验证码", "captcha", "verify", "安全验证", "登录", "login",
  "频繁", "rate limit", "429", "封禁", "blocked", "forbidden", "403",
  "操作过于频繁", "请稍后再试", "异常", "risk"
];

export class ChromiumCollectWorker extends EventEmitter {
  private views: Map<string, BrowserView> = new Map();
  private mainWindow: BrowserWindow | null = null;
  private maxConcurrency: number = 3;
  private activeCount: number = 0;
  private taskQueue: CollectTask[] = [];
  private isRunning: boolean = false;
  private collectSession: Electron.Session | null = null;
  private requestCount: number = 0;
  private lastRequestTime: number = 0;

  constructor() {
    super();
  }

  setMainWindow(window: BrowserWindow): void {
    this.mainWindow = window;
  }

  setConcurrency(max: number): void {
    this.maxConcurrency = Math.max(1, Math.min(10, max));
    this.processQueue();
  }

  getConcurrency(): number {
    return this.maxConcurrency;
  }

  getActiveCount(): number {
    return this.activeCount;
  }

  getQueueLength(): number {
    return this.taskQueue.length;
  }

  async init(): Promise<void> {
    this.collectSession = session.fromPartition("persist:xhs-collect", { cache: true });
    await this.collectSession.clearStorageData({
      storages: ["cookies", "localstorage", "cache"],
    });
    this.collectSession.setUserAgent(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    );
    this.collectSession.webRequest.onBeforeSendHeaders((details, callback) => {
      details.requestHeaders["Referer"] = "https://www.xiaohongshu.com/";
      details.requestHeaders["Origin"] = "https://www.xiaohongshu.com";
      callback({ requestHeaders: details.requestHeaders });
    });
  }

  enqueue(task: CollectTask): void {
    this.taskQueue.push(task);
    this.emit("task:queued", { taskId: task.id, queueLength: this.taskQueue.length });
    this.processQueue();
  }

  enqueueBatch(tasks: CollectTask[]): void {
    for (const task of tasks) {
      this.taskQueue.push(task);
    }
    this.emit("task:batch_queued", { count: tasks.length, queueLength: this.taskQueue.length });
    this.processQueue();
  }

  cancelTask(taskId: string): boolean {
    const idx = this.taskQueue.findIndex((t) => t.id === taskId);
    if (idx !== -1) {
      this.taskQueue.splice(idx, 1);
      this.emit("task:cancelled", { taskId });
      return true;
    }
    return false;
  }

  clearQueue(): number {
    const count = this.taskQueue.length;
    this.taskQueue = [];
    return count;
  }

  private async rateLimitGuard(): Promise<void> {
    const now = Date.now();
    const minInterval = 2000;
    const elapsed = now - this.lastRequestTime;
    if (elapsed < minInterval) {
      await this.delay(minInterval - elapsed);
    }
    this.lastRequestTime = Date.now();
    this.requestCount++;
  }

  private processQueue(): void {
    while (this.activeCount < this.maxConcurrency && this.taskQueue.length > 0) {
      const task = this.taskQueue.shift()!;
      this.executeTask(task);
    }
  }

  private async executeTask(task: CollectTask): Promise<void> {
    this.activeCount++;
    this.isRunning = true;
    this.emit("task:start", { taskId: task.id, targetType: task.targetType, activeCount: this.activeCount });

    const url = XHS_NOTE_CONFIG.buildUrl(task.targetId, task.targetType, task.targetUrl);
    const extractScript = task.targetType === "user"
      ? XHS_NOTE_CONFIG.userExtractScript
      : XHS_NOTE_CONFIG.noteExtractScript;

    const view = new BrowserView({
      webPreferences: {
        session: this.collectSession || undefined,
        nodeIntegration: false,
        contextIsolation: true,
        javascript: true,
        plugins: false,
        webSecurity: true,
      },
    });

    this.views.set(task.id, view);

    try {
      await this.rateLimitGuard();
      await this.loadAndExtract(view, task, url, extractScript);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      this.emit("task:failed", { taskId: task.id, error: errorMessage });
    } finally {
      this.destroyView(task.id);
      this.finishTask();
    }
  }

  private loadAndExtract(
    view: BrowserView,
    task: CollectTask,
    url: string,
    extractScript: string
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`采集超时: ${task.targetType}/${task.targetId}`));
      }, XHS_NOTE_CONFIG.timeout);

      let settled = false;

      const settle = (fn: () => void) => {
        if (settled) return;
        settled = true;
        clearTimeout(timeout);
        fn();
      };

      view.webContents.on("did-finish-load", async () => {
        try {
          await this.delay(2000);

          const riskDetected = await this.checkRisk(view);
          if (riskDetected) {
            settle(() => {
              const result: CollectResult = {
                taskId: task.id,
                targetId: task.targetId,
                targetType: task.targetType,
                status: "risk_detected",
                error: riskDetected,
                collectedAt: new Date().toISOString(),
              };
              this.emit("task:risk", result);
              this.emit("task:result", result);
              resolve();
            });
            return;
          }

          if (XHS_NOTE_CONFIG.waitForSelector) {
            await this.waitForSelector(view, XHS_NOTE_CONFIG.waitForSelector, 10000);
          }

          await this.delay(1500);

          const extracted = await view.webContents.executeJavaScript(extractScript);

          const result: CollectResult = {
            taskId: task.id,
            targetId: task.targetId,
            targetType: task.targetType,
            status: "success",
            data: extracted || {},
            collectedAt: new Date().toISOString(),
          };

          settle(() => {
            this.emit("task:success", result);
            this.emit("task:result", result);
            resolve();
          });
        } catch (err) {
          settle(() => reject(err));
        }
      });

      view.webContents.on("did-fail-load", (_event, errorCode, errorDesc) => {
        settle(() => reject(new Error(`页面加载失败: ${errorCode} ${errorDesc}`)));
      });

      view.webContents.on("render-process-gone", () => {
        settle(() => reject(new Error("渲染进程崩溃")));
      });

      view.webContents.loadURL(url);
    });
  }

  private async checkRisk(view: BrowserView): Promise<string | null> {
    try {
      const title = await view.webContents.executeJavaScript("document.title");
      const bodyText = await view.webContents.executeJavaScript(
        "document.body ? document.body.innerText.substring(0, 3000) : ''"
      );
      const currentUrl = view.webContents.getURL();

      if (currentUrl.includes("login") || currentUrl.includes("verify")) {
        return "风控检测: 页面被重定向到登录/验证页面";
      }

      const combined = (title + " " + bodyText).toLowerCase();
      for (const keyword of RISK_KEYWORDS) {
        if (combined.includes(keyword.toLowerCase())) {
          return `风控检测: 发现关键词"${keyword}"`;
        }
      }
      return null;
    } catch {
      return null;
    }
  }

  private waitForSelector(view: BrowserView, selector: string, timeoutMs: number): Promise<void> {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const check = async () => {
        try {
          const found = await view.webContents.executeJavaScript(
            `document.querySelector('${selector}') !== null`
          );
          if (found) {
            resolve();
            return;
          }
        } catch {}

        if (Date.now() - start > timeoutMs) {
          resolve();
          return;
        }
        setTimeout(check, 500);
      };
      check();
    });
  }

  private destroyView(taskId: string): void {
    const view = this.views.get(taskId);
    if (view) {
      try {
        view.webContents.close();
      } catch {}
      this.views.delete(taskId);
    }
  }

  private finishTask(): void {
    this.activeCount--;
    if (this.activeCount === 0) {
      this.isRunning = false;
      this.emit("queue:empty");
    }
    this.processQueue();
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  destroy(): void {
    for (const [taskId] of this.views) {
      this.destroyView(taskId);
    }
    this.taskQueue = [];
    this.activeCount = 0;
    this.isRunning = false;
    this.removeAllListeners();
  }
}
