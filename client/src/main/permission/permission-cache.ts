import * as fs from "fs";
import * as path from "path";
import { FEATURE_GATES, PLAN_LIMITS, isPlanSufficient, PlanTier, FeatureGateDefinition } from "@shared/constants/feature-gates";

export interface PermissionState {
  plan: PlanTier;
  gates: Record<string, boolean>;
  quotas: Record<string, { used: number; limit: number }>;
  lastRefreshed: string | null;
}

const CACHE_FILE = "permission_cache.json";
const CACHE_TTL_MS = 30 * 60 * 1000;

export class LocalPermissionCache {
  private state: PermissionState = {
    plan: "free",
    gates: {},
    quotas: {},
    lastRefreshed: null,
  };
  private cachePath: string;

  constructor(dataDir?: string) {
    const dir = dataDir || path.join(process.cwd(), "data");
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    this.cachePath = path.join(dir, CACHE_FILE);
    this.loadFromDisk();
  }

  async refreshFromServer(serverUrl: string, token: string): Promise<void> {
    try {
      const axios = require("axios");
      const { data } = await axios.get(`${serverUrl}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      this.state.plan = data.plan || "free";
      this.state.lastRefreshed = new Date().toISOString();

      this.rebuildGates();
      this.rebuildQuotas(data.usage || {});
      this.saveToDisk();
    } catch {}
  }

  checkGate(gateKey: string): boolean {
    return this.state.gates[gateKey] ?? false;
  }

  getAllGates(): Record<string, boolean> {
    return { ...this.state.gates };
  }

  getPlan(): PlanTier {
    return this.state.plan;
  }

  getQuota(quotaKey: string): { used: number; limit: number } | null {
    return this.state.quotas[quotaKey] ?? null;
  }

  checkQuota(quotaKey: string, increment: number = 0): boolean {
    const quota = this.state.quotas[quotaKey];
    if (!quota) return true;
    return quota.used + increment <= quota.limit;
  }

  incrementQuota(quotaKey: string, amount: number = 1): void {
    const quota = this.state.quotas[quotaKey];
    if (quota) {
      quota.used += amount;
      this.saveToDisk();
    }
  }

  getState(): PermissionState {
    return { ...this.state };
  }

  clear(): void {
    this.state = {
      plan: "free",
      gates: {},
      quotas: {},
      lastRefreshed: null,
    };
    try {
      if (fs.existsSync(this.cachePath)) {
        fs.unlinkSync(this.cachePath);
      }
    } catch {}
  }

  updateFromLicense(license: { plan: string; features: string[]; isValid: boolean }): void {
    if (!license.isValid) return;
    this.state.plan = (license.plan || "free") as PlanTier;
    this.state.lastRefreshed = new Date().toISOString();
    this.rebuildGates();
    this.saveToDisk();
  }

  private rebuildGates(): void {
    const gates: Record<string, boolean> = {};
    for (const gate of FEATURE_GATES) {
      gates[gate.key] = isPlanSufficient(this.state.plan, gate.requiredPlan);
    }
    this.state.gates = gates;
  }

  private rebuildQuotas(usage: Record<string, number>): void {
    const limits = PLAN_LIMITS[this.state.plan];
    const quotas: Record<string, { used: number; limit: number }> = {
      "gate:monitor:add": {
        used: usage.productCount || 0,
        limit: limits.maxProducts === -1 ? Infinity : limits.maxProducts,
      },
      "gate:collect:daily": {
        used: usage.dailyCollectCount || 0,
        limit: limits.dailyCollectLimit === -1 ? Infinity : limits.dailyCollectLimit,
      },
      "gate:collect:concurrency": {
        used: 0,
        limit: limits.maxConcurrency,
      },
    };
    this.state.quotas = quotas;
  }

  private loadFromDisk(): void {
    try {
      if (fs.existsSync(this.cachePath)) {
        const raw = fs.readFileSync(this.cachePath, "utf-8");
        const parsed = JSON.parse(raw);
        this.state = { ...this.state, ...parsed };
      } else {
        this.rebuildGates();
      }
    } catch {
      this.rebuildGates();
    }
  }

  private saveToDisk(): void {
    try {
      fs.writeFileSync(this.cachePath, JSON.stringify(this.state, null, 2), "utf-8");
    } catch {}
  }
}
