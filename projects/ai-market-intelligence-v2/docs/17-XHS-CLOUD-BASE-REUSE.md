# 现网基座复用与 V2 对接蓝图

> **版本**：v1.0  
> **原则**：**不重复造轮子** — 支付、授权码、JWT、设备绑定、Legacy 报告库 **一律复用** `xhs-cloud`  
> **V2 实验室** 只新增：AI 情报内容、类目关注、进阶 UX；合并时 **扩展** 而非重写

---

## 一、现网基座地图

```
https://monitor.xhs365.cn/member
  └── xhs-cloud/cloud_deploy/cloud_api/main.py
        ├── auth.py              JWT + 双槽设备 (pc / web)
        ├── payment_service.py   扫码支付 → 授权码 → 履约
        ├── payment_plans.py     monthly / quarterly / …
        ├── database_pg.py       users / memberships / auth_codes / report_archives
        └── assets/member_portal.html  单页会员中心（购买/登录/报告库/收藏）
```

**vuemonitor/server** 仅通过 `X-Sync-Key` 代理 **管理端** 授权码，**不是** C 端会员 API。

---

## 二、必须复用（禁止实验室重写）

| 能力 | 现网路径 | 关键 API | V2 动作 |
|------|----------|----------|---------|
| **扫码支付** | `payment_service.py` + `hwxun_pay.py` | `POST /api/v1/payment/orders`<br>`GET /api/v1/payment/qrcode`<br>`…/notify/hwxun` | 仅 **新增 plan_code**，不改回调 |
| **授权码** | `database_pg.py` | `register` / `login-code` / `activate` / `renew-with-code` | V2 套餐映射到 `plan_code` + `note.entitlements` |
| **JWT 会话** | `auth.py` | `Bearer` / cookie / `access_token` | insight 路由 `Depends(current_member)` |
| **设备绑定** | `users.pc_*` / `web_*` | 登录时 `device_id: web:{uuid}` | PC WebView 与浏览器 **双槽共存** |
| **会员校验** | `current_member()` | 过期 → **402** | 情报 API 同样 402 |
| **Legacy 报告库** | `report_archives` | `GET /api/v1/member/library` | V1 履约 **不动** |
| **商品收藏** | `member_watchlist` | `GET/POST/DELETE …/watchlist` | **保留** V1 商品级收藏，与 V2 类目关注 **并存** |
| **管理端发码** | `manage_auth_codes.py` + web-admin | `POST /api/v1/admin/auth-codes` | 体验码 / 活动码继续用 |

---

## 三、V2 新增（扩展点）

| 能力 | 说明 | 建议实现 |
|------|------|----------|
| **AI 情报库** | 新 archive_type 或新表 | `insight_daily_html` 写入 `report_archives` 或 `insight_reports` |
| **类目关注** | 与商品 watchlist **不同** | 新表 `member_insight_watchlist(user_id, category)` — 见 `cloud-stubs/insight_watchlist.py` |
| **情报 API** | 会员只读 | `GET /api/v1/member/insight/library` 等 — 见 `cloud-stubs/insight_routes.py` |
| **套餐 entitlements** | 控制类目数/对比/PDF | 扩展 `auth_codes.note` JSON + `get_member_entitlements()` |
| **Team 席位** | 现网 **尚无** | 新表 `member_orgs` / `org_seats` — 见 `cloud-stubs/team_seats_migration.sql` |

---

## 四、支付套餐扩展（不新建支付通道）

在 `payment_plans.py` **追加** V2 SKU（示例见 `cloud-stubs/payment_plans_v2_patch.py`）：

| plan_code | 说明 | 与现网关系 |
|-----------|------|------------|
| `monthly` | ¥99/30天 Legacy 全量 | **已有** |
| `insight_monthly` | AI 情报月卡 | **新增** entitlements |
| `insight_pro_monthly` | 情报 Pro（5 类目/日） | 新增 |
| `insight_team_monthly` | 团队版 5 席 | 新增 + seats |
| `experience` | 体验会员 | **已有** plan_code + note JSON |

支付流程 **不变**：下单 → 二维码 → hwxun 回调 → 自动生成授权码 → 用户注册/登录激活。

---

## 五、体验会员（现网已支持，直接复用）

`database_pg.py` 已有：

- `plan_code = "experience"`
- `auth_codes.note` → JSON `entitlements`：
  ```json
  {
    "entitlements": {
      "plan_code": "experience",
      "insight_categories_per_day": 1,
      "insight_compare": false,
      "legacy_report_download_limited": true,
      "allowed_archive_types": ["member_daily_zip"],
      "allowed_report_dates": ["2026-07-12"]
    }
  }
  ```

**合规后可以开放免费/低价体验**：发 **experience 授权码** 或 **0 元支付+自动发码**，无需新支付系统。

---

## 六、实验室 vs 现网运行模式

| 模式 | 配置 | 行为 |
|------|------|------|
| **Lab** | 默认，无 `XHS_CLOUD_API_BASE` | mock 套餐 / 本地 JSON 关注列表 |
| **Bridge** | `XHS_CLOUD_API_BASE=https://monitor.xhs365.cn` + JWT | 登录/支付跳转现网 portal；情报仍走实验室或 Shadow |

实验室 **不提供** 假支付二维码；购买 Tab 链到现网 `member_portal.html#buy`。

---

## 七、合并 Checklist（Phase 2→3）

- [ ] `insight_routes.py` 接入 `current_member` from `auth.py`
- [ ] `payment_plans_v2_patch.py` 合并进 `payment_plans.py`
- [ ] `member_insight_watchlist` 表 + CRUD
- [ ] `member_portal.html` 增加 AI 情报 Tab（`member_insight_panel.html`）
- [ ] `get_member_entitlements()` 识别 `insight_*` 字段
- [ ] Shadow 管道写 `insight_daily_html` 到 archives
- [ ] **不修改** hwxun notify URL / JWT secret / 授权码格式

---

## 八、文件索引

| 文件 | 用途 |
|------|------|
| `cloud-stubs/payment_plans_v2_patch.py` | V2 套餐定义（合并用） |
| `cloud-stubs/insight_watchlist.py` | 类目关注 DB + 路由 |
| `cloud-stubs/team_seats_migration.sql` | Team 席位 schema |
| `cloud-stubs/insight_routes.py` | 情报会员 API |
| `docs/18-MEMBERSHIP-SCHEME-DESIGNS.md` | 会员体系方案穷举 |

**现网参考**：`xhs-cloud/cloud_deploy/assets/member_portal.html`（支付/授权码/报告库）
