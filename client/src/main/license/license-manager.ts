import * as crypto from "crypto";
import * as os from "os";
import * as fs from "fs";
import * as path from "path";

export interface LicenseInfo {
  licenseKey: string;
  deviceId: string;
  plan: "free" | "pro" | "premium" | "enterprise";
  expiresAt: string | null;
  activatedAt: string;
  features: string[];
  machineFingerprint: string;
  isValid: boolean;
  lastVerified: string;
}

export interface ActivationResult {
  success: boolean;
  license?: LicenseInfo;
  error?: string;
}

export interface VerificationResult {
  valid: boolean;
  plan: string;
  expiresAt: string | null;
  features: string[];
  error?: string;
}

const LICENSE_FILE = "license.dat";
const PLAN_FEATURES: Record<string, string[]> = {
  free: ["gate:monitor:add", "gate:monitor:manual_refresh", "gate:ai:basic_analysis"],
  pro: [
    "gate:monitor:add", "gate:monitor:manual_refresh", "gate:monitor:auto_refresh",
    "gate:ai:basic_analysis", "gate:ai:trend_score", "gate:monitor:export",
  ],
  premium: [
    "gate:monitor:add", "gate:monitor:manual_refresh", "gate:monitor:auto_refresh",
    "gate:ai:basic_analysis", "gate:ai:trend_score", "gate:ai:prediction",
    "gate:ai:risk_warning", "gate:monitor:export",
  ],
  enterprise: [
    "gate:monitor:add", "gate:monitor:manual_refresh", "gate:monitor:auto_refresh",
    "gate:ai:basic_analysis", "gate:ai:trend_score", "gate:ai:prediction",
    "gate:ai:risk_warning", "gate:monitor:export", "gate:admin:dashboard",
  ],
};

const PLAN_QUOTAS: Record<string, Record<string, number>> = {
  free: { maxProducts: 10, maxConcurrent: 2, maxScheduleTasks: 0, aiCallsPerDay: 5 },
  pro: { maxProducts: 100, maxConcurrent: 5, maxScheduleTasks: 20, aiCallsPerDay: 50 },
  premium: { maxProducts: 500, maxConcurrent: 8, maxScheduleTasks: 100, aiCallsPerDay: 200 },
  enterprise: { maxProducts: -1, maxConcurrent: 10, maxScheduleTasks: -1, aiCallsPerDay: -1 },
};

export class LicenseManager {
  private licensePath: string;
  private cachedLicense: LicenseInfo | null = null;
  private verificationInterval: ReturnType<typeof setInterval> | null = null;

  constructor(dataDir?: string) {
    const dir = dataDir || path.join(process.cwd(), "data");
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    this.licensePath = path.join(dir, LICENSE_FILE);
  }

  getMachineFingerprint(): string {
    const hostname = os.hostname();
    const cpus = os.cpus();
    const cpuModel = cpus.length > 0 ? cpus[0].model : "unknown";
    const totalMem = os.totalmem();
    const platform = os.platform();
    const arch = os.arch();

    const raw = `${hostname}|${cpuModel}|${totalMem}|${platform}|${arch}`;
    return crypto.createHash("sha256").update(raw).digest("hex").substring(0, 32);
  }

  generateDeviceId(): string {
    const fingerprint = this.getMachineFingerprint();
    const random = crypto.randomBytes(8).toString("hex");
    return crypto.createHash("sha256").update(fingerprint + random).digest("hex").substring(0, 24);
  }

