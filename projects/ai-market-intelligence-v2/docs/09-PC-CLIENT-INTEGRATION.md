# PC 端 ProductAnalyzer 对接方案

> **代码仓库**：`E:\小红书监控系统所有文件相关\xhs_shelf_time`（不在 vuemonitor 内）  
> **云端 API**：与 Web 会员中心相同 `https://monitor.xhs365.cn`  
> **设备标识**：`pc:{machine_id}`（与 Web `web:` 分槽，单设备登录）

---

## 1. 现状（V1）

| 模块 | 行为 |
|------|------|
| `core/cloud_client.py` | 登录、会员状态、反馈、关键词 |
| 报告 | 调用 `/api/v1/member/library` + `/download` 拉 zip |
| 上传 | plan_b `POST /api/v1/sync/report-upload`（Sync Key / 会员态） |
| 收藏 | `/api/v1/member/watchlist` 与 Web 共享 |

---

## 2. V2 目标

**定位**：AI 市场研究助手 — 用户看自己关注的方向 + 读 AI 情报，不批量导出商品表。

| 功能 | V2 行为 |
|------|---------|
| 情报列表 | `GET /api/v1/member/insight/library` |
| 阅读报告 | 内嵌 WebView 或系统浏览器打开 `.../insight/{date}/{category}/view` |
| Legacy zip | 仅 `plan_code` 含 legacy 时显示「数据报告」菜单 |
| 本地上传 zip | Legacy 维护期保留；V2 新用户隐藏 |
| 用户笔记 | 本地 SQLite + 可选云同步（Phase 3+） |

---

## 3. cloud_client.py 新增接口

**补丁草案（可合并）**：`cloud-stubs/pc_cloud_client_v2_patch.py`  
**合并说明**：`cloud-stubs/PC-1-CLOUD-CLIENT-INTEGRATION.md`

参考实现片段：

```python
def fetch_insight_library() -> dict:
    code, data = _request("GET", "/api/v1/member/insight/library", token=get_token(), timeout=30)
    if code != 200:
        raise RuntimeError(_api_error(data, code, "获取情报库失败"))
    return data

def insight_view_url(report_date: str, category: str) -> str:
    from urllib.parse import quote
    base = get_cloud_base_url().rstrip("/")
    token = get_token() or ""
    q = f"?access_token={quote(token)}" if token else ""
    return f"{base}/api/v1/member/insight/{report_date}/{quote(category)}/view{q}"
```

---

## 4. UI 改造（Electron / PyWebView）

### 4.1 侧栏菜单

```
报告中心
├── AI 市场情报      ← 默认（V2）
├── 选品数据报告     ← 仅 Legacy 套餐显示
└── 我的研究笔记     ← 本地
```

### 4.2 情报页

- 列表：日期 + 类目 + 星级 + 一句话摘要
- 点击：`webbrowser.open()` 或 `<webview src="...">`
- **禁止**：「导出 CSV」「下载 data.js」按钮（V2）

### 4.3 会员态判断

优先使用 `GET /api/v1/member/profile` + `resolve_menu_flags()`（与 Web 一致）：

```python
from core.cloud_client import fetch_member_profile, resolve_menu_flags

flags = resolve_menu_flags(fetch_member_profile())
show_legacy = flags["show_legacy_zip"]
show_insight = flags["show_insight"]
```

---

## 5. 发版节奏

| 顺序 | 端 | 内容 |
|------|-----|------|
| 1 | 云端 | insight API + Shadow 管道 |
| 2 | Web 会员页 | 双 Tab |
| 3 | PC | 读 insight API + WebView |
| 4 | PC | Legacy 入口按 entitlements 隐藏 |

PC 与云端 **向后兼容**：旧 PC 仍可调 V1 API；新 PC 需 `productanalyzer-version.json` 最低版本门控。

---

## 6. 配置项（local_sync.env / 设置页）

```env
XHS_CLOUD_REPORT_MODE=plan_b          # Legacy 上传，V2 逐步废弃
XHS_INSIGHT_ENABLED=1                 # 显示情报菜单
XHS_LEGACY_ZIP_ENABLED=0              # V2 用户默认关
XHS_CLOUD_BASE=https://monitor.xhs365.cn
```

---

## 7. 测试清单

- [ ] `pc:` 登录后可拉 `insight/library`
- [ ] WebView 打开 HTML 无 goods_id
- [ ] Legacy 授权码用户仍见 zip 下载
- [ ] V2 授权码用户只见情报
- [ ] 单设备踢出逻辑与 Web 一致

---

## 8. 与 vuemonitor 仓库关系

| 仓库 | 改动 |
|------|------|
| `vuemonitor/xhs-cloud` | insight API、会员页、管道 |
| `xhs_shelf_time` | cloud_client、侧栏、WebView |
| `vuemonitor/projects/ai-market-intelligence-v2` | 设计 + 实验室（先行） |

实验室验证通过后，再把 `cloud_client` 补丁抄进 `xhs_shelf_time` 发版。
