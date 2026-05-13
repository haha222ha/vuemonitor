import { BrowserView, BrowserWindow, session, app } from "electron";
import * as path from "path";
import * as fs from "fs";
import { EventEmitter } from "events";
import { buildXHSGoodsUrl, buildXHSNoteUrl, parseXHSUrl } from "@shared/constants/platforms";
import { crashRecovery } from "../recovery/crash-recovery";
import { logger } from "../logger/logger";

export interface CollectTask {
  id: string;
  targetId: string;
  targetType: "goods" | "note" | "user" | "search" | "url";
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

export interface RiskDetectedEvent {
  taskId: string;
  riskType: string;
  riskLevel: "low" | "medium" | "high" | "critical";
  detail: string;
  paused: boolean;
}

const UA_POOL = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ver}.0) Gecko/20100101 Firefox/{ver}.0",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.{ver} Safari/605.1.15",
];

const CAPTCHA_SELECTORS = [
  'iframe[src*="captcha"]',
  'div[class*="captcha"]',
  'div[class*="verify"]',
  '#captcha',
  '.geetest_panel',
  '.nc_wrapper',
  '[class*="slider-verify"]',
  '[class*="puzzle-verify"]',
  '[class*="check"]',
];

const BEHAVIOR_SIGNATURES = [
  { selector: 'script[src*="fingerprint"]', name: "fingerprint_js" },
  { selector: 'script[src*="track"]', name: "tracking_js" },
  { selector: 'script[src*="monitor"]', name: "monitor_js" },
  { selector: 'script[src*="anti"]', name: "anti_bot_js" },
  { selector: 'script[src*="detect"]', name: "detection_js" },
];

