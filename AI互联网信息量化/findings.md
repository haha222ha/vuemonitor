# AI互联网情报系统 — 系统审计发现

> 审计日期：2026-05-24
> 审计范围：D:\vuemonitor 全系统架构 + AI互联网信息量化子系统

---

## 一、系统总体架构

### 1.1 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端 | FastAPI + SQLAlchemy + Alembic | Python 3.x |
| 数据库 | PostgreSQL + Redis | - |
| 用户端前端 | Vue 3 + Vite | web-user/ |
| 管理端前端 | Vue 3 + Vite | web-admin/ |
| 情报端前端 | Vue 3 + Element Plus + Pinia + Axios | web-intel/ |
| 桌面客户端 | Electron + Vue 3 | client/ |
| 部署 | GitHub Actions CI/CD + Systemd + Nginx | - |
| SSL | Cloudflare Flexible SSL | 源站纯HTTP |

### 1.2 域名体系

| 域名 | 服务 | Nginx配置 | 状态 |
|------|------|----------|------|
| www.xhs365.cn | 用户端前端 | ✅ | 运行中 |
| admin.xhs365.cn | 管理后台前端 | ✅ | 运行中 |
| api.xhs365.cn | FastAPI API | ✅ | 运行中 |
| intel.xhs365.cn | 情报系统前端 | nginx/intel.conf ✅ | **待部署** |

### 1.3 Git仓库

- GitHub: https://github.com/haha222ha/vuemonitor.git
- 主分支: main
- 服务器路径: /opt/vuemonitor/
- 最新提交: `b236989 CF Flexible SSL: 源站纯HTTP+本地构建dist+文档更新`

---

## 二、情报子系统架构详解

### 2.1 数据流

```
本地工作站 (Windows)
  商业情报中转站/database/*.json  ──→  remote_sync/api_client.py  ──HTTP POST──→  FastAPI /api/v1/intel/sync/*
  商业情报中转站/topics/*.json    ──→  remote_sync/full_sync.py   ──Bearer Token──→  PostgreSQL intelligence_* 表

用户访问:
  https://intel.xhs365.cn  ──CF──→  Nginx :80  ──→  web-intel/dist/ (SPA)
                                    Nginx /api/  ──→  FastAPI :8000/api/v1/intel/*
```

### 2.2 后端API模块 (server/app/api/intelligence/)

| 模块 | 路由前缀 | 功能 | 鉴权方式 |
|------|---------|------|---------|
| sync.py | /sync/ | 数据同步推送 | Bearer Token (INTEL_SYNC_API_KEY) |
| auth.py | /auth/ | 授权码激活 + 会员查询 | JWT (CurrentUser) |
| admin.py | /admin/ | 授权码管理 | Admin JWT |
| dashboard.py | /dashboard | 仪表盘数据 | JWT + 会员校验 |
| trends.py | /trends | 趋势列表 | JWT + 会员校验 |
| opportunities.py | /opportunities | 商业机会 | JWT + 会员校验 |
| risks.py | /risks | 风险预警 | JWT + 会员校验 |
| topics.py | /topics | 选题库 | JWT + 会员校验 |
| signals.py | /signals | 平台信号 | JWT + 会员校验 |
| emotions.py | /emotions | 用户情绪 | JWT + 会员校验 |
| reports.py | /reports | 报告 | JWT + 会员校验 |

### 2.3 数据库模型 (10张表)

| 表名 | 用途 | 关键索引 |
|------|------|---------|
| intelligence_trends | 趋势数据 | category, platform, lifecycle, trend_status |
| intelligence_opportunities | 商业机会 | category, verdict, status |
| intelligence_risks | 风险预警 | status, severity, risk_type |
| intelligence_xhs_topics | 小红书选题 | hook_type |
| intelligence_platform_signals | 平台信号 | platform (unique) |
| intelligence_user_emotions | 用户情绪 | emotion_type |
| intelligence_reports | 报告 | report_type, report_date |
| intel_auth_codes | 授权码 | status, plan |
| intel_memberships | 会员 | user_id, status |
| intel_sync_batches | 同步批次 | batch_id, created_at |

### 2.4 前端架构 (web-intel/)

- **框架**: Vue 3 + TypeScript + Vite
- **UI库**: Element Plus
- **状态管理**: Pinia (auth.ts + intel.ts)
- **路由**: vue-router (7个数据页面 + 2个独立页面)
- **鉴权**: 独立JWT体系 (intel_token / intel_refresh_token)
- **API封装**: Axios + JWT自动刷新 + 重试机制
- **构建**: 本地构建dist/已提交Git，服务器免build

### 2.5 本地同步客户端 (remote_sync/)

