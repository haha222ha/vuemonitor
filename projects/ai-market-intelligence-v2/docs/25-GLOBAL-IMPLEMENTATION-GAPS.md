# 25 — 全局实施缺口清单（T0 → GA）

> **目的**：回答「需求文档还缺什么才能全局实施？」  
> **关联**：`20-REQUIREMENTS-V2.2-ROLLOUT.md`、`24-GLOBAL-TASK-ROADMAP-ISOLATION.md`、`22-INSIGHT-PRECOMPUTE-CACHE-DESIGN.md`

---

## 0. 预生成与 AI 的关系（已澄清）

| 阶段 | 是否调 LLM | 说明 |
|------|------------|------|
| **L0 夜间预生成** | **是** | systemd `xhs-insight-report.timer` 02:30 批量跑 pipeline，**每类目/日 1 次** Agent |
| **用户白天访问** | **否** | 读 PG + 磁盘 HTML（Cache-First）；会员页 / PC **零 LLM 调用** |
| **现网 skeleton** | mock | `insight_ai_mock.py`；`INSIGHT_USE_LLM=1` 未接真 Agent |

降本核心：**把 LLM 从「用户请求路径」挪到「离线批处理路径」**。

---

## 1. 已具备（可并行开工）

| 项 | 状态 | 路径 |
|----|------|------|
| 需求 / 路线图 | ✅ | doc 20–24 |
| Legacy 隔离 gate | ✅ 骨架 | `legacy_gate.py`、`member_entitlements.py` |
| Insight API 路由 | ✅ 骨架 | `insight_routes.py` |
| PG 表 DDL | ✅ | `database/08_insight_v2_tables.sql` |
| 报告管道（PG→HTML） | ✅ mock AI | `reporting/insight_pipeline.py` |
| 会员页 AI Tab | ✅ 骨架 | `member_insight.js` |
| Shadow timer | ✅ 草案 | `systemd/xhs-insight-report.*` |
| PC cloud_client 补丁 | ✅ 草案 | `cloud-stubs/pc_cloud_client_v2_patch.py` |
| Lab 路径隔离 + 测试 | ✅ | `report_storage.py`、44 tests |

---

## 2. 阻塞 T0 Shadow（7 天）的缺口

| ID | 缺口 | 负责人轨 | 验收 |
|----|------|----------|------|
| **GAP-T0-01** | **运维 Runbook 单页** | 运维 | ✅ `26-T0-SHADOW-RUNBOOK.md` |
| **GAP-T0-02** | 云主机执行 `08_insight_v2_tables.sql` + 验证 | 运维 | `\dt insight_*` |
| **GAP-T0-03** | 启用 `XHS_INSIGHT_SHADOW_TIMER=1` + `ensure_insight_report_timer.sh` | 运维 | `systemctl list-timers` 见 02:30 |
| **GAP-T0-04** | Shadow 输出目录与权限 `data/insight_shadow/` | 运维 | 脚本可写、API library 可读 |
| **GAP-T0-05** | **真 LLM 接入** | 后端 | ✅ admin 后台 + `INSIGHT_USE_LLM` / PG settings |
| **GAP-T0-06** | E2E：三 persona（legacy / insight / dual）HTTP 用例 | QA | 扩展 `run_e2e.sh` |

---

## 3. 阻塞 T1 小流量（`XHS_V2_LAUNCH=1` 新 SKU）的缺口

