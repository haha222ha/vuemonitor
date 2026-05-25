# Sprint 1 & 2 执行手册

## Sprint 1（P0）— SaaS 赚钱路径

| ID | 内容 | 自动化 |
|----|------|--------|
| E-1 | 注册/登录/刷新/资料 | `scripts/sprint1_runner.py` |
| E-2 | 商品 CRUD | 同上 |
| E-5 | 监控规则+通知 | 同上 |
| E-4 | AI basic_analysis | `--run-ai` 需 `DEEPSEEK_API_KEY` |

**Web 修复**：`web-user` 登录后用 `/user/profile` 拉用户信息。

### 主机执行

```bash
cd /opt/vuemonitor/server && source .venv/bin/activate && \
  python3 ../scripts/sprint1_runner.py --base-url http://127.0.0.1:8000
```

带 AI：

```bash
RUN_AI=1 bash /opt/vuemonitor/scripts/run_sprints.sh
```

## Sprint 2（P1）— 同步 + 授权码

| ID | 内容 | 自动化 |
|----|------|--------|
| E-10 | sync push/pull/status | `scripts/sprint2_runner.py` |
| E-6 | Admin 发码 → 用户激活 | 需先 `seed_admin.py` |
| E-9 | Discovery hot-goods | 同上 |

### 首次 Admin

```bash
python3 ../scripts/seed_admin.py --email admin@xhs365.cn --password '强密码'
```

### 完整 Sprint 2

```bash
ADMIN_EMAIL=admin@xhs365.cn ADMIN_PASSWORD='强密码' \
  python3 ../scripts/sprint2_runner.py --base-url http://127.0.0.1:8000
```

## Electron 打包（仅 Windows 开发机）

```powershell
cd D:\vuemonitor\client
.\scripts\package-win.ps1
```

产物：`deploy/downloads/XHS365-Setup-latest.exe`（需自行 commit dist 或 SCP 到服务器 downloads 目录）。

## Client 采集（需人工 Cookie）

自动化无法在无头服务器完成小红书 BrowserView 采集。步骤：

1. 桌面端登录
2. 设置页导入 Cookie
3. 采集中心添加笔记链接
4. 查看本地库 + 云同步状态

## 集成到 host-update

`host-update.sh` 已自动跑 `run_sprints.sh`（默认 `RUN_AI=0`）。
