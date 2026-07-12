# 31 — 体验码 Day1–3 转化 SOP（REQ-RET-040～042）

## 发码（Admin）

1. admin.xhs365.cn → **选品会员** → 生成授权码
2. 套餐：**AI 情报体验 (7天 · insight_only)**
3. 发给用户，引导 https://monitor.xhs365.cn/member 注册

## Day1 — 蓝海认知

- 用户登录后默认 **AI 选品情报** Tab
- 查看 **今日机会雷达** + 4 条预生成类目（不扣配额，只读 Shadow）
- 话术：「今日系统已筛出 N 个蓝海方向，点类目看完整情报」

## Day2 — 趋势价值

- 引导打开 **时间轴/7日趋势**（Pro 可见；体验码可看预览条）
- 话术：「看这个类目近 7 天增速，决定是否跟进」

## Day3 — 转化

- 推送 **AI 选品情报 Pro** 购买链接（支付页在 `XHS_V2_LAUNCH=1` 后仅 insight SKU）
- 体验码用户升级后 entitlements 含 `insight_compare` + 更高类目/日配额

## 运营指标

| 指标 | 目标 |
|------|------|
| Day1 登录 | >80% |
| Day1 至少 1 次 view | >60% |
| Day3 付费转化 | 12–18% |

## 技术验收

```bash
export XHS_SMOKE_EXPECT=insight_only
bash /opt/xhs-cloud/cloud_deploy/scripts/insight_shadow_smoke.sh
```

profile 应：`insight_enabled=true`, `legacy_zip_enabled=false`, `portal_route=insight_only`
