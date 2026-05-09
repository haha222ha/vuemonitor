# VueMonitor 完整部署与使用教程

---

## 先搞清楚一件事：你的服务器在哪？

VueMonitor 分为 **3 个部分**，它们可以运行在同一台机器上，也可以分开：

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │  Electron    │   │  Web Admin  │   │  FastAPI    │       │
│  │  桌面客户端  │   │  管理后台   │   │  后端服务   │       │
│  │             │   │             │   │             │       │
│  │  用户电脑上 │   │  服务器上   │   │  服务器上   │       │
│  │  (Windows)  │   │  (浏览器)   │   │  (Python)   │       │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │                 │                 │               │
│         └────────┬────────┘                 │               │
│                  │                          │               │
│                  ▼                          ▼               │
│           都需要知道                    需要连接            │
│          服务器的IP地址              PostgreSQL + Redis     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**核心问题：客户端和管理后台怎么找到后端服务？**
答案：通过 `VITE_API_BASE_URL` 这个配置项，告诉它们服务器在哪。

---

## 场景一：全部在自己电脑上（最简单）

> 适合：开发调试、个人使用
> 条件：一台 Windows 电脑

### 步骤

```
1. 右键 setup.bat → 以管理员身份运行
2. 等它跑完（大约5-10分钟，取决于网速）
3. 自动弹出3个窗口：API服务、客户端、管理后台
4. 完成！
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 客户端 | http://localhost:5173 |
| 管理后台 | http://localhost:5174 |
| API 文档 | http://localhost:8000/docs |

### 以后每次使用

```
双击 start.bat → 自动启动全部服务
```

### 如果要打包给朋友用

```
双击 build.bat
→ 提示输入服务器地址时，输入 http://你的IP:8000
→ 等构建完成
→ 把 client\release\ 里的安装程序发给朋友
```

> **注意**：朋友安装后，你的电脑必须开着并且运行着 API 服务，朋友才能使用。

---

## 场景二：部署到云服务器（推荐）

> 适合：正式使用、多人共享
> 条件：一台云服务器（阿里云/腾讯云/AWS）+ 你的 Windows 电脑

### 整体流程

```
你的 Windows 电脑                    云服务器 (Linux)
─────────────────                    ──────────────
                                     1. 上传代码
                                     2. 运行 deploy.sh
                                        → 自动装好一切
                                     3. API 服务跑起来了

3. 双击 build.bat
   → 输入服务器IP
   → 打包出安装程序
4. 把安装程序分发给用户
```

### 第一步：准备云服务器

**最低配置：**
- CPU: 2核
- 内存: 4GB
- 硬盘: 40GB
- 系统: Ubuntu 22.04 / CentOS 8+
- 需要开放端口: 80, 8000

### 第二步：上传代码到服务器

**方式 A：用 Git（推荐）**
```bash
# 在服务器上
git clone https://你的仓库地址.git /opt/vuemonitor
```

**方式 B：用 SCP 直接传**
```bash
# 在你的 Windows 电脑上（PowerShell）
scp -r D:\vuemonitor root@你的服务器IP:/opt/vuemonitor
```

**方式 C：用宝塔面板**
```
宝塔面板 → 文件 → 上传 → 把整个 vuemonitor 文件夹上传到 /opt/
```

### 第三步：在服务器上一键部署

```bash
# SSH 登录服务器
ssh root@你的服务器IP

# 进入项目目录
cd /opt/vuemonitor

# 一键部署
sudo bash deploy.sh
```

这个脚本会自动完成：
- ✅ 安装 Python 3.11、Node.js 20、PostgreSQL 16、Redis 7、Nginx
- ✅ 创建数据库和用户
- ✅ 导入 Schema 和种子数据
- ✅ 生成安全密钥（JWT、加密密钥）
- ✅ 安装项目依赖
- ✅ 注册为系统服务（开机自启）
- ✅ 配置 Nginx 反向代理

部署完成后，服务器上就跑起来了：
- API: `http://你的服务器IP/api/v1`
- 管理后台: `http://你的服务器IP`
- API 文档: `http://你的服务器IP/docs`

### 第四步：在你的电脑上打包客户端

```
1. 双击 build.bat
2. 提示输入服务器地址时输入: http://你的服务器IP
   例如: http://123.45.67.89
3. 等构建完成
4. 把 client\release\VueMonitor Setup.exe 发给用户
```

用户安装后，客户端会自动连接到你服务器上的 API。

### 第五步：配置 AI 功能（可选）

```bash
# 在服务器上编辑配置
nano /opt/vuemonitor/server/.env

# 修改这两行：
OPENAI_API_KEY=sk-你的OpenAI密钥
DEEPSEEK_API_KEY=sk-你的DeepSeek密钥

# 重启服务
systemctl restart vuemonitor
```

### 服务器日常管理