const XHS_COLLECT_CONFIG = {
  buildUrl: (targetId: string, targetType: string, targetUrl?: string): string => {
    if (targetUrl) {
      const parsed = parseXHSUrl(targetUrl);
      if (parsed.type === "goods" && parsed.id) {
        return buildXHSGoodsUrl(parsed.id);
      }
      if (parsed.type === "note" && parsed.id && parsed.id !== "short_url") {
        return buildXHSNoteUrl(parsed.id);
      }
      return targetUrl;
    }
    if (targetType === "goods") {
      return buildXHSGoodsUrl(targetId);
    }
    if (targetType === "user") {
      return `https://www.xiaohongshu.com/user/profile/${targetId}`;
    }
    return buildXHSNoteUrl(targetId);
  },
  waitForSelector: "div.goods-name, .note-item, .note-container, .content-container, [class*='note'], [class*='feed']",
  timeout: 30000,
  goodsExtractScript: `
    (function() {
      var data = { platform: 'xhs', targetType: 'goods' };

      var nameEl = document.querySelector('div.goods-name');
      data.product_name = nameEl ? nameEl.textContent.trim().substring(0, 500) : '';

      var price = 0;
      var priceElements = document.querySelectorAll('span[data-v-8686a314]');
      if (priceElements && priceElements.length > 0) {
        for (var i = 0; i < priceElements.length; i++) {
          var priceText = priceElements[i].textContent.trim();
          if (/^\\d+(\\.\\d+)?$/.test(priceText)) {
            price = parseFloat(priceText);
            break;
          }
        }
      }
      if (price === 0) {
        var altPriceEl = document.querySelector('.price, .product-price, .goods-price');
        if (altPriceEl) {
          var altText = altPriceEl.textContent.trim();
          var match = altText.match(/\\d+(\\.\\d+)?/);
          if (match) price = parseFloat(match[0]);
        }
      }
      data.price = price > 0 ? price : null;

      var salesEl = document.querySelector('span.spu-text');
      var sales = 0;
      if (salesEl) {
        var salesText = salesEl.textContent.replace('已售', '').trim();
        if (salesText.includes('万')) {
          var num = parseFloat(salesText.replace(/[^0-9.]/g, ''));
          sales = Math.floor(num * 10000);
        } else {
          sales = parseInt(salesText.replace(/[^0-9]/g, '')) || 0;
        }
      }
      data.sales_count = sales > 0 ? sales : null;
      data.monthly_sales = data.sales_count;

      var shopNameEl = document.querySelector('p.seller-name');
      data.shop_name = shopNameEl ? shopNameEl.textContent.trim() : null;

      var shopSales = 0;
      var shopSalesElements = document.querySelectorAll('span.sub-title');
      if (shopSalesElements && shopSalesElements.length > 0) {
        for (var j = 0; j < shopSalesElements.length; j++) {
          var sText = shopSalesElements[j].textContent.trim();
          if (sText.includes('已售')) {
            var sNum = sText.replace('已售', '').trim();
            if (sNum.includes('万')) {
              shopSales = Math.floor(parseFloat(sNum.replace(/[^0-9.]/g, '')) * 10000);
            } else {
              shopSales = parseInt(sNum.replace(/[^0-9]/g, '')) || 0;
            }
            break;
          }
        }
      }
      data.shop_sales = shopSales > 0 ? shopSales : null;

      var imgEl = document.querySelector('div.goods-img img, .swiper-slide img, [class*="goods"] img, [class*="product"] img');
      data.image_url = imgEl ? imgEl.src : null;

      var pathname = window.location.pathname;
      var goodsMatch = pathname.match(/\\/goods-detail\\/([a-f0-9]+)/);
      data.platform_product_id = goodsMatch ? goodsMatch[1] : '';
      data.product_url = window.location.href;

      var descEl = document.querySelector('[class*="desc"], [class*="detail"], .goods-desc');
      data.description = descEl ? descEl.textContent.trim().substring(0, 1000) : null;

      var tagEls = document.querySelectorAll('[class*="tag"] a, .tag, [class*="hash-tag"]');
      data.category = tagEls.length > 0 ? Array.from(tagEls).map(function(t) { return t.textContent.trim().replace('#', ''); }).filter(Boolean).join(',') : null;

      var ratingEl = document.querySelector('[class*="rating"], [class*="score"]');
      data.rating = ratingEl ? parseFloat(ratingEl.textContent.replace(/[^0-9.]/g, '')) || null : null;

      var reviewEl = document.querySelector('[class*="review-count"], [class*="comment-count"]');
      data.review_count = reviewEl ? parseInt(reviewEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      var favEl = document.querySelector('[class*="like"] .count, [class*="favorite"] .count, [class*="collect"] .count');
      data.favorite_count = favEl ? parseInt(favEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      return data;
    })()
  `,
  noteExtractScript: `
    (function() {
      var data = { platform: 'xhs', targetType: 'note' };

      var titleEl = document.querySelector(
        '.title, [class*="title"], h1, [class*="note-content"] [class*="title"]'
      );
      data.product_name = titleEl ? titleEl.textContent.trim().substring(0, 500) : '';

      var authorEl = document.querySelector(
        '.author-wrapper .name, [class*="author"] [class*="name"], .user-nickname, [class*="user-info"] [class*="name"]'
      );
      data.shop_name = authorEl ? authorEl.textContent.trim() : null;

      var likeEl = document.querySelector(
        '.like-wrapper .count, [class*="like"] .count, .engagement-bar .count, [class*="engage"] [class*="like"]'
      );
      data.favorite_count = likeEl ? parseInt(likeEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      var collectEl = document.querySelector(
        '.collect-wrapper .count, [class*="collect"] .count, [class*="engage"] [class*="collect"]'
      );
      data.sales_count = collectEl ? parseInt(collectEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      var commentEl = document.querySelector(
        '.chat-wrapper .count, [class*="comment"] .count, [class*="engage"] [class*="chat"]'
      );
      data.review_count = commentEl ? parseInt(commentEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      var imgEl = document.querySelector(
        '.slide-item img, [class*="image"] img, .carousel-img img, [class*="note-content"] img'
      );
      data.image_url = imgEl ? imgEl.src : null;

      var tagEls = document.querySelectorAll('[class*="tag"] a, .tag, [class*="hash-tag"]');
      data.category = tagEls.length > 0 ? Array.from(tagEls).map(function(t) { return t.textContent.trim().replace('#', ''); }).filter(Boolean).join(',') : null;

      var pathname = window.location.pathname;
      var match = pathname.match(/\\/explore\\/([a-f0-9]+)/) || pathname.match(/\\/discovery\\/item\\/([a-f0-9]+)/);
      data.platform_product_id = match ? match[1] : '';
      data.product_url = window.location.href;

      var dateEl = document.querySelector('[class*="date"], [class*="time"], .bottom-container .date');
      data.publish_date = dateEl ? dateEl.textContent.trim() : null;

      var descEl = document.querySelector('[class*="desc"], [class*="note-content"] span, .content');
      data.description = descEl ? descEl.textContent.trim().substring(0, 1000) : null;

      return data;
    })()
  `,
  userExtractScript: `
    (function() {
      var data = { platform: 'xhs', targetType: 'user' };

      var nameEl = document.querySelector('[class*="user-name"], [class*="nickname"], .user-name');
      data.shop_name = nameEl ? nameEl.textContent.trim() : '';

      var descEl = document.querySelector('[class*="desc"], [class*="bio"], .user-desc');
      data.description = descEl ? descEl.textContent.trim() : null;

      var fansEl = document.querySelector('[class*="fans"] [class*="count"], [class*="follower"]');
      data.fans_count = fansEl ? parseInt(fansEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      var noteCountEl = document.querySelector('[class*="note-count"], [class*="notes"]');
      data.note_count = noteCountEl ? parseInt(noteCountEl.textContent.replace(/[^0-9]/g, '')) || null : null;

      var pathname = window.location.pathname;
      var match = pathname.match(/\\/user\\/profile\\/([a-f0-9]+)/);
      data.platform_product_id = match ? match[1] : '';
      data.product_url = window.location.href;
      data.product_name = data.shop_name + '的主页';

      return data;
    })()
  `,
};

