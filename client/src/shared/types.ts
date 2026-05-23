export interface Product {
  id: string;
  platform: string;
  platform_product_id: string;
  product_name: string;
  category_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  [key: string]: unknown;
}

export interface ProductFeature {
  id: string;
  product_id: string;
  likes: number;
  comments: number;
  shares: number;
  collects: number;
  sold: number;
  price: number;
  collected_at: string;
  [key: string]: unknown;
}

export interface AIAnalysis {
  id: string;
  product_id: string;
  analysis_type: string;
  result: Record<string, unknown>;
  confidence: number;
  analyzed_at: string;
}

export interface MonitorRule {
  id: string;
  product_id: string;
  rule_name: string;
  rule_type: string;
  conditions: Record<string, unknown>;
  is_active: boolean;
  trigger_count: number;
  created_at: string;
  [key: string]: unknown;
}

export interface LocalNotification {
  id: string;
  type: string;
  title: string;
  content: string;
  is_read: boolean;
  related_id: string | null;
  related_type: string;
  created_at: string;
  source: "local" | "server";
}

export interface Category {
  id: string;
  name: string;
  icon: string | null;
  color: string | null;
  sort_order: number;
  parent_id: string | null;
  product_count: number;
  created_at: string | null;
}

export interface CollectStatus {
  isRunning: boolean;
  activeCount: number;
  queueLength: number;
  concurrency: number;
  resourceUsage: Record<string, unknown>;
  isPaused: boolean;
  riskStats: Record<string, unknown>;
}

export interface SyncStatus {
  isSyncing: boolean;
  lastSyncAt: string | null;
  pendingCount: number;
  errorCount: number;
}

export interface LicenseInfo {
  plan: string;
  features: Record<string, boolean>;
  quotas: Record<string, number>;
}

export interface OfflineStatus {
  isOnline: boolean;
  lastCheckedAt: string | null;
  pendingOperations: number;
}