  async activate(licenseKey: string, serverUrl?: string): Promise<ActivationResult> {
    const cleanKey = licenseKey.trim().toUpperCase();

    if (!this.validateKeyFormat(cleanKey)) {
      return { success: false, error: "授权码格式无效" };
    }

    const deviceId = this.generateDeviceId();
    const fingerprint = this.getMachineFingerprint();

    if (serverUrl) {
      try {
        const result = await this.verifyWithServer(cleanKey, deviceId, fingerprint, serverUrl);
        if (!result.valid) {
          return { success: false, error: result.error || "服务端验证失败" };
        }

        const license: LicenseInfo = {
          licenseKey: cleanKey,
          deviceId,
          plan: result.plan as LicenseInfo["plan"],
          expiresAt: result.expiresAt,
          activatedAt: new Date().toISOString(),
          features: result.features,
          machineFingerprint: fingerprint,
          isValid: true,
          lastVerified: new Date().toISOString(),
        };

        this.saveLicense(license);
        this.cachedLicense = license;
        this.startPeriodicVerification(serverUrl);

        return { success: true, license };
      } catch (err) {
        return { success: false, error: `服务端验证异常: ${(err as Error).message}` };
      }
    }

    const offlineResult = this.verifyOffline(cleanKey);
    if (!offlineResult.valid) {
      return { success: false, error: offlineResult.error || "离线验证失败" };
    }

    const license: LicenseInfo = {
      licenseKey: cleanKey,
      deviceId,
      plan: offlineResult.plan as LicenseInfo["plan"],
      expiresAt: offlineResult.expiresAt,
      activatedAt: new Date().toISOString(),
      features: offlineResult.features,
      machineFingerprint: fingerprint,
      isValid: true,
      lastVerified: new Date().toISOString(),
    };

    this.saveLicense(license);
    this.cachedLicense = license;

    return { success: true, license };
  }

  private validateKeyFormat(key: string): boolean {
    return /^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(key) ||
           /^[A-Z0-9]{16,32}$/.test(key);
  }

  private verifyOffline(key: string): VerificationResult {
    const decoded = this.decodeKey(key);
    if (!decoded) {
      return { valid: false, plan: "free", expiresAt: null, features: PLAN_FEATURES.free, error: "无效的授权码" };
    }

    if (decoded.expiresAt && new Date(decoded.expiresAt) < new Date()) {
      return { valid: false, plan: "free", expiresAt: null, features: PLAN_FEATURES.free, error: "授权码已过期" };
    }

    return {
      valid: true,
      plan: decoded.plan,
      expiresAt: decoded.expiresAt,
      features: PLAN_FEATURES[decoded.plan] || PLAN_FEATURES.free,
    };
  }

  private decodeKey(key: string): { plan: string; expiresAt: string | null } | null {
    try {
      const cleanKey = key.replace(/-/g, "");
      if (cleanKey.length < 16) return null;

      const planCode = cleanKey.substring(0, 2);
      const planMap: Record<string, string> = { PR: "pro", PM: "premium", EN: "enterprise" };
      const plan = planMap[planCode] || "free";

      const checksum = cleanKey.substring(cleanKey.length - 4);
      const payload = cleanKey.substring(0, cleanKey.length - 4);
      const expectedChecksum = crypto.createHash("sha256").update(payload + "xhs_monitor_2024").digest("hex").substring(0, 4).toUpperCase();

      if (checksum !== expectedChecksum) return null;

      return { plan, expiresAt: null };
    } catch {
      return null;
    }
  }

  private async verifyWithServer(
    key: string,
    deviceId: string,
    fingerprint: string,
    serverUrl: string
  ): Promise<VerificationResult> {
    try {
      const axios = require("axios");
      const { data } = await axios.post(`${serverUrl}/api/v1/license/verify`, {
        license_key: key,
        device_id: deviceId,
        machine_fingerprint: fingerprint,
        app_version: "1.0.0",
      });

      if (data.valid) {
        return {
          valid: true,
          plan: data.plan || "free",
          expiresAt: data.expires_at || null,
          features: data.features || PLAN_FEATURES[data.plan] || PLAN_FEATURES.free,
        };
      }

      return {
        valid: false,
        plan: "free",
        expiresAt: null,
        features: PLAN_FEATURES.free,
        error: data.message || "验证失败",
      };
    } catch (err) {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      const message = axiosErr.response?.data?.message || (err as Error).message;
      return {
        valid: false,
        plan: "free",
        expiresAt: null,
        features: PLAN_FEATURES.free,
        error: message,
      };
    }
  }

