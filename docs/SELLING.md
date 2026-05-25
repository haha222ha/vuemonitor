# XHS365 人工售卖手册（授权码，无在线支付）

## 流程

1. 用户 **www.xhs365.cn** 免费注册
2. 用户打开 **/purchase** 或定价页，加 **QQ 客服**（默认 898382699）
3. 用户说明套餐：Pro / Premium / Enterprise + 月数
4. 收款（微信转账等，线下自行约定）
5. 管理员登录 **admin.xhs365.cn** → **主系统授权码** → 生成对应 `plan` 与 `duration_days`
6. 将授权码发给用户（QQ）
7. 用户在 **设置 → 授权码激活** 粘贴激活

## 后台生成授权码

```
admin.xhs365.cn → 主系统授权码 → 生成授权码
```

API：`POST /api/v1/admin/licenses/generate`  
参数：`plan`（pro/premium/enterprise）、`count`、`duration_days`

导出：`GET /api/v1/admin/licenses/export`

## 参考定价（可与客服口头调整）

| 套餐 | 建议价 | 后端权益要点 |
|------|--------|----------------|
| Free | ¥0 | 3 商品、基础 AI 次数 |
| Pro | ¥49/月 | 50 商品、定时采集、更多 AI |
| Premium | ¥149/月 | 500 商品、爆品/风险 AI |
| Enterprise | 议价 | 不限量、API、私有化 |

## 运营检查（每周）

```bash
cd /opt/vuemonitor && bash scripts/host-update.sh
curl -s https://api.xhs365.cn/api/v1/public/support
```

## 用户常见问题

- **没有收到邮件？** 不依赖邮箱，找 QQ 客服。
- **激活失败？** 检查码是否复制完整、是否已使用/过期；后台可查授权列表。
- **换电脑？** 授权码与账号绑定，重新登录同一账号即可（企业版多设备见合同）。
