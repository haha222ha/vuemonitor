# 成熟互联网技术服务对标方案（2025）

> 对标对象：Google Confidential Analytics / TrustDS 政策驱动数据治理 / 主流 B2B Market Intelligence SaaS  
> 目标：在 **2G 云主机 + PC 客户端 + 国内 LLM** 约束下，采用**可落地**的成熟架构，而非论文级过度设计。

---

## 一、架构对标总图（升级版六层）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Experience Layer  体验层                                                │
│  Web 会员情报中心 │ PC WebView │ 移动端(H5) │ Admin 运营台                 │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│  API Gateway  统一网关（FastAPI + Nginx）                                │
│  · 外部 API（会员 JWT）  · 内部 API（Sync Key）  · 零信任分域              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Insight       │     │ Legacy Report   │     │ Member / Pay    │
│ Service V2    │     │ Service V1      │     │ Auth Service    │
│ (新)          │     │ (维护)          │     │ (现有)          │
└───────┬───────┘     └────────┬────────┘     └─────────────────┘
        │                      │
┌───────▼──────────────────────▼─────────────────────────────────────────┐
│  Intelligence Pipeline  情报管道（Event-Driven）                        │
│  Scheduler → Extract → Aggregate → Index → AI Agents → Compliance Gate  │
│           → Render HTML → Publish → Notify                              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│  Data Plane  数据平面                                                    │
│  PG(raw 内部) │ PG(insight 对外) │ Redis(缓存/队列) │ Object(HTML 静态)   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│  Collection Plane  采集平面（内部隔离，PC Agent 可选）                     │
│  用户授权浏览 │ 合规频率 │ 快照入库 │ 禁止对外暴露                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、对标能力矩阵

| 能力 | 行业成熟做法 | 我们 V2 方案 | 阶段 |
|------|--------------|--------------|------|
| **Policy-First 治理** | TrustDS：策略编译→执行图→审计证据 | `ComplianceGate` + 发布策略 YAML | P1 |
| **Release Boundary** | 只在发布层输出聚合结果 | L4 指标 JSON → Gate → L6 HTML | P1 |
| **LLM 输入最小化** | Google PPI：TEE+DP；我们轻量版：仅指标 JSON | `ai_orchestrator` 输入 whitelist | P1 |
| **多 Agent 编排** | LangGraph / CrewAI 模式 | 5 Agent 串并行（市场/数据/风险/运营/CEO） | P2 |
| **内容安全** | 国内大模型自带 + 后置审核 | 敏感词 + 违法建议规则 + 人工抽检 | P1 |
| **可观测性** | OpenTelemetry + 结构化日志 | journald + 发布 job 状态表 | P2 |
| **Feature Flag** | LaunchDarkly / 自研配置 | `plan_code` + entitlements 双轨 | P1 |
| **异步管道** | Kafka / Redis Stream | systemd timer + Redis 队列（2G 友好） | P2 |
| **CDN 静态情报** | 报告 HTML 边缘缓存 | Nginx 缓存 insight HTML | P3 |
| **客户端** | WebView + 本地 SQLite 笔记 | PC 研究助手，非数据分发 | P3 |

---

## 三、情报管道（对标 Palantir / Bloomberg 轻量版）

### 3.1 阶段与 SLA

| Job | 触发 | 输入 | 输出 | SLA |
|-----|------|------|------|-----|
| `extract_snapshots` | 每日 | PG raw | 清洗快照 | 内网 |
| `aggregate_metrics` | 每日 16:00 | 快照 | `insight_metrics_daily` | <30min |
| `run_ai_agents` | 16:30 | 指标 JSON | `insight_reports.report_json` | <20min |
| `compliance_audit` | 16:45 | report_json | pass/fail | <5min |
| `render_publish` | 17:00 | 过审 JSON | HTML + `insight_archives` | <10min |
| `notify_members` | 17:05 | — | 站内消息（可选） | — |

与现网 `cloud_gen_report` 17:00 并行，**V1/V2 独立 timer**。

### 3.2 Event 模型（Redis / PG job 表）

```json
{
  "job_id": "insight-20260712-001",
  "type": "insight_daily",
  "report_date": "2026-07-12",
  "status": "pending|running|audited|published|failed",
  "trace_id": "uuid",
  "formula_version": "idx-v1",
  "prompt_version": "agent-v1"
}
```

