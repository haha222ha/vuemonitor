# 远程主机升级 Runbook（会员选品报告中心 → V2 情报）

> **前提**：实验室 `local-web-prototype` 与 `run_insight_pipeline.py` 已验收。  
> **原则**：Shadow 先行，双轨并行，Legacy 不断服。

---

## Phase 2a — 数据库（无用户感知）

SSH 登录云主机：

```bash
cd /opt/xhs-cloud
sudo -u postgres psql -d vuemonitor -f /opt/vuemonitor/projects/ai-market-intelligence-v2/docs/07-DATABASE-SCHEMA-V2.sql
# 若文件在 git 中：
# sudo -u postgres psql -d vuemonitor -f /opt/vuemonitor/xhs-cloud/../projects/ai-market-intelligence-v2/docs/07-DATABASE-SCHEMA-V2.sql
```

验证：

```bash
sudo -u postgres psql -d vuemonitor -c "\dt xhs_monitor.insight_*"
```

---

## Phase 2b — 合并代码（Shadow 管道）

### 开发机

1. 将 `projects/ai-market-intelligence-v2/services/*` 复制为 `xhs-cloud/cloud_deploy/reporting/insight_*.py`
2. 将 `cloud-stubs/cloud_insight_report.py` → `xhs-cloud/cloud_deploy/scripts/`
3. 将 `cloud-stubs/insight_routes.py` 合并进 `main.py`（或 `include_router`）
4. `constants.py` 追加：

```python
ARCHIVE_INSIGHT_DAILY = "insight_daily_html"
```

5. `_MEMBER_ARCHIVE_TYPES` 增加 `insight_daily_html`

### 部署

```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main
rsync -a /opt/vuemonitor/xhs-cloud/ /opt/xhs-cloud/ --delete --exclude data --exclude venv --exclude .env
cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh
```

### Shadow 定时任务（只生成不展示）

```bash
# 手动试跑
cd /opt/xhs-cloud
sudo -u admin env PYTHONPATH=/opt/xhs-cloud \
  ./venv/bin/python cloud_deploy/scripts/cloud_insight_report.py \
  --date $(date +%Y-%m-%d) --shadow

# 检查输出目录（不进 report_archives 或 status=shadow）
ls -la data/insight_shadow/
```

---

## Phase 3 — 会员页双 Tab（双轨）

### UI 改动 `member_portal.html`

| Tab | 用户 | 内容 |
|-----|------|------|
| 选品报告（Legacy） | `plan` 含 daily_zip | 现有 zip 下载/预览 |
| AI 市场情报 | `plan` 含 insight | 在线 HTML，无下载 data.js |

JS 新增：

```javascript
async function loadInsightLibrary() {
  const data = await api('/api/v1/member/insight/library', { auth: true });
  renderInsightList(data.items || []);
}
```

### Entitlements

Admin 生成授权码时 `note` JSON：

```json
{"allowed_archive_types":["member_daily_zip"]}
{"allowed_archive_types":["insight_daily_html"]}
{"allowed_archive_types":["member_daily_zip","insight_daily_html"]}
```

---

## Phase 4 — 切换与下线

| 里程碑 | 动作 |
|--------|------|
| 新购停 V1 | 支付套餐只绑 `insight_pro` |
| Legacy 到期 | 自动隐藏 Legacy Tab |
| zip 下载 | 仅 admin 可触发 re-publish |
| PC 发版 | 同步隐藏 V2 用户的 zip 入口 |

---

## 回滚

```bash
# 1. 注释 insight systemd timer
sudo systemctl disable --now xhs-insight-report.timer 2>/dev/null || true
# 2. git revert 合并 commit
# 3. host-update.sh
# V1 member_daily_zip 不受影响
```

---

## 一键部署（代码已 push 后）

```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && rsync -a /opt/vuemonitor/xhs-cloud/ /opt/xhs-cloud/ --delete --exclude data --exclude venv --exclude .env && cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh
```

---

## 监控

```bash
curl -s http://127.0.0.1:8080/api/v1/health
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8080/api/v1/member/insight/library
journalctl -u xhs-cloud-api -n 50 --no-pager
```