- api_client.py: 5个同步目标 + 批量upsert + 幂等 + checksum
- full_sync.py: 同步主控，支持dry-run、单目标、健康检查
- sync_config.json: 配置文件，remote_host = api.xhs365.cn

---

## 三、关键发现与问题

### 3.1 🔴 服务器Git权限问题（阻塞部署）

**现象**: `git pull origin main` 报错 `insufficient permission for adding an object to repository database .git/objects`

**原因**: 服务器上 `/opt/vuemonitor/.git/objects/` 目录权限不对，可能被root或其他用户创建的文件占用

**解决方案**:
```bash
sudo chown -R $(whoami):$(whoami) /opt/vuemonitor/.git/
# 或
sudo chown -R admin:admin /opt/vuemonitor/.git/
```

### 3.2 🟡 .gitignore 排除 dist/ 但 web-intel/dist 已提交

**问题**: `.gitignore` 第21行有 `dist/` 通配规则，但 `web-intel/dist/` 已成功提交到Git

**分析**: 这是因为 `web-intel/dist/` 是在 `.gitignore` 添加 `dist/` 规则之前就已经被 `git add -f` 强制添加了。Git会继续跟踪已提交的文件，即使匹配.gitignore规则。

**风险**: 如果有人执行 `git rm -r --cached web-intel/dist/`，dist文件会被删除

**建议**: 在 .gitignore 中添加例外 `!web-intel/dist/` 以明确保护

### 3.3 🟡 setup-intel.sh 和 update-v2.sh 不在仓库中

**问题**: V2升级工程实施现状.md 中提到 `sudo bash update-v2.sh` 和 `sudo bash setup-intel.sh`，但这两个脚本在本地仓库中不存在

**影响**: 服务器端无法执行这些脚本，需要手动创建或手动执行命令

### 3.4 🟡 web-intel/nginx.conf 与 nginx/intel.conf 冲突

**问题**: 存在两个intel Nginx配置文件：
- `web-intel/nginx.conf`: Docker容器内使用，包含SSL配置（443端口），指向 `/usr/share/nginx/html/intel`
- `nginx/intel.conf`: 服务器原生部署使用，纯HTTP（80端口），指向 `/opt/vuemonitor/web-intel/dist`

**分析**: 架构决策已确定使用CF Flexible SSL + 源站HTTP，所以 `nginx/intel.conf` 是正确的配置。`web-intel/nginx.conf` 是Docker部署用的，当前不采用Docker部署。

### 3.5 🟡 deploy.ps1 仍包含 npm build 步骤

**问题**: `scripts/deploy.ps1` 中对 web-intel 仍执行 `npm install && npm run build`，但架构决策已改为本地构建+提交dist

**建议**: 更新 deploy.ps1，移除 web-intel 的 npm build 步骤

### 3.6 🟡 前端登录复用主站用户体系

**发现**: web-intel 的 LoginView.vue 调用 `/auth/login` 端点，这是主站的用户登录端点，不是情报系统专用的

**分析**: 这是正确的设计——情报系统用户就是主站用户，通过授权码激活情报会员权限。登录后通过 `/intel/auth/me` 查询情报会员状态。

### 3.7 🟢 会员计划限制逻辑

**发现**: dashboard.py 中定义了 PLAN_LIMITS，free用户只能看3条趋势，weekly看5条，monthly/yearly/enterprise无限制

**注意**: trends.py 中 free 限制3条、weekly限制5条，但 monthly 过滤了 falling 方向的趋势

### 3.8 🟢 同步幂等性

**发现**: sync.py 通过 batch_id 实现幂等——相同 batch_id 的同步请求会被标记为 duplicate 跳过

---

## 四、部署状态总结

| 步骤 | 状态 | 说明 |
|------|------|------|
| 本地代码开发 | ✅ 完成 | 后端API + 前端 + 同步客户端 |
| 本地构建dist | ✅ 完成 | web-intel/dist/ 已提交Git |
| Git push到GitHub | ✅ 完成 | 最新提交 b236989 |
| 服务器git pull | ❌ 失败 | .git/objects 权限不足 |
| 数据库迁移 alembic | ⏳ 待执行 | 依赖git pull成功 |
| 服务重启 vuemonitor | ⏳ 待执行 | 依赖git pull成功 |
| Nginx intel.conf 安装 | ⏳ 待执行 | setup-intel.sh 不存在，需手动 |
| Nginx reload | ⏳ 待执行 | 依赖intel.conf安装 |
| CF DNS intel.xhs365.cn | ❓ 待确认 | 需在CF后台添加A记录 |
| 数据同步 full_sync.py | ⏳ 待执行 | 依赖服务端运行 |
| 端到端验证 | ⏳ 待执行 | https://intel.xhs365.cn 可访问 |
