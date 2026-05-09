# VueMonitor + Cloudflare 部署指南

---

## 核心原理

```
你的真实服务器IP: 123.45.67.89（只有你和 Cloudflare 知道）
Cloudflare 分配的IP: 104.x.x.x（用户看到的是这个）

用户访问流程:
  用户 → api.yourdomain.com → Cloudflare(104.x.x.x) → 你的服务器(123.45.67.89)

所以：
  ✅ build.bat 填域名: https://api.yourdomain.com
  ❌ 不要填 IP: http://123.45.67.89:8000  （这会绕过 Cloudflare 保护）
```

---

## 第一步：Cloudflare DNS 设置

登录 Cloudflare Dashboard → 选择你的域名 → DNS

### 需要添加的记录

| 类型 | 名称 | 内容 | 代理状态 | 说明 |
|------|------|------|----------|------|
| A | api | 你的服务器IP | ☁️ 已代理 | API 服务 |
| A | admin | 你的服务器IP | ☁️ 已代理 | 管理后台 |
| A | @ | 你的服务器IP | ☁️ 已代理 | 可选，默认管理后台 |

**关键**：代理状态必须是 **☁️ 已代理**（橙色云朵），不是灰色DNS only！

这样设置后：
- `api.yourdomain.com` → Cloudflare 自动分配 IP → 转发到你的服务器
- 外部无法看到你的真实 IP
- Cloudflare 自动提供 DDoS 防护和 WAF

---

## 第二步：Cloudflare SSL/TLS 设置

Cloudflare Dashboard → SSL/TLS → 概述

### 推荐模式：完全（严格）

```
用户 ──HTTPS──→ Cloudflare ──HTTPS──→ 你的服务器
     (Cloudflare证书)        (你的自签证书/Let's Encrypt)
```

设置步骤：
1. SSL/TLS → 概述 → 加密模式 → 选择 **完全（严格）**
2. SSL/TLS → 边缘证书 → 最低 TLS 版本 → TLS 1.2
3. SSL/TLS → 边缘证书 → 始终使用 HTTPS → **开启**

---

## 第三步：服务器上安装 SSL 证书

因为选了"完全（严格）"，源站也需要 HTTPS。用 Let's Encrypt 免费证书：

```bash
# 在服务器上
apt install certbot -y

# 申请证书（替换 yourdomain.com 为你的域名）
certbot certonly --standalone -d api.yourdomain.com -d admin.yourdomain.com

# 证书位置：
# /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/api.yourdomain.com/privkey.pem

# 设置自动续期
certbot renew --dry-run
```

---

## 第四步：服务器 Nginx 配置

```bash
nano /etc/nginx/sites-available/vuemonitor
```

写入以下内容（替换 `yourdomain.com`）：

```nginx
# API 服务
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # API 反向代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $http_cf_connecting_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持（Cloudflare 默认支持）
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $http_cf_connecting_ip;
        proxy_read_timeout 86400;
    }
}

# 管理后台
server {
    listen 443 ssl http2;
    server_name admin.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    root /opt/vuemonitor/web-admin/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $http_cf_connecting_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name api.yourdomain.com admin.yourdomain.com;
    return 301 https://$host$request_uri;
}
```

启用配置：
```bash
ln -sf /etc/nginx/sites-available/vuemonitor /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
```

---

## 第五步：Cloudflare 专用配置

### 5.1 开启 WebSocket 支持

Cloudflare Dashboard → 网络 → WebSockets → **开启**

> Cloudflare 免费版就支持 WebSocket，默认已开启

### 5.2 配置防火墙规则（WAF）

Cloudflare Dashboard → 安全性 → WAF → 创建规则

**规则 1：只允许中国 IP 访问管理后台**
```
URI Path 包含 "/admin"
且 国家 不等于 中国
→ 操作: 阻止
```

**规则 2：API 速率限制**
```
URI Path 包含 "/api/v1/auth/login"
且 速率 > 10次/分钟
→ 操作: 质询
```

### 5.3 配置速率限制

Cloudflare Dashboard → 安全性 → 速率限制规则

```
URL: *yourdomain.com/api/v1/auth/*
请求阈值: 20次/10秒
操作: 质询
```

### 5.4 关闭不需要的端口

Cloudflare 只代理以下端口，其他端口自动屏蔽：

```
HTTP:  80, 8080, 8880, 2052, 2082, 2086, 2095
HTTPS: 443, 2053, 2083, 2087, 2096, 8443
```

所以 **8000 端口不需要开放**，所有流量走 443 通过 Nginx 代理。

---

## 第六步：修改服务端配置

编辑服务器上的 `/opt/vuemonitor/server/.env`：

```env
# CORS 必须包含你的域名
CORS_ORIGINS=["https://admin.yourdomain.com","https://api.yourdomain.com"]

# 其他不变
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vuemonitor
DB_USER=saas_user
DB_PASSWORD=你的密码
REDIS_HOST=localhost
REDIS_PORT=6379
```

