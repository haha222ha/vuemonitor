# AI互联网情报系统 — V2工程任务规划

> 创建日期：2026-05-24
> 目标：完成情报系统生产部署 + 后续工程任务

---

## 目标声明

将已开发完成的 AI互联网情报系统 V2 部署到生产环境，解决当前服务器 git 权限阻塞问题，完成 Nginx 配置、数据库迁移、数据同步，并规划后续工程优化任务。

---

## 阶段一：修复服务器Git权限 + 完成代码拉取 [P0-紧急]

**状态**: `in_progress`

### 任务清单

- [ ] 1.1 SSH到服务器，修复 .git/objects 权限
  ```bash
  sudo chown -R admin:admin /opt/vuemonitor/.git/
  ```
- [ ] 1.2 重新执行 git pull origin main
  ```bash
  cd /opt/vuemonitor && git pull origin main
  ```
- [ ] 1.3 验证 web-intel/dist/ 目录存在
  ```bash
  ls -la /opt/vuemonitor/web-intel/dist/index.html
  ```

### 遇到的错误

| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
| insufficient permission for adding an object to repository database .git/objects | 1 | sudo chown -R admin:admin .git/ |

---

## 阶段二：数据库迁移 + 服务重启 [P0-紧急]

**状态**: `pending`

### 任务清单

- [ ] 2.1 执行 Alembic 迁移（创建10张情报表）
  ```bash
  cd /opt/vuemonitor/server && source .venv/bin/activate
  PYTHONPATH=/opt/vuemonitor/server alembic upgrade head
  ```
- [ ] 2.2 验证数据库表已创建
  ```bash
  python -c "from app.core.database import engine; import asyncio; from sqlalchemy import text; async def check(): async with engine.begin() as c: r = await c.execute(text(\"SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'intel%'\"); print([row[0] for row in r]); asyncio.run(check())"
  ```
- [ ] 2.3 重启 FastAPI 服务
  ```bash
  sudo systemctl restart vuemonitor
  ```
- [ ] 2.4 验证 API 健康状态
  ```bash
  curl -s http://localhost:8000/health | python3 -m json.tool
  ```
- [ ] 2.5 验证情报 API 端点可用
  ```bash
  curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/health
  ```

---

## 阶段三：Nginx配置安装 + 域名解析 [P0-紧急]

**状态**: `pending`

### 任务清单

- [ ] 3.1 安装 intel.xhs365.cn Nginx 配置
  ```bash
  sudo cp /opt/vuemonitor/nginx/intel.conf /etc/nginx/sites-available/intel.xhs365.cn
  sudo ln -sf /etc/nginx/sites-available/intel.xhs365.cn /etc/nginx/sites-enabled/intel.xhs365.cn
  ```
- [ ] 3.2 测试 Nginx 配置
  ```bash
  sudo nginx -t
  ```
- [ ] 3.3 重载 Nginx
  ```bash
  sudo systemctl reload nginx
  ```
- [ ] 3.4 验证本地HTTP访问
  ```bash
  curl -s -o /dev/null -w '%{http_code}' -H "Host: intel.xhs365.cn" http://localhost/
  ```
- [ ] 3.5 Cloudflare 后台添加 intel.xhs365.cn DNS 记录
  - 类型: A
  - 名称: intel
  - 内容: 服务器IP
  - 代理状态: Proxied (橙色云朵)
  - SSL: Flexible
- [ ] 3.6 验证 HTTPS 访问
  ```bash
  curl -s -o /dev/null -w '%{http_code}' https://intel.xhs365.cn
  ```

---

## 阶段四：数据同步验证 [P1-重要]

**状态**: `pending`

### 任务清单

- [ ] 4.1 确认服务器 .env 中 INTEL_SYNC_API_KEY 已配置
  ```bash
  grep INTEL_SYNC_API_KEY /opt/vuemonitor/server/.env
  ```
- [ ] 4.2 确认 CORS_ORIGINS 包含 intel.xhs365.cn
  ```bash
  grep intel.xhs365.cn /opt/vuemonitor/server/.env
  ```
- [ ] 4.3 本地执行 dry-run 验证
  ```bash
  cd D:\vuemonitor\AI互联网信息量化\remote_sync
  python full_sync.py --dry-run --base-url https://api.xhs365.cn --api-token <TOKEN>
  ```
- [ ] 4.4 执行完整数据同步
  ```bash
  python full_sync.py --base-url https://api.xhs365.cn --api-token <TOKEN>
  ```
- [ ] 4.5 验证同步结果（检查各表数据量）
  ```bash
  curl -s -H "Authorization: Bearer <JWT>" https://api.xhs365.cn/api/v1/intel/dashboard
  ```

---

## 阶段五：端到端功能验证 [P1-重要]

**状态**: `pending`

### 任务清单

- [ ] 5.1 访问 https://intel.xhs365.cn 验证前端加载
- [ ] 5.2 测试登录功能（使用主站账号）
- [ ] 5.3 测试授权码激活流程
- [ ] 5.4 测试仪表盘数据展示
- [ ] 5.5 测试各数据列表页（趋势/机会/风险/选题/信号/情绪）
- [ ] 5.6 测试会员权限限制（free vs pro）

---

## 阶段六：工程优化任务 [P2-后续]

**状态**: `pending`

### 6.1 代码修复

- [ ] 6.1.1 更新 .gitignore 添加 `!web-intel/dist/` 例外
- [ ] 6.1.2 更新 scripts/deploy.ps1 移除 web-intel npm build 步骤
- [ ] 6.1.3 创建 setup-intel.sh 部署脚本并提交到仓库
- [ ] 6.1.4 创建 update-v2.sh 更新脚本并提交到仓库

### 6.2 管理端集成

- [ ] 6.2.1 在 web-admin 中添加授权码管理界面
  - 生成授权码
  - 查看授权码列表
  - 吊销授权码
  - 查看授权码统计

### 6.3 安全增强

- [ ] 6.3.1 授权码 SHA256 哈希存储（当前存明文）
- [ ] 6.3.2 企业级 client_id + client_secret
- [ ] 6.3.3 HMAC 签名验证
- [ ] 6.3.4 使用日志表 (auth_code_usage_logs)
- [ ] 6.3.5 Redis 缓存集成（JWT黑名单/限流）

### 6.4 功能增强

- [ ] 6.4.1 会员到期自动降级定时任务
- [ ] 6.4.2 报告生成 API（PDF/HTML导出）
- [ ] 6.4.3 静态数据预构建（Phase 2优化层）

### 6.5 清理

- [ ] 6.5.1 删除 notion_sync/ 目录
- [ ] 6.5.2 更新 V2升级工程实施现状.md 完成状态

---

## 关键决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-05-24 | 服务器git权限用 chown 修复 | admin用户是部署用户，.git应归admin所有 |
| 2026-05-24 | 使用 nginx/intel.conf（纯HTTP）而非 web-intel/nginx.conf（SSL） | CF Flexible SSL，源站无需证书 |
| 2026-05-24 | 手动执行部署命令而非脚本 | setup-intel.sh 不在仓库中，手动更可控 |
