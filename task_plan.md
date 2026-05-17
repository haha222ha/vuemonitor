# XHS365 系统重构工程规划

> 创建日期：2026-05-16 | 版本：V3.0 | 基于：产品重构方案V2.0 + UI/UX方案V2.0 + 视觉设计规范V2.0

---

## 一、项目背景与目标

### 1.1 重构背景

当前系统已完成85%的代码开发，但存在以下核心问题：

| 问题类别 | 具体表现 | 影响 |
|---------|---------|------|
| 产品定位偏差 | 首页是运维监控台，展示采集数/队列数/内存 | 用户打开软件的反应是"我要用什么功能"而非"今天有什么机会" |
| 服务端能力浪费 | 15+个API未被客户端使用（排名/基准/热力图/告警） | 已有的AI能力、特征工程能力未被充分利用 |
| 告警系统重复 | 客户端本地规则 + 服务端告警引擎并存 | 维护两套规则系统，增加复杂度 |
| UI/UX不一致 | Dashboard有渐变圆角卡片，AIView用裸奔inline style | 视觉风格混乱，缺乏品牌识别度 |

### 1.2 重构目标

**产品定位升级**：从"数据监控工具" → "商业情报决策终端"

**用户体验目标**：
- 用户打开软件的第一反应："今天有什么机会"
- 关键操作3步内完成
- 高频信息首屏可见

**设计原则**：
1. **信息先行** - 先展示结论，再展示数据
2. **渐进披露** - 首屏只展示核心，详情按需展开
3. **真实驱动** - FOMO基于真实排名/基准/热力图数据
4. **场景导航** - 按决策场景组织，不按工具功能组织

---

## 二、系统架构（重构后）

### 2.1 双层架构模型

