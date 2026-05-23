export interface Product {
  id: string;
  platform: string;
  platform_product_id: string;
  product_name: string;
  shop_name: string | null;
  category: string | null;
  category_id: string | null;
  image_url: string | null;
  product_url: string | null;
  is_active: number;
  last_collected_at: string | null;
  created_at: string;
  updated_at: string;
  latest_feature?: ProductFeature;
  _ranking?: Record<string, any>;
  _benchmark?: Record<string, any>;
  ref?: string;
  title?: string;
  store_name?: string;
  growth_24h?: Growth24h | null;
}

export interface Growth24h {
  sales_delta: number;
  sales_pct: number | null;
  revenue_delta: number | null;
}

export interface WeekOverWeekMetric {
  this_week: number;
  last_week: number;
  change_pct: number | null;
}

export interface WeekOverWeek {
  products: WeekOverWeekMetric;
  collects: WeekOverWeekMetric;
  ai_analyses: WeekOverWeekMetric;
}

export interface ProductFeature {
  id: string;
  product_id: string;
  price: number | null;
  original_price: number | null;
  sales_count: number | null;
  monthly_sales: number | null;
  rating: number | null;
  review_count: number | null;
  favorite_count: number | null;
  stock_status: string | null;
  extra_features: Record<string, unknown>;
  collected_at: string;
  source: string;
  created_at: string;
}

export interface MonitorRule {
  id: string;
  product_id: string;
  rule_name: string;
  rule_type: string;
  conditions: Record<string, unknown>;
  is_active: number;
  last_triggered_at: string | null;
  trigger_count: number;
  created_at: string;
}

export interface AIAnalysis {
  id: string;
  product_id: string;
  analysis_type: string;
  result: Record<string, unknown>;
  confidence: number;
  analyzed_at: string;
  created_at?: string;
  provider?: string;
  model?: string;
  status?: string;
}

export interface AlertEvent {
  id: string;
  rule_id: string;
  product_id: string;
  event_type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  title: string;
  details: Record<string, unknown>;
  is_acknowledged: boolean;
  created_at: string;
}

export interface Team {
  id: string;
  name: string;
  member_count: number;
  created_at: string;
}

export interface TeamMember {
  id: string;
  team_id: string;
  user_id: string;
  role: string;
  joined_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface SecurityLog {
  id: string;
  event_type: string;
  severity: string;
  description: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface OpportunityItem {
  product_id: string;
  product_name: string;
  score: number;
  reason: string;
  category: string | undefined;
}

export interface HeatmapItem {
  category: string;
  count: number;
  avg_price: number;
  avg_sales: number;
  heat_score: number;
  heat_level: "hot" | "warm" | "cold";
  product_count?: number;
  avg_rating?: number;
}

export interface AIRecommendation {
  id: string;
  type: string;
  title: string;
  description: string;
  confidence: number;
  data: Record<string, unknown>;
  created_at: string;
  product_id?: string;
  event_id?: string;
  category?: string;
  product_name?: string;
  reason?: string;
  metric?: Record<string, any>;
}

export interface AIReport {
  id: string;
  title: string;
  report_type: string;
  product_ids: string[];
  content: Record<string, unknown>;
  created_at: string;
  status?: string;
}
