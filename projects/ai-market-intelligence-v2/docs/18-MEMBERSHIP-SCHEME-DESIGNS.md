# 会员体系设计方案穷举（V2 · 合规后）

> **版本**：v1.0  
> **前提**：支付/授权码/JWT/设备绑定 **复用现网**（见 `17-XHS-CLOUD-BASE-REUSE.md`）  
> **问题**：月度付费为主 → 合规后是否开放免费体验？会员体系如何设计？

---

## 一、设计约束（不可动摇）

| 约束 | 说明 |
|------|------|
| 支付基座 | hwxun 微信/支付宝扫码、`payment_service.py` **不改** |
| 授权码 | `XHS-xxx` 格式、`renew_with_auth_code` 叠加天数 **不改** |
| 账号一体 | 同一 `users` 表，Legacy 与 V2 **同一登录** |
| 合规 | 体验会员也不得开放 raw 商品表 bulk 下载 |
| 双轨 | 在期 Legacy 买家须履约至到期 |

---

## 二、方案总览（6 套）

| 方案 | 代号 | 一句话 | 推荐阶段 |
|------|------|--------|----------|
| **A** | 纯 Legacy 月付 | 维持现状，仅 zip 数据包 | 已过时（仅履约） |
| **B** | 纯 V2 情报月付 | 只卖 AI 情报，停售 zip | Phase 4 目标 |
| **C** | 双轨套餐 | 一条 SKU 含 Legacy+情报 | 过渡 6～12 月 |
| **D** | 体验码引流 | 免费/低价 experience 码，受限情报 | **合规后首选拉新** |
| **E** | Freemium 注册即用 | 未付费也能看 1 类目/日 | 需评估成本与滥用 |
| **F** | Team 席位 B2B | 主账号买 Team，子账号占席 | Pro 之上增量 |

**推荐组合（2026-07-12 拍板）**：**B 终局 + D 拉新**；**取消 C 双轨新售**；Legacy zip **仅老用户履约至 expires_at**  
详见 **`19-LEGACY-SUNSET-AND-V2-LAUNCH.md`**

---

## 三、方案 A — 纯 Legacy 月付（现状）

| 项 | 内容 |
|----|------|
| SKU | `monthly` ¥99/30天 … `yearly` |
| 交付 | `member_daily_zip` 等 |
| 支付 | 扫码 → 自动授权码 → 注册/续费 |
| 体验 | 无 AI 情报 |

**适用**：仅服务在期老用户履约，**新用户停售**。

---

## 四、方案 B — 纯 V2 情报月付（目标态）

| SKU | 价格（建议） | entitlements |
|-----|-------------|--------------|
| `insight_monthly` | ¥129/30天 | 3 类目/日；**无**对比/时间轴/工作流/PDF |
| `insight_pro_monthly` | ¥299/30天 | 5 类目/日；对比 + 时间轴(30d) + 工作流 + PDF |
| `insight_team_monthly` | ¥899/30天 | 5 席，20 类目/日；同 Pro 高阶功能 + 更高 LLM 预算 |

**支付**：同一扫码流程，回调写 `auth_codes.note`：

```json
{"entitlements": {"insight_enabled": true, "insight_categories_per_day": 5, ...}}
```

**会员页**：默认 Tab = AI 情报；Legacy Tab 对老用户只读历史。

---

## 五、方案 C — 双轨套餐（过渡）

| SKU | 说明 |
|-----|------|
| `dual_monthly` | ¥149/30天 = zip + 情报（3 类目/日） |
| 存量 `monthly` | 自动视为仅 Legacy，**不自动升情报**（避免争议） |

**迁移话术**：「续费可升级双轨月卡，同时保留数据包与 AI 情报」。

---

## 六、方案 D — 体验码引流（推荐拉新）★

**现网已具备 80%**：`plan_code=experience` + `auth_codes.note.entitlements`

### D1 客服/活动发码（零支付）

- 管理端 `web-admin` / `manage_auth_codes.py` 批量生成  
- `note` 示例见 `entitlements_v2.EXPERIENCE_ENTITLEMENTS_INSIGHT`  
- 限制：`allowed_report_dates` 仅 1～3 天、`insight_categories_per_day: 1`

### D2 公开「免费体验包」（已有）

- `trial_public_service.py` + 会员页「免费体验包」Tab  
- **无登录** 预览 zip / 在线预览  
- V2 扩展：增加 **「AI 情报体验日」** 静态样例页（无 LLM 实时生成，降成本）

### D3 0 元支付自动发码（可选）

- 新增 `plan_code=experience_free`，`amount=0.01` 或走 **纯授权码**  
- **不建议真 0 元走支付通道**（网关限制）；优先 **D1 发码**

### D4 邀请裂变（后期）

- 老用户邀请码 → 双方各得 3 天 experience  
- 需防刷：设备绑定 + 手机号（可选）