```
┌─────────────────────────────────────────────────────────────┐
│                      服务端 (Python/FastAPI)                   │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ 采集引擎  │  │ AI分析服务    │  │ 特征引擎(CloudFeature) │ │
│  │ CollectEngine│ │ AIService    │  │ ·品类统计              │ │
│  │ ·服务端采集│ │ ·8种分析类型  │  │ ·商品排名              │ │
│  │ ·任务队列  │ │ ·4种报告类型  │  │ ·群体热力图            │ │
│  │           │ │ ·规则引擎兜底│  │ ·行为模式              │ │
│  └──────────┘  └──────────────┘  │ ·匿名基准              │ │
│  ┌──────────┐  ┌──────────────┐  └────────────────────────┘ │
│  │ 监控评估  │  │ 告警引擎      │                            │
│  │ RuleEvaluator│ │AlertRuleEngine│                           │
│  │ ·价格下跌  │ │ ·12种指标    │                            │
│  │ ·销量激增  │ │ ·8种操作符   │                            │
│  │ ·评分下降  │ │ ·3种严重级别 │                            │
│  │ ·库存变化  │ │ ·Webhook/邮件│                            │
│  └──────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                            ↕ 同步 + WebSocket
┌─────────────────────────────────────────────────────────────┐
│                   Electron客户端 (Vue3)                       │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ 本地采集  │  │ 本地SQLite    │  │ 云端同步               │ │
│  │ ChromiumWorker│ │ ·products    │  │ CloudSyncManager      │ │
│  │ Playwright│ │ ·features    │  │ ·push本地数据到云端     │ │
│  │ ·并发控制  │ │ ·monitor_rules│ │ ·pull云端数据到本地     │ │
│  │ ·定时调度  │ │ ·notifications│ │ ·冲突检测与解决        │ │
│  └──────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 职责划分

| 层级 | 职责 | 不做什么 |
|-----|------|---------|
| 服务端 | AI分析、特征计算、排名排序、告警评估、群体洞察、数据聚合 | 不做UI渲染 |
| 客户端 | 数据采集（唯一写入点）、数据展示、用户交互、离线降级 | 不重复做服务端计算 |
| 同步层 | push本地采集数据到云端、pull云端计算结果到本地 | 不做业务逻辑 |

---

## 三、重构实施计划

### Phase 1：首页重构「机会雷达」[P0]

**目标**：将Dashboard从运维监控台改造为商业情报盘

#### Phase 1a：统计卡片替换（最小改动，最大效果）

| 任务 | 涉及文件 | 改动 |
|-----|---------|------|
| 统计卡片替换 | `DashboardView.vue` | 4个运维指标→4个商业指标 |
| 新增首页数据获取逻辑 | `DashboardView.vue` | 调用`/dashboard/stats`+`/feature/product-rankings`+`/alert-rules/events/all` |
| 离线降级 | `DashboardView.vue` | 保留本地Store作为fallback |

**统计卡片对照表**：

| 当前 | 新 | 数据来源 |
|-----|---|---------|
| 监控商品数 | 机会商品数 | `/feature/product-rankings` 排名前30% |
| 活跃采集数 | 今日趋势 | `/dashboard/stats` → `today_trend` |
| 队列任务数 | 异动提醒 | `/alert-rules/events/all` 未确认数 |
| 已调度任务数 | AI洞察 | `/dashboard/stats` → `today_ai_count` |

#### Phase 1b：今日机会榜

| 任务 | 涉及文件 | 改动 |
|-----|---------|------|
| 新增OpportunityCard组件 | `components/OpportunityCard.vue` | 新建 |
| 新增今日机会榜区域 | `DashboardView.vue` | 调用`/feature/product-rankings` |
| 空状态处理 | `DashboardView.vue` | 排名为空时引导添加商品 |

**OpportunityCard设计**：

```
┌──────────────────────────────┐
│  🖼  商品名称A                │
│      店铺名 · 小红书           │
│                               │
│  销量 ████████░░ 87%         │
│  趋势 ↑15.2% (7天)           │
│  阶段 🟢 成长期               │
│                               │
│  [AI分析▾]                    │
└──────────────────────────────┘
```

#### Phase 1c：异动监控区

| 任务 | 涉及文件 | 改动 |
|-----|---------|------|
| 新增AlertEventCard组件 | `components/AlertEventCard.vue` | 新建 |
| 新增异动监控区域 | `DashboardView.vue` | 调用`/alert-rules/events/all` |
| 告警确认操作 | `DashboardView.vue` | 调用`/alert-rules/events/{id}/acknowledge` |

**AlertEventCard设计**：

```
┌──────────────────────────────────────────────┐
│  🔴 CRITICAL                                  │
│  商品A - 价格下跌超过10%                       │
│  触发值: ¥79 (原值: ¥89, 跌幅11.2%)           │
│  10分钟前                                     │
│  [确认] [查看详情] [AI风险分析]                 │
└──────────────────────────────────────────────┘
```

#### Phase 1d：品类热力图增强

| 任务 | 涉及文件 | 改动 |
|-----|---------|------|
| 热力图增强 | `DashboardView.vue` | 增加趋势时间序列 |
| 移除运维指标区 | `DashboardView.vue` | 移除采集状态/并发/内存/队列 |

#### Phase 1 验收标准

- [ ] 首页4个统计卡片显示商业指标（非运维指标）
- [ ] 今日机会榜展示商品排名百分位
- [ ] 异动监控区展示未确认告警事件
- [ ] 品类热力图展示市场趋势
- [ ] 离线状态下显示本地数据降级

---

### Phase 2：导航重构 [P1]

**目标**：将侧边栏从工具思维改为决策思维

| 任务 | 涉及文件 | 改动 |
|-----|---------|------|
| 侧边栏重命名 | `MainLayout.vue` | 数据盘面→机会雷达等 |
| 侧边栏分组调整 | `MainLayout.vue` | 按决策场景分组 |
| 路由更新 | `router/index.ts` | 保持URL兼容，改显示名 |
| 页面标题更新 | `MainLayout.vue` | PAGE_TITLES映射更新 |

**导航分组对照**：

| 现状分组 | 现状内容 | 新分组 | 新内容 |
|---------|---------|--------|--------|
| 核心功能 | 数据盘面/商品监控/AI分析 | 洞察 | 机会雷达/我的商品/AI决策 |
| 工具 | 采集调度/监控规则/通知中心 | 管理 | 告警中心/通知中心/采集调度 |
| 系统 | 设置/授权管理 | 系统 | 设置/授权管理 |

**路由标题映射**：

```typescript
const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "机会雷达",
  "/products": "我的商品",
  "/ai": "AI决策",
  "/monitor": "告警中心",
  "/notifications": "通知中心",
  "/scheduler": "采集调度",
  "/compare": "商品对比",
  "/settings": "设置",
  "/license": "授权管理",
};
```

#### Phase 2 验收标准

- [ ] 侧边栏显示新的导航结构
- [ ] 点击菜单项跳转到正确页面
- [ ] 页面标题正确显示

---

### Phase 3：商品页增强 [P1]

**目标**：增强商品列表和详情页，展示排名百分位和匿名基准

| 任务 | 涉及文件 | 改动 |
|-----|---------|------|
| 商品卡片增加排名 | `ProductsView.vue` | 调用`/feature/product-rankings` |
| 商品详情排名展示增强 | `ProductDetailView.vue` | 优化已有fetchRanking/fetchBenchmark的展示效果 |
| 快捷AI分析按钮 | `ProductsView.vue` | 一键趋势评分/爆品预测 |

**ProductDetailView已有API**（需优化展示）：
- `/feature/product-ranking/{id}` - 排名百分位 ✅已实现
- `/feature/anonymous/price-benchmark` - 价格基准 ✅已实现
- `/feature/anonymous/sales-benchmark` - 销量基准 ✅已实现

**商品详情排名基准卡设计**：

```
┌─ 排名基准 ──────────────────────────────────────────────┐
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 销量排名  │  │ 价格定位  │  │ 评分排名  │              │
│  │  前13%   │  │  偏低    │  │  前25%   │              │
│  │ 超过87%  │  │ 均价¥95 │  │ 超过75%  │              │
│  │ 同类商品  │  │ 你¥79   │  │ 同类商品  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                       │
│  生命周期: 成长期 🟢      竞争力指数: 78/100             │
└───────────────────────────────────────────────────────┘
```

#### Phase 3 验收标准

- [ ] 商品列表显示排名百分位进度条
- [ ] 商品详情页显示排名基准卡
- [ ] 价格/销量基准对比可视化
- [ ] 快捷AI分析按钮可用

---

### Phase 4：AI页优化 [P2]

**目标**：优化AI分析结果展示，增加可视化

| 任务 | 涉及文件 | 改动 |
|-----|---------|------|
| 快捷分析入口 | `AIView.vue` | 基于用户商品提供分析类型快捷按钮 |
| 分析结果可视化 | `AIView.vue` | 仪表盘/等级徽章/三色卡 |
| 报告展示优化 | `AIView.vue` | 更好的结构化渲染 |

**分析结果卡片设计**：

```
┌─ 分析结果 ──────────────────────────────────────────────┐
│  📈 趋势评分 - 商品A                                    │
│                                                       │
│  ████████░░░░ 85%  置信度: 高                         │
│                                                       │
│  "该商品近7天销量持续上升，预计未来3天..."              │
│                                                       │
│  2分钟前 · DeepSeek                                    │
│  [查看完整分析] [再分析]                                │
└───────────────────────────────────────────────────────┘
```

#### Phase 4 验收标准

- [ ] 8种AI分析类型快捷入口可用
- [ ] 分析结果结构化展示（非纯文本）
- [ ] 置信度可视化仪表盘
- [ ] 风险预警三色卡展示

---

### Phase 5：告警系统统一 [P2]

**目标**：统一使用服务端告警引擎，移除客户端本地规则

| 任务 | 涉及文件 | 改动 |
|-----|---------|------|
| 监控规则改用服务端API | `MonitorView.vue` | 从本地IPC改为`/alert-rules` |
| 通知中心整合 | `NotificationsView.vue` | 统一展示3类通知 |
| 本地评估器降级 | `local-evaluator.ts` | 仅离线模式启用 |

**告警系统API**：

| API | 用途 |
|-----|------|
| `GET /alert-rules` | 告警规则列表 |
| `POST /alert-rules` | 创建告警规则 |
| `PUT /alert-rules/{id}` | 更新告警规则 |
| `DELETE /alert-rules/{id}` | 删除告警规则 |
| `GET /alert-rules/events/all` | 告警事件列表 |
| `POST /alert-rules/events/{id}/acknowledge` | 确认告警 |

#### Phase 5 验收标准

- [ ] 告警规则CRUD使用服务端API
- [ ] 告警事件列表展示未确认事件
- [ ] 告警确认操作正常
- [ ] 本地规则仅在离线模式使用

---

## 十五、当前状态总结（2026-05-17）

### 已完成 ✅

| 类别 | 项目 | 状态 |
|------|------|------|
| 数据库 | alert_events 表创建（Alembic迁移） | ✅ |
| 缓存 | Redis 安装并启动 | ✅ |
| 服务端 | 所有核心 API 验证通过 | ✅ |
| 服务端 | `/dashboard/home` SQL 语法修复 | ✅ |
| 服务端 | `/dashboard/trend` GROUP BY + datetime 修复 | ✅ |
| 前端 | Phase 1-5 UI 重构全部完成 | ✅ |
| 前端 | 组件抽取（4个独立组件） | ✅ |
| 前端 | Vite 构建成功 | ✅ |
| 前后端 | Electron 客户端启动，连接服务器 | ✅ |

### API 验证清单

| API | 状态 | 返回数据 |
|-----|------|---------|
| `GET /health` | ✅ 200 | `{"status":"ok","version":"0.1.0"}` |
| `GET /dashboard/home` | ✅ 200 | biz_stats + rankings + alert_events |
| `GET /dashboard/trend?days=7` | ✅ 200 | dates + products + collects + ai_analyses |
| `GET /feature/product-rankings` | ✅ 200 | rankings 数组 |
| `GET /feature/crowd/category-heatmap` | ✅ 200 | heatmap 数组 |
| `GET /feature/crowd/behavior-patterns` | ✅ 200 | lifecycle + trend + price_bands |
| `GET /feature/crowd/trend-timeseries?days=30` | ✅ 200 | series 时间序列 |
| `GET /alert-rules/events/all` | ✅ 200 | 告警事件列表 |
| `GET /ai/analyses` | ✅ 200 | AI 分析记录 |
| `GET /products` | ✅ 200 | 商品列表 |

### 当前运行状态

```
┌─────────────────────────────────────────────┐
│  FastAPI 服务器                              │
│  http://localhost:8000                       │
│  状态: ✅ 运行中                              │
├─────────────────────────────────────────────┤
│  PostgreSQL 数据库                           │
│  localhost:5432                              │
│  状态: ✅ 运行中                              │
├─────────────────────────────────────────────┤
│  Redis 缓存                                  │
│  localhost:6379                              │
│  状态: ✅ 运行中                              │
├─────────────────────────────────────────────┤
│  Electron 客户端 (Vite Dev)                  │
│  http://127.0.0.1:5173                       │
│  状态: ✅ 运行中                              │
└─────────────────────────────────────────────┘
```

---

## 十六、下一步任务规划

### Phase 6：端到端联调验证 [P0] 🔴

**目标**：验证 Electron 客户端登录 → 首页加载 → 各页面数据流通的完整链路

| # | 任务 | 验证内容 | 涉及文件 |
|---|------|---------|---------|
| 6.1 | 登录流程验证 | 用户登录 → JWT Token 获取 → Token 刷新 | `LoginView.vue`, `stores/auth.ts`, `api.ts` |
| 6.2 | 首页数据加载 | Dashboard 加载 → 4个统计卡片 → 机会榜 → 异动监控 → 市场洞察 | `DashboardView.vue` |
| 6.3 | 商品页数据加载 | 商品列表 → 排名百分位 → 商品详情 → 排名基准卡 | `ProductsView.vue`, `ProductDetailView.vue` |
| 6.4 | AI 分析页验证 | AI 分析类型列表 → 分析记录 → 报告列表 | `AIView.vue` |
| 6.5 | 告警页验证 | 告警规则 CRUD → 告警事件列表 → 确认操作 | `MonitorView.vue` |
| 6.6 | 采集调度验证 | 采集任务创建 → 执行 → 结果展示 | `SchedulerView.vue` |
| 6.7 | 通知中心验证 | 通知列表 → 已读/未读 → 通知类型 | `NotificationsView.vue` |

#### Phase 6 验收标准

- [ ] 用户可正常登录并获取 JWT Token
- [ ] 首页 4 个统计卡片显示正确数据
- [ ] 机会榜展示商品排名（或空状态引导）
- [ ] 异动监控展示告警事件（或"暂无异动"）
- [ ] 市场洞察展示热力图/行为模式/趋势
- [ ] 商品列表和详情页数据正常
- [ ] AI 分析页功能可用
- [ ] 告警规则 CRUD 正常
- [ ] 离线降级逻辑正常（断网时显示本地数据）

---

### Phase 7：AI 能力激活 [P0] 🔴

**目标**：配置 AI API Key，验证 9 种 AI 分析类型的端到端流程

| # | 任务 | 说明 |
|---|------|------|
| 7.1 | 配置 AI API Key | 在 `server/.env` 中配置 OpenAI/DeepSeek API Key |
| 7.2 | 验证 basic_analysis | 基础分析：商品综合描述 |
| 7.3 | 验证 trend_score | 趋势评分：销量/评分趋势分析 |
| 7.4 | 验证 prediction | 爆品预测：未来趋势预测 |
| 7.5 | 验证 risk_warning | 风险预警：价格下跌/销量下降预警 |
| 7.6 | 验证 competitor_analysis | 竞品分析：同类商品对比 |
| 7.7 | 验证 product_selection | 选品建议：基于市场数据推荐 |
| 7.8 | 验证 product_optimization | 商品优化：标题/描述/定价建议 |
| 7.9 | 验证 batch_analysis | 批量分析：多商品并行分析 |
| 7.10 | 验证 AI 报告生成 | 4 种报告类型：商品分析/竞品对比/趋势预测/风险评估 |

#### Phase 7 验收标准

- [ ] AI API Key 配置成功
- [ ] 9 种分析类型均可正常调用
- [ ] 规则引擎 fallback 在 AI 不可用时生效
- [ ] AI 分析结果正确展示在客户端
- [ ] 4 种报告类型可正常生成

---

### Phase 8：数据采集链路验证 [P1] 🟡

**目标**：验证从客户端采集到服务端存储的完整数据流

| # | 任务 | 说明 |
|---|------|------|
| 8.1 | 本地采集验证 | Chromium/Playwright 采集小红书商品数据 |
| 8.2 | 数据标准化验证 | 采集数据 → 标准化 → 存入 SQLite |
| 8.3 | 云端同步验证 | 本地数据 → push 到服务端 PostgreSQL |
| 8.4 | 特征计算验证 | 服务端 CloudFeatureEngine 计算排名/基准/热力图 |
| 8.5 | 数据回传验证 | 服务端计算结果 → pull 到客户端展示 |

#### Phase 8 验收标准

- [ ] 本地采集可正常执行并存入 SQLite
- [ ] 云端同步 push/pull 正常
- [ ] CloudFeatureEngine 计算正确
- [ ] 端到端数据流：采集 → 标准化 → 同步 → 计算 → 展示

---

### Phase 9：性能优化与错误处理 [P1] 🟡

**目标**：优化性能，完善错误处理和日志

| # | 任务 | 说明 |
|---|------|------|
| 9.1 | API 响应缓存优化 | Redis 缓存策略调优，减少数据库查询 |
| 9.2 | 前端加载优化 | 骨架屏、懒加载、代码分割 |
| 9.3 | 错误边界处理 | Vue errorBoundary、API 错误统一处理 |
| 9.4 | 日志完善 | 客户端日志 + 服务端日志关联 |
| 9.5 | WebSocket 重连 | 断线重连 + 消息队列 |

---

### Phase 10：生产部署准备 [P2] 🟢

**目标**：准备生产环境部署

| # | 任务 | 说明 |
|---|------|------|
| 10.1 | Electron 打包配置 | electron-builder 配置，Windows/Mac 安装包 |
| 10.2 | 服务端 Docker 化 | Dockerfile + docker-compose 生产配置 |
| 10.3 | 环境变量管理 | 生产环境 .env 配置 |
| 10.4 | CI/CD 流水线 | GitHub Actions 自动构建/测试/部署 |
| 10.5 | 监控告警 | 服务端健康检查 + 告警通知 |

---

## 十七、关键阻塞点与依赖

| # | 阻塞点 | 影响范围 | 解决方案 |
|---|--------|---------|---------|
| B-1 | AI API Key 未配置 | Phase 7 全部 | 需用户提供 OpenAI/DeepSeek API Key |
| B-2 | 远程服务器状态未知 | Phase 10 | 需确认服务器是否可恢复或需重装 |
| B-3 | 小红书采集合规性 | Phase 8 | 需确认采集行为符合平台政策 |
| B-4 | 用户数据量不足 | Phase 6 验证 | 新用户无历史数据，排名/基准/热力图为空 |

---

## 四、API对接清单

### 4.1 首页需要调用的API

| API | 用途 | 调用时机 | 状态 |
|-----|------|---------|------|
| `GET /feature/product-rankings` | 机会榜商品排名 | 页面加载 | 需对接 |
| `GET /alert-rules/events/all` | 异动告警事件 | 页面加载+WS推送 | 需对接 |
| `GET /feature/crowd/category-heatmap` | 品类热力图 | 页面加载 | 需对接 |
| `GET /feature/crowd/behavior-patterns` | 行为模式 | 页面加载 | 需对接 |
| `GET /feature/crowd/trend-timeseries` | 趋势时间序列 | 页面加载 | 需对接 |
| `GET /dashboard/stats` | 统计数据 | 页面加载 | 需对接 |
| `GET /dashboard/trend` | 趋势图 | 页面加载 | 需对接 |
| `GET /dashboard/activities` | 最近活动 | 页面加载 | 需对接 |

### 4.2 商品页需要调用的API

| API | 用途 | 调用时机 | 状态 |
|-----|------|---------|------|
| `GET /feature/product-ranking/{id}` | 单商品排名百分位 | 进入详情 | ✅已实现 |
| `GET /feature/anonymous/price-benchmark` | 价格基准对比 | 进入详情 | ✅已实现 |
| `GET /feature/anonymous/sales-benchmark` | 销量基准对比 | 进入详情 | ✅已实现 |
| `GET /feature/category-stats` | 品类统计 | 进入详情 | 需对接 |

### 4.3 AI页需要调用的API

| API | 用途 | 调用时机 | 状态 |
|-----|------|---------|------|
| `POST /ai/analyze` | 执行AI分析 | 用户触发 | ✅已实现 |
| `POST /ai/report` | 生成报告 | 用户触发 | ✅已实现 |
| `GET /ai/analyses` | 分析记录列表 | 页面加载 | ✅已实现 |
| `GET /ai/reports` | 报告列表 | 页面加载 | ✅已实现 |
| `GET /ai/status` | AI服务状态 | 页面加载 | ✅已实现 |

### 4.4 告警页需要调用的API

| API | 用途 | 调用时机 | 状态 |
|-----|------|---------|------|
| `GET /alert-rules` | 告警规则列表 | 页面加载 | 需对接 |
| `POST /alert-rules` | 创建告警规则 | 用户触发 | 需对接 |
| `PUT /alert-rules/{id}` | 更新告警规则 | 用户触发 | 需对接 |
| `DELETE /alert-rules/{id}` | 删除告警规则 | 用户触发 | 需对接 |
| `GET /alert-rules/events/all` | 告警事件列表 | 页面加载 | 需对接 |
| `POST /alert-rules/events/{id}/acknowledge` | 确认告警 | 用户触发 | 需对接 |

---

## 五、冷启动与空状态设计

服务端排名/基准/热力图数据依赖 `CloudFeatureEngine.compute_all_rankings()` 计算，新用户或数据量少的用户可能面临空数据问题。

| 场景 | 空状态处理 |
|-----|----------|
| 排名数据为空 | 显示"数据积累中，添加更多商品后自动生成排名"，引导添加商品 |
| 品类热力图无数据 | 显示"需连接云端服务并积累数据"，引导配置同步 |
| 匿名基准数据不足 | API返回 `{"benchmark": null, "reason": "数据不足"}`，前端显示"同类商品数据不足，暂无法生成基准" |
| 告警事件为空 | 显示"暂无异动，一切正常" + 绿色安全图标 |
| 首页整体无数据 | 显示引导流程："1.添加商品 → 2.采集数据 → 3.查看洞察" |

---

## 六、离线降级策略

采用"本地优先 + 云端增强"策略，确保离线时首页不会空白：

| 数据 | 本地来源 | 云端来源 | 离线行为 |
|-----|---------|---------|---------|
| 机会商品数 | productStore.productCount | /feature/product-rankings | 显示本地商品数，标注"连接云端查看排名" |
| 今日趋势 | 本地最近两次采集对比 | /dashboard/stats → today_trend | 显示本地计算趋势或"-" |
| 异动提醒 | 本地风控告警 | /alert-rules/events/all | 显示本地风控告警 |
| AI洞察 | 本地AI分析记录数 | /dashboard/stats → today_ai_count | 显示本地分析数 |
| 机会榜 | 无 | /feature/product-rankings | 显示"需连接云端" |
| 品类热力图 | 无 | /feature/crowd/category-heatmap | 显示"需连接云端" |

---

## 七、视觉设计规范（关键摘录）

### 7.1 色彩系统

```
主色调：Indigo（靛蓝）
  Primary-500:  #4F46E5   ← 主色（按钮/链接/活跃态）
  Primary-600:  #4338CA   ← 按钮Active
  Primary-900:  #1E1B4B   ← 侧边栏背景

