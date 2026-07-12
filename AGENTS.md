# vuemonitor — Agent 开发指南（必读）

> Cursor / Agent 在动手改代码前，请先读本文件，并按路径加载 `.cursor/rules/` 下对应规则。

## 通用约束

1. **需求不清先问**，不要猜。
2. **改代码前先理解**现有逻辑与目录边界，不要贸然动现网。
3. **能读就不写**——先搜索、读文件、跑测试，再改。
4. **第三方 API / 协议 / 加密**不熟时，先查文档或抓包确认。
5. **能复用现网基座就不重复造轮子**（支付、JWT、PG、会员页见 V2 文档 17）。
6. **Phase 0～2 默认不改现网** `xhs-cloud/cloud_deploy/assets/member_portal.html`，除非用户明确要求合并上线。

## 仓库子系统

| 子系统 | 路径 | 栈 | 生产路径 / 说明 |
|--------|------|-----|-----------------|
| **SaaS 后端** | `server/` | FastAPI + SQLAlchemy + **PostgreSQL** + Redis | `/opt/vuemonitor/server` |
| **选品云 / 会员** | `xhs-cloud/` | FastAPI + **PostgreSQL** (`XHS_DATABASE_URL`) | `/opt/xhs-cloud` |
| **PC 客户端** | `client/` | **Electron + Vue 3 + Element Plus** | Windows 安装包 |
| **V2 情报实验室** | `projects/ai-market-intelligence-v2/` | FastAPI Lab + `cloud-stubs/` | 本地；合并进 `xhs-cloud` |
| **本地采集 Agent** | `xhs-cloud/tools/` | Python + tkinter + PyInstaller | Windows 便携包 |

**注意**：本仓库主栈是 **FastAPI**，不是 Django。PC 主客户端是 **Electron**，不是 PyQt。PyQt / Django 规范仅适用于未来独立子项目或 `需求文档/` 下遗留工具。

## Python 版本（自适应，禁止写死）

以**当前子项目已有约定**为准，Agent 不得自作主张升级/降级：

| 子项目 | 版本来源 | 常见值 |
|--------|----------|--------|
| `server/` | `deploy.sh` / `INSTALL.md` / 服务器 `.venv` | **3.11** |
| `xhs-cloud/` | `host-update.sh` 的 `python3` + `requirements-cloud.txt` | 云主机系统 **python3**（≥3.10） |
| V2 Lab | `requirements-lab.txt` | 与开发机 venv 一致 |
| 本地 Agent | `build_portable_agent.ps1` | **3.10+** |

虚拟环境：生产 `server/.venv`、`/opt/xhs-cloud/venv`；本地新建项目可参考 `~/.env/<项目名>`。

## PostgreSQL 环境变量

| 用途 | 变量 | 说明 |
|------|------|------|
| Legacy / 选品云 | `XHS_DATABASE_URL` | `xhs-cloud` 会员、报告库、授权码 |
| SaaS 主库 | `DATABASE_URL` / `server/.env` | `server/` 业务 |
| V2 情报（可选） | `INSIGHT_PG_DSN` | 未配置则 Lab mock |

## V2 战略方向（摘要）

- **舍弃** Legacy 数据包下载为新会员默认路径；老月卡履约至 `expires_at`。
- **同址上线**：最终 `https://monitor.xhs365.cn/member` → V2（扩展 AI Tab + entitlements）。
- **实验室与现网两轨**：Lab 验证 → 按 PR 清单合并 `cloud-stubs/` 进 `xhs-cloud`。
- **降本**：夜间预生成情报库（L0）+ 精确缓存（L1），见文档 22。

## 开发前必读文档（按任务）

| 任务 | 文档 |
|------|------|
| 现网复用 / 支付 JWT | `projects/ai-market-intelligence-v2/docs/17-XHS-CLOUD-BASE-REUSE.md` |
| V2 需求与验收 | `projects/ai-market-intelligence-v2/docs/20-REQUIREMENTS-V2.2-ROLLOUT.md` |
| 会员页合并 PR | `projects/ai-market-intelligence-v2/docs/21-MEMBER-PORTAL-AI-TAB-PR-CHECKLIST.md` |
| AI 预生成缓存 | `projects/ai-market-intelligence-v2/docs/22-INSIGHT-PRECOMPUTE-CACHE-DESIGN.md` |
| PC 重设计 / 打包 | `projects/ai-market-intelligence-v2/docs/23-PC-CLIENT-V2-REDESIGN-AND-PACKAGING.md` |
| 全局路线图（隔离） | `projects/ai-market-intelligence-v2/docs/24-GLOBAL-TASK-ROADMAP-ISOLATION.md` |
| **主 TODO 跟踪器** | `projects/ai-market-intelligence-v2/docs/28-MASTER-TODO-TRACKER.md` |
| **留存 × PG 需求** | `projects/ai-market-intelligence-v2/docs/27-RETENTION-PG-STICKINESS-REQUIREMENTS.md` |
| Legacy 下线策略 | `projects/ai-market-intelligence-v2/docs/19-LEGACY-SUNSET-AND-V2-LAUNCH.md` |
| 云部署 | `.cursor/rules/xhs-cloud-deploy.mdc` |

## UI 主题与视觉风格（必读）

完整规则：**.cursor/rules/ui-theme-style.mdc**（`alwaysApply: true`）

| 子系统 | 主题方案 |
|--------|----------|
| **PyQt GUI** | **四选一**（每项目定一种，写入 `config/settings.json`） |
| | 1. `fusion_dark` — Fusion + QPalette 暗色（默认，零依赖） |
| | 2. `qdarkstyle` — 专业暗色（`pip install qdarkstyle`） |
| | 3. `qt-material` — Material Design（`pip install qt-material`） |
| | 4. `qfluentwidgets` — Win11 Fluent（`pip install qfluentwidgets`） |
| **PC client/** | Electron + Vue；`useTheme.ts` + `variables.css`；主色 `#4F46E5` |
| **会员页 / V2 Web** | Apple 风；主色 `#0071e3`；CSS 变量 |
| **本地 Agent** | tkinter 系统主题（不适用四选一） |

**禁止**同一应用叠加多套 PyQt 主题库；**禁止**在 `client/` 使用 PyQt 主题。

## 测试与质量（新 Python 模块）

新建或大幅扩展的 Python 代码：**pytest** + **ruff** + **mypy**（与现有子项目保持一致即可，不强制全仓一次性补齐）。