```bash
# 查看服务状态
systemctl status vuemonitor

# 查看实时日志
journalctl -u vuemonitor -f

# 重启服务
systemctl restart vuemonitor

# 停止服务
systemctl stop vuemonitor

# 更新代码后重新部署
cd /opt/vuemonitor
git pull
sudo bash deploy.sh
```

---

## 场景三：Docker 部署（最省心）

> 适合：不想折腾环境、快速上线
> 条件：服务器装了 Docker

### 第一步：安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 或者用宝塔面板 → Docker管理器 → 安装
```

### 第二步：上传代码

同场景二的第二步。

### 第三步：一键启动

```bash
cd /opt/vuemonitor
docker compose up -d --build
```

等几分钟，自动完成：
- ✅ 构建 API 服务镜像
- ✅ 构建管理后台镜像
- ✅ 启动 PostgreSQL（自动导入 Schema）
- ✅ 启动 Redis
- ✅ 启动 Nginx 反向代理

### 第四步：配置 AI 密钥

```bash
# 编辑 .env 文件
nano /opt/vuemonitor/.env

# 添加：
OPENAI_API_KEY=sk-你的key

# 重启
docker compose restart
```

### Docker 日常管理

```bash
# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f server

# 重启
docker compose restart

# 停止
docker compose down

# 更新代码后重新构建
docker compose up -d --build

# 完全重置（包括数据库）
docker compose down -v
docker compose up -d --build
```

### Windows 上 Docker 部署

如果你想在 Windows 上用 Docker：
```
双击 docker-deploy.bat → 等着就行
```

---

## 场景四：已有服务器环境（手动配置）

> 适合：服务器已有 PostgreSQL/Redis，不想重装

### 第一步：修改配置

```
双击 config.bat → 选 3 → 修改数据库密码
```

或者手动编辑 `server\.env`：

```env
DB_HOST=你的数据库地址
DB_PORT=5432
DB_NAME=vuemonitor
DB_USER=你的用户名
DB_PASSWORD=你的密码
REDIS_HOST=你的Redis地址
REDIS_PORT=6379
```

### 第二步：初始化数据库

```bash
psql -U 你的用户名 -d vuemonitor -f database/schema.sql
psql -U 你的用户名 -d vuemonitor -f database/seed.sql
```

### 第三步：启动

```
双击 start.bat
```

---

## 配置详解：每个文件控制什么？

### 文件关系图

```
vuemonitor/
├── server/.env          ← 后端服务所有配置（数据库、密钥、AI、邮件）
├── client/.env          ← 客户端连接哪个服务器（VITE_API_BASE_URL）
├── web-admin/.env       ← 管理后台连接哪个服务器（VITE_API_BASE_URL）
├── .env                 ← Docker Compose 用的配置
└── docker-compose.yml   ← Docker 容器编排
```

### server/.env 关键配置说明

```env
# ═══════ 必须修改（生产环境）═══════

# JWT 签名密钥 — 生成方法：
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET=这里放生成的密钥
JWT_REFRESH_SECRET=这里放另一个生成的密钥

# 数据加密密钥 — 生成方法：
#   python -c "import secrets; print(secrets.token_hex(16))"
ENCRYPTION_KEY=这里放生成的32位hex

# ═══════ 数据库连接 ═══════

DB_HOST=localhost       # 数据库地址，Docker 里填 postgres
DB_PORT=5432
DB_NAME=vuemonitor
DB_USER=saas_user
DB_PASSWORD=saas_pass   # 改成你自己的强密码

# ═══════ Redis ═══════

REDIS_HOST=localhost    # Redis地址，Docker 里填 redis
REDIS_PORT=6379

# ═══════ AI 服务（至少配一个）═══════

AI_DEFAULT_PROVIDER=openai    # openai 或 deepseek
AI_DEFAULT_MODEL=gpt-4o-mini  # 模型名
OPENAI_API_KEY=sk-xxx         # OpenAI 密钥
DEEPSEEK_API_KEY=sk-xxx       # DeepSeek 密钥（备用）

# ═══════ 跨域配置 ═══════

# 允许哪些网址访问 API，必须包含客户端和管理后台的地址
CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]

# 如果部署到服务器，要加上服务器的地址：
# CORS_ORIGINS=["http://123.45.67.89","http://123.45.67.89:5174","http://localhost:5173"]
```

### client/.env 和 web-admin/.env

这两个文件只有一个配置项：

```env
# 后端 API 的完整地址
VITE_API_BASE_URL=http://localhost:8000/api/v1

