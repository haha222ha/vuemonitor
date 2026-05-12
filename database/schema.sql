-- XHS365 Database Schema
-- PostgreSQL 16+

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- M01 用户与认证
-- ============================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    nickname VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    plan VARCHAR(20) NOT NULL DEFAULT 'free',
    plan_expires_at TIMESTAMP,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    email_notify_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    device_info VARCHAR(255),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ============================================================
-- M02 授权码与套餐
-- ============================================================

CREATE TABLE license_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(64) UNIQUE NOT NULL,
    plan VARCHAR(20) NOT NULL,
    duration_days SMALLINT NOT NULL,
    max_activations SMALLINT NOT NULL DEFAULT 1,
    current_activations SMALLINT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'unused',
    batch_id VARCHAR(64),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_license_codes_code ON license_codes(code);
CREATE INDEX idx_license_codes_status ON license_codes(status);

CREATE TABLE license_activations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    license_id UUID NOT NULL REFERENCES license_codes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_fingerprint VARCHAR(255),
    activated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- M03 Feature Gate
-- ============================================================

CREATE TABLE feature_gates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gate_key VARCHAR(100) UNIQUE NOT NULL,
    gate_name VARCHAR(200) NOT NULL,
    gate_type VARCHAR(20) NOT NULL,
    required_plan VARCHAR(20) NOT NULL,
    description TEXT,
    config JSONB DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE feature_gate_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gate_key VARCHAR(100) NOT NULL,
    used_at TIMESTAMP NOT NULL DEFAULT NOW(),
    detail JSONB DEFAULT '{}'
);

CREATE INDEX idx_feature_gate_usage_user_gate ON feature_gate_usage(user_id, gate_key);
CREATE INDEX idx_feature_gate_usage_used_at ON feature_gate_usage(used_at);

-- ============================================================
-- M04 商品与特征
-- ============================================================

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    platform_product_id VARCHAR(255) NOT NULL,
    product_name VARCHAR(500) NOT NULL,
    shop_name VARCHAR(255),
    category VARCHAR(100),
    image_url VARCHAR(500),
    product_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_collected_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, platform, platform_product_id)
);

CREATE INDEX idx_products_user_id ON products(user_id);
CREATE INDEX idx_products_platform ON products(platform);

CREATE TABLE product_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price DECIMAL(12, 2),
    original_price DECIMAL(12, 2),
    sales_count INTEGER,
    monthly_sales INTEGER,
    rating DECIMAL(3, 2),
    review_count INTEGER,
    favorite_count INTEGER,
    stock_status VARCHAR(20),
    extra_features JSONB DEFAULT '{}',
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    source VARCHAR(20) NOT NULL DEFAULT 'local',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_features_product_id ON product_features(product_id);
CREATE INDEX idx_product_features_collected_at ON product_features(collected_at);

-- ============================================================
-- M05 AI分析与报告
-- ============================================================