| 优点 | 风险 |
|------|------|
| 合规叙事清晰（受限情报非数据批发） | 体验过好可能导致不愿付费 |
| 无需新支付系统 | 需控制 LLM 日调用上限 |
| 与现网授权码体系一致 | 发码需审计 |

**结论**：合规后 **优先 D1+D2**，不做无门槛全自动 Freemium。

---

## 七、方案 E — Freemium 注册即用

| 项 | 设计 |
|----|------|
| 注册 | 无需授权码，账号即 `insight_categories_per_day: 1` |
| 内容 | 只看 **昨日** 固定类目情报（缓存），非实时 LLM |
| 升级 | 扫码买 `insight_monthly` 解锁当日+多类目 |

| 优点 | 缺点 |
|------|------|
| 转化漏斗短 | 与现网「授权码开通」心智冲突 |
| SEO/传播友好 | 滥用注册、LLM 成本难控 |
| | 需新建「免费 tier」逻辑分支 |

**建议**：**暂不采用**；用 **方案 D** 达到类似效果且复用发码体系。

---

## 八、方案 F — Team 多席位

| 项 | 内容 |
|----|------|
| 购买 | `insight_team_monthly` 扫码 |
| 数据 | `member_orgs` + `member_org_seats`（见 `team_seats_migration.sql`） |
| 权益 | `insight_team_seats: 5`，子账号共享主账号 `expires_at` |
| 管理 | 主账号邀请邮箱 → 子账号接受 → 占 1 seat |

**实验室**：`workflow.html` + `GET /api/v1/member/team` mock。

---

## 九、权益矩阵（穷举字段）

| 权益字段 | Starter/体验 | Pro | Team | Legacy monthly |
|----------|-------------|-----|------|----------------|
| `insight_enabled` | ✅ | ✅ | ✅ | ❌ |
| `insight_categories_per_day` | 1 | 5 | 20 | 0 |
| `insight_compare` | ❌ | ✅ | ✅ | ❌ |
| `insight_timeline_days` | 7 | 30 | 30 | ❌ |
| `insight_pdf_export` | ❌ | ✅ | ✅ | ❌ |
| `insight_workflow` | ❌ | ✅ | ✅ | ❌ |
| `insight_team_seats` | 1 | 1 | 5 | 1 |
| `legacy_zip_enabled` | 限日期 | ❌ | ❌ | ✅ |
| 商品 watchlist | ✅ | ✅ | ✅ | ✅ |
| 类目 insight watchlist | ✅ | ✅ | ✅ | ❌ |

---

## 十、定价周期穷举

| 周期 | 现网 | V2 建议 | 说明 |
|------|------|---------|------|
| 月付 | ✅ monthly | insight_*_monthly | **主售** |
| 季付 | ✅ quarterly | insight_pro_quarterly | 9 折 |
| 半年/年 | ✅ | insight_pro_yearly | 高 LTV 用户 |
| 日付/周付 | ❌ | 仅 `pay_test` 联调 | 不做 C 端 |
| 永久 | ❌ | **不做** | 合规与成本不可控 |
| 免费体验 | experience 码 | D 方案 | **合规后开放** |

---

## 十一、推荐落地路线

```mermaid
flowchart LR
  P0[现网 Legacy 月付] --> P1[+D 体验码情报]
  P1 --> P2[+ insight_monthly SKU]
  P2 --> P3[Legacy 停新签]
  P3 --> P4[纯 V2 + Team]
```

| 阶段 | 动作 |
|------|------|
| **现在** | 文档+stub；实验室 UX；**不改现网支付** |
| **Phase 3** | 合并 `payment_plans_v2_patch`；会员页加情报 Tab |
| **Phase 3b** | 管理端发 **experience+insight** 码内测 |
| **Phase 4** | 新用户仅 V2 SKU；Legacy 到期下线 |
| **Phase 5** | Team 席位 + 季付年付情报包 |

---

## 十二、与实验室 mock 的对应

| 实验室 | 生产 |
|--------|------|
| `config/plans.yaml` | `payment_plans.py` + `entitlements_v2` |
| `subscription_mock.py` | `memberships` + `get_member_entitlements()` |
| `PUT /api/v1/member/insight/watchlist` | `insight_watchlist.py` + PG 表 |
| 套餐下拉 demo | 扫码支付 **跳转现网** |

---

## 十三、决策清单（产品拍板）

- [ ] 新用户默认方案：**B 纯情报** 还是 **C 双轨**？
- [ ] 体验引流：**D1 发码** 还是加 **D2 公开情报样例**？
- [ ] 是否做 **E Freemium**？（建议否）
- [ ] `insight_monthly` 首发价：¥129 还是 ¥99？
- [ ] Legacy 老用户续费是否自动赠 7 天情报体验？
- [ ] Team 版首发是否包含 PC 多设备（仍受双槽限制）？

---

**关联**：`17-XHS-CLOUD-BASE-REUSE.md`、`cloud-stubs/payment_plans_v2_patch.py`、`entitlements_v2.py`
