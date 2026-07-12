# 28 — V2 主 TODO 跟踪器（T0 → GA）

> **今日冲刺**：`30-T1-LAUNCH-CHECKLIST.md` → `v2-t1-launch.sh`  
> **一键部署**：`29-V2-ONECLICK-DEPLOY-RUNBOOK.md` → `v2-oneclick-deploy.sh`

**图例**：`[x]` 已完成 · `[~]` 进行中 · `[ ]` 未开始

---

## Phase T0 — Shadow

- [x] 部署 + smoke 8/8 + timer + LLM admin
- [~] D1–D7 journal（`xhs-v2-daily-ops.timer` 每天 08:00 自动；或手跑 `launch_daily_ops.sh`）

---

## Phase T1 — 开流量

- [x] 代码：`XHS_V2_LAUNCH=1` / get_plan / 体验码 UI / nginx / cache / aggregate timer
- [x] **`v2-t1-launch.sh`** 一键开 T1
- [x] **`31-EXPERIENCE-CODE-SOP.md`**
- [~] 云主机执行 T1 launch + 体验码 insight_only smoke（**你今天做**）

---

## Phase T2 — 留存

- [x] recommendations / health-score / workflow API + 会员页推荐+健康度
- [x] `11_insight_workflow_schema.sql`
- [x] `ensure_v2_daily_ops_timer.sh` + systemd 08:00
- [x] pgvector 扩展 + `category_embeddings` 表（deterministic 兜底可入库）
- [~] **Phase Q1 情报质量**（5 Agent + 类目树 + L1 cache）→ **`32-INTELLIGENCE-QUALITY-FULL-IMPLEMENTATION-PLAN.md`**
  - [x] Q1-B：5 Agent 移植 `insight_agent_graph.py` + `prompts/agents.yaml`
  - [x] Q1-A：类目树 `category_taxonomy.yaml` + enrich + k-匿名
  - [x] Q1-C：HTML 指标依据折叠 + L1 cache schema 修复
- [ ] Redis L1（可选，未做）

---

## Phase GA — Legacy Sunset

- [x] `disable_legacy_report_timer.sh` + `PC-V2-GA-GATE.md`
- [x] `launch_daily_ops.sh` 监控
- [ ] PC ProductAnalyzer 合并（独立仓库，GA 项）

---

## 今天一条命令（T1）

```bash
export XHS_MEMBER_TOKEN='...'
bash /opt/vuemonitor/xhs-cloud/cloud_deploy/scripts/v2-t1-launch.sh
```

---

## 更新日志

| 日期 | 变更 |
|------|------|
| 2026-07-12 | **32 情报质量全方位实施计划**（Q0～Q4） |
| 2026-07-12 | 今日冲刺：T1 launch、T2 API/UI、doc 30/31、daily ops |
| 2026-07-12 | T1 批量 + 一键部署 + nginx 修复 |
