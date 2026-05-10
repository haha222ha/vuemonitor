import { chromium, type Browser, type BrowserContext, type Page } from "playwright-core";
import { EventEmitter } from "events";
import * as path from "path";
import * as fs from "fs";
import { parseXHSUrl, buildXHSNoteUrl } from "../../../shared/constants/platforms";

export interface PlaywrightTask {
  id: string;
  targetUrl: string;
  targetType: "note" | "user" | "search";
  targetId: string;
  options?: PlaywrightTaskOptions;
}

export interface PlaywrightTaskOptions {
  scrollCount?: number;
  waitForNetworkIdle?: boolean;
  screenshot?: boolean;
  timeout?: number;
}

export interface PlaywrightResult {
  taskId: string;
  targetId: string;
  targetType: string;
  status: "success" | "failed" | "risk_detected";
  data?: Record<string, unknown>;
  error?: string;
  screenshotPath?: string;
  collectedAt: string;
}

const DEFAULT_OPTIONS: Required<PlaywrightTaskOptions> = {
  scrollCount: 3,
  waitForNetworkIdle: true,
  screenshot: false,
  timeout: 45000,
};

export class PlaywrightCollector extends EventEmitter {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private isLaunching: boolean = false;
  private activeTasks: number = 0;
  private maxConcurrency: number = 2;
  private taskQueue: PlaywrightTask[] = [];
  private screenshotDir: string;

  constructor(screenshotDir?: string) {
    super();
    this.screenshotDir = screenshotDir || path.join(process.cwd(), "data", "screenshots");
  }

  getActiveCount(): number {
    return this.activeTasks;
  }

  getQueueLength(): number {
    return this.taskQueue.length;
  }

  setConcurrency(max: number): void {
    this.maxConcurrency = Math.max(1, Math.min(5, max));
    this.processQueue();
  }

