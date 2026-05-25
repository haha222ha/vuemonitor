# XHS365 全局任务规划（v2）

> 更新日期：2026-05-23 | 基于 v2 深度审计
> 前版日期：2026-05-22

---

## 目标声明

将 XHS365 从「代码完成85%但功能可用40%」推进到「生产就绪、核心业务端到端可用」状态。

---

## 阶段总览

| 阶段 | 名称 | 优先级 | 状态 | 预计子任务 |
|------|------|--------|------|-----------|
| A | 系统现状验证 | P0 | ✅ 完成 | 6 |
| B | AI能力激活 | P0 | ✅ 完成 | 7 |
| **C** | **代码部署与同步** | **P0** | **✅ 完成** | **8** |
| D | Web-Admin API客户端重写 | P0 | ✅ 完成 | 5 |
| E | 核心业务端到端联调 | P1 | **⏳ 自动化已接入** | 12 |
| F | Nginx性能优化 | P1 | ⏳ 待执行 | 4 |
| G | 服务端性能优化 | P1 | ✅ 完成 | 3 |
| H | 框架模块完善 | P2 | ⏳ 待执行 | 4 |
| I | Electron打包发布 | P2 | ⏳ 待执行 | 6 |
| J | 生产环境加固 | P2 | ⏳ 待执行 | 6 |
| K | UI/UX体验优化 | P3 | ⏳ 待执行 | 5 |
| L | 产品化与发布 | P3 | ⏳ 待执行 | 4 |

---

## 阶段 C：代码部署与同步（P0-紧急）

> 阻塞项：SSH授权密钥

### C-1 ~ C-8
- [x] git 一键更新 `host-update.sh` + `HOST_UPDATE.md`
- [x] API health 200 + api_smoke + e2e_api_flow 集成
- [x] `scripts/verify_production.sh` 外网验收
- [x] `scripts/seed_admin.py` 管理员种子
- [x] `local-release.ps1` 本地发版
- [ ] GitHub Secrets 启用 `host-auto-update.yml`（可选）
- [ ] 生产 SMTP / DEEPSEEK_API_KEY 确认（运维）

---

## 阶段 D：Web-Admin API客户端重写（P0-紧急）

> 发现：web-admin/src/utils/api.ts 仅29行，缺少Token刷新/重试/错误处理

### D-1 重写API客户端
- [x] 参照 web-user/src/utils/api.ts (153行) 重写
- [x] 添加Token自动刷新机制
- [x] 添加并发刷新请求队列
- [x] 添加指数退避重试（2次）
- [x] 添加ElMessage错误提示
- [x] 添加响应数据自动解包

### D-2 优化路由守卫
- [x] 移除每次导航的API验证调用
- [x] 改用JWT本地解码验证Token有效性
- [x] 添加admin角色本地校验

### D-3 添加TypeScript支持
- [x] 添加typecheck脚本到package.json
- [x] 修复所有TypeScript类型错误
- [x] 添加API响应类型定义

### D-4 测试验证
- [x] 验证构建通过（npm run build成功）
- [x] 验证TypeScript类型检查通过

### D-5 构建部署
- [x] npm run build 成功
- [ ] 部署到服务器（依赖阶段C）

---

## 阶段 E：核心业务端到端联调（P1-高优）

> 2026-05-25：已添加 `scripts/api_smoke.py` 自动化冒烟；邮件验证码接入 `email_service`；Client `TrendChart` 移除假数据。

### E-1 用户注册登录流程
- [x] API 自动化 `sprint1_runner.py`（注册/登录/刷新/profile）
- [x] Web-User 修复 `fetchUser` → `/user/profile`
- [ ] Client: 注册 → 登录 → Token持久化 → 自动刷新（手工）

### E-2 商品管理流程
- [x] API 自动化：创建/列表/详情
- [ ] 验证商品数据在Web-User和Client间同步

### E-3 数据采集流程
- [ ] Client: 创建采集任务 → Chromium采集 → 数据入库（需 Cookie）
- [ ] 验证采集数据同步到服务端
- [ ] Web-User: 查看采集数据和进度

