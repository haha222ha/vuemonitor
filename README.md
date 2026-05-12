# XHS365 - 小红书AI选品数据监控与分析工具

## 项目概述

XHS365 是一款基于 Electron 的桌面端数据监控与分析工具，专注于小红书平台的商品数据采集、特征分析、AI 智能选品推荐。系统采用五层混合架构，支持实时采集与后台补充采集，提供本地优先的数据存储与云端同步能力。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron 主控层                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ 窗口管理  │ │ 托盘管理  │ │ IPC 通信  │ │  生命周期管理  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                  Chromium 实时采集层                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │BrowserView│ │ 脚本注入  │ │ 风控对抗  │ │  并发控制     │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
├─────────────────────────────────────────────────────────────┤
│               Playwright 后台补充层                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ 无头浏览器│ │ 截图采集  │ │ 数据提取  │ │  任务调度     │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                   Node 归一化层                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ 数据清洗  │ │ 格式转换  │ │ 去重合并  │ │  质量校验     │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    AI 分析层                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ 特征工程  │ │ 趋势分析  │ │ 竞品对比  │ │  报告生成     │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

### 客户端 (Electron)
- **框架**: Electron 28+
- **前端**: Vue 3 + TypeScript + Vite
- **UI 库**: Element Plus
- **状态管理**: Pinia
- **图表**: ECharts 5
- **数据库**: better-sqlite3 (本地 SQLite)
- **采集引擎**: Chromium BrowserView + Playwright
- **自动更新**: electron-updater

### 服务端 (FastAPI)
- **框架**: FastAPI + Uvicorn
- **ORM**: SQLAlchemy 2.0 (异步)
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7+
- **任务队列**: 自研 Redis 任务队列
- **监控**: Prometheus + Grafana
- **链路追踪**: 自研分布式追踪
- **错误监控**: Sentry (可选)

### Web 管理端
- **框架**: Vue 3 + TypeScript + Vite
- **UI 库**: Element Plus
- **图表**: ECharts 5

## 项目结构

```
vuemonitor/
├── client/                          # Electron 桌面客户端
│   ├── src/
│   │   ├── main/                    # 主进程
│   │   │   ├── index.ts             # 应用入口
│   │   │   ├── preload.ts           # 预加载脚本
│   │   │   ├── collect/             # 采集模块
│   │   │   │   ├── chromium-worker.ts    # Chromium 采集
│   │   │   │   ├── playwright-collector.ts # Playwright 采集
│   │   │   │   ├── normalizer.ts         # 数据归一化
│   │   │   │   ├── data-mart.ts          # 数据集市
│   │   │   │   ├── local-scheduler.ts    # 本地调度器
│   │   │   │   └── concurrency-controller.ts # 并发控制
│   │   │   ├── communication/       # 通信模块
│   │   │   │   └── ws-client.ts     # WebSocket 客户端
│   │   │   ├── sync/                # 同步模块
│   │   │   │   └── cloud-sync.ts    # 云端同步
│   │   │   ├── feature/             # 特征工程
│   │   │   │   └── feature-engine.ts
│   │   │   ├── monitor/             # 监控模块
│   │   │   │   └── local-evaluator.ts
│   │   │   ├── storage/             # 存储模块
│   │   │   │   └── sqlite.ts        # SQLite 数据库
│   │   │   ├── license/             # 授权模块
│   │   │   │   └── license-manager.ts
│   │   │   ├── update/              # 更新模块
│   │   │   │   └── auto-updater.ts
│   │   │   ├── services/            # 服务层
│   │   │   │   ├── window-manager.ts
│   │   │   │   ├── tray-manager.ts
│   │   │   │   ├── offline-mode.ts
│   │   │   │   ├── performance-monitor.ts
│   │   │   │   └── app-lifecycle.ts
│   │   │   ├── recovery/            # 故障恢复
│   │   │   │   └── crash-recovery.ts
│   │   │   ├── logger/              # 日志系统
│   │   │   │   └── logger.ts
│   │   │   └── ipc/                 # IPC 处理器
│   │   │       └── handlers.ts
│   │   └── renderer/                # 渲染进程
│   │       ├── views/               # 页面组件
│   │       ├── stores/              # Pinia 状态
│   │       ├── components/          # 通用组件
│   │       └── i18n/                # 国际化
│   ├── scripts/                     # 构建脚本
│   ├── build/                       # 构建资源
│   └── electron-builder.json        # 打包配置
│
├── server/                          # FastAPI 服务端
│   ├── app/
│   │   ├── main.py                  # 应用入口
│   │   ├── api/                     # API 路由
│   │   │   ├── auth.py              # 认证
│   │   │   ├── products.py          # 商品
│   │   │   ├── monitor.py           # 监控
│   │   │   ├── ai.py                # AI 分析
│   │   │   ├── license.py           # 授权
│   │   │   ├── team.py              # 团队
│   │   │   ├── gdpr.py              # GDPR
│   │   │   ├── alerts.py            # 告警
│   │   │   ├── system.py            # 系统管理
│   │   │   ├── admin.py             # 管理后台
│   │   │   └── ws.py                # WebSocket
│   │   ├── models/                  # 数据模型
│   │   ├── services/                # 业务服务
│   │   │   ├── license_service.py
│   │   │   ├── alert_service.py
│   │   │   ├── backup_service.py
│   │   │   ├── feature_flag.py
│   │   │   ├── sla_monitor.py
│   │   │   ├── error_capture.py
│   │   │   ├── gdpr_service.py
│   │   │   └── audit_service.py
│   │   ├── middleware/              # 中间件
│   │   │   ├── rate_limit.py
│   │   │   ├── quota.py
│   │   │   ├── prometheus.py
│   │   │   ├── tracing.py
│   │   │   ├── security_audit.py
│   │   │   ├── structured_logging.py
│   │   │   └── security_headers.py
│   │   ├── core/                    # 核心模块
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── cache.py
│   │   │   ├── encryption.py
│   │   │   └── graceful_shutdown.py
│   │   ├── task_queue/              # 任务队列
│   │   │   ├── queue.py
│   │   │   └── handlers.py
│   │   └── scheduler/               # 定时任务
│   ├── tests/                       # 测试
│   ├── alembic/                     # 数据库迁移
│   ├── scripts/                     # 工具脚本
│   ├── grafana/                     # Grafana 配置
│   └── Dockerfile
│
├── web-user/                        # Web 管理端
│   └── src/
│       └── views/
│
├── shared/                          # 共享常量
│   └── constants/
│
├── 需求文档/                         # 需求文档
│   └── 工程级系统需求分析文档.md
│
└── docker-compose.yml               # Docker 编排
```

