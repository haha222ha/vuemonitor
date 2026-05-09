#!/bin/bash
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   XHS365 + Cloudflare 一键配置          ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$EUID" -ne 0 ]; then
    echo -e "  ${RED}请使用 sudo 运行${NC}"
    exit 1
fi

# ===== 收集信息 =====
echo -e "  ${CYAN}请输入以下信息：${NC}"
echo ""

read -p "  你的域名（例如 example.com）: " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo "  域名不能为空"
    exit 1
fi

API_DOMAIN="api.${DOMAIN}"
ADMIN_DOMAIN="admin.${DOMAIN}"

echo ""
echo -e "  API 域名: ${GREEN}${API_DOMAIN}${NC}"
echo -e "  管理后台域名: ${GREEN}${ADMIN_DOMAIN}${NC}"
echo ""

read -p "  服务器真实IP（本机IP，留空自动检测）: " SERVER_IP
if [ -z "$SERVER_IP" ]; then
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo -e "  自动检测到: ${GREEN}${SERVER_IP}${NC}"
fi

read -p "  OpenAI API Key（留空跳过）: " OPENAI_KEY
read -p "  DeepSeek API Key（留空跳过）: " DEEPSEEK_KEY

echo ""
echo -e "  ${YELLOW}即将执行以下操作：${NC}"
echo "  1. 安装 Nginx + Certbot"
echo "  2. 申请 Let's Encrypt SSL 证书"
echo "  3. 配置 Nginx 反向代理"
echo "  4. 配置 XHS365 服务端"
echo "  5. 注册系统服务"
echo ""
read -p "  确认继续？(y/N): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "  已取消"
    exit 0
fi

# ===== 1. 安装依赖 =====
echo -e "  ${CYAN}[1/5]${NC} 安装依赖..."
apt update -qq
apt install -y -qq nginx certbot python3-certbot-nginx python3-certbot-dns-cloudflare > /dev/null 2>&1

# ===== 2. 先部署 XHS365（如果还没部署）=====
if [ ! -f "$SCRIPT_DIR/server/.env" ]; then
    echo -e "  ${CYAN}首次部署，运行 deploy.sh...${NC}"
    cd "$SCRIPT_DIR"
    bash deploy.sh
fi

# ===== 3. 申请 SSL 证书 =====
echo -e "  ${CYAN}[2/5]${NC} 申请 SSL 证书..."

# 先配置临时 HTTP Nginx 以通过验证
cat > /etc/nginx/sites-available/vuemonitor-temp << EOF
server {
    listen 80;
    server_name ${API_DOMAIN} ${ADMIN_DOMAIN};
    location / { return 200 'ok'; }
}
EOF
ln -sf /etc/nginx/sites-available/vuemonitor-temp /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t 2>/dev/null && systemctl reload nginx

certbot certonly --nginx -d "${API_DOMAIN}" -d "${ADMIN_DOMAIN}" --non-interactive --agree-tos --email "admin@${DOMAIN}" 2>/dev/null || {
    echo -e "  ${YELLOW}Nginx 验证失败，尝试 DNS 验证...${NC}"
    echo -e "  ${YELLOW}请先在 Cloudflare 添加 DNS 记录：${NC}"
    echo -e "    A  api  → ${SERVER_IP}  → ☁️已代理"
    echo -e "    A  admin → ${SERVER_IP}  → ☁️已代理"
    echo ""
    read -p "  DNS 记录已添加？(y/N): " DNS_READY
    if [ "$DNS_READY" = "y" ] || [ "$DNS_READY" = "Y" ]; then
        certbot certonly --nginx -d "${API_DOMAIN}" -d "${ADMIN_DOMAIN}" --non-interactive --agree-tos --email "admin@${DOMAIN}"
    fi
}

rm -f /etc/nginx/sites-enabled/vuemonitor-temp

# ===== 4. 配置 Nginx =====
echo -e "  ${CYAN}[3/5]${NC} 配置 Nginx..."

cat > /etc/nginx/sites-available/vuemonitor << NGINXEOF
server {
    listen 443 ssl http2;
    server_name ${API_DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${API_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${API_DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$http_cf_connecting_ip;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Request-ID \$http_x_request_id;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$http_cf_connecting_ip;
        proxy_read_timeout 86400;
    }
}

server {
    listen 443 ssl http2;
    server_name ${ADMIN_DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${API_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${API_DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    root /opt/vuemonitor/web-admin/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$http_cf_connecting_ip;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
}

server {
    listen 80;
    server_name ${API_DOMAIN} ${ADMIN_DOMAIN};
    return 301 https://\$host\$request_uri;
}
NGINXEOF

ln -sf /etc/nginx/sites-available/vuemonitor /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t 2>/dev/null && systemctl reload nginx

# ===== 5. 配置 XHS365 =====
echo -e "  ${CYAN}[4/5]${NC} 配置 XHS365..."

ENV_FILE="$SCRIPT_DIR/server/.env"
if [ -f "$ENV_FILE" ]; then
    sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=[\"https://${ADMIN_DOMAIN}\",\"https://${API_DOMAIN}\"]|" "$ENV_FILE"
    sed -i "s|^DEBUG=.*|DEBUG=false|" "$ENV_FILE"

    [ -n "$OPENAI_KEY" ] && sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${OPENAI_KEY}|" "$ENV_FILE"
    [ -n "$DEEPSEEK_KEY" ] && sed -i "s|^DEEPSEEK_API_KEY=.*|DEEPSEEK_API_KEY=${DEEPSEEK_KEY}|" "$ENV_FILE"
fi

# ===== 6. 防火墙 =====
echo -e "  ${CYAN}[5/5]${NC} 配置防火墙..."
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 80/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1
ufw --force enable > /dev/null 2>&1

# 重启服务
systemctl restart vuemonitor 2>/dev/null || true

# ===== 完成 =====
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║          🎉 配置完成！                    ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  API:     https://${API_DOMAIN}    ║"
echo "  ║  管理后台: https://${ADMIN_DOMAIN}  ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  打包客户端时输入:                        ║"
echo "  ║  https://${API_DOMAIN}             ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  Cloudflare 还需手动设置:                ║"
echo "  ║  1. DNS 添加 A 记录（☁️已代理）          ║"
echo "  ║  2. SSL/TLS → 完全（严格）               ║"
echo "  ║  3. 网络 → WebSocket → 开启              ║"
echo "  ║  4. SSL/TLS → 始终HTTPS → 开启           ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