### E-4 AI分析流程
- [x] API 自动化 `sprint1_runner.py --run-ai`（需 Key）
- [ ] 验证Feature Gate对付费分析的限制

### E-5 监控告警流程
- [x] API 自动化：监控规则+通知列表
- [ ] 规则评估触发真实告警事件（待数据）

### E-6 授权码流程
- [x] API 自动化 `sprint2_runner.py` + 修复 `/license/activate` fingerprint
- [ ] 验证Feature Gate随套餐变化（Web/Client UI）

### E-7 团队协作流程
- [ ] 创建团队 → 邀请成员 → 共享规则/商品
- [ ] 验证权限控制

### E-8 AIPic作图流程
- [ ] 提交作图任务 → 队列处理 → 查看结果
- [ ] 验证积分扣减

### E-9 发现页流程
- [x] API：`/discovery/hot-goods`（sprint2）
- [ ] Discovery DB 文件配置与 UI

### E-10 数据同步流程
- [x] API：push/pull/batch/status（sprint2）
- [ ] Client → Server 端到端（桌面端手工）
- [ ] 冲突检测和解决

### E-11 GDPR合规流程
- [ ] 数据导出请求 → 生成导出包
- [ ] 数据删除请求 → 确认删除

### E-12 Dashboard数据展示
- [ ] 验证统计数据正确性
- [ ] 验证图表渲染
- [ ] 验证趋势数据

---

## 阶段 F：Nginx性能优化（P1-高优）

### F-1 添加Gzip压缩
- [x] 配置gzip on
- [x] 配置gzip_types（text/css, application/javascript, application/json等）
- [x] 配置gzip_min_length 1024
- [ ] 验证压缩率

### F-2 添加静态资源缓存
- [x] CSS/JS: cache-control max-age=31536000, immutable
- [ ] 图片: cache-control max-age=86400
- [x] HTML: cache-control no-cache
- [ ] 添加ETag支持

### F-3 添加安全头
- [x] X-Content-Type-Options: nosniff
- [x] X-Frame-Options: DENY
- [ ] Strict-Transport-Security（如不依赖Cloudflare）

### F-4 添加速率限制
- [x] limit_req_zone by $binary_remote_addr
- [x] API路径: 10r/s
- [x] 静态路径: 30r/s
- [x] 登录路径: 2r/s

---

## 阶段 G：服务端性能优化（P1-高优）

### G-1 限流中间件优化
- [x] 将JWT解码结果缓存到请求state
- [x] 避免在rate_limit中间件中重复解码
- [x] security_audit中间件复用缓存payload

### G-2 数据库连接池调优
- [x] pool_size从20降低到10
- [x] max_overflow从10降低到5
- [x] 适配1.6GB RAM服务器

### G-3 Redis连接优化
- [x] max_connections从50降低到20
- [x] 适配1.6GB RAM服务器

---

## 阶段 H：框架模块完善（P2-中优）

### H-1 崩溃恢复完善
- [ ] 实现任务快照保存
- [ ] 实现检查点机制
- [ ] 实现自动重启逻辑

### H-2 定时任务调度器
- [ ] 实现Cron表达式解析
- [ ] 实现周期性调度
- [ ] 实现失败重试机制

### H-3 通知系统
- [ ] 配置SMTP
- [ ] 实现邮件通知模板
- [ ] 实现通知发送队列

### H-4 Feature Engine云端
- [ ] 复用本地Feature Engine逻辑
- [ ] 添加群体行为聚合
- [ ] 添加匿名化处理

---

## 阶段 I：Electron打包发布（P2-中优）

### I-1 打包环境准备
- [x] `client/scripts/package-win.ps1` 脚本
- [ ] 确认Windows构建环境执行一次

### I-2 首次打包测试
- [ ] npm run build + dist（开发机执行 package-win.ps1）
- [ ] 验证安装包生成并上传 deploy/downloads

### I-3 安装测试
- [ ] 安装XHS365-Setup-0.1.0.exe
- [ ] 验证应用启动
- [ ] 验证登录功能
- [ ] 验证采集功能

