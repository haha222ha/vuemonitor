# AI智能作图模块集成需求文档

> 将 D:\aipic (AI智能作图系统) 作为独立功能模块集成到 vuemonitor (XHS365) 系统中

## 1. 系统对比审计

### 1.1 技术栈差异

| 维度 | aipic (源系统) | vuemonitor (目标系统) |
|------|---------------|---------------------|
| Web框架 | FastAPI (同步) | FastAPI (异步 async/await) |
| 数据库 | SQLite (单文件, 同步) | PostgreSQL (异步 asyncpg) |
| ORM | 原生 sqlite3 + 手写SQL | SQLAlchemy 2.0 (异步, Mapped) |
| 认证 | Cookie + 授权码 | JWT + OAuth2 |
| 用户体系 | 授权码激活, 独立用户表 | 邮箱注册, users 表 |
| 积分体系 | credits 字段 + 独立日志表 | 会员套餐 + FeatureGate 门控 |
| 任务队列 | SQLite 队列表 + 线程Worker | PostgreSQL + 异步任务 |
| 文件存储 | 本地 outputs/ 目录 | 待定 (可对接OSS) |
| 前端 | 原生HTML/JS | Vue3 + Electron |

### 1.2 数据库冲突分析

| 冲突点 | aipic 表名 | vuemonitor 表名 | 冲突级别 |
|--------|-----------|----------------|---------|
| 用户表 | global_user_info | users | **高** - 字段完全不同 |
| 管理员表 | global_admin | rbac_user_role + admin相关 | **高** - 认证机制不同 |
| 操作日志 | global_operation_log | operation_audit_log | **中** - 结构不同 |
| 授权码 | global_auth_codes | license_codes | **中** - 语义重叠但结构不同 |
| 积分日志 | global_credits_log | user_quota | **中** - 设计理念不同 |
| 风格库 | global_style_library | 无对应 | **无** - 新增 |
| 生成队列 | global_generate_queue | 无对应 | **无** - 新增 |
| 用户作品 | user_works (每用户独立DB) | 无对应 | **无** - 新增 |
| 限流 | global_rate_limits / global_user_actions / global_user_freeze | Redis 限流 | **高** - 实现方式不同 |

**结论**: aipic 使用 SQLite，vuemonitor 使用 PostgreSQL，两者数据库引擎完全不同，**不存在表名冲突**。但需要将 aipic 的数据模型迁移到 PostgreSQL 并适配 vuemonitor 的 ORM 体系。

## 2. 集成架构设计

### 2.1 模块边界原则

```
vuemonitor/
├── server/app/
│   ├── api/
│   │   ├── aipic/                    # 新增：AI作图模块路由
│   │   │   ├── __init__.py
│   │   │   ├── generate_routes.py    # 生图API
│   │   │   ├── style_routes.py       # 风格库API
│   │   │   └── aipic_admin_routes.py # 作图管理API
│   ├── models/
│   │   ├── aipic/                    # 新增：AI作图模型
│   │   │   ├── __init__.py
│   │   │   ├── generate.py           # 生成任务/队列模型
│   │   │   ├── style.py              # 风格库模型
│   │   │   ├── credits.py            # 积分模型
│   │   │   └── work.py               # 用户作品模型
│   ├── services/
│   │   ├── aipic/                    # 新增：AI作图业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── generate_service.py   # 图片生成服务
│   │   │   ├── queue_service.py      # 队列管理服务
│   │   │   ├── style_service.py      # 风格库服务
│   │   │   ├── credits_service.py    # 积分服务
│   │   │   └── worker_service.py     # Worker管理服务
│   ├── workers/
│   │   ├── aipic_worker.py           # 新增：异步生成Worker
│   │   └── aipic_cleanup.py          # 新增：清理Worker
```

### 2.2 数据库隔离策略

**核心原则**: 所有 aipic 表使用 `aipic_` 前缀，与 vuemonitor 现有表完全隔离

