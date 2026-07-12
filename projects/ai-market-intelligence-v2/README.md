# AI Market Intelligence Platform V2.0（独立设计实验室）

> **隔离原则**：本目录与现网完全隔离。  
> **Phase 0～1 不修改**：远程主机、现网会员页、PC ProductAnalyzer。  
> **用途**：完整设计方案 + **可运行参考代码** + 远程/PC 升级蓝图。

## 核心理念

**数据是原料，算法是能力，AI 是产品，情报才是价值。**

## 快速开始

```powershell
cd E:\vuemonitor\projects\ai-market-intelligence-v2
copy .env.example .env          # 填入 PackyAPI Key（deepseek-officially 分组）
pip install -r requirements-lab.txt
python scripts/test_llm_connection.py   # 验证 DeepSeek V4 Flash
python scripts/run_insight_pipeline.py --date 2026-07-12
cd local-web-prototype && python server.py
# 会员 UX 原型: http://127.0.0.1:8765/member-demo.html
# 类目对比:     http://127.0.0.1:8765/compare.html
# 趋势时间轴:   http://127.0.0.1:8765/timeline.html
# 决策工作流:   http://127.0.0.1:8765/workflow.html
# 提醒中心:     http://127.0.0.1:8765/notifications.html
# 开发者页:     http://127.0.0.1:8765/
```

## 文档（按阅读顺序）

| 文档 | 说明 |
|------|------|
| **`docs/03-FULL-IMPLEMENTATION-GUIDE.md`** | **总实施指南** |
| `docs/00-MASTER-SPEC.md` | 战略与合规 |
| `docs/06-API-SPEC-V2.md` | API |
| `docs/07-DATABASE-SCHEMA-V2.sql` | 数据库 |
| `docs/08-REMOTE-UPGRADE-RUNBOOK.md` | 云主机升级 |
| **`docs/10-COMPLIANCE-LEGAL-CN.md`** | **中国法律法规合规实施方案** |
| **`docs/11-TECH-BENCHMARK-2025.md`** | **成熟互联网技术对标方案** |
| **`docs/12-DESIGN-GAPS-AND-ROADMAP.md`** | **设计缺陷与 Phase 2～4 路线图** |
| **`docs/13-LLM-PACKYAPI-DEEPSEEK.md`** | **PackyAPI + DeepSeek V4 Flash 接入** |
| **`docs/14-REQUIREMENTS-V2.1.md`** | **Phase 2 PRD 入口** |
| **`docs/15-UX-EXPERIENCE-DESIGN.md`** | **用户体验设计规范** |
| **`docs/16-ADVANCED-PRODUCT-ARCHITECTURE.md`** | **进阶产品架构（V2.5）** |
| `config/ux_copy.yaml` | 统一 UX 文案 |
| `local-web-prototype/member-demo.html` | **会员中心 UX 原型（推荐入口）** |
| `local-web-prototype/compare.html` | 类目对比工作台 |
| `local-web-prototype/timeline.html` | 趋势时间轴 |
| `local-web-prototype/workflow.html` | 决策工作流 Kanban |
| `local-web-prototype/notifications.html` | 智能提醒中心 |
| `config/plans.yaml` | V2 套餐定义 |
| `services/subscription_mock.py` | 套餐 / 额度 mock |
| `services/notification_mock.py` | 提醒规则 mock |
| `services/report_export.py` | PDF 摘要（打印 HTML） |
| **`docs/07-AI-AGENTS-LANGGRAPH.md`** | **LangGraph 多 Agent + LLM 对接** |
| `docs/18-MEMBERSHIP-SCHEME-DESIGNS.md` | **会员体系 6 方案穷举** |
| `docs/17-XHS-CLOUD-BASE-REUSE.md` | **现网基座平移（禁止重造支付/授权码）** |
| `docs/legal/` | 用户协议 / 隐私 / AI 说明模板 |

## 代码

| 路径 | 说明 |
|------|------|
| `config/insight_policy.yaml` | 发布策略配置（Policy-First） |
| `services/compliance_gate.py` | ★ 合规发布网关（强制） |
| `services/agent_graph.py` | ★ LangGraph 多 Agent（真 LLM + mock） |
| `services/llm_client.py` | OpenAI 兼容 LLM 客户端 |
| `prompts/agents.yaml` | 5 Agent Prompt v1 |
| `.env.example` | LLM 环境变量示例 |
| `local-web-prototype/` | 本地 Web 验证 |
| `cloud-stubs/` | **合并 xhs-cloud**：支付套餐/类目关注/Team/权益 |

## 升级路径

实验室验证 → 合并 xhs-cloud → 云主机 deploy → PC `xhs_shelf_time` 发版
