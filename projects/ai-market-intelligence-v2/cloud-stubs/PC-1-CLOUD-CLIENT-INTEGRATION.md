# PC-1 cloud_client V2 补丁 — 合并说明

> **目标文件**：`xhs_shelf_time/core/cloud_client.py`  
> **补丁源**：`cloud-stubs/pc_cloud_client_v2_patch.py`  
> **需求**：`23-PC-CLIENT-V2-REDESIGN-AND-PACKAGING.md` REQ-PC-V2-001

## 1. 合并步骤（约 30 分钟）

1. 复制 `pc_cloud_client_v2_patch.py` 中以下函数到 `cloud_client.py` 末尾：
   - `fetch_member_profile`
   - `fetch_insight_library`
   - `fetch_insight_categories`（可选）
   - `insight_view_url`
   - `resolve_menu_flags`
   - `open_insight_in_browser`

2. 函数体内 `_api()` 改为现网 `_request()` 调用风格，例如：

```python
def fetch_insight_library() -> dict:
    code, data = _request("GET", "/api/v1/member/insight/library", token=get_token(), timeout=30)
    if code != 200:
        raise RuntimeError(_api_error(data, code, "获取情报库失败"))
    return data
```

3. **不要删除** 现有 `fetch_library` / `download_report` / `upload_report` 等 Legacy 函数。

## 2. UI 挂钩点（PyQt 侧栏）

```python
profile = fetch_member_profile()  # 或 cloud_status() 扩展读 profile
flags = resolve_menu_flags(profile)

if flags["show_insight"]:
    menu_insight.setVisible(True)
if flags["show_legacy_zip"]:
    menu_legacy.setVisible(True)
else:
    menu_legacy.setVisible(False)
    menu_upload.setVisible(False)  # plan_b

# 默认页
if flags["default_section"] == "insight":
    stack.setCurrentWidget(page_insight)
```

## 3. 情报页最小实现

```python
lib = fetch_insight_library()
for item in lib.get("items") or []:
    # 列表：item["category"], item["report_date"], item["stars"]
    url = insight_view_url(item["report_date"], item["category"])
    # WebView.load(url) 或 webbrowser.open(url)
```

## 4. 配置（local_sync.env）

```env
XHS_CLOUD_BASE=https://monitor.xhs365.cn
XHS_INSIGHT_ENABLED=auto
XHS_LEGACY_ZIP_ENABLED=auto
```

`auto` = 登录后读 `profile.legacy_zip_enabled` / `insight_enabled`。

## 5. 验收（REQ-PC-*）

- [ ] Legacy monthly 在期：Legacy 菜单 + zip 下载正常
- [ ] insight_pro 新码：仅情报菜单，无 zip
- [ ] legacy_preview：双菜单
- [ ] WebView URL 打开 HTML，无 goods_id 字段

## 6. vuemonitor 内自测

```bash
cd projects/ai-market-intelligence-v2
python -m pytest tests/test_pc_cloud_client_patch.py -q
```