const RISK_KEYWORDS = [
  "验证码", "captcha", "verify", "安全验证",
  "频繁", "rate limit", "429", "封禁", "blocked", "forbidden", "403",
  "操作过于频繁", "请稍后再试", "异常",
  "滑动验证", "图形验证", "人机验证", "robot", "automated",
  "access denied", "unusual traffic", "suspicious activity",
];

const RISK_URL_PATTERNS = [
  "/login", "/verify", "/captcha", "/safe", "/check",
  "/security", "/risk", "/anti-bot", "/challenge",
];

const RISK_LEVEL_MAP: Record<string, "low" | "medium" | "high" | "critical"> = {
  captcha: "high",
  login_required: "high",
  rate_limit: "medium",
  ip_blocked: "critical",
  behavior_detected: "low",
  redirect: "medium",
};

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
  private currentUAIndex: number = 0;
  private consecutiveRiskCount: number = 0;
  private isPaused: boolean = false;
  private backoffMultiplier: number = 1.0;
  private cookieRotationIndex: number = 0;
  private riskStats = {
    totalRiskDetected: 0,
    captchaCount: 0,
    rateLimitCount: 0,
    ipBlockedCount: 0,
    lastRiskAt: null as string | null,
  };
  private checkpointPath: string;
  private checkpointData: Map<string, { taskId: string; targetId: string; targetType: string; targetUrl?: string; shardIndex: number; shardTotal: number }> = new Map();
  private memoryWatchInterval: ReturnType<typeof setInterval> | null = null;
  private maxMemoryMB: number = 512;

  constructor() {
    super();
    this.checkpointPath = path.join(app.getPath("userData"), "collect-checkpoint.json");
    this.loadCheckpoint();
    this.startMemoryWatch();
  }

  private loadCheckpoint(): void {
    try {
      if (fs.existsSync(this.checkpointPath)) {
        const raw = fs.readFileSync(this.checkpointPath, "utf-8");
        const data = JSON.parse(raw);
        if (Array.isArray(data)) {
          for (const item of data) {
            this.checkpointData.set(item.taskId, item);
          }
          logger.info("ChromiumWorker", "加载断点续采数据", { count: this.checkpointData.size });
        }
      }
    } catch (e) {
      logger.warn("ChromiumWorker", "加载断点数据失败", { error: String(e) });
    }
  }

  private saveCheckpoint(): void {
    try {
      const data = Array.from(this.checkpointData.values());
      fs.writeFileSync(this.checkpointPath, JSON.stringify(data, null, 2), "utf-8");
    } catch (e) {
      logger.warn("ChromiumWorker", "保存断点数据失败", { error: String(e) });
    }
  }

  private startMemoryWatch(): void {
    this.memoryWatchInterval = setInterval(() => {
      const mem = process.memoryUsage();
      const heapMB = Math.round(mem.heapUsed / 1024 / 1024);
      if (heapMB > this.maxMemoryMB) {
        logger.warn("ChromiumWorker", "内存使用超过阈值，暂停新任务", { heapMB, maxMB: this.maxMemoryMB });
        if (!this.isPaused) {
          this.pauseQueue();
          this.emit("memory:high", { heapMB, maxMB: this.maxMemoryMB });
        }
      }
    }, 30000);
  }

  setMaxMemory(mb: number): void {
    this.maxMemoryMB = Math.max(128, mb);
  }

  getMemoryUsage(): { heapUsedMB: number; heapTotalMB: number; rssMB: number } {
    const mem = process.memoryUsage();
    return {
      heapUsedMB: Math.round(mem.heapUsed / 1024 / 1024),
      heapTotalMB: Math.round(mem.heapTotal / 1024 / 1024),
      rssMB: Math.round(mem.rss / 1024 / 1024),
    };
  }

  enqueueBatchSharded(tasks: CollectTask[], shardSize: number = 5): void {
    const shards: CollectTask[][] = [];
    for (let i = 0; i < tasks.length; i += shardSize) {
      shards.push(tasks.slice(i, i + shardSize));
    }

    for (let shardIndex = 0; shardIndex < shards.length; shardIndex++) {
      const shard = shards[shardIndex];
      for (const task of shard) {
        this.taskQueue.push(task);
        this.checkpointData.set(task.id, {
          taskId: task.id,
          targetId: task.targetId,
          targetType: task.targetType,
          targetUrl: task.targetUrl,
          shardIndex,
          shardTotal: shards.length,
        });
      }
    }

    this.saveCheckpoint();
    this.emit("task:batch_queued", { count: tasks.length, queueLength: this.taskQueue.length, shards: shards.length });
    logger.info("ChromiumWorker", "分片入队采集任务", { count: tasks.length, shardSize, shards: shards.length });
    this.processQueue();
  }

  getPendingCheckpoints(): CollectTask[] {
    const pending: CollectTask[] = [];
    for (const [taskId, cp] of this.checkpointData) {
      const inQueue = this.taskQueue.some((t) => t.id === taskId);
      if (!inQueue) {
        pending.push({
          id: cp.taskId,
          targetId: cp.targetId,
          targetType: cp.targetType as any,
          targetUrl: cp.targetUrl,
        });
      }
    }
    return pending;
  }

  resumeFromCheckpoint(): number {
    const pending = this.getPendingCheckpoints();
    if (pending.length === 0) return 0;
    for (const task of pending) {
      this.taskQueue.push(task);
    }
    this.emit("task:batch_queued", { count: pending.length, queueLength: this.taskQueue.length });
    logger.info("ChromiumWorker", "从断点恢复采集任务", { count: pending.length });
    this.processQueue();
    return pending.length;
  }

  clearCheckpoint(): void {
    this.checkpointData.clear();
    try {
      if (fs.existsSync(this.checkpointPath)) {
        fs.unlinkSync(this.checkpointPath);
      }
    } catch {}
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

  getRiskStats() {
    return { ...this.riskStats };
  }

  isQueuePaused(): boolean {
    return this.isPaused;
  }

  resumeQueue(): void {
    this.isPaused = false;
    this.consecutiveRiskCount = 0;
    this.backoffMultiplier = 1.0;
    this.emit("queue:resumed");
    this.processQueue();
  }

  pauseQueue(): void {
    this.isPaused = true;
    this.emit("queue:paused", { pendingCount: this.taskQueue.length });
  }

  private generateUA(): string {
    const template = UA_POOL[this.currentUAIndex % UA_POOL.length];
    const ver = Math.floor(Math.random() * 16) + 115;
    const ua = template.replace(/{ver}/g, String(ver));
    this.currentUAIndex++;
    return ua;
  }

  private rotateUA(): void {
    const ua = this.generateUA();
    if (this.collectSession) {
      this.collectSession.setUserAgent(ua);
    }
    this.emit("ua:rotated", { ua: ua.substring(0, 60) + "..." });
  }

  async init(): Promise<void> {
    this.collectSession = session.fromPartition("persist:xhs-collect", { cache: true });
    const initialUA = this.generateUA();
    this.collectSession.setUserAgent(initialUA);
    logger.info("ChromiumWorker", "采集会话初始化", { ua: initialUA.substring(0, 60) });

    this.collectSession.webRequest.onBeforeSendHeaders((details, callback) => {
      details.requestHeaders["Referer"] = "https://www.xiaohongshu.com/";
      details.requestHeaders["Origin"] = "https://www.xiaohongshu.com";
      details.requestHeaders["Sec-Ch-Ua"] = this.generateSecChUa();
      details.requestHeaders["Sec-Ch-Ua-Mobile"] = "?0";
      details.requestHeaders["Sec-Ch-Ua-Platform"] = '"Windows"';
      details.requestHeaders["Sec-Fetch-Dest"] = "document";
      details.requestHeaders["Sec-Fetch-Mode"] = "navigate";
      details.requestHeaders["Sec-Fetch-Site"] = "none";
      details.requestHeaders["Sec-Fetch-User"] = "?1";
      details.requestHeaders["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8";
      callback({ requestHeaders: details.requestHeaders });
    });

    this.collectSession.cookies.on("changed", (_event, cookie, cause, removed) => {
      if (!removed && cause === "explicit") {
        this.emit("cookie:updated", { name: cookie.name, domain: cookie.domain });
      }
    });
  }

  private generateSecChUa(): string {
    const ver = Math.floor(Math.random() * 16) + 115;
    return `"Chromium";v="${ver}", "Google Chrome";v="${ver}", "Not-A.Brand";v="99"`;
  }

  async getCookies(): Promise<Electron.Cookie[]> {
    if (!this.collectSession) return [];
    return this.collectSession.cookies.get({ domain: ".xiaohongshu.com" });
  }

  async setCookies(cookies: Array<{ name: string; value: string; domain?: string; path?: string }>): Promise<void> {
    if (!this.collectSession) return;
    for (const c of cookies) {
      await this.collectSession.cookies.set({
        url: "https://www.xiaohongshu.com",
        name: c.name,
        value: c.value,
        domain: c.domain || ".xiaohongshu.com",
        path: c.path || "/",
      });
    }
    this.emit("cookie:rotated", { count: cookies.length });
  }

  async clearCookies(): Promise<void> {
    if (!this.collectSession) return;
    const cookies = await this.collectSession.cookies.get({});
    for (const c of cookies) {
      if (c.domain.includes("xiaohongshu")) {
        await this.collectSession.cookies.remove("https://www.xiaohongshu.com", c.name);
      }
    }
    this.emit("cookie:cleared");
  }

  async checkCookieHealth(): Promise<{ valid: boolean; count: number; details: string }> {
    if (!this.collectSession) return { valid: false, count: 0, details: "会话未初始化" };
    const cookies = await this.collectSession.cookies.get({ domain: ".xiaohongshu.com" });
    const essentialCookies = ["web_session", "a1", "webId"];
    const found = essentialCookies.filter((name) => cookies.some((c) => c.name === name));

    if (found.length === 0) {
      return { valid: false, count: cookies.length, details: "缺少关键Cookie，可能需要登录" };
    }
    if (cookies.length < 3) {
      return { valid: false, count: cookies.length, details: "Cookie数量过少，会话可能过期" };
    }

    const now = Date.now() / 1000;
    const expiredCount = cookies.filter((c) => c.expirationDate && c.expirationDate < now).length;
    if (expiredCount > cookies.length * 0.5) {
      return { valid: false, count: cookies.length, details: `${expiredCount}个Cookie已过期` };
    }

    return { valid: true, count: cookies.length, details: `Cookie健康，共${cookies.length}个` };
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
    logger.info("ChromiumWorker", "批量入队采集任务", { count: tasks.length, queueLength: this.taskQueue.length });
    this.processQueue();
  }

  cancelTask(taskId: string): boolean {
    const idx = this.taskQueue.findIndex((t) => t.id === taskId);
    if (idx !== -1) {
      this.taskQueue.splice(idx, 1);
      this.emit("task:cancelled", { taskId });
      logger.info("ChromiumWorker", "取消采集任务", { taskId });
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
    if (this.isPaused) {
      throw new Error("采集队列已暂停（风控触发），请手动恢复");
    }

    const baseMin = 2000;
    const baseMax = 6000;
    const minInterval = baseMin * this.backoffMultiplier;
    const maxInterval = baseMax * this.backoffMultiplier;
    const randomInterval = minInterval + Math.random() * (maxInterval - minInterval);

    const now = Date.now();
    const elapsed = now - this.lastRequestTime;
    if (elapsed < randomInterval) {
      await this.delay(randomInterval - elapsed);
    }
    this.lastRequestTime = Date.now();
    this.requestCount++;
  }

  private handleRiskDetected(riskType: string): void {
    this.consecutiveRiskCount++;
    this.riskStats.totalRiskDetected++;
    this.riskStats.lastRiskAt = new Date().toISOString();

    if (riskType === "captcha") {
      this.riskStats.captchaCount++;
      this.backoffMultiplier = Math.min(this.backoffMultiplier * 3.0, 10.0);
    } else if (riskType === "rate_limit") {
      this.riskStats.rateLimitCount++;
      this.backoffMultiplier = Math.min(this.backoffMultiplier * 2.0, 8.0);
    } else if (riskType === "ip_blocked") {
      this.riskStats.ipBlockedCount++;
      this.backoffMultiplier = Math.min(this.backoffMultiplier * 4.0, 15.0);
    } else {
      this.backoffMultiplier = Math.min(this.backoffMultiplier * 1.5, 6.0);
    }

    this.rotateUA();

    if (this.consecutiveRiskCount >= 3 || riskType === "ip_blocked") {
      this.pauseQueue();
      logger.warn("ChromiumWorker", "风控达到临界阈值，暂停采集队列", { riskType, consecutiveCount: this.consecutiveRiskCount, backoffMultiplier: this.backoffMultiplier });
      this.emit("risk:critical", {
        riskType,
        consecutiveCount: this.consecutiveRiskCount,
        backoffMultiplier: this.backoffMultiplier,
        pendingTasks: this.taskQueue.length,
      } as RiskDetectedEvent & { consecutiveCount: number; backoffMultiplier: number; pendingTasks: number });
    }
  }

  private handleSuccess(): void {
    if (this.consecutiveRiskCount > 0) {
      this.consecutiveRiskCount = Math.max(0, this.consecutiveRiskCount - 1);
    }
    this.backoffMultiplier = Math.max(1.0, this.backoffMultiplier * 0.85);
  }

  private processQueue(): void {
    if (this.isPaused) return;
    while (this.activeCount < this.maxConcurrency && this.taskQueue.length > 0) {
      const task = this.taskQueue.shift()!;
      this.executeTask(task);
    }
  }

  private async executeTask(task: CollectTask): Promise<void> {
    if (this.isPaused) {
      this.taskQueue.unshift(task);
      return;
    }

    this.activeCount++;
    this.isRunning = true;
    this.emit("task:start", { taskId: task.id, targetType: task.targetType, activeCount: this.activeCount });

    crashRecovery.saveSnapshot({
      id: task.id,
      taskType: "chromium",
      targetId: task.targetId,
      targetType: task.targetType,
      targetUrl: task.targetUrl || null,
      status: "running",
      progress: 0,
      startedAt: new Date().toISOString(),
      retryCount: 0,
      maxRetries: 3,
      error: null,
      metadata: JSON.stringify({ queueLength: this.taskQueue.length }),
    });

    let currentPhase: "loading" | "extracting" | "risk_check" | "normalizing" | "saving" = "loading";
    let currentProgress = 0;

    crashRecovery.startPeriodicCheckpoint(task.id, () => ({
      phase: currentPhase,
      progress: currentProgress,
      partialData: null,
    }));

    const url = XHS_COLLECT_CONFIG.buildUrl(task.targetId, task.targetType, task.targetUrl);
    let extractScript: string;
    if (task.targetType === "goods") {
      extractScript = XHS_COLLECT_CONFIG.goodsExtractScript;
    } else if (task.targetType === "user") {
      extractScript = XHS_COLLECT_CONFIG.userExtractScript;
    } else {
      extractScript = XHS_COLLECT_CONFIG.noteExtractScript;
    }

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
      currentPhase = "loading";
      currentProgress = 10;
      await this.loadAndExtract(view, task, url, extractScript, (phase, progress) => {
        currentPhase = phase;
        currentProgress = progress;
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      crashRecovery.updateSnapshotStatus(task.id, "failed", undefined, errorMessage);
      this.emit("task:failed", { taskId: task.id, error: errorMessage });
    } finally {
      crashRecovery.stopPeriodicCheckpoint(task.id);
      this.destroyView(task.id);
      this.finishTask();
    }
  }

  private loadAndExtract(
    view: BrowserView,
    task: CollectTask,
    url: string,
    extractScript: string,
    onPhase: (phase: "loading" | "extracting" | "risk_check" | "normalizing" | "saving", progress: number) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`采集超时: ${task.targetType}/${task.targetId}`));
      }, XHS_COLLECT_CONFIG.timeout);

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

          onPhase("risk_check", 30);
          const riskResult = await this.checkRiskEnhanced(view);
          if (riskResult) {
            settle(() => {
              this.handleRiskDetected(riskResult.riskType);
              crashRecovery.updateSnapshotStatus(task.id, "risk_detected", undefined, riskResult.detail);
              const result: CollectResult = {
                taskId: task.id,
                targetId: task.targetId,
                targetType: task.targetType,
                status: "risk_detected",
                error: riskResult.detail,
                collectedAt: new Date().toISOString(),
              };
              this.emit("task:risk", result);
              this.emit("task:result", result);
              this.emit("risk:detected", {
                taskId: task.id,
                riskType: riskResult.riskType,
                riskLevel: riskResult.riskLevel,
                detail: riskResult.detail,
                paused: this.isPaused,
              } as RiskDetectedEvent);
              resolve();
            });
            return;
          }

          if (XHS_COLLECT_CONFIG.waitForSelector) {
            await this.waitForSelector(view, XHS_COLLECT_CONFIG.waitForSelector, 10000);
          }

          await this.delay(1500);

          onPhase("extracting", 50);
          const extracted = await view.webContents.executeJavaScript(extractScript);

          onPhase("saving", 80);
          const result: CollectResult = {
            taskId: task.id,
            targetId: task.targetId,
            targetType: task.targetType,
            status: "success",
            data: extracted || {},
            collectedAt: new Date().toISOString(),
          };

          settle(() => {
            this.handleSuccess();
            crashRecovery.updateSnapshotStatus(task.id, "completed", 100);
            crashRecovery.removeSnapshot(task.id);
            this.checkpointData.delete(task.id);
            this.saveCheckpoint();
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

  private async checkRiskEnhanced(
    view: BrowserView
  ): Promise<{ riskType: string; riskLevel: "low" | "medium" | "high" | "critical"; detail: string } | null> {
    try {
      const currentUrl = view.webContents.getURL();

      for (const pattern of RISK_URL_PATTERNS) {
        if (currentUrl.toLowerCase().includes(pattern)) {
          return {
            riskType: "redirect",
            riskLevel: "medium",
            detail: `风控检测: 页面被重定向到${pattern}页面`,
          };
        }
      }

      const captchaDetected = await view.webContents.executeJavaScript(`
        (function() {
          var selectors = ${JSON.stringify(CAPTCHA_SELECTORS)};
          for (var i = 0; i < selectors.length; i++) {
            var el = document.querySelector(selectors[i]);
            if (el) {
              var rect = el.getBoundingClientRect();
              if (rect.width > 0 && rect.height > 0) {
                return { found: true, selector: selectors[i], visible: true };
              }
            }
          }
          return { found: false };
        })()
      `);

      if (captchaDetected && captchaDetected.found) {
        return {
          riskType: "captcha",
          riskLevel: "high",
          detail: `风控检测: 发现验证码元素 (${captchaDetected.selector})`,
        };
      }

      const behaviorResult = await view.webContents.executeJavaScript(`
        (function() {
          var signatures = ${JSON.stringify(BEHAVIOR_SIGNATURES)};
          var detected = [];
          for (var i = 0; i < signatures.length; i++) {
            var el = document.querySelector(signatures[i].selector);
            if (el) detected.push(signatures[i].name);
          }

          var hasAutomation = !!(window._phantom || window.__nightmare || window.callPhantom);
          var hasWebDriver = navigator.webdriver === true;
          var hasHeadless = /HeadlessChrome/.test(navigator.userAgent);

          return {
            detectedScripts: detected,
            hasAutomation: hasAutomation,
            hasWebDriver: hasWebDriver,
            hasHeadless: hasHeadless
          };
        })()
      `);

      if (behaviorResult) {
        if (behaviorResult.hasWebDriver || behaviorResult.hasAutomation || behaviorResult.hasHeadless) {
          return {
            riskType: "behavior_detected",
            riskLevel: "high",
            detail: "风控检测: 检测到自动化浏览器特征",
          };
        }
        if (behaviorResult.detectedScripts && behaviorResult.detectedScripts.length >= 2) {
          return {
            riskType: "behavior_detected",
            riskLevel: "low",
            detail: `风控检测: 发现反爬脚本 (${behaviorResult.detectedScripts.join(", ")})`,
          };
        }
      }

      const hasLoginForm = await view.webContents.executeJavaScript(
        "!!(document.querySelector('input[type=\"password\"]') || document.querySelector('[class*=\"login-form\"]') || document.querySelector('[class*=\"signin\"]'))"
      );
      if (hasLoginForm && !currentUrl.includes("/explore/") && !currentUrl.includes("/discovery/")) {
        return {
          riskType: "login_required",
          riskLevel: "high",
          detail: "风控检测: 页面出现登录表单，可能需要先登录小红书",
        };
      }

      const title = await view.webContents.executeJavaScript("document.title");
      const bodyText = await view.webContents.executeJavaScript(
        "document.body ? document.body.innerText.substring(0, 3000) : ''"
      );

      const combined = (title + " " + bodyText).toLowerCase();

      for (const keyword of RISK_KEYWORDS) {
        if (combined.includes(keyword.toLowerCase())) {
          let riskType = "rate_limit";
          if (["验证码", "captcha", "verify", "安全验证", "滑动验证", "图形验证", "人机验证"].includes(keyword)) {
            riskType = "captcha";
          } else if (["封禁", "blocked", "forbidden", "403"].includes(keyword)) {
            riskType = "ip_blocked";
          }
          return {
            riskType,
            riskLevel: RISK_LEVEL_MAP[riskType] || "medium",
            detail: `风控检测: 发现关键词"${keyword}"`,
          };
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