### I-4 自动更新配置
- [ ] 配置GitHub Releases
- [ ] 验证electron-updater
- [ ] 测试更新流程

### I-5 代码签名
- [ ] 获取Windows代码签名证书
- [ ] 配置签名流程
- [ ] 验证签名后的安装包

### I-6 发布
- [ ] 创建GitHub Release
- [ ] 上传安装包
- [ ] 更新latest.yml

---

## 阶段 J：生产环境加固（P2-中优）

### J-1 备份加密
- [ ] 修改db-backup服务添加AES-256加密
- [ ] 验证加密备份可恢复
- [ ] 添加密钥管理

### J-2 日志脱敏审计
- [ ] 审计所有logger调用点
- [ ] 确认log_sanitizer覆盖所有路径
- [ ] 添加敏感字段自动过滤

### J-3 Token黑名单
- [ ] 实现JWT黑名单（Redis存储）
- [ ] 登出时添加Token到黑名单
- [ ] 密码修改时批量黑名单

### J-4 监控体系激活
- [ ] 部署Prometheus
- [ ] 部署Grafana
- [ ] 配置告警规则
- [ ] 配置仪表盘

### J-5 CI/CD连接
- [ ] 配置GitHub Secrets（DEPLOY_SSH_KEY等）
- [ ] 测试自动部署流程
- [ ] 添加回滚机制

### J-6 安全审计
- [ ] 运行ZAP安全扫描
- [ ] 修复发现的漏洞
- [ ] 生成安全审计报告

---

## 阶段 K：UI/UX体验优化（P3-低优）

### K-1 大文件拆分
- [ ] SettingsView.vue (1465行) → 拆分为6-8个子组件
- [ ] DashboardView.vue (771行) → 拆分为3-4个子组件

### K-2 设计Token统一
- [ ] 统一CSS变量到tokens.css
- [ ] 移除inline style
- [ ] 确保暗色模式兼容

### K-3 AI分析结果结构化渲染
- [ ] 替换纯文本渲染为结构化组件
- [ ] 添加图表可视化
- [ ] 添加交互式分析结果

### K-4 UI重设计实施
- [ ] 评估2026-05-13-electron-ui-redesign.md
- [ ] 分阶段实施设计变更
- [ ] 验证设计一致性

### K-5 响应式优化
- [ ] 验证窄窗口布局
- [ ] 优化移动端适配
- [ ] 优化表格/图表在小屏幕的表现

---

## 阶段 L：产品化与发布（P3-低优）

### L-1 用户文档
- [x] FAQ `/faq`
- [x] 购买教程 `/purchase` + [docs/SELLING.md](docs/SELLING.md)
- [ ] 视频教程链接

### L-2 定价页面
- [x] PricingView 与 feature_gates 对齐（Premium 500 商品）
- [x] 人工售卖流程（不接支付）

### L-3 落地页优化
- [x] 服务条款 `/terms`、隐私 `/privacy`
- [ ] 添加产品截图/演示
- [ ] 添加客户评价

### L-4 发布检查清单
- [x] 授权码售卖链路（admin 生成 + Web 激活）
- [ ] 浏览器 E2E 手工验收
- [ ] 安全审计通过
- [ ] Windows 安装包上传 `deploy/downloads/`
- [x] `scripts/verify_launch.sh`

---

## 决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-05-23 | 新增阶段D（Admin API重写）为P0 | 发现Admin API客户端仅29行，几乎不可用 |
| 2026-05-23 | 新增阶段F（Nginx优化）为P1 | Nginx缺少gzip/缓存，严重影响性能 |
| 2026-05-23 | 新增阶段G（服务端性能优化）为P1 | JWT重复解码、连接池配置需优化 |
| 2026-05-23 | 将原"代码部署"从阶段C拆出独立 | 部署是所有后续工作的前提 |
| 2026-05-22 | 重新规划10阶段任务 | 基于深度审计结果 |

---

## 遇到的错误

| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
| pool.invalidated属性不存在 | 1 | 改为try/except兼容方案 |
| SSH无授权密钥 | 1 | 需手动添加公钥到服务器 |
