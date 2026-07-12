# V2 情报 API 规格（实验室 → 合并 xhs-cloud）

> Base URL（实验室）: `http://127.0.0.1:8765`  
> Base URL（生产）: `https://monitor.xhs365.cn`

## 1. 会员情报库

### GET `/api/v1/member/insight/library`

**鉴权**: Bearer / Cookie（同现网 `current_user`）

**响应**:
```json
{
  "membership": { "username": "...", "plan_code": "insight_pro", "is_active": true },
  "items": [
    {
      "report_date": "2026-07-12",
      "archive_type": "insight_daily_html",
      "category": "小学教辅",
      "title": "AI 市场情报 · 小学教辅",
      "stars": 5,
      "preview_url": "/api/v1/member/insight/2026-07-12/小学教辅/view",
      "has_legacy_zip": false
    }
  ],
  "legacy": {
    "daily": [],
    "note": "V1 zip 仅 Legacy 套餐可见"
  }
}
```

### GET `/api/v1/member/insight/{date}/{category}/view`

**响应**: `text/html`（6 页情报，无 data.js）

### GET `/api/v1/member/insight/{date}/{category}/summary`

**响应**: `application/json`（`InsightReport` 结构，见 samples/ai-report-sample.json）

**禁止**: 响应中含 `goods_id`, `store_id`, `title`（商品级）, `download_url` 指向 zip+data.js

---

## 2. 内部管道（仅 Sync Key / systemd）

### POST `/api/v1/internal/insight/generate`

**鉴权**: `X-Sync-Key` 或 systemd 本地

**Body**:
```json
{ "report_date": "2026-07-12", "categories": ["auto"], "force": false }
```

**响应**:
```json
{ "ok": true, "generated": 3, "archive_type": "insight_daily_html" }
```

---

## 3. PC 客户端专用

### GET `/api/v1/member/insight/library`

同 Web；PC 使用 `device_id: pc:XXXX`。

### GET `/api/v1/member/insight/{date}/{category}/view`

PC 内嵌 WebView 或系统浏览器打开；**不再**下载 `member_daily_zip`。

### POST `/api/v1/member/research-notes`（Phase 3+）

用户自有笔记，与云端情报关联（不含商品 ID 导出）。

---

## 4. 与 V1 API 共存

| V1（保留） | V2（新增） |
|------------|------------|
| `GET /member/library` → daily zip 列表 | `GET /member/insight/library` |
| `GET /member/reports/{d}/download` | ❌ V2 无 bulk data.js 下载 |
| `GET /member/reports/{d}/view/index_with_gr.html` | `GET /member/insight/{d}/{cat}/view` |

**Entitlements**:
- `plan_code=legacy` → 仅 `legacy.daily`
- `plan_code=insight_pro` → 仅 `insight` items
- 过渡期 `hybrid` → 两者

---

## 5. 错误码

| HTTP | 含义 |
|------|------|
| 401 | 未登录 |
| 402 | 会员过期 |
| 403 | 套餐不含情报 / Legacy 不含 V2 |
| 404 | 报告未生成 |
| 422 | 参数错误 |
