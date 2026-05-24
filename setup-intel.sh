#!/bin/bash
set -e

echo ""
echo "============================================"
echo "  intel.xhs365.cn 首次部署 (仅需执行一次)"
echo "  SSL: Cloudflare Flexible SSL (源站HTTP)"
echo "============================================"
echo ""

echo "[1/2] 安装 Nginx 配置..."
sudo cp /opt/vuemonitor/nginx/intel.conf /etc/nginx/sites-available/intel.xhs365.cn
sudo ln -sf /etc/nginx/sites-available/intel.xhs365.cn /etc/nginx/sites-enabled/intel.xhs365.cn
echo "  OK"

echo "[2/2] 重载 Nginx..."
sudo nginx -t && sudo systemctl reload nginx
echo "  OK"

echo ""
echo "============================================"
echo "  首次部署完成!"
echo "============================================"
echo ""
echo "  Cloudflare 设置:"
echo "    DNS: intel.xhs365.cn -> 服务器IP (A记录, Proxied)"
echo "    SSL: Flexible 模式"
echo ""
echo "  访问: https://intel.xhs365.cn"
echo "============================================"
