import * as crypto from "crypto";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 12;
const AUTH_TAG_LENGTH = 16;
const SALT_LENGTH = 32;
const ITERATIONS = 100000;

const SENSITIVE_FIELDS = new Set([
  "password", "token", "secret", "api_key", "private_key",
  "access_token", "refresh_token", "cookie", "authorization",
  "credit_card", "phone", "email", "id_card",
]);

let masterKey: Buffer | null = null;
let _keySalt: Buffer | null = null;

function deriveKey(passphrase: string, salt: Buffer): Buffer {
  return crypto.pbkdf2Sync(passphrase, salt, ITERATIONS, 32, "sha512");
}

function getKeyFilePath(): string {
  const dataDir = path.join(process.cwd(), "data");
  if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });
  return path.join(dataDir, ".enc_key");
}

function loadOrGenerateKeySalt(): { passphrase: string; salt: Buffer } {
  const keyFile = getKeyFilePath();
  const machineId = getMachineFingerprint();

  if (fs.existsSync(keyFile)) {
    try {
      const stored = JSON.parse(fs.readFileSync(keyFile, "utf-8"));
      if (stored.salt && stored.version === 2) {
        return {
          passphrase: machineId,
          salt: Buffer.from(stored.salt, "base64"),
        };
      }
    } catch {}
  }

  const salt = crypto.randomBytes(SALT_LENGTH);
  try {
    fs.writeFileSync(keyFile, JSON.stringify({
      salt: salt.toString("base64"),
      version: 2,
      created_at: new Date().toISOString(),
    }), { mode: 0o600 });
  } catch {}

  return { passphrase: machineId, salt };
}

export function initEncryption(passphrase?: string): void {
  if (masterKey) return;
  const machineId = getMachineFingerprint();

  if (passphrase) {
    _keySalt = _keySalt || Buffer.from(machineId, "hex");
    masterKey = deriveKey(passphrase + machineId, _keySalt!);
  } else {
    const { passphrase: derivedPass, salt } = loadOrGenerateKeySalt();
    _keySalt = salt;
    masterKey = deriveKey(derivedPass, salt);
  }
}

export function encryptField(plaintext: string): string {
  if (!masterKey) initEncryption();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, masterKey!, iv);
  const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return Buffer.concat([iv, authTag, encrypted]).toString("base64");
}

export function decryptField(ciphertext: string): string {
  if (!masterKey) initEncryption();
  const data = Buffer.from(ciphertext, "base64");
  const iv = data.subarray(0, IV_LENGTH);
  const authTag = data.subarray(IV_LENGTH, IV_LENGTH + AUTH_TAG_LENGTH);
  const encrypted = data.subarray(IV_LENGTH + AUTH_TAG_LENGTH);
  const decipher = crypto.createDecipheriv(ALGORITHM, masterKey!, iv);
  decipher.setAuthTag(authTag);
  return decipher.update(encrypted) + decipher.final("utf8");
}

export function isSensitiveField(fieldName: string): boolean {
  return SENSITIVE_FIELDS.has(fieldName.toLowerCase());
}

export function encryptRow(row: Record<string, any>): Record<string, any> {
  const encrypted: Record<string, any> = {};
  for (const [key, value] of Object.entries(row)) {
    if (value != null && typeof value === "string" && isSensitiveField(key)) {
      encrypted[key] = encryptField(value);
      encrypted[`_${key}_enc`] = 1;
    } else {
      encrypted[key] = value;
    }
  }
  return encrypted;
}

export function decryptRow(row: Record<string, any>): Record<string, any> {
  const decrypted: Record<string, any> = {};
  for (const [key, value] of Object.entries(row)) {
    if (key.endsWith("_enc")) continue;
    if (row[`_${key}_enc`] === 1 && typeof value === "string") {
      try {
        decrypted[key] = decryptField(value);
      } catch {
        decrypted[key] = value;
      }
    } else {
      decrypted[key] = value;
    }
  }
  return decrypted;
}

function getMachineFingerprint(): string {
  try {
    const cpus = os.cpus();
    const totalMem = os.totalmem();
    const hostname = os.hostname();
    const raw = `${hostname}:${cpus.length}:${totalMem}`;
    return crypto.createHash("sha256").update(raw).digest("hex").substring(0, 32);
  } catch {
    throw new Error("Cannot generate machine fingerprint for encryption");
  }
}

export function hashValue(value: string): string {
  return crypto.createHash("sha256").update(value).digest("hex");
}

export function generateSecureToken(length: number = 32): string {
  return crypto.randomBytes(length).toString("hex");
}