---

## 四、AI 技术栈对标（国内可落地）

| 组件 | 推荐 | 备选 | 说明 |
|------|------|------|------|
| LLM | 智谱 GLM-4/5 | 通义、DeepSeek、Moonshot | 国内节点，降低出境风险 |
| 编排 | 自研轻量 DAG → LangGraph | Dify 私有部署 | Phase 1 用 mock，Phase 2 接 API |
| Prompt 管理 | Git 版本化 `prompts/*.yaml` | Langfuse | 可审计、可回滚 |
| 输出审核 | 关键词 + 规则引擎 | 云厂商内容安全 API | 必选 |
| 缓存 | Redis hash(metrics) | — | 同指标 24h 不重算 |
| RAG | **不对用户暴露**；仅内部类目知识库 | — | 避免把商品库喂给用户 |

### 4.1 Agent 图（对标 CrewAI）

```
        ┌─────────────┐
        │ MarketAgent │
        └──────┬──────┘
               │
   ┌───────────┼───────────┐
   ▼           ▼           ▼
DataAgent  RiskAgent   (parallel)
   └───────────┬───────────┘
               ▼
        OpsAdvisorAgent
               ▼
         CEOAgent
               ▼
      ComplianceGate.audit()
               ▼
         HTML Renderer
```

---

## 五、API 设计对标（REST + 任务型）

| 模式 | 对标 | 我们 |
|------|------|------|
| 同步读 | Stripe/GitHub API | `GET /member/insight/library` |
| 异步生成 | OpenAI Batch | `POST /internal/insight/generate` → job_id |
| 幂等 | Idempotency-Key | `report_date+category+formula_version` UNIQUE |
| 版本 | API-Version header | `X-Insight-Formula: idx-v1` |
| 鉴权 | OAuth2 Bearer | 现网 JWT + 设备槽 |

---

## 六、前端对标

| 场景 | 成熟方案 | 我们 |
|------|----------|------|
| 情报阅读 | Notion / Medium 阅读体验 | 6 页卡片式 HTML |
| 数据可视化 | ECharts 指数雷达 | 类目级雷达图（无商品点） |
| PC 嵌入 | Electron WebView | `insight/.../view` |
| 离线 | PWA 缓存摘要 | Phase 4 可选 PDF |

---

## 七、安全对标（Zero Trust 轻量版）

```
Internet → Nginx(WAF) → FastAPI
              │
              ├─ /api/v1/member/*     → JWT + session + entitlements
              ├─ /api/v1/internal/*   → Sync Key + IP allowlist
              └─ /api/v1/agent/*      → Agent Key（现有）

DB: raw_* 表无 SELECT GRANT 给 app_member 角色（Phase 2）
```

---

## 八、与 V1 共存的技术策略

| 维度 | V1 | V2 |
|------|----|----|
| archive_type | `member_daily_zip` | `insight_daily_html` |
| 存储 | zip 文件 | HTML + insight.json |
| 预览 | index_with_gr.html + data.js | index.html 纯情报 |
| timer | xhs-daily-report | xhs-insight-report（新） |
| entitlements | legacy | insight_pro |

**Feature Flag**：`auth_codes.note.allowed_archive_types` 控制可见 Tab。

---

## 九、2G 云主机落地优先级

| 优先级 | 组件 | 原因 |
|--------|------|------|
| P0 | ComplianceGate + 指标聚合 | 合规核心 |
| P0 | insight HTML 静态发布 | 低内存 |
| P1 | Redis 缓存 AI 结果 | 省 LLM 费用 |
| P2 | 异步 job 表 | 解耦 timer |
| P3 | LangGraph 完整编排 | 复杂度上升 |
| 不做 | 重型 Kafka / K8s | 超 2G 预算 |

---

## 十、References（延伸阅读）

- 生成式人工智能服务管理暂行办法（国务院，2023）
- Google Research: Provably Private Insights / Confidential Federated Analytics
- TrustDS: Policy-Compiled Governance for Marketplace Analytics (2025)
- 最高法：已公开个人信息合理范围参考案例

---

**升级结论**：V2 技术路线 = **Policy-First 合规网关 + 指标发布边界 + 国内 LLM 多 Agent + 双轨 Feature Flag**，在现网 FastAPI/PG/systemd 上演进，而非推倒重来。
