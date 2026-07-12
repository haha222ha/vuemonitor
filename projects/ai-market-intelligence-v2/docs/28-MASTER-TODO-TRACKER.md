# 28 — V2 主 TODO 跟踪器（T0 → GA）

> **用途**：单页勾选全部需求；Agent / 运维按 `[ ]` → `[x]` 更新。  
> **关联**：`20-REQUIREMENTS-V2.2-ROLLOUT.md`、`25-GLOBAL-IMPLEMENTATION-GAPS.md`、`27-RETENTION-PG-STICKINESS-REQUIREMENTS.md`、`26-T0-SHADOW-RUNBOOK.md`

**图例**：`[x]` 已完成 · `[~]` 进行中 · `[ ]` 未开始 · `[-]` 跳过/延期

---

## Phase 0 — 文档与 Lab（已完成基线）

- [x] doc 00–26 索引与 V2.2 需求
- [x] Lab 44 tests + insight_portal 原型
- [x] cloud-stubs → xhs-cloud 合并骨架

---

## Phase T0 — Shadow 7 天（当前焦点）

### 运维 / 部署

- [x] `08_insight_v2_tables.sql` 上云
- [x] `xhs-insight-report.timer` 02:30
- [x] Admin LLM 配置页（admin.xhs365.cn/insight-llm）
- [x] `INSIGHT_USE_LLM` / PG settings 真 LLM
- [x] `26-T0-SHADOW-RUNBOOK.md`
- [ ] **09_retention_pg_schema.sql** 上云（pull 后 psql）
- [ ] Shadow **D1–D7** journal 无 ERROR
- [ ] 云主机 pull 最新 + host-update

### 后端 / 双轨

- [x] `legacy_dual`：在期老月卡 insight + legacy zip
- [x] `entitlements_v2` + `legacy_gate` + `member_entitlements`
- [x] `insight_routes` library/view
- [x] `payment_service._payment_fulfillment_note`（W2-1）
- [x] Shadow pipeline `insight_pipeline.py`

### 前端

- [x] `member_insight.js` + AI Tab 骨架
- [ ] 老月卡 **双 Tab E2E**（Ctrl+F5 + 重登）
- [ ] AI Tab 预览 iframe 有 Shadow 报告

### 验收脚本

- [x] `insight_shadow_smoke.py` / `.sh`（W1-5）
- [x] `test_payment_entitlements_note.py`（W2-1）
- [ ] 云主机跑 smoke：`XHS_SMOKE_EXPECT=legacy_dual`

### T0 出口标准

- [ ] 7 天 timer 成功率 100%
- [ ] smoke 全 PASS（profile + library + view）
- [ ] LLM mode=on 至少 1 天有 4+ 类目 HTML

---

## Phase T1 — 小流量上线（`XHS_V2_LAUNCH=1`）

### 支付 / 套餐

- [ ] `XHS_V2_LAUNCH=1` 仅售 `insight_*` SKU
- [x] 支付回调写 entitlements JSON note
- [ ] admin 发 insight 体验码 UI
- [ ] 新购 E2E：支付 → profile `insight_only`

### API / 配额

- [ ] `POST /member/insight/generate` + 配额原子扣减
- [ ] Cache-First 读 `insight_report_cache`（REQ-CACHE-002）
- [ ] Watchlist PG API（`member_insight_watchlist`）
- [ ] nginx 限流 insight 10 req/min

### PG 留存 P0（doc 27）

- [x] `daily_category_metrics` 表 + 聚合脚本
- [x] pipeline 写 metrics + LLM `trend_7d`
- [x] `user_behavior` 表 + view 埋点
- [ ] 定时 `aggregate_daily_category_metrics` systemd（02:00）
- [ ] 机会雷达 API / 会员横幅（REQ-RET-001）
- [ ] 体验码 Day1–3 SOP（REQ-RET-040～042）

### 文档

- [ ] `06-API-SPEC-V2.md` 正式版
- [ ] doc 20 REQ-PROD-* 状态全量同步

---

## Phase T2 — 留存增强

- [ ] pgvector `category_embeddings` + 相似类目 Prompt
- [ ] 「为你推荐」基于 user_behavior
- [ ] 工作流进货回填 + 30 天提醒
- [ ] 用户健康度评分 + 流失预警
- [ ] Redis L1 缓存（可选）

---

## Phase GA — Legacy Sunset

- [ ] PC ProductAnalyzer 合并（xhs_shelf_time 仓库）
- [ ] PC 安装包 + version.json 门控
- [ ] 生产报告路径 `{user_id}/{date}/{category}/`
- [ ] 最后 Legacy expires_at 后停 `xhs-daily-report.timer`
- [ ] 监控告警：timer / LLM 预算 / 生成延迟

---

## 按轨道速查

| 轨道 | 进行中 | 下一项 |
|------|--------|--------|
| **运维** | Shadow D7 | pull + smoke + 09 SQL |
| **后端** | trend_7d | generate API + cache |
| **前端** | 双 Tab 验证 | 机会雷达 UI |
| **数据** | daily_metrics | 02:00 timer |
| **PC** | cloud_client 补丁草案 | 合并 xhs_shelf_time |

---

## 云主机一键（每次 push 后）

```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main \
  && rsync -a /opt/vuemonitor/xhs-cloud/ /opt/xhs-cloud/ --delete --exclude data --exclude venv --exclude .env \
  && cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh
```

**新增迁移（T1 前）**：

```bash
psql "$XHS_DATABASE_URL" -f /opt/xhs-cloud/cloud_deploy/database/09_retention_pg_schema.sql
```

**验收**：

```bash
export XHS_MEMBER_TOKEN='...'   # localStorage xhs_member_token
export XHS_SMOKE_EXPECT=legacy_dual
bash /opt/xhs-cloud/cloud_deploy/scripts/insight_shadow_smoke.sh
```

---

## 更新日志

| 日期 | 变更 |
|------|------|
| 2026-07-12 | 初版：合并战略报告 → doc 27；本跟踪器；T0 smoke + PG-1 代码 |