| aipic 原表 | 迁移后表名 | 所属PostgreSQL |
|-----------|-----------|---------------|
| global_config | aipic_config | vuemonitor (同一库) |
| global_user_info | **不迁移** → 复用 users 表 | - |
| global_auth_codes | aipic_auth_codes | vuemonitor |
| global_credits_log | aipic_credits_log | vuemonitor |
| global_generate_queue | aipic_generate_queue | vuemonitor |
| global_admin | **不迁移** → 复用 RBAC 体系 | - |
| global_operation_log | **不迁移** → 复用 operation_audit_log | - |
| global_daily_summary | aipic_daily_summary | vuemonitor |
| global_style_library | aipic_style_library | vuemonitor |
| global_rate_limits | **不迁移** → 复用 Redis 限流 | - |
| global_user_actions | **不迁移** → 复用 Redis 限流 | - |
| global_user_freeze | **不迁移** → 复用 Redis 限流 | - |
| global_secrets | **不迁移** → 复用 config/env | - |
| user_works (每用户DB) | aipic_user_works | vuemonitor (统一表) |
| user_generate_history | aipic_generate_history | vuemonitor |

### 2.3 用户体系对接

**关键决策**: aipic 用户体系完全废弃，复用 vuemonitor 的 users 表

```
aipic 原用户字段          → vuemonitor 对接方式
─────────────────────────────────────────────
user_id (USER_xxx_xxxx)  → user.id (UUID)
username                  → user.email / user.nickname
auth_code_hash            → 废弃 (JWT认证)
package_type              → user.plan (free/pro/premium/enterprise)
credits                   → aipic_credits (新增字段/独立表)
daily_generate_limit      → PLAN_LIMITS 配置
expire_time               → user_membership.expire_at
status                    → user.is_active
```

**积分体系对接方案**:

新建 `aipic_user_credits` 表，与 users 表一对一关联:

```python
class AipicUserCredits(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_user_credits"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), unique=True)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    total_purchased: Mapped[int] = mapped_column(Integer, default=0)
    total_used: Mapped[int] = mapped_column(Integer, default=0)
    daily_generate_limit: Mapped[int] = mapped_column(Integer, default=10)
    today_generated_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reset_date: Mapped[date] = mapped_column(default=date.today)
```

### 2.4 认证体系对接

```
aipic 原认证              → vuemonitor 对接方式
─────────────────────────────────────────────
Cookie (user_id + session) → JWT Bearer Token
授权码激活登录              → 废弃, 复用 vuemonitor 登录
管理员 Cookie 认证          → 废弃, 复用 RBAC 权限
rate_limit (SQLite)        → Redis 限流 (已有)
```

所有 aipic API 端点使用 `CurrentUser` (JWT) 依赖注入，与 vuemonitor 现有认证完全一致。

### 2.5 权限门控对接

新增 aipic 相关 FeatureGate:

| gate_key | gate_name | required_plan | 说明 |
|----------|-----------|---------------|------|
| gate:aipic:generate | AI作图 | free | 基础文生图/图生图 |
| gate:aipic:hd | 高清画质 | pro | HD画质生成 |
| gate:aipic:ultra | 超清画质 | premium | Ultra画质生成 |
| gate:aipic:style | 风格库 | pro | 自定义风格 |
| gate:aipic:batch | 批量生成 | premium | 批量生图 |
| gate:aipic:api | API访问 | premium | API密钥调用 |

PLAN_LIMITS 新增:

```python
"aipicDailyLimit": {"free": 3, "pro": 50, "premium": 200, "enterprise": -1}
"aipicMaxQuality": {"free": "standard", "pro": "hd", "premium": "ultra", "enterprise": "ultra"}
```

## 3. 数据模型设计 (PostgreSQL + SQLAlchemy 2.0)

### 3.1 AipicConfig - 全局配置