CREATE TABLE ai_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    analysis_type VARCHAR(50) NOT NULL,
    provider VARCHAR(30) NOT NULL,
    model VARCHAR(50) NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    result JSONB NOT NULL,
    confidence DECIMAL(3, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_analyses_user_id ON ai_analyses(user_id);
CREATE INDEX idx_ai_analyses_product_id ON ai_analyses(product_id);
CREATE INDEX idx_ai_analyses_type ON ai_analyses(analysis_type);

CREATE TABLE ai_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- M06 采集与调度
-- ============================================================

CREATE TABLE collect_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_type VARCHAR(30) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    target_type VARCHAR(30) NOT NULL,
    target_ids JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority SMALLINT NOT NULL DEFAULT 5,
    progress SMALLINT NOT NULL DEFAULT 0,
    result_summary JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_collect_tasks_user_id ON collect_tasks(user_id);
CREATE INDEX idx_collect_tasks_status ON collect_tasks(status);

CREATE TABLE collect_task_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES collect_tasks(id) ON DELETE CASCADE,
    target_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_collect_task_items_task_id ON collect_task_items(task_id);

-- ============================================================
-- M07 监控与通知
-- ============================================================

CREATE TABLE monitor_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    rule_name VARCHAR(200) NOT NULL,
    rule_type VARCHAR(30) NOT NULL,
    conditions JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at TIMESTAMP,
    trigger_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_monitor_rules_user_id ON monitor_rules(user_id);
CREATE INDEX idx_monitor_rules_product_id ON monitor_rules(product_id);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(30) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    related_id UUID,
    related_type VARCHAR(30),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(user_id, is_read);

-- ============================================================
-- M10 RBAC
-- ============================================================

CREATE TABLE rbac_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    data_scope VARCHAR(20) NOT NULL DEFAULT 'self',
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE rbac_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permission_key VARCHAR(100) UNIQUE NOT NULL,
    permission_name VARCHAR(200) NOT NULL,
    module VARCHAR(50) NOT NULL,
    action VARCHAR(30) NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE rbac_role_permissions (
    role_id UUID NOT NULL REFERENCES rbac_roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES rbac_permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE rbac_user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES rbac_roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- ============================================================
-- M21-B 云端采集代理池
-- ============================================================

CREATE TABLE proxy_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_name VARCHAR(100) UNIQUE NOT NULL,
    api_endpoint VARCHAR(500) NOT NULL,
    api_key_encrypted TEXT,
    protocol VARCHAR(10) NOT NULL DEFAULT 'http',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE proxy_pool (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID REFERENCES proxy_providers(id) ON DELETE SET NULL,
    ip VARCHAR(45) NOT NULL,
    port INTEGER NOT NULL,
    protocol VARCHAR(10) NOT NULL DEFAULT 'http',
    username VARCHAR(100),
    password_encrypted TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    health_score SMALLINT NOT NULL DEFAULT 100,
    last_checked_at TIMESTAMP,
    last_used_at TIMESTAMP,
    fail_count SMALLINT NOT NULL DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_proxy_pool_status ON proxy_pool(status);
CREATE INDEX idx_proxy_pool_health ON proxy_pool(health_score);

-- ============================================================
-- 风控事件
-- ============================================================

CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES collect_tasks(id) ON DELETE SET NULL,
    platform VARCHAR(20) NOT NULL,
    risk_type VARCHAR(30) NOT NULL,
    risk_level VARCHAR(10) NOT NULL DEFAULT 'medium',
    detail JSONB DEFAULT '{}',
    proxy_id UUID REFERENCES proxy_pool(id) ON DELETE SET NULL,
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_risk_events_platform ON risk_events(platform);
CREATE INDEX idx_risk_events_occurred_at ON risk_events(occurred_at);

-- ============================================================
-- 操作日志
-- ============================================================

CREATE TABLE admin_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    detail JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_admin_audit_logs_user_id ON admin_audit_logs(user_id);
CREATE INDEX idx_admin_audit_logs_created_at ON admin_audit_logs(created_at);

-- ============================================================
-- M12 修正 授权码表（对齐需求文档M12 §5）
-- 注意：license_codes表中 code→license_key, max_activations→max_devices
-- 新增 bound_user_id, bound_device_fingerprint 字段
-- ============================================================

-- ALTER license_codes: 添加需求文档M12规范字段
ALTER TABLE license_codes ADD COLUMN IF NOT EXISTS license_key VARCHAR(19) UNIQUE;
ALTER TABLE license_codes ADD COLUMN IF NOT EXISTS max_devices INTEGER DEFAULT 1;
ALTER TABLE license_codes ADD COLUMN IF NOT EXISTS bound_user_id UUID REFERENCES users(id);
ALTER TABLE license_codes ADD COLUMN IF NOT EXISTS bound_device_fingerprint VARCHAR(255);

-- 迁移已有code到license_key（如已有数据）
UPDATE license_codes SET license_key = code WHERE license_key IS NULL;

-- ============================================================
-- M13 用户配额
-- ============================================================

CREATE TABLE user_quotas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gate_key VARCHAR(100) NOT NULL,
    used_count INTEGER NOT NULL DEFAULT 0,
    limit_count INTEGER,
    period VARCHAR(20) NOT NULL DEFAULT 'daily',
    reset_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, gate_key, period)
);

CREATE INDEX idx_user_quotas_user_id ON user_quotas(user_id);

-- ============================================================
-- M14 Feature Engine — 匿名特征值
-- ============================================================

CREATE TABLE features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    growth_rate FLOAT,
    acceleration FLOAT,
    volatility FLOAT,
    competition_index FLOAT,
    lifecycle_stage VARCHAR(20),
    price FLOAT,
    sales_velocity FLOAT,
    is_anonymized BOOLEAN NOT NULL DEFAULT TRUE,
    calculated_at TIMESTAMP,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_features_user_id ON features(user_id);
CREATE INDEX idx_features_platform ON features(platform);
CREATE INDEX idx_features_category ON features(category);

-- ============================================================
-- M14 Feature Engine — 类目聚合统计
-- ============================================================

CREATE TABLE category_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    watch_count INTEGER,
    unique_products INTEGER,
    unique_users INTEGER,
    avg_growth_rate FLOAT,
    avg_volatility FLOAT,
    heat_index FLOAT,
    up_trend_ratio FLOAT,
    down_trend_ratio FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(category, platform, date)
);

