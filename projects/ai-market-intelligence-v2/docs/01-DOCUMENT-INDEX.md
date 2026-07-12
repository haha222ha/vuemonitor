# V2.0 设计文档索引（15 + 1）

> 主文档：`00-MASTER-SPEC.md`  
> 编写顺序建议：01 → 15，每份文档独立可交付给大模型分段开发。

| # | 文档名 | 文件名（待写） | 受众 | 状态 |
|---|--------|----------------|------|------|
| 01 | 项目商业设计 | `01-BUSINESS.md` | CEO / 产品负责人 | 待写 |
| 02 | 产品架构 | `02-PRODUCT-ARCHITECTURE.md` | 产品 / 架构 | 待写 |
| 03 | 功能树 | `03-FEATURE-TREE.md` | 产品 / 开发 | 待写 |
| 04 | 页面原型 | `04-PROTOTYPE.md` | 产品 / 设计 | 待写 |
| 05 | 数据库 ER | `05-DATABASE-ER.md` | 后端 | 待写 |
| 06 | API 设计 | `06-API-SPEC.md` | 前后端 | 待写 |
| 07 | AI Agent 设计 | `07-AI-AGENTS.md` | AI / 后端 | 待写 |
| 08 | Prompt 设计 | `08-PROMPTS.md` | AI | 待写 |
| 09 | 指标体系设计 | `09-INDEX-SYSTEM.md` | 算法 / 产品 | 待写 |
| 10 | AI 报告模板 | `10-REPORT-TEMPLATES.md` | 产品 / 前端 | 待写 |
| 11 | UI 设计规范 | `11-UI-GUIDE.md` | 设计 / 前端 | 待写 |
| 12 | 开发规范 | `12-DEV-STANDARDS.md` | 全员 | 待写 |
| 13 | 部署方案 | `13-DEPLOYMENT.md` | 运维 | 待写 |
| 14 | 权限设计 | `14-AUTH-PERMISSIONS.md` | 后端 / 安全 | 待写 |
| 15 | 合规边界设计 | `15-COMPLIANCE.md` | 法务 / 产品 / 开发 | **见 10-COMPLIANCE-LEGAL-CN.md** |
| 16 | 中国法律合规实施方案 | **`10-COMPLIANCE-LEGAL-CN.md`** | 全员 / 法务 | ✅ v1.0 |
| 17 | 互联网技术对标 | **`11-TECH-BENCHMARK-2025.md`** | 架构 / 开发 | ✅ v1.0 |
| 18 | 设计缺陷与路线图 | **`12-DESIGN-GAPS-AND-ROADMAP.md`** | 产品 / 架构 | ✅ v1.0 |
| 19 | LangGraph 多 Agent | **`07-AI-AGENTS-LANGGRAPH.md`** | AI / 后端 | ✅ v1.0 |
| 20 | 用户服务协议模板 | **`legal/USER-SERVICE-AGREEMENT-TEMPLATE.md`** | 法务 / 产品 | ✅ v1.0-template |
| 21 | 隐私政策模板 | **`legal/PRIVACY-POLICY-TEMPLATE.md`** | 法务 | ✅ v1.0-template |
| 22 | AI 生成内容说明 | **`legal/AI-CONTENT-DISCLOSURE-TEMPLATE.md`** | 产品 / 法务 | ✅ v1.0-template |
| 23 | PackyAPI DeepSeek 接入 | **`13-LLM-PACKYAPI-DEEPSEEK.md`** | AI / 运维 | ✅ v1.0 |
| 24 | Phase 2 PRD | **`14-REQUIREMENTS-V2.1.md`** | 产品 / 开发 | ✅ v2.1-draft |
| 25 | 用户体验设计 | **`15-UX-EXPERIENCE-DESIGN.md`** | 产品 / 设计 | ✅ v1.0 |
| 26 | 进阶产品架构 | **`16-ADVANCED-PRODUCT-ARCHITECTURE.md`** | 产品 / 架构 | ✅ v1.0 |
| 27 | 现网基座复用 | **`17-XHS-CLOUD-BASE-REUSE.md`** | 架构 / 运维 | ✅ v1.0 |
| 28 | 会员体系方案穷举 | **`18-MEMBERSHIP-SCHEME-DESIGNS.md`** | 产品 / 商业 | ✅ v1.0 |
| 29 | Legacy 下线与 V2 上线 | **`19-LEGACY-SUNSET-AND-V2-LAUNCH.md`** | 产品 / 运维 | ✅ v1.0 |
| 30 | Phase 2.2 上线需求（评估落地） | **`20-REQUIREMENTS-V2.2-ROLLOUT.md`** | 产品 / 开发 / 运维 | ✅ v2.2.4 |
| 31 | 现网 PR：member 合并 AI Tab | **`21-MEMBER-PORTAL-AI-TAB-PR-CHECKLIST.md`** | 开发 / 运维 | ✅ v1.0 |
| 32 | 预生成情报库与降本缓存 | **`22-INSIGHT-PRECOMPUTE-CACHE-DESIGN.md`** | 架构 / AI | ✅ v1.0 |
| 33 | PC 端 V2 重设计与打包 | **`23-PC-CLIENT-V2-REDESIGN-AND-PACKAGING.md`** | 产品 / PC | ✅ v1.0 |
| 34 | 全局任务路线图（Legacy 隔离） | **`24-GLOBAL-TASK-ROADMAP-ISOLATION.md`** | 全员 | ✅ v1.0 |
| 35 | 全局实施缺口清单（T0→GA） | **`25-GLOBAL-IMPLEMENTATION-GAPS.md`** | 全员 / 运维 | ✅ v1.0 |
| 36 | T0 Shadow 7 天 Runbook | **`26-T0-SHADOW-RUNBOOK.md`** | 运维 | ✅ v1.0 |
| + | PC 客户端对接（接口） | `09-PC-CLIENT-INTEGRATION.md` | 开发 | ✅ 草案 |
| + | PC-1 cloud_client 合并说明 | `cloud-stubs/PC-1-CLOUD-CLIENT-INTEGRATION.md` | PC 开发 | ✅ 草案 |

## Phase 划分

| Phase | 内容 | 触现网 |
|-------|------|--------|
| 0 | 主文档 + 索引 + 本地样例 | ❌ |
| 1 | 15 份子文档 + 本地 Web 原型 | ❌ |
| 2 | 内部 Shadow 管道（与 V1 并行） | ⚠️ 只读对照 |
| 3 | 在期买家 V1 履约完毕 | V1 只维护 |
| 4 | 选品报告中心升级 V2 | ✅ 受控切换 |
