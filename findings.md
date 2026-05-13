# XHS365 审计发现记录

> 创建日期：2026-05-13

---

## 一、系统架构发现

### 1.1 整体架构评级：⭐⭐⭐⭐⭐ (95/100)

- 五层混合架构设计完整，模块职责清晰
- 双链路架构（本地采集 vs 云端采集）完全解耦，架构合理
- M06 Proxy Manager已正确废弃并迁入M21-B，本地Electron合规直连
- 数据流单向清晰：采集→标准化→中台→AI→展示

### 1.2 技术栈一致性

| 组件 | 技术栈 | 状态 |
|------|--------|------|
| Electron客户端 | Vue3 + TypeScript + Pinia + Element Plus + ECharts | ✅ 统一 |
| FastAPI服务端 | Python 3.11 + SQLAlchemy 2.0 + asyncpg + Redis | ✅ 统一 |
| Web-user | Vue3 + TypeScript + Vite | ✅ 统一 |
| Web-admin | Vue3 + TypeScript + Vite | ✅ 统一 |
| 共享常量 | shared/constants (TS + PY双版本) | ✅ 统一 |

---

## 二、安全发现

### 2.1 🔴 高危问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| SEC-1 | JWT_SECRET/JWT_REFRESH_SECRET 使用默认值 | server/.env.example | 攻击者可伪造Token |
| SEC-2 | ENCRYPTION_KEY 使用默认值 | server/.env.example | 数据加密形同虚设 |
| SEC-3 | PostgreSQL 默认密码 saas_pass | docker-compose.yml | 数据库可被未授权访问 |
| SEC-4 | ~~服务端未强制HTTPS~~ | ~~Nginx配置~~ | ✅ 已解决：Cloudflare Flexible SSL + 始终HTTPS重定向，用户端流量全程HTTPS |
| SEC-5 | Redis 无密码 | docker-compose.yml | Redis可被未授权访问 |

### 2.2 🟡 中危问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| SEC-6 | CORS开发环境允许localhost | server配置 | 可能被恶意网站利用 |
| SEC-7 | PostgreSQL/Redis端口映射到宿主机 | docker-compose.yml | 外部可直接访问 |
| SEC-8 | 备份文件未加密 | scripts/backup.ps1 | 备份数据泄露风险 |
| SEC-9 | AI API Key未配置 | 服务器.env | AI功能不可用 |

### 2.3 🟢 低危问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| SEC-10 | 日志可能包含敏感信息 | 全局 | 信息泄露风险 |
| SEC-11 | 依赖版本范围宽松 | requirements.txt/package.json | 兼容性风险 |

---

## 三、功能完整性发现

### 3.1 已完成模块（18个）

所有核心模块代码已完成，包括：
- 客户端：M01主进程/M02 UI/M03-A Chromium采集/M03-B Playwright/M03-C标准化/M04数据中台/M05特征引擎/M07存储/M08权限/M09通信
- 服务端：M10 API网关/M11用户/M12授权/M13 Feature Gate/M15 AI引擎/M18数据库
- 前端：M22管理后台/Web-user用户前端

### 3.2 框架就绪但未完善（4个）

| 模块 | 现状 | 缺失 |
|------|------|------|
| M20 崩溃恢复 | 基础结构已有 | 完整的快照/检查点/恢复逻辑 |
| M21 定时任务 | tasks.py基础结构 | 实际调度逻辑、任务队列 |
| M21-B API采集引擎 | engine.py+parsers.py | 实际API调用测试、代理池管理 |
| M23 通知系统 | API端点已有 | WebSocket推送、邮件通知接入 |

### 3.3 待开发模块（3个）

| 模块 | 优先级 | 说明 |
|------|--------|------|
| M14 云端Feature Engine | P2 | 与M05逻辑复用，需增加群体聚合 |
| M16 AI报告生成器 | P2 | 依赖AI分析可用 |
| M17 匿名聚合 | P3 | MVP不需要，数据量足够后再开发 |

---

## 四、部署发现

### 4.1 当前部署状态

- 服务器：阿里云ECS 2C/1.6GB RAM（配置偏低）
- 域名：xhs365.cn（Cloudflare托管，Flexible SSL）
- 部署方式：GitHub同步部署（非Docker）
- 所有服务运行正常：Nginx + uvicorn + PostgreSQL + Redis

### 4.2 部署风险

| # | 风险 | 说明 |
|---|------|------|
| DEP-1 | 服务器内存仅1.6GB | 已添加2GB Swap，但高并发可能不足 |
| DEP-2 | ~~Cloudflare Flexible SSL~~ | ✅ 已解决：CF Flexible SSL + 始终HTTPS重定向，用户端流量全程HTTPS |
| DEP-3 | 单实例部署 | 无高可用，服务中断无法自动恢复 |
| DEP-4 | Electron客户端未打包 | 代码完成但未实际打包测试 |

---

## 五、代码质量发现

### 5.1 服务端

- 代码结构分层清晰：API → Service → Model → Core
- 异常处理统一：自定义异常类 + 全局异常处理器
- 数据库会话管理良好：异步 + 自动提交/回滚
- 缓存策略完善：Redis + 装饰器 + 批量操作

### 5.2 客户端

- 进程隔离严格：主进程/渲染进程IPC通信
- 安全预加载：contextBridge + 白名单通道
- 状态管理模块化：Pinia Store
- 错误恢复：崩溃恢复 + 检查点 + 重试

### 5.3 潜在问题

| # | 问题 | 说明 |
|---|------|------|
| CODE-1 | SQLite JSONB→TEXT修复 | 需确认所有SQLite相关代码已修复 |
| CODE-2 | gate:proxy:* 废弃清理 | 需确认前端/后端所有proxy相关Gate已标记废弃 |
| CODE-3 | M05↔M14字段映射 | 本地features表与云端features表字段映射需验证 |
| CODE-4 | 产品化语言审查 | 需全面检查异常提示是否使用产品化语言 |

---

## 六、业务逻辑发现

### 6.1 会员体系

| 等级 | 监控上限 | AI能力 | 定价策略 |
|------|---------|--------|---------|
| Free | 3个 | 3次/日，基础描述 | 免费（引流） |
| Pro | 50个 | 无限，趋势评分+历史对比 | 授权码 |
| Premium | 无限 | 爆品预测+风险预警+多维评分 | 授权码 |
| Enterprise | 无限 | API+私有部署+自定义AI | 授权码/合同 |

### 6.2 核心转化策略

**数据深度差异**（非功能锁）：
- Free：当前状态数据 → "销量正在上升"
- Pro：历史趋势+基础分析 → "7天增长12%，评分★★★★☆"
- Premium：AI预测+多维模型 → "爆品概率85%，未来3天预测↑"

### 6.3 SaaS演进路线

- Phase 1 (1-3月)：MVP验证 — Free+Pro，小红书，1000用户
- Phase 2 (3-6月)：增长期 — +Premium，+淘宝，10000用户
- Phase 3 (6-12月)：规模期 — +Enterprise，全平台，50000+用户

---

## 七、关键待确认项

| # | 问题 | 影响 | 需要确认方 |
|---|------|------|-----------|
| Q-1 | AI API Key何时配置？ | AI功能无法使用 | 用户/运营 |
| Q-2 | Electron客户端是否需要Mac/Linux版？ | 打包策略 | 用户 |
| Q-3 | 服务器是否需要升级配置？ | 并发承载能力 | 运维 |
| Q-4 | 是否需要对接支付系统？ | 商业化路径 | 产品 |
| Q-5 | 小红书采集合规性确认？ | 法律风险 | 法务 |