重启服务：
```bash
systemctl restart vuemonitor
```

---

## 第七步：打包客户端

在你的 Windows 电脑上：

```
双击 build.bat
→ 提示输入服务器地址时输入: https://api.yourdomain.com
→ 等构建完成
→ 把 client\release\VueMonitor Setup.exe 发给用户
```

**关键**：填域名，不要填 IP！

---

## 完整配置总结

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare 配置                           │
│                                                             │
│  DNS 记录:                                                  │
│    api.yourdomain.com   → A → 你的IP → ☁️已代理            │
│    admin.yourdomain.com → A → 你的IP → ☁️已代理            │
│                                                             │
│  SSL/TLS: 完全（严格）                                      │
│  WebSocket: 开启                                            │
│  始终HTTPS: 开启                                            │
│  最低TLS: 1.2                                               │
├─────────────────────────────────────────────────────────────┤
│                    服务器配置                                │
│                                                             │
│  Nginx:                                                     │
│    api.yourdomain.com:443 → proxy_pass 127.0.0.1:8000      │
│    admin.yourdomain.com:443 → 静态文件 + API代理            │
│                                                             │
│  SSL 证书: Let's Encrypt (自动续期)                          │
│  Firewall: 只开 80, 443, 22                                │
├─────────────────────────────────────────────────────────────┤
│                    客户端配置                                │
│                                                             │
│  build.bat 服务器地址: https://api.yourdomain.com           │
│  client/.env: VITE_API_BASE_URL=https://api.yourdomain.com/api/v1 │
├─────────────────────────────────────────────────────────────┤
│                    服务端配置                                │
│                                                             │
│  server/.env:                                               │
│    CORS_ORIGINS=["https://admin.yourdomain.com",            │
│                  "https://api.yourdomain.com"]               │
└─────────────────────────────────────────────────────────────┘
```

---

## 防攻击架构

```
攻击者                    Cloudflare              你的服务器
──────                  ──────────              ──────────

DDoS 攻击 ──→ Cloudflare 自动吸收 ──→ 正常流量通过
                (Tb级防护)

恶意爬虫 ──→ WAF 规则拦截 ──→ 干净请求通过

暴力破解 ──→ 速率限制 ──→ 质询/阻止

真实IP扫描 ──→ 看不到真实IP ──→ 无法直接攻击源站

SQL注入 ──→ WAF 拦截 ──→ 安全请求通过
```

你的源站 IP 只有 Cloudflare 知道，攻击者无法绕过 Cloudflare 直接攻击你的服务器。

---

## 常见问题

### Q: Cloudflare 免费版够用吗？

**够用**。免费版包含：
- ✅ DDoS 防护（不限流量）
- ✅ WAF（基础规则集）
- ✅ WebSocket 支持
- ✅ SSL 证书
- ✅ 速率限制（基础）
- ✅ 隐藏源站 IP

### Q: WebSocket 连接断开？

Cloudflare 免费版 WebSocket 超时 100 秒。我们的心跳机制是 30 秒，没问题。

如果还断开，检查：
1. Cloudflare → 网络 → WebSockets 是否开启
2. Nginx 的 `proxy_read_timeout` 是否够大（已设 86400）

### Q: 用 Cloudflare 后 API 变慢了？

正常现象，多了一层 CDN。但好处是：
- 全球有 CDN 节点，海外用户反而更快
- 防 DDoS，比速度重要得多

如果在意延迟，可以在 Cloudflare → 规则 → 配置规则中：
```
URI Path 包含 "/api/v1/"
→ 缓存级别: 绕过
```

### Q: 如何确认 Cloudflare 代理生效？

```bash
# 查看域名解析，应该返回 Cloudflare 的 IP
nslookup api.yourdomain.com

# 应该返回 104.x.x.x 或 172.x.x.x 之类的 Cloudflare IP
# 不应该返回你的真实服务器 IP
```

### Q: Let's Encrypt 证书续期失败？

Cloudflare 代理模式下，certbot 的 HTTP-01 验证会被 Cloudflare 拦截。

**解决方法**：临时关闭 Cloudflare 代理续期，或用 DNS-01 验证：

```bash
# 安装 Cloudflare DNS 插件
apt install python3-certbot-dns-cloudflare

# 创建 Cloudflare API Token 配置
echo "dns_cloudflare_api_token = 你的CF_API_TOKEN" > /etc/letsencrypt/cloudflare.ini
chmod 600 /etc/letsencrypt/cloudflare.ini

# 用 DNS 验证申请证书
certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  -d api.yourdomain.com \
  -d admin.yourdomain.com
```

### Q: 想让管理后台只能自己访问？

在 Cloudflare WAF 中添加规则：

```
主机名 等于 admin.yourdomain.com
且 IP 源地址 不等于 你的IP
→ 操作: 阻止
```

这样只有你能访问管理后台，其他人都被 Cloudflare 拦截。