CREATE INDEX idx_category_stats_category ON category_stats(category);
CREATE INDEX idx_category_stats_date ON category_stats(date);

-- ============================================================
-- M14 Feature Engine — 增强特征
-- ============================================================

CREATE TABLE enhanced_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    base_growth_rate FLOAT,
    enhanced_growth_rate FLOAT,
    market_share_percentile FLOAT,
    heat_trend VARCHAR(20),
    prediction_score FLOAT,
    risk_level VARCHAR(20),
    calculated_at TIMESTAMP
);

CREATE INDEX idx_enhanced_features_product_id ON enhanced_features(product_id);

-- ============================================================
-- M15 AI分析引擎 — 分析结果（正式表）
-- ============================================================

CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id VARCHAR(255),
    analysis_type VARCHAR(50) NOT NULL,
    input_snapshot JSONB,
    result JSONB NOT NULL,
    confidence FLOAT,
    model_used VARCHAR(100),
    prompt_version VARCHAR(50),
    input_tokens INTEGER,
    output_tokens INTEGER,
    duration_ms INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analysis_results_user_id ON analysis_results(user_id);
CREATE INDEX idx_analysis_results_type ON analysis_results(analysis_type);
CREATE INDEX idx_analysis_results_created_at ON analysis_results(created_at);

-- ============================================================
-- M15 AI分析引擎 — Prompt模板库
-- ============================================================

CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    template TEXT NOT NULL,
    output_schema JSONB,
    model VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompt_templates_type ON prompt_templates(analysis_type);

-- ============================================================
-- M17 匿名聚合 — 聚合审计
-- ============================================================

CREATE TABLE aggregation_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    sample_users INTEGER,
    min_threshold INTEGER,
    passed_threshold BOOLEAN,
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_aggregation_audit_date ON aggregation_audit(date);

-- ============================================================
-- M18 商业化 — 会员套餐
-- ============================================================

CREATE TABLE membership_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    ai_quota INTEGER NOT NULL DEFAULT 0,
    task_limit INTEGER NOT NULL DEFAULT 5,
    max_projects INTEGER NOT NULL DEFAULT 10,
    features JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- M18 商业化 — 用户订阅
-- ============================================================

CREATE TABLE user_membership (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES membership_plans(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1
);

CREATE INDEX idx_user_membership_user_id ON user_membership(user_id);
CREATE INDEX idx_user_membership_plan_id ON user_membership(plan_id);

-- ============================================================
-- M18 商业化 — 商品动态指标
-- ============================================================

CREATE TABLE product_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    favorites INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    add_to_cart INTEGER DEFAULT 0,
    sales_estimate INTEGER DEFAULT 0,
    trend_score FLOAT,
    ai_score FLOAT,
    snapshot_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_metrics_product_id ON product_metrics(product_id);
CREATE INDEX idx_product_metrics_snapshot_time ON product_metrics(snapshot_time);

-- ============================================================
-- M18 商业化 — AI爆品预测结果
-- ============================================================

CREATE TABLE ai_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    score FLOAT NOT NULL,
    label VARCHAR(20) NOT NULL,
    breakdown JSONB,
    reason TEXT,
    model_version VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_predictions_product_id ON ai_predictions(product_id);
CREATE INDEX idx_ai_predictions_score ON ai_predictions(score);

-- ============================================================
-- M18 商业化 — 采集任务（M18 §15.6 独立于collect_tasks）
-- ============================================================

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    keyword VARCHAR(255),
    schedule_type VARCHAR(20) NOT NULL DEFAULT 'once',
    cron_expression VARCHAR(50),
    status SMALLINT NOT NULL DEFAULT 0,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- ============================================================
-- M18 商业化 — 任务日志
-- ============================================================

CREATE TABLE task_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    log TEXT,
    duration INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_logs_task_id ON task_logs(task_id);

-- ============================================================
-- M18 商品ID映射（本地↔云端）
-- ============================================================

CREATE TABLE product_id_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    local_product_id VARCHAR(255) UNIQUE NOT NULL,
    cloud_product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_id_mapping_user_id ON product_id_mapping(user_id);
CREATE INDEX idx_product_id_mapping_cloud ON product_id_mapping(cloud_product_id);
CREATE INDEX idx_product_id_mapping_sync_status ON product_id_mapping(sync_status);

-- ============================================================
-- M18 数据库运行时配置
-- ============================================================

CREATE TABLE db_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