```python
class AipicConfig(Base):
    __tablename__ = "aipic_config"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_model: Mapped[str] = mapped_column(String(50), default="gpt-image-2")
    daily_generate_limit: Mapped[int] = mapped_column(Integer, default=500)
    content_filter_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### 3.2 AipicAuthCode - 授权码

```python
class AipicAuthCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_auth_codes"
    
    auth_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    package_type: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_days: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="未激活")  # 未激活/已激活/已过期
    activate_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("users.id"))
    batch_no: Mapped[str] = mapped_column(String(50), default="")
    batch_name: Mapped[str] = mapped_column(String(100), default="")
    export_tag: Mapped[str] = mapped_column(String(100), default="")
```

### 3.3 AipicCreditsLog - 积分流水

```python
class AipicCreditsLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "aipic_credits_log"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    change_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # purchase/consume/refund/daily_reset
    description: Mapped[str] = mapped_column(String(500), default="")
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
```

### 3.4 AipicGenerateQueue - 生成队列

```python
class AipicGenerateQueue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_generate_queue"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(String(50), default="gpt-image-2")
    ratio_key: Mapped[str] = mapped_column(String(20), default="square")
    style_name: Mapped[str] = mapped_column(String(100), default="")
    task_type: Mapped[str] = mapped_column(String(20), default="text2img")  # text2img/img2img
    quality_tier: Mapped[str] = mapped_column(String(20), default="standard")  # standard/hd/ultra
    credits_cost: Mapped[int] = mapped_column(Integer, default=1)
    input_image_path: Mapped[str] = mapped_column(String(500), default="")
    task_status: Mapped[str] = mapped_column(String(20), default="待执行")  # 待执行/执行中/已完成/失败/已取消
    queue_order: Mapped[float] = mapped_column(Numeric, default=0)
    execute_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fail_reason: Mapped[str] = mapped_column(Text, default="")
    output_image_path: Mapped[str] = mapped_column(String(500), default="")
    seed: Mapped[int] = mapped_column(Integer, default=-1)
```

### 3.5 AipicStyleLibrary - 风格库

```python
class AipicStyleLibrary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_style_library"
    
    style_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    style_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    style_negative_prompt: Mapped[str] = mapped_column(Text, default="")
    preview_image: Mapped[str] = mapped_column(String(500), default="")
    category: Mapped[str] = mapped_column(String(50), default="通用")
    is_preset: Mapped[bool] = mapped_column(Boolean, default=True)
