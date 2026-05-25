# QQ 客服（替代 SMTP）

产品注册为 **用户名 + 密码**，邮箱选填，**不依赖网易 SMTP**。

## 配置（`server/.env`）

```env
SUPPORT_QQ=898382699
SUPPORT_QQ_QR_URL=/support-qq.png
SUPPORT_SITE_URL=https://www.xhs365.cn

二维码图片已内置：`web-user/public/support-qq.png`（构建后进 `dist/support-qq.png`）。
```

## API

`GET /api/v1/public/support` — 返回 QQ 号、会话链接、二维码 URL。

## 前端展示位置

- 登录 / 注册页底部
- 首页页脚「客服」
- 设置页「联系客服」

## 部署后

```bash
cd /opt/vuemonitor/web-user && npm ci && npm run build
sudo systemctl restart vuemonitor
sudo systemctl reload nginx
```

## 网易 SMTP 说明（可选）

`535 ERR.LOGIN.PASSERR` 表示授权码错误或未使用；后台显示「尚未使用」说明从未成功登录过 SMTP。  
若不做邮件，可删除 `server/.env` 中 `SMTP_*` 配置。