| ID | 缺口 | 说明 |
|----|------|------|
| **GAP-T1-01** | **07-DATABASE-SCHEMA-V2.sql** 与 08 统一命名、迁移顺序文档 | 避免 DBA 双轨 |
| **GAP-T1-02** | **06-API-SPEC-V2** 正式版（现多为 Lab stub） | 前后端契约 |
| **GAP-T1-03** | `POST /insight/generate` 配额 + Cache-First（REQ-CACHE-002） | 用户触发生成走 L1 |
| **GAP-T1-04** | Watchlist PG 持久化（现 mock / 内存） | `insight_watchlist` 表已有 DDL |
| **GAP-T1-05** | 管理端发码：insight SKU + entitlements | web-admin 或脚本 |
| **GAP-T1-06** | nginx 限流 / 大报告 timeout（REQ-INFRA-007） | `nginx/www.conf` 片段 |
| **GAP-T1-07** | 法务页面上线（隐私 / 用户协议 / AI 披露） | doc 10 模板 → 静态页 |
| **GAP-T1-08** | doc 20 中 REQ-PROD-* 状态与代码同步 | 大量仍 ⏳ |

---

## 4. 阻塞 GA（Legacy  sunset）的缺口

| ID | 缺口 |
|----|------|
| **GAP-GA-01** | PC ProductAnalyzer **实际合并**（`xhs_shelf_time` 仓库，非 vuemonitor） |
| **GAP-GA-02** | PC 安装包重打包 + 自动更新 channel（doc 23） |
| **GAP-GA-03** | 生产 `{user_id}/{date}/{category}/` 报告路径（A4 Prod） |
| **GAP-GA-04** | Redis L1 精确缓存（可选，doc 22 Phase 2） |
| **GAP-GA-05** | 监控告警：timer 失败、LLM 预算、生成延迟 |
| **GAP-GA-06** | Legacy 到期用户迁移通信 + 降级 UX |

---

## 5. 文档层面仍「待写」但非硬阻塞

| 文档 | 用途 | 优先级 |
|------|------|--------|
| `05-DATABASE-ER-V2.md` | ER 图 | P2 |
| `06-API-SPEC-V2.md` 完整版 | OpenAPI 级 | P1（T1 前） |
| `26-T0-SHADOW-RUNBOOK.md` | Shadow 7 天 | ✅ |
| `27-LLM-PRODUCTION-WIRING.md` | 环境变量、模型、预算 | P2（已并入 admin 页） |
| `28-NGINX-INSIGHT-LIMITS.md` | 限流配置 | P2 |

---

## 6. 建议实施顺序（与 doc 24 对齐）

```mermaid
flowchart LR
  A[PC-1 补丁草案] --> B[Shadow timer 7d]
  B --> C[真 LLM + mock 开关]
  C --> D[T0 Runbook + E2E]
  D --> E[XHS_V2_LAUNCH 新 SKU]
  E --> F[PC 合并 xhs_shelf_time]
  F --> G[GA Legacy sunset]
```

**当前可立即执行**（本仓库内）：

1. ✅ PC-1 `pc_cloud_client_v2_patch.py` + 测试  
2. ✅ Shadow systemd + `run_insight_report_shadow.sh`  
3. ⏳ 写 `26-T0-SHADOW-RUNBOOK.md`（下一步）  
4. ⏳ `INSIGHT_USE_LLM` 接 lab Agent 或 xhs-cloud 内实现  

**必须跨仓库**：

- ProductAnalyzer PyQt UI（`xhs_shelf_time`）  
- 云主机 PG 迁移 + timer 启用（运维）  

---

## 7. 结论

**需求体系（20–24 + 22）已足够启动全局实施**；缺的不是「再写一份大需求」，而是：

1. **T0 运维 Runbook**（Shadow 怎么开、怎么验、怎么回滚）  
2. **生产 LLM 接线**（mock → Agent + 预算）  
3. **契约文档**（06 API 正式版、07/08 SQL 统一）  
4. **PC 与 xhs_shelf_time 的实际代码合并**（vuemonitor 只能提供补丁草案）  
5. **REQ 状态表与代码对齐**（避免 doc 写 ✅ 代码仍 mock）

完成 **GAP-T0-01～06** 即可开始 Shadow 7 天；**GAP-T1-*** 完成后可开 `XHS_V2_LAUNCH=1` 新购。
