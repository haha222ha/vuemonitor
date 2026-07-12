# 28 — V2 主 TODO 跟踪器（T0 → GA）

> **用途**：单页勾选全部需求；Agent / 运维按 `[ ]` → `[x]` 更新。  
> **关联**：`20-REQUIREMENTS-V2.2-ROLLOUT.md`、`25-GLOBAL-IMPLEMENTATION-GAPS.md`、`27-RETENTION-PG-STICKINESS-REQUIREMENTS.md`、`26-T0-SHADOW-RUNBOOK.md`  
> **一键部署**：`29-V2-ONECLICK-DEPLOY-RUNBOOK.md` → `v2-oneclick-deploy.sh`

**图例**：`[x]` 已完成 · `[~]` 进行中 · `[ ]` 未开始 · `[-]` 跳过/延期

---

## Phase 0 — 文档与 Lab（已完成基线）

- [x] doc 00–26 索引与 V2.2 需求
- [x] Lab 44 tests + insight_portal 原型
- [x] cloud-stubs → xhs-cloud 合并骨架

---

## Phase T0 — Shadow 7 天

### 运维 / 部署

- [x] `08_insight_v2_tables.sql` 上云
- [x] `xhs-insight-report.timer` 02:30
- [x] Admin LLM 配置页（admin.xhs365.cn/insight-llm）
- [x] `INSIGHT_USE_LLM` / PG settings 真 LLM
- [x] `26-T0-SHADOW-RUNBOOK.md`
- [x] **09/10 PG schema** 纳入一键脚本
- [~] Shadow **D1–D7** journal 无 ERROR（`shadow_t0_health_check.sh` 自动验）
- [x] 云主机 pull + host-update（`v2-oneclick-deploy.sh`）
- [x] 云主机 smoke **8/8 PASS**（zzll1234 legacy_dual）

### 后端 / 双轨

- [x] `legacy_dual`：在期老月卡 insight + legacy zip
- [x] `entitlements_v2` + `legacy_gate` + `member_entitlements`
- [x] `insight_routes` library/view/radar/generate/watchlist/recommendations
- [x] `payment_service._payment_fulfillment_note`（W2-1）
- [x] Shadow pipeline `insight_pipeline.py` + L1 cache

### 前端

- [x] `member_insight.js` + AI Tab E2E
- [x] 机会雷达 API + 会员横幅 UI

### 验收脚本

- [x] `insight_shadow_smoke.py` / `.sh`
- [x] `shadow_t0_health_check.sh`（T0 出口自动验）
- [x] 云主机 smoke **8/8 PASS**

### T0 出口标准

- [~] 7 天 timer 成功率 100%（需满 7 天实跑；脚本验 journal）
- [x] smoke 全 PASS
- [~] LLM on 4+ 类目/天（脚本验 pipeline_summary.json）

---

## Phase T1 — 小流量上线（`XHS_V2_LAUNCH=1`）

### 支付 / 套餐

- [x] `XHS_V2_LAUNCH=1` 代码就绪（`.env` 设 1 即仅 insight SKU）
- [x] `get_plan()` 支持 `insight_*` 下单
- [x] 支付回调写 entitlements JSON note
- [x] admin **AI 情报体验码**（PickMemberView `experience_insight`）
- [~] 新购 E2E：支付 → profile `insight_only`（待 T1 开 `XHS_V2_LAUNCH=1` 后验）

### API / 配额

- [x] `POST /member/insight/generate` + 配额原子扣减（fix user_id）
- [x] L1 `insight_report_cache` 批处理去重（pipeline）
- [x] Watchlist GET/PUT
- [x] nginx insight 限流 10 req/min（`monitor.conf` + snippet）

### PG 留存 P0（doc 27）

- [x] `daily_category_metrics` + 聚合脚本
- [x] pipeline metrics + `trend_7d`
- [x] `user_behavior` + 埋点
- [x] `xhs-aggregate-metrics.timer` 02:00
- [x] 机会雷达 API + 横幅 UI
- [~] 体验码 Day1–3 SOP（运营文档，非代码）

---

## Phase T2 — 留存增强

- [x] pgvector schema `10_pgvector_embeddings.sql`（embedding 批处理待接）
- [x] `GET /member/insight/recommendations`（user_behavior 骨架）
- [ ] 工作流进货回填 + 30 天提醒
- [ ] 用户健康度评分 + 流失预警
- [ ] Redis L1 缓存（可选）

---

## Phase GA — Legacy Sunset

- [ ] PC ProductAnalyzer 合并（xhs_shelf_time 仓库）
- [ ] PC 安装包 + version.json 门控
- [ ] 生产报告路径 `{user_id}/{date}/{category}/`
- [x] `disable_legacy_report_timer.sh` + `XHS_LEGACY_ZIP_GENERATION=0`
- [~] 监控告警：timer / LLM 预算（`shadow_t0_health_check.sh` 部分覆盖）

---

## 按轨道速查

| 轨道 | 状态 | 下一项 |
|------|------|--------|
| **运维** | T0 验收取证 | 满 7 天跑 health check |
| **后端** | T1 代码完成 | 开 `XHS_V2_LAUNCH=1` |
| **前端** | 体验码 UI 完成 | 会员页推荐区块 |
| **数据** | aggregate timer | pgvector 嵌入批处理 |
| **PC** | 未合并 | xhs_shelf_time 仓库 |

---

## 全链路一键部署（每次 push 后）

```bash
export XHS_MEMBER_TOKEN='...'
export XHS_SMOKE_EXPECT=legacy_dual
bash /opt/xhs-cloud/cloud_deploy/scripts/v2-oneclick-deploy.sh
```

**T1 开流量**（一次性，写入 `/opt/xhs-cloud/.env`）：

```bash
echo 'XHS_V2_LAUNCH=1' >> /opt/xhs-cloud/.env
bash /opt/xhs-cloud/cloud_deploy/scripts/v2-oneclick-deploy.sh
```

脚本：**pull → rsync → PG 08/09/10 → host-update → health → smoke → T0 health**

---

## 更新日志

| 日期 | 变更 |
|------|------|
| 2026-07-12 | **T1 批量落地**：get_plan、L1 cache、nginx、aggregate timer、体验码 UI、T0/GA 脚本 |
| 2026-07-12 | 全链路一键：`v2-oneclick-deploy.sh` + doc 29 |
| 2026-07-12 | T1：radar / generate / watchlist API + 会员雷达横幅 |
| 2026-07-12 | 初版：doc 27 + 本跟踪器 |