# 本地开发 → http://localhost:8000/api/v1
# 远程服务器 → http://123.45.67.89/api/v1
# 域名 → https://api.example.com/api/v1
```

> **重要**：这个值在 `npm run build` 时会被写死到代码里。所以打包前必须确认地址正确！

---

## build.bat 详解：服务器地址怎么配？

### 方式 A：交互式（推荐）

```
双击 build.bat
→ 弹出提示："请输入你的服务器地址"
→ 输入: http://123.45.67.89
→ 回车，自动构建
```

### 方式 B：命令行参数

```bash
# 在 cmd 或 PowerShell 中
build.bat http://123.45.67.89
```

### 方式 C：用 config.bat 预先配置

```
1. 双击 config.bat → 选 1 → 输入服务器地址
2. 双击 build.bat → 直接回车（使用已配置的地址）
```

### 不同场景的地址填写

| 场景 | 输入 |
|------|------|
| 本地开发 | `http://localhost:8000` |
| 局域网服务器 | `http://192.168.1.100:8000` |
| 云服务器（有IP） | `http://123.45.67.89` |
| 云服务器（有域名） | `https://api.example.com` |
| Docker 部署（Nginx代理） | `http://123.45.67.89` |

> **注意**：如果服务器配了 Nginx（deploy.sh 会自动配），API 在 80 端口，不需要加 `:8000`。

---

## 防火墙与安全组配置

### 云服务器需要开放的端口

| 端口 | 用途 | 是否必须 |
|------|------|----------|
| 80 | Nginx（管理后台+API代理） | ✅ 必须 |
| 8000 | API 直连（调试用） | ❌ 可选 |
| 5432 | PostgreSQL | ❌ 不建议开放 |
| 6379 | Redis | ❌ 不建议开放 |
| 22 | SSH | ✅ 必须 |

### 阿里云/腾讯云安全组设置

```
入方向规则：
  80/TCP   允许 0.0.0.0/0    ← 允许所有IP访问
  22/TCP   允许 你的IP       ← 只允许你SSH
```

### Ubuntu 防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

---

## 完整操作速查表

### Windows 本地开发

| 操作 | 方法 |
|------|------|
| 首次安装 | 右键 `setup.bat` → 管理员运行 |
| 启动服务 | 双击 `start.bat` |
| 停止服务 | 关闭终端窗口 |
| 修改配置 | 双击 `config.bat` |
| 打包客户端 | 双击 `build.bat` |
| 运行测试 | `cd server && poetry run pytest` |

### Linux 服务器

| 操作 | 命令 |
|------|------|
| 首次部署 | `sudo bash deploy.sh` |
| 查看状态 | `systemctl status vuemonitor` |
| 重启服务 | `systemctl restart vuemonitor` |
| 查看日志 | `journalctl -u vuemonitor -f` |
| 修改配置 | `nano /opt/vuemonitor/server/.env` 然后 `systemctl restart vuemonitor` |
| 更新代码 | `git pull && sudo bash deploy.sh` |

### Docker

| 操作 | 命令 |
|------|------|
| 首次部署 | `docker compose up -d --build` |
| 查看状态 | `docker compose ps` |
| 查看日志 | `docker compose logs -f server` |
| 重启 | `docker compose restart` |
| 停止 | `docker compose down` |
| 更新 | `git pull && docker compose up -d --build` |
| 完全重置 | `docker compose down -v && docker compose up -d --build` |

---

## 常见问题

### Q: 客户端打开后白屏/连接失败？

**原因**：客户端找不到后端 API。

**解决**：
1. 确认后端服务在运行：浏览器打开 `http://服务器IP:8000/docs`
2. 如果打不开，检查防火墙是否开放了端口
3. 用 `config.bat` → 选 1 → 重新输入正确的服务器地址
4. 重新 `build.bat` 打包

### Q: 管理后台登录后跳回登录页？

**原因**：CORS 配置不正确。

**解决**：编辑 `server\.env`，在 `CORS_ORIGINS` 中添加管理后台的访问地址：
```env
CORS_ORIGINS=["http://123.45.67.89","http://localhost:5174"]
```
然后重启服务。

### Q: AI 分析报错？

**原因**：未配置 AI 密钥或密钥无效。

**解决**：
1. 双击 `config.bat` → 选 2 → 输入 API Key
2. 或编辑 `server\.env` 中的 `OPENAI_API_KEY`
3. 重启服务

### Q: 服务器重启后服务没了？

**Linux 服务器**：`deploy.sh` 已注册开机自启，重启后自动运行。

**Docker**：`docker compose.yml` 已设置 `restart: unless-stopped`，重启后自动运行。

**Windows 本地**：需要手动双击 `start.bat`。

### Q: 如何修改管理员密码？

```bash
# 在服务器上
cd /opt/vuemonitor/server
poetry run python -c "
from app.core.security import hash_password
print(hash_password('你的新密码'))
"
# 复制输出的哈希值

psql -U saas_user -d vuemonitor -c "UPDATE users SET password_hash='上面复制的哈希值' WHERE role='admin';"
```

### Q: 如何备份数据？

```bash
# 备份数据库
pg_dump -U saas_user vuemonitor > backup_$(date +%Y%m%d).sql

# 恢复
psql -U saas_user vuemonitor < backup_20250101.sql
```
