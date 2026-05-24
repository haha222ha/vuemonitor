#!/bin/bash
set -e

echo ""
echo "============================================"
echo "  intel.xhs365.cn 首次部署 (仅需执行一次)"
echo "============================================"
echo ""

# 1. 复制 Nginx 配置
echo "[1/3] 安装 Nginx 配置..."
sudo cp /opt/vuemonitor/nginx/intel.conf /etc/nginx/sites-available/intel.xhs365.cn
sudo ln -sf /etc/nginx/sites-available/intel.xhs365.cn /etc/nginx/sites-enabled/intel.xhs365.cn
echo "  OK"

# 2. 申请 SSL 证书
echo "[2/3] 申请 SSL 证书..."
if sudo certbot --nginx -d intel.xhs365.cn --non-interactive --agree-tos --email admin@xhs365.cn 2>/dev/null; then
  echo "  OK"
else
  echo "  certbot 自动申请失败，请手动执行:"
  echo "    sudo certbot --nginx -d intel.xhs365.cn"
fi

# 3. 重载 Nginx
echo "[3/3] 重载 Nginx..."
sudo nginx -t && sudo systemctl reload nginx
echo "  OK"

echo ""
echo "============================================"
echo "  首次部署完成!"
echo "============================================"
echo ""
echo "  访问: https://intel.xhs365.cn"
echo "============================================"