  async launch(): Promise<void> {
    if (this.browser && this.browser.isConnected()) return;
    if (this.isLaunching) return;

    this.isLaunching = true;
    try {
      const chromePath = this.findChromePath();

      this.browser = await chromium.launch({
        executablePath: chromePath || undefined,
        headless: true,
        args: [
          "--disable-blink-features=AutomationControlled",
          "--disable-features=IsolateOrigins,site-per-process",
          "--disable-web-security",
          "--no-sandbox",
          "--disable-setuid-sandbox",
          "--disable-dev-shm-usage",
          "--disable-gpu",
        ],
      });

      this.context = await this.browser.newContext({
        viewport: { width: 1440, height: 900 },
        userAgent:
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale: "zh-CN",
        timezoneId: "Asia/Shanghai",
        extraHTTPHeaders: {
          Referer: "https://www.xiaohongshu.com/",
          Origin: "https://www.xiaohongshu.com",
        },
      });

      await this.context.addInitScript(() => {
        Object.defineProperty(navigator, "webdriver", { get: () => false });
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters: any) =>
          parameters.name === "notifications"
            ? Promise.resolve({ state: Notification.permission } as PermissionStatus)
            : originalQuery(parameters);
      });

      this.emit("launched");
    } catch (err) {
      this.emit("error", { phase: "launch", error: (err as Error).message });
      throw err;
    } finally {
      this.isLaunching = false;
    }
  }

  private findChromePath(): string | null {
    const candidates: string[] = [];

    if (process.platform === "win32") {
      const pf = process.env["ProgramFiles"] || "C:\\Program Files";
      const pf86 = process.env["ProgramFiles(x86)"] || "C:\\Program Files (x86)";
      const localAppData = process.env["LOCALAPPDATA"] || "";

      candidates.push(
        path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
        path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
        path.join(localAppData, "Google", "Chrome", "Application", "chrome.exe"),
        path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
        path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
        path.join(localAppData, "Microsoft", "Edge", "Application", "msedge.exe")
      );
    }

    for (const p of candidates) {
      if (fs.existsSync(p)) return p;
    }
    return null;
  }

  enqueue(task: PlaywrightTask): void {
    this.taskQueue.push(task);
    this.emit("task:queued", { taskId: task.id, queueLength: this.taskQueue.length });
    this.processQueue();
  }

  enqueueBatch(tasks: PlaywrightTask[]): void {
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
      return true;
    }
    return false;
  }

  clearQueue(): number {
    const count = this.taskQueue.length;
    this.taskQueue = [];
    return count;
  }

  private processQueue(): void {
    while (this.activeTasks < this.maxConcurrency && this.taskQueue.length > 0) {
      const task = this.taskQueue.shift()!;
      this.executeTask(task);
    }
  }

  private async executeTask(task: PlaywrightTask): Promise<void> {
    this.activeTasks++;
    this.emit("task:start", { taskId: task.id, activeCount: this.activeTasks });

    if (!this.browser || !this.browser.isConnected()) {
      await this.launch();
    }

    const page = await this.context!.newPage();

    try {
      await page.goto(task.targetUrl, {
        waitUntil: "networkidle",
        timeout: task.options?.timeout || DEFAULT_OPTIONS.timeout,
      });

      await this.delay(2000);

      const riskDetected = await this.checkRisk(page);
      if (riskDetected) {
        const result: PlaywrightResult = {
          taskId: task.id,
          targetId: task.targetId,
          targetType: task.targetType,
          status: "risk_detected",
          error: riskDetected,
          collectedAt: new Date().toISOString(),
        };
        this.emit("task:risk", result);
        this.emit("task:result", result);
        return;
      }

      const scrollCount = task.options?.scrollCount ?? DEFAULT_OPTIONS.scrollCount;
      await this.autoScroll(page, scrollCount);

      if (task.options?.waitForNetworkIdle ?? DEFAULT_OPTIONS.waitForNetworkIdle) {
        await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
      }

      await this.delay(1500);

      const extracted = await this.extractData(page, task.targetType);

      let screenshotPath: string | undefined;
      if (task.options?.screenshot ?? DEFAULT_OPTIONS.screenshot) {
        screenshotPath = await this.takeScreenshot(page, task.id);
      }

      const result: PlaywrightResult = {
        taskId: task.id,
        targetId: task.targetId,
        targetType: task.targetType,
        status: "success",
        data: extracted,
        screenshotPath,
        collectedAt: new Date().toISOString(),
      };

      this.emit("task:success", result);
      this.emit("task:result", result);
    } catch (err) {
      const errorMessage = (err as Error).message;
      const result: PlaywrightResult = {
        taskId: task.id,
        targetId: task.targetId,
        targetType: task.targetType,
        status: "failed",
        error: errorMessage,
        collectedAt: new Date().toISOString(),
      };
      this.emit("task:failed", result);
      this.emit("task:result", result);
    } finally {
      await page.close().catch(() => {});
      this.activeTasks--;
      this.processQueue();
    }
  }

  private async autoScroll(page: Page, count: number): Promise<void> {
    for (let i = 0; i < count; i++) {
      await page.evaluate(() => {
        window.scrollBy(0, window.innerHeight);
      });
      await this.delay(800 + Math.random() * 1200);
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await this.delay(500);
  }

  private async checkRisk(page: Page): Promise<string | null> {
    const url = page.url();
    if (url.includes("login") || url.includes("verify") || url.includes("captcha")) {
      return "风控检测: 页面被重定向到登录/验证页面";
    }

    const riskKeywords = ["验证码", "captcha", "verify", "安全验证", "频繁", "封禁", "blocked", "forbidden"];
    const bodyText = await page.evaluate(() => document.body?.innerText?.substring(0, 3000) || "");
    const title = await page.title();

    const combined = (title + " " + bodyText).toLowerCase();
    for (const keyword of riskKeywords) {
      if (combined.includes(keyword.toLowerCase())) {
        return `风控检测: 发现关键词"${keyword}"`;
      }
    }

    return null;
  }

  private async extractData(page: Page, targetType: string): Promise<Record<string, unknown>> {
    if (targetType === "user") {
      return this.extractUserProfile(page);
    }
    if (targetType === "search") {
      return this.extractSearchResults(page);
    }
    return this.extractNoteDetail(page);
  }

  private async extractNoteDetail(page: Page): Promise<Record<string, unknown>> {
    return page.evaluate(() => {
      const data: Record<string, unknown> = { platform: "xhs" };

      const titleEl = document.querySelector(
        '.title, [class*="title"], h1, [class*="note-content"] [class*="title"]'
      );
      data.product_name = titleEl?.textContent?.trim().substring(0, 500) || "";

      const authorEl = document.querySelector(
        '.author-wrapper .name, [class*="author"] [class*="name"], .user-nickname'
      );
      data.shop_name = authorEl?.textContent?.trim() || null;

      const likeEl = document.querySelector(
        '.like-wrapper .count, [class*="like"] .count, [class*="engage"] [class*="like"]'
      );
      data.favorite_count = likeEl ? parseInt(likeEl.textContent?.replace(/[^0-9]/g, "") || "") || null : null;

      const collectEl = document.querySelector(
        '.collect-wrapper .count, [class*="collect"] .count, [class*="engage"] [class*="collect"]'
      );
      data.sales_count = collectEl ? parseInt(collectEl.textContent?.replace(/[^0-9]/g, "") || "") || null : null;

      const commentEl = document.querySelector(
        '.chat-wrapper .count, [class*="comment"] .count, [class*="engage"] [class*="chat"]'
      );
      data.review_count = commentEl ? parseInt(commentEl.textContent?.replace(/[^0-9]/g, "") || "") || null : null;

      const imgEl = document.querySelector(
        '.slide-item img, [class*="image"] img, .carousel-img img'
      );
      data.image_url = (imgEl as HTMLImageElement)?.src || null;

      const tagEls = document.querySelectorAll('[class*="tag"] a, .tag, [class*="hash-tag"]');
      data.category = tagEls.length > 0
        ? Array.from(tagEls).map((t) => t.textContent?.trim().replace("#", "")).filter(Boolean).join(",")
        : null;

      const pathname = window.location.pathname;
      const match = pathname.match(/\/explore\/([a-f0-9]+)/) || pathname.match(/\/discovery\/item\/([a-f0-9]+)/);
      data.platform_product_id = match ? match[1] : "";
      data.product_url = window.location.href;

      const dateEl = document.querySelector('[class*="date"], [class*="time"]');
      data.publish_date = dateEl?.textContent?.trim() || null;

      const descEl = document.querySelector('[class*="desc"], [class*="note-content"] span, .content');
      data.description = descEl?.textContent?.trim().substring(0, 1000) || null;

      const noteContent = document.querySelector('[class*="note-content"], [class*="content-container"]');
      data.full_text = noteContent?.textContent?.trim().substring(0, 3000) || null;

      const commentList = document.querySelectorAll('[class*="comment-item"], [class*="comment-list"] > div');
      data.top_comments = commentList.length > 0
        ? Array.from(commentList).slice(0, 10).map((c) => {
            const userEl = c.querySelector('[class*="name"], [class*="nickname"]');
            const contentEl = c.querySelector('[class*="content"], [class*="text"]');
            return {
              user: userEl?.textContent?.trim() || "",
              content: contentEl?.textContent?.trim() || "",
            };
          })
        : [];

      return data;
    });
  }

  private async extractUserProfile(page: Page): Promise<Record<string, unknown>> {
    return page.evaluate(() => {
      const data: Record<string, unknown> = { platform: "xhs", targetType: "user" };

      const nameEl = document.querySelector('[class*="user-name"], [class*="nickname"]');
      data.shop_name = nameEl?.textContent?.trim() || "";

      const descEl = document.querySelector('[class*="desc"], [class*="bio"]');
      data.description = descEl?.textContent?.trim() || null;

      const fansEl = document.querySelector('[class*="fans"] [class*="count"], [class*="follower"]');
      data.fans_count = fansEl ? parseInt(fansEl.textContent?.replace(/[^0-9]/g, "") || "") || null : null;

      const noteCountEl = document.querySelector('[class*="note-count"], [class*="notes"]');
      data.note_count = noteCountEl ? parseInt(noteCountEl.textContent?.replace(/[^0-9]/g, "") || "") || null : null;

      const pathname = window.location.pathname;
      const match = pathname.match(/\/user\/profile\/([a-f0-9]+)/);
      data.platform_product_id = match ? match[1] : "";
      data.product_url = window.location.href;
      data.product_name = (data.shop_name as string) + "的主页";

      const noteCards = document.querySelectorAll('[class*="note-item"], [class*="feed-item"], section a');
      data.recent_notes = Array.from(noteCards).slice(0, 20).map((card) => {
        const link = (card as HTMLAnchorElement).href || card.querySelector("a")?.getAttribute("href") || "";
        const title = card.textContent?.trim().substring(0, 200) || "";
        return { title, link };
      });

      return data;
    });
  }

  private async extractSearchResults(page: Page): Promise<Record<string, unknown>> {
    return page.evaluate(() => {
      const data: Record<string, unknown> = { platform: "xhs", targetType: "search" };

      const searchInput = document.querySelector('[class*="search-input"], input[type="search"]');
      data.search_keyword = (searchInput as HTMLInputElement)?.value || "";

      const noteCards = document.querySelectorAll('[class*="note-item"], [class*="feed-item"], section a');
      data.results = Array.from(noteCards).slice(0, 50).map((card) => {
        const link = (card as HTMLAnchorElement).href || card.querySelector("a")?.getAttribute("href") || "";
        const titleEl = card.querySelector('[class*="title"], [class*="name"]');
        const authorEl = card.querySelector('[class*="author"], [class*="nickname"]');
        const likeEl = card.querySelector('[class*="like"] .count, [class*="like-count"]');

        return {
          title: titleEl?.textContent?.trim() || "",
          author: authorEl?.textContent?.trim() || "",
          likes: likeEl ? parseInt(likeEl.textContent?.replace(/[^0-9]/g, "") || "") || 0 : 0,
          link,
        };
      });

      data.result_count = (data.results as unknown[]).length;
      data.product_url = window.location.href;

      return data;
    });
  }

  private async takeScreenshot(page: Page, taskId: string): Promise<string | undefined> {
    try {
      if (!fs.existsSync(this.screenshotDir)) {
        fs.mkdirSync(this.screenshotDir, { recursive: true });
      }
      const filePath = path.join(this.screenshotDir, `${taskId}_${Date.now()}.png`);
      await page.screenshot({ path: filePath, fullPage: false });
      return filePath;
    } catch {
      return undefined;
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async close(): Promise<void> {
    if (this.context) {
      await this.context.close().catch(() => {});
      this.context = null;
    }
    if (this.browser) {
      await this.browser.close().catch(() => {});
      this.browser = null;
    }
    this.taskQueue = [];
    this.activeTasks = 0;
    this.removeAllListeners();
  }
}

export const playwrightCollector = new PlaywrightCollector();
