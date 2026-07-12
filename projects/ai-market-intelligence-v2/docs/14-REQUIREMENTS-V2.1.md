# Phase 2 需求文档（V2.1 PRD 入口）

> **版本**：v2.1-draft  
> **日期**：2026-07-12  
> **基线**：`12-DESIGN-GAPS-AND-ROADMAP.md`  
> **上线需求（评估落地 + 基础设施审计）**：见 **`20-REQUIREMENTS-V2.2-ROLLOUT.md`** §12  
> **LLM 标准配置**：PackyAPI + **deepseek-v4-flash**（见 `13-LLM-PACKYAPI-DEEPSEEK.md`）

---

## 1. 目标

在 **不影响 V1 现网** 前提下，完成 Shadow 管道 + DeepSeek 真 LLM 多 Agent + 合规 Gate 全链路，白名单用户可预览 AI 情报。

---

## 2. 已交付（Phase 1.5）

| ID | 需求 | 状态 |
|----|------|------|
| REQ-LLM-001 | PackyAPI OpenAI 兼容客户端 | ✅ `llm_client.py` |
| REQ-LLM-002 | 默认 `deepseek-v4-flash`，thinking 可关 | ✅ |
| REQ-LLM-003 | 分 Agent 模型配置 | ✅ `llm_profiles.yaml` |
| REQ-AI-001 | LangGraph 5 Agent 编排 | ✅ `agent_graph.py` |
| REQ-AI-002 | JSON 结构校验 | ✅ `agent_validate.py` |
| REQ-AI-003 | Token 用量记录 | ✅ `llm_meta.usage` |
| REQ-DATA-003 | k-匿名发布 Gate | ✅ `compliance_gate` |
| REQ-LEGAL-002 | 审计 JSONL | ✅ `audit_log.py` |
| REQ-DATA-001 | PG 数据源骨架 | ⚠️ `metric_engine_pg.py`（待 DSN，暂不需要） |
| REQ-UX-001 | 双轨 Tab 会员原型 | ✅ `member-demo.html` |
| REQ-UX-002 | 报告可解释性 | ✅ `report_builder` 指标面板 |
| REQ-UX-003 | 生成进度反馈 | ✅ `member-demo.js` |
| REQ-UX-004 | 投诉 stub | ✅ `POST /api/v1/feedback` |
| REQ-UX-005 | 情报库 | ✅ `GET /api/v1/insight/library` |
| REQ-UX-007 | 类目对比工作台 | ✅ `compare.html` + `/insight/compare` |
| REQ-UX-008 | 趋势时间轴 7/14/30d | ✅ `timeline.html` + `/insight/timeline` |
| REQ-UX-009 | 决策工作流 Kanban | ✅ `workflow.html` + `/workflow/*` |
| REQ-UX-010 | 智能提醒中心 | ✅ `notifications.html` |
| REQ-UX-011 | PDF 摘要导出（水印） | ✅ `/insight/report/print` |
| REQ-UX-012 | V2 套餐额度模拟 | ✅ `config/plans.yaml` |
| REQ-RT-004 | 会员 profile + portal_route | ✅ `GET /api/v1/member/profile` |
| REQ-UX-020 | V2 独立门户 | ✅ `insight_portal.html` |
| REQ-LLM-010 | 日 LLM 预算熔断 | ✅ `llm_budget.py` |
| REQ-INFRA-* | 基础设施与现网对接审计 | ✅ 见 **`20-REQUIREMENTS-V2.2-ROLLOUT.md` §12** |

---

## 3. Phase 2 待办（优先级）

> **上线需求（评估落地）**：见 **`20-REQUIREMENTS-V2.2-ROLLOUT.md`**（v2.2.1 Lab 已交付路由/门户/配额隔离）

### P0

1. **INSIGHT_PG_DSN** 对接 xhs-cloud `raw_product_snapshots` 表结构
2. 法务定稿三份法律模板并挂网
3. 合并 `cloud-stubs/` → xhs-cloud 开发分支
4. `POST /api/v2/feedback` 投诉通道

### P1

5. Prompt 版本 DB 表 `prompt_registry`
6. 日 LLM 预算熔断（基于 `llm_meta.usage`）
7. 会员页双 Tab（Legacy + AI 情报）— **实验室双轨对照** `member-demo.html`；**新会员默认** `insight_portal.html`
8. PC `cloud_client.py` insight API
9. **类目对比工作台**（见 `16-ADVANCED-PRODUCT-ARCHITECTURE.md`）— ✅ 实验室原型
10. **趋势时间轴** 7/14/30 天 — ✅ 实验室原型
11. **决策工作流 Kanban** — ✅ 实验室原型

### P2

9. 类目树 `config/category_taxonomy.yaml`
10. 黄金样本回归测试集（20 metrics → 结构快照）

---

## 4. LLM 配置规范（强制）

```bash
INSIGHT_LLM_PROVIDER=packy_deepseek
INSIGHT_LLM_API_KEY=<PackyAPI deepseek-officially 分组>
INSIGHT_LLM_BASE_URL=https://www.packyapi.com/v1
INSIGHT_LLM_MODEL=deepseek-v4-flash
INSIGHT_LLM_THINKING=disabled
```

验证：`python scripts/test_llm_connection.py`

---

## 5. 非功能需求（NFR）

| 项 | 指标 |
|----|------|
| LLM 超时 | 60s / Agent，最多 2 次重试 |
| k-匿名 | 默认 k=5，`INSIGHT_K_ANONYMITY` 可配 |
| 降级 | 无 Key 或 CEO 失败 → mock（`FALLBACK_MOCK=1`） |
| 审计 | 每次发布写 `output/audit/audit_YYYYMMDD.jsonl` |

---

## 6. 双轨状态机

```
legacy_only → shadow → dual → v2_only
```

当前：**legacy_only**（实验室 isolated）

---

**维护**：Phase 2 冲刺结束时更新 §2 已交付表。