```

### 3.6 AipicUserWork - 用户作品

```python
class AipicUserWork(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_user_works"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    ratio_key: Mapped[str] = mapped_column(String(20), default="square")
    style_name: Mapped[str] = mapped_column(String(100), default="")
    task_type: Mapped[str] = mapped_column(String(20), default="text2img")
    quality_tier: Mapped[str] = mapped_column(String(20), default="standard")
    credits_cost: Mapped[int] = mapped_column(Integer, default=1)
    input_image_path: Mapped[str] = mapped_column(String(500), default="")
    output_image_path: Mapped[str] = mapped_column(String(500), default="")
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
```

### 3.7 AipicDailySummary - 每日统计

```python
class AipicDailySummary(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "aipic_daily_summary"
    
    summary_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    total_generated: Mapped[int] = mapped_column(Integer, default=0)
    active_users: Mapped[int] = mapped_column(Integer, default=0)
```

## 4. API 端点设计

所有端点挂载在 `/api/aipic/` 前缀下，与 vuemonitor 现有 `/api/` 前缀隔离。

### 4.1 生图模块 `/api/aipic/generate`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /text2img | 文生图 | gate:aipic:generate |
| POST | /img2img | 图生图 | gate:aipic:generate |
| GET | /status/{task_id} | 查询任务状态 | 登录用户 |
| GET | /queue | 队列状态 | 登录用户 |
| POST | /cancel/{task_id} | 取消任务 | 登录用户 |
| GET | /models | 可用模型列表 | 公开 |
| GET | /styles | 风格列表 | gate:aipic:style |
| GET | /pricing | 价格方案 | 公开 |

### 4.2 用户模块 `/api/aipic/user`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /works | 我的作品列表 | 登录用户 |
| POST | /works/{id}/favorite | 收藏/取消收藏 | 登录用户 |
| DELETE | /works/{id} | 删除作品 | 登录用户 |
| GET | /works/{id}/download | 下载作品 | 登录用户 |
| GET | /credits | 积分余额 | 登录用户 |
| GET | /credits/log | 积分流水 | 登录用户 |
| GET | /credits/summary | 积分概览 | 登录用户 |
| POST | /credits/activate | 激活授权码 | 登录用户 |

### 4.3 管理模块 `/api/aipic/admin`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /stats | 系统统计 | admin |
| GET | /config | 全局配置 | admin |
| POST | /config | 更新配置 | admin |
| GET | /codes | 授权码列表 | admin |
| POST | /codes/generate | 生成授权码 | admin |
| POST | /codes/batch-generate | 批量生成 | admin |
| DELETE | /codes/{id} | 删除授权码 | admin |
| GET | /codes/batches | 批次列表 | admin |
| GET | /codes/export | 导出授权码 | admin |
| GET | /credits/overview | 积分总览 | admin |
| GET | /credits/log | 全部积分流水 | admin |
| GET | /users/{id}/credits | 用户积分详情 | admin |
| GET | /styles | 风格列表 | admin |
| POST | /styles | 添加风格 | admin |
| DELETE | /styles/{id} | 删除风格 | admin |
| GET | /queue | 队列管理 | admin |
| GET | /workers | Worker状态 | admin |

## 5. 核心业务逻辑迁移

### 5.1 图片生成服务

**原系统**: 同步 httpx 调用 OpenAI API
**迁移方案**: 改为异步 httpx.AsyncClient，集成到 vuemonitor 的异步架构

```python
# services/aipic/generate_service.py
async def generate_image_async(
    prompt: str,
    ratio_key: str = "square",
    quality_tier: str = "standard",
    task_type: str = "text2img",
    input_image_path: str = "",
    style_prompt: str = "",
) -> dict:
    async with httpx.AsyncClient(timeout=180) as client:
        # ... 异步调用 OpenAI API
```

### 5.2 任务队列

**原系统**: SQLite 队列表 + threading Worker 轮询
**迁移方案**: PostgreSQL 队列表 + asyncio Worker

```python
# workers/aipic_worker.py
class AipicWorker:
    async def _worker_loop(self):
        while self.running:
            task = await self._get_next_task()
            if not task:
                await asyncio.sleep(1)
                continue
            await self._execute_task(task)
```

### 5.3 积分体系

**原系统**: SQLite 全局锁 + 直接SQL
**迁移方案**: PostgreSQL 事务 + SQLAlchemy ORM

```python
# services/aipic/credits_service.py
async def deduct_credits(db: AsyncSession, user_id: UUID, amount: int, description: str) -> bool:
    async with db.begin():
        credits = await db.execute(
            select(AipicUserCredits).where(AipicUserCredits.user_id == user_id)
            .with_for_update()
        )
        user_credits = credits.scalar_one_or_none()
        if not user_credits or user_credits.credits < amount:
            return False
        user_credits.credits -= amount
        user_credits.total_used += amount
        log = AipicCreditsLog(
            user_id=user_id,
            change_amount=-amount,
            change_type="consume",
            description=description,
            balance_after=user_credits.credits,
        )
        db.add(log)
    return True
```

### 5.4 限流

**原系统**: SQLite 存储时间戳数组
**迁移方案**: 复用 vuemonitor 已有的 Redis 限流中间件

### 5.5 内容过滤

**原系统**: 关键词匹配 (config中配置)
**迁移方案**: 复用 vuemonitor 的 security_audit 中间件

## 6. 配置项设计

在 vuemonitor 的 `app/config.py` 中新增:

```python
# AI作图模块配置
AIPIC_ENABLED: bool = True
AIPIC_OPENAI_API_KEY: str = ""
AIPIC_OPENAI_BASE_URL: str = "https://api.openai.com/v1"
AIPIC_OPENAI_MODEL: str = "gpt-image-2"
AIPIC_OPENAI_TIMEOUT: int = 180
AIPIC_WORKER_COUNT: int = 3
AIPIC_WORKER_INTERVAL: float = 1.0
AIPIC_MAX_QUEUE_SIZE: int = 1000
AIPIC_OUTPUTS_DIR: str = ""  # 默认 {BASE_DIR}/aipic_outputs
AIPIC_TEMP_DIR: str = ""     # 默认 {BASE_DIR}/aipic_temp
AIPIC_CONTENT_FILTER: bool = True
AIPIC_STUCK_TASK_TIMEOUT_MINUTES: int = 10
AIPIC_CLEANUP_INTERVAL_SECONDS: int = 3600
```

## 7. 前端集成设计

### 7.1 Electron 端

新增 `AipicView.vue` 视图，包含:

- **创作工作台**: 提示词输入 + 画幅选择 + 画质选择 + 风格选择
- **我的作品**: 瀑布流展示 + 收藏/下载/删除
- **积分中心**: 余额 + 流水 + 激活授权码
- **队列状态**: 实时队列位置 + 任务进度

### 7.2 路由注册

```typescript
// client/src/renderer/router/index.ts
{
  path: '/aipic',
  name: 'Aipic',
  component: () => import('../views/AipicView.vue'),
  meta: { title: 'AI作图', icon: 'palette', requiresAuth: true }
}
```

### 7.3 权限控制

```vue
<template>
  <div v-if="hasGate('gate:aipic:generate')">
    <!-- 创作面板 -->
  </div>
  <div v-else>
    <UpgradePrompt feature="AI作图" required-plan="free" />
  </div>
</template>
```

## 8. 冲突规避检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 表名冲突 | ✅ 无冲突 | 所有新表使用 `aipic_` 前缀 |
| API路由冲突 | ✅ 无冲突 | 所有新API使用 `/api/aipic/` 前缀 |
| 用户体系冲突 | ✅ 已解决 | 复用 users 表 + JWT 认证 |
| 管理员体系冲突 | ✅ 已解决 | 复用 RBAC 权限体系 |
| 限流机制冲突 | ✅ 已解决 | 复用 Redis 限流 |
| 日志体系冲突 | ✅ 已解决 | 复用 operation_audit_log |
| 配置项冲突 | ✅ 无冲突 | 所有新配置使用 `AIPIC_` 前缀 |
| 文件存储冲突 | ✅ 无冲突 | 独立 aipic_outputs/ 目录 |
| Redis Key冲突 | ✅ 无冲突 | 使用 `aipic:` 前缀 |
| 前端路由冲突 | ✅ 无冲突 | 使用 `/aipic` 路由前缀 |

## 9. 实施阶段

### Phase 1: 数据模型 + 基础架构 (P0)
1. 创建 aipic 数据模型 (7个表)
2. 注册模型到 `__init__.py`
3. 添加配置项到 `config.py`
4. 创建 aipic API 路由骨架

### Phase 2: 核心业务迁移 (P0)
1. 积分服务 (credits_service.py)
2. 图片生成服务 (generate_service.py)
3. 队列服务 (queue_service.py)
4. 风格库服务 (style_service.py)

### Phase 3: Worker + 清理 (P1)
1. 异步生成 Worker (aipic_worker.py)
2. 清理 Worker (aipic_cleanup.py)
3. 启动生命周期集成

### Phase 4: API 端点实现 (P1)
1. 生图 API (text2img, img2img, status, queue)
2. 用户 API (works, credits)
3. 管理 API (stats, config, codes, styles)

### Phase 5: 权限门控 + 前端 (P2)
1. 新增 aipic FeatureGate
2. Electron 前端页面
3. 路由 + 导航集成

### Phase 6: 测试 + 上线 (P2)
1. 单元测试
2. 集成测试
3. 数据迁移脚本 (如有存量数据)