## 快速开始

### 环境要求

- **Node.js**: 18+
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Docker** (可选): 20.10+

### 服务端启动

```bash
# 1. 进入服务端目录
cd server

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等

# 5. 运行数据库迁移
alembic upgrade head

# 6. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker 部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f server

# 停止服务
docker-compose down
```

### 客户端启动

```bash
# 1. 进入客户端目录
cd client

# 2. 安装依赖
npm install

# 3. 开发模式启动
npm run dev

# 4. 构建生产版本
npm run build

# 5. 打包安装包
npm run package
```

### Web 管理端启动

```bash
# 1. 进入 Web 端目录
cd web-user

# 2. 安装依赖
npm install

# 3. 开发模式启动
npm run dev

# 4. 构建生产版本
npm run build
```

## 核心功能

### 1. 数据采集
- **实时采集**: 基于 Chromium BrowserView 的实时数据采集
- **后台采集**: 基于 Playwright 的无头浏览器后台补充采集
- **多平台支持**: 小红书、抖音、淘宝、京东、拼多多
- **风控对抗**: UA 池轮换、请求间隔随机化、验证码检测、Cookie 管理

### 2. 特征工程
- 销售速度分析
- 增长率计算 (7天/30天)
- 波动性评估
- 竞争指数
- 生命周期阶段判断
- 趋势分析 (短期/长期)

### 3. AI 分析
- 商品趋势预测
- 竞品对比分析
- 智能选品推荐
- 报告自动生成
- 多模板支持

### 4. 监控告警
- 价格变动监控
- 销量激增检测
- 库存变化追踪
- 评分下降预警
- 自定义规则引擎
- 多渠道告警 (Webhook/邮件/日志)

### 5. 团队协作
- 团队创建与管理
- 成员邀请与权限控制
- 资源共享 (监控规则/商品)
- 角色管理 (Owner/Admin/Member)

### 6. 数据同步
- 本地优先存储
- 云端自动同步
- 冲突检测与解决
- 离线操作队列
- 增量同步

### 7. 授权管理
- 授权码生成与验证
- 设备绑定
- 配额管理
- 续期与升级
- 吊销管理

## API 文档

启动服务端后，访问以下地址查看 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

生成静态文档：

```bash
cd server
python scripts/generate_api_docs.py
```

## 测试

```bash
# 运行所有测试
cd server
pytest tests/ -v

# 运行单元测试
pytest tests/test_unit.py tests/test_services.py -v

# 运行集成测试
pytest tests/test_api_integration.py -v

# 运行契约测试
pytest tests/test_contract.py -v

# 运行基准测试
pytest tests/test_benchmark.py -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

## 监控与运维

### Prometheus 指标

访问 `http://localhost:8000/metrics` 查看 Prometheus 指标。

### Grafana 仪表盘

导入 `server/grafana/dashboards/system-overview.json` 到 Grafana。

### 健康检查

```bash
curl http://localhost:8000/health
```

### 日志管理

服务端日志输出到标准输出，支持 JSON 格式结构化日志。

客户端日志存储在用户数据目录，支持：
- 日志级别过滤
- 模块过滤
- 日志导出 (JSON/文本)
- 日志上传

## 安全

- **认证**: JWT (Access + Refresh Token)
- **密码**: bcrypt 哈希
- **API 限流**: 基于 Redis 的令牌桶算法
- **数据加密**: AES-256-GCM 本地数据加密
- **安全审计**: 请求风险评分、SQL 注入/XSS 检测
- **GDPR 合规**: 数据导出、删除请求、同意管理
- **速率限制**: 基于计划的差异化限流

## 部署

### 生产环境检查清单

- [ ] 修改所有默认密码和密钥
- [ ] 配置 HTTPS 证书
- [ ] 设置防火墙规则
- [ ] 配置数据库备份策略
- [ ] 设置监控告警
- [ ] 配置日志采集
- [ ] 执行部署验证脚本

```bash
# 运行部署验证
.\scripts\deploy-verify.ps1
```

## 开发指南

### 代码规范

- Python: PEP 8
- TypeScript: ESLint + Prettier
- Vue: Vue 3 Composition API

### 提交规范

使用 Conventional Commits 规范：

```
feat: 新功能
fix: 修复
docs: 文档
style: 格式
refactor: 重构
test: 测试
chore: 构建/工具
```

### 分支策略

- `main`: 生产分支
- `develop`: 开发分支
- `feature/*`: 功能分支
- `fix/*`: 修复分支
- `release/*`: 发布分支

## 许可证

私有软件，保留所有权利。