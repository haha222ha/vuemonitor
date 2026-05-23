import { safeStorage } from "electron";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";
import { logger } from "../logger/logger";

const SECURE_STORE_FILE = "secure-store.enc";
const ENCODING = "utf-8";

class SecureStorage {
  private storePath: string;
  private cache: Map<string, string> = new Map();
  private loaded: boolean = false;

  constructor() {
    this.storePath = path.join(app.getPath("userData"), SECURE_STORE_FILE);
  }

  private load(): void {
    if (this.loaded) return;
    this.loaded = true;

    if (!fs.existsSync(this.storePath)) return;

    try {
      const raw = fs.readFileSync(this.storePath, ENCODING);
      const entries = JSON.parse(raw) as Record<string, string>;
      for (const [key, encryptedBase64] of Object.entries(entries)) {
        try {
          if (safeStorage.isEncryptionAvailable()) {
            const buffer = Buffer.from(encryptedBase64, "base64");
            this.cache.set(key, safeStorage.decryptString(buffer));
          } else {
            this.cache.set(key, encryptedBase64);
          }
        } catch (err) {
          logger.error("SecureStorage", `decrypt failed for key ${key}: ${err}`);
        }
      }
    } catch (err) {
      logger.error("SecureStorage", `load failed: ${err}`);
    }
  }

  private save(): void {
    const entries: Record<string, string> = {};
    for (const [key, value] of this.cache.entries()) {
      try {
        if (safeStorage.isEncryptionAvailable()) {
          const encrypted = safeStorage.encryptString(value);
          entries[key] = encrypted.toString("base64");
        } else {
          entries[key] = value;
        }
      } catch (err) {
        logger.error("SecureStorage", `encrypt failed for key ${key}: ${err}`);
      }
    }
    try {
      fs.writeFileSync(this.storePath, JSON.stringify(entries), ENCODING);
    } catch (err) {
      logger.error("SecureStorage", `save failed: ${err}`);
    }
  }

  get(key: string): string | null {
    this.load();
    return this.cache.get(key) ?? null;
  }

  set(key: string, value: string): void {
    this.load();
    this.cache.set(key, value);
    this.save();
  }

  delete(key: string): void {
    this.load();
    this.cache.delete(key);
    this.save();
  }

  clear(): void {
    this.cache.clear();
    this.loaded = true;
    this.save();
  }
}

let instance: SecureStorage | null = null;

export function getSecureStorage(): SecureStorage {
  if (!instance) {
    instance = new SecureStorage();
  }
  return instance;
}