语义色：
  Success:  #10B981   ← 增长/在线/完成
  Warning:  #F59E0B   ← 告警/注意
  Danger:   #EF4444   ← 下跌/错误/删除
  Info:     #0EA5E9   ← 次要信息

告警级别色：
  Critical:  #EF4444   ← 红色，左侧4px竖条+Badge
  Warning:   #F59E0B   ← 黄色，左侧4px竖条+Badge
  Info:      #10B981   ← 绿色，左侧4px竖条+Badge

生命周期色：
  新品期:  #6366F1   ← 靛蓝Badge
  成长期:  #10B981   ← 绿色Badge
  稳定期:  #64748B   ← 灰色Badge
  衰退期:  #EF4444   ← 红色Badge
```

### 7.2 字号层级

| 层级 | 字号 | 行高 | 用途 |
|-----|------|------|------|
| display | 36px | 44px | 大数字展示（统计卡片数值） |
| h1 | 28px | 36px | 页面标题 |
| h2 | 20px | 28px | 区域标题 |
| h3 | 16px | 24px | 卡片标题 |
| body | 14px | 22px | 正文 |
| body-sm | 13px | 20px | 次要内容 |
| caption | 12px | 16px | 辅助标签/时间戳 |

### 7.3 间距系统

| 场景 | 间距 |
|-----|------|
| 页面内容区padding | 24px |
| 卡片内padding | 16px-20px |
| 卡片间距 | 16px |
| 统计卡片间距 | 16px |
| 按钮组间距 | 8px |
| 侧边栏item间距 | 4px |

### 7.4 圆角系统

```
radius-xs:  4px   ← 小标签内部
radius-sm:  6px   ← Badge/Tag/小按钮
radius-base: 8px  ← 输入框/按钮/下拉
radius-lg:  12px  ← 卡片
radius-xl:  16px  ← 弹窗/对话框
radius-full: 9999px ← 圆形头像/状态点
```

---

## 八、组件清单

### 8.1 新增组件

| 组件 | 文件 | 说明 |
|-----|------|------|
| OpportunityCard | `components/OpportunityCard.vue` | 机会商品卡片 |
| AlertEventCard | `components/AlertEventCard.vue` | 告警事件卡片 |
| StatCard | `components/StatCard.vue` | 统计卡片（已有，需重构） |
| EmptyState | `components/EmptyState.vue` | 空状态组件（已有） |
| TrendBadge | `components/TrendBadge.vue` | 趋势徽章（已有） |
| RankingGauge | `components/RankingGauge.vue` | 排名仪表盘（新建） |

### 8.2 需重构组件

| 组件 | 现有问题 | 重构方向 |
|-----|---------|---------|
| DashboardView.vue | 771行，混杂运维指标 | 拆分为机会雷达布局 |
| ProductDetailView.vue | 已有API调用，展示需增强 | 优化排名基准卡展示 |
| ProductsView.vue | 只显示商品名+时间 | 增加排名百分位+快捷AI |
| AIView.vue | 纯文本展示 | 结构化卡片+可视化 |
| MonitorView.vue | 本地规则 | 改为服务端API |
| MainLayout.vue | 导航项需更新 | 更新导航结构和标题 |

---

## 九、实施优先级与工作量估算

| Phase | 任务 | 优先级 | 工作量 | 风险 |
|-------|------|--------|--------|------|
| Phase 1a | 统计卡片替换 | P0 | 低 | 低 |
| Phase 1b | 今日机会榜 | P0 | 中 | 中（API依赖） |
| Phase 1c | 异动监控区 | P0 | 中 | 中（API依赖） |
| Phase 1d | 品类热力图 | P1 | 中 | 中（API依赖） |
| Phase 2 | 导航重构 | P1 | 低 | 低 |
| Phase 3 | 商品页增强 | P1 | 中 | 低（已有API） |
| Phase 4 | AI页优化 | P2 | 中 | 低 |
| Phase 5 | 告警统一 | P2 | 高 | 中（需迁移数据） |

---

## 十、里程碑

| 里程碑 | 完成条件 | 对应Phase |
|--------|---------|-----------|
| M1: 首页可用 | 统计卡片+机会榜+异动监控可正常展示 | Phase 1 |
| M2: 导航就绪 | 新导航结构上线，用户可正常浏览 | Phase 2 |
| M3: 商品增强 | 商品列表+详情页展示排名基准 | Phase 3 |
| M4: AI优化 | AI分析结果结构化展示 | Phase 4 |
| M5: 告警统一 | 告警系统全部使用服务端API | Phase 5 |

---

## 十一、关键依赖与阻塞点

| # | 阻塞点 | 影响 | 依赖 |
|---|--------|------|------|
| B-1 | 服务端API稳定性 | 前端重构无法测试 | 服务端正常运行 |
| B-2 | `/feature/product-rankings` API | 机会榜无数据 | 云端Feature Engine |
| B-3 | `/alert-rules/events/all` API | 异动监控无数据 | 告警引擎 |
| B-4 | 前后端联调 | 无法验证端到端 | 前后端对接完成 |

---

## 十三、重构实施状态（2026-05-16 评估）

### 已完成 ✅

| Phase | 任务 | 状态 | 说明 |
|-------|------|------|------|
| Phase 1a | 统计卡片替换 | ✅ 已完成 | DashboardView已实现：机会商品/今日趋势/异动提醒/AI洞察 |
| Phase 1b | 今日机会榜 | ✅ 已完成 | API对接 `/feature/product-rankings`，含空状态处理 |
| Phase 1c | 异动监控区 | ✅ 已完成 | API对接 `/alert-rules/events/all`，支持确认操作 |
| Phase 1d | 品类热力图 | ✅ 已完成 | 市场洞察区展示品类热度、行为模式、趋势序列 |
| Phase 2 | 导航重构 | ✅ 已完成 | MainLayout已更新：决策中心/运营工具/系统 分组 |
| Phase 3 | 商品页增强 | ✅ 已完成 | ProductsView已实现排名显示+快捷AI；ProductDetailView已实现排名基准卡+雷达图 |
| Phase 4 | AI页优化 | ✅ 已完成 | AIView已实现快捷分析+智能推荐+置信度可视化+结构化卡片 |
| Phase 5 | 告警统一 | ✅ 已完成 | MonitorView已对接服务端API `/alert-rules` |

### 组件实现状态

| 组件 | 文件 | 状态 |
|-----|------|------|
| StatCard | `components/StatCard.vue` | ✅ 已实现 |
| OpportunityCard | 需新建 | ⚠️ 可复用Dashboard内联组件 |
| AlertEventCard | 需新建 | ⚠️ 可复用Dashboard内联组件 |
| EmptyState | `components/EmptyState.vue` | ✅ 已实现 |
| TrendBadge | `components/TrendBadge.vue` | ✅ 已实现 |
| PageHeader | `components/PageHeader.vue` | ✅ 已实现 |
| SearchInput | `components/SearchInput.vue` | ✅ 已实现 |
| RankingGauge | `components/RankingGauge.vue` | ⚠️ ProductDetailView内联实现 |

### 仍需完善的工作

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P1 | Dashboard代码重构 | 虽有自定义看板功能，但整体结构可进一步模块化 |
| P1 | 组件库建设 | 将Dashboard中的内联组件抽取为独立组件 |
| P2 | API数据验证 | 确认各API实际返回数据格式是否与前端期望一致 |
| P2 | 离线降级验证 | 确认各模块离线状态下的降级表现 |
| P2 | 空状态完善 | 各模块空状态UI一致性 |
| P3 | 动画与交互优化 | 按UI/UX规范实现动效 |

### 核心阻塞点

| # | 阻塞点 | 影响 | 依赖 |
|---|--------|------|------|
| B-1 | 服务端API稳定性 | 前端重构无法测试 | 服务端正常运行 |
| B-2 | `/feature/product-rankings` API | 机会榜无数据 | 云端Feature Engine |
| B-3 | `/alert-rules/events/all` API | 异动监控无数据 | 告警引擎 |
| B-4 | 前后端联调 | 无法验证端到端 | 前后端对接完成 |

---

## 十四、下一步建议行动

### 立即行动（P0）

1. **服务端健康检查** - 验证以下API是否正常返回数据：
   - `GET /dashboard/stats`
   - `GET /feature/product-rankings`
   - `GET /alert-rules/events/all`
   - `GET /feature/crowd/category-heatmap`

2. **前后端联调测试** - 按页面验证数据流：
   - 首页：统计卡片数据来源
   - 商品页：排名百分位API对接
   - 告警页：规则CRUD功能

### 短期优化（P1）

1. **组件抽取** - 将Dashboard内联组件独立：
   - `OpportunityCard.vue`
   - `AlertEventCard.vue`
   - `RankingGauge.vue`

2. **代码模块化** - DashboardView.vue (600+行) 拆分为：
   - `OpportunitySection.vue`
   - `AlertSection.vue`
   - `MarketInsightSection.vue`

### 中期完善（P2）

1. **离线降级测试** - 模拟离线场景验证各模块降级
2. **空状态完善** - 统一各模块空状态UI
3. **动画规范落地** - 按UI/UX文档实现动效

---

## 十二、验收标准总览

### 12.1 Phase 1 验收标准

- [ ] 首页4个统计卡片显示商业指标
- [ ] 今日机会榜展示商品排名百分位
- [ ] 异动监控区展示未确认告警事件
- [ ] 品类热力图展示市场趋势
- [ ] 离线状态下显示本地数据降级

### 12.2 Phase 2 验收标准

- [ ] 侧边栏显示新的导航结构
- [ ] 点击菜单项跳转到正确页面
- [ ] 页面标题正确显示

### 12.3 Phase 3 验收标准

- [ ] 商品列表显示排名百分位进度条
- [ ] 商品详情页显示排名基准卡
- [ ] 价格/销量基准对比可视化
- [ ] 快捷AI分析按钮可用

### 12.4 Phase 4 验收标准

- [ ] 8种AI分析类型快捷入口可用
- [ ] 分析结果结构化展示
- [ ] 置信度可视化仪表盘
- [ ] 风险预警三色卡展示

### 12.5 Phase 5 验收标准

- [ ] 告警规则CRUD使用服务端API
- [ ] 告警事件列表展示未确认事件
- [ ] 告警确认操作正常
- [ ] 本地规则仅在离线模式使用