  private startPeriodicVerification(serverUrl: string): void {
    if (this.verificationInterval) {
      clearInterval(this.verificationInterval);
    }

    this.verificationInterval = setInterval(async () => {
      await this.periodicCheck(serverUrl);
    }, 30 * 60 * 1000);
  }

  private async periodicCheck(serverUrl: string): Promise<void> {
    const license = this.getCurrentLicense();
    if (!license || !license.isValid) return;

    try {
      const result = await this.verifyWithServer(
        license.licenseKey,
        license.deviceId,
        license.machineFingerprint,
        serverUrl
      );

      if (!result.valid) {
        license.isValid = false;
        license.lastVerified = new Date().toISOString();
        this.saveLicense(license);
        this.cachedLicense = license;
        return;
      }

      license.plan = result.plan as LicenseInfo["plan"];
      license.features = result.features;
      license.expiresAt = result.expiresAt;
      license.isValid = true;
      license.lastVerified = new Date().toISOString();
      this.saveLicense(license);
      this.cachedLicense = license;
    } catch {}
  }

  getCurrentLicense(): LicenseInfo | null {
    if (this.cachedLicense) return this.cachedLicense;
    return this.loadLicense();
  }

  getPlan(): string {
    const license = this.getCurrentLicense();
    return license?.isValid ? license.plan : "free";
  }

  getFeatures(): string[] {
    const license = this.getCurrentLicense();
    if (!license?.isValid) return PLAN_FEATURES.free;
    return license.features;
  }

  getQuotas(): Record<string, number> {
    const plan = this.getPlan();
    return PLAN_QUOTAS[plan] || PLAN_QUOTAS.free;
  }

  checkFeature(gateKey: string): boolean {
    return this.getFeatures().includes(gateKey);
  }

  isExpired(): boolean {
    const license = this.getCurrentLicense();
    if (!license?.expiresAt) return false;
    return new Date(license.expiresAt) < new Date();
  }

  deactivate(): boolean {
    this.cachedLicense = null;
    if (this.verificationInterval) {
      clearInterval(this.verificationInterval);
      this.verificationInterval = null;
    }
    try {
      if (fs.existsSync(this.licensePath)) {
        fs.unlinkSync(this.licensePath);
      }
      return true;
    } catch {
      return false;
    }
  }

  private saveLicense(license: LicenseInfo): void {
    const encrypted = this.encrypt(JSON.stringify(license));
    fs.writeFileSync(this.licensePath, encrypted, "utf-8");
  }

  private loadLicense(): LicenseInfo | null {
    try {
      if (!fs.existsSync(this.licensePath)) return null;
      const encrypted = fs.readFileSync(this.licensePath, "utf-8");
      const decrypted = this.decrypt(encrypted);
      const license = JSON.parse(decrypted) as LicenseInfo;

      if (license.expiresAt && new Date(license.expiresAt) < new Date()) {
        license.isValid = false;
      }

      this.cachedLicense = license;
      return license;
    } catch {
      return null;
    }
  }

  private encrypt(text: string): string {
    const key = crypto.createHash("sha256").update("xhs-monitor-license-key-2024").digest();
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv("aes-256-cbc", key, iv);
    let encrypted = cipher.update(text, "utf-8", "hex");
    encrypted += cipher.final("hex");
    return iv.toString("hex") + ":" + encrypted;
  }

  private decrypt(encryptedText: string): string {
    const key = crypto.createHash("sha256").update("xhs-monitor-license-key-2024").digest();
    const parts = encryptedText.split(":");
    const iv = Buffer.from(parts[0], "hex");
    const encrypted = parts[1];
    const decipher = crypto.createDecipheriv("aes-256-cbc", key, iv);
    let decrypted = decipher.update(encrypted, "hex", "utf-8");
    decrypted += decipher.final("utf-8");
    return decrypted;
  }

  destroy(): void {
    if (this.verificationInterval) {
      clearInterval(this.verificationInterval);
    }
    this.cachedLicense = null;
  }
}

export const licenseManager = new LicenseManager();
