#!/bin/bash
# Plan A 安全同步 —— 只覆盖白名单文件，禁止全量 rsync --delete
# 用法（服务器）:
#   sudo bash /opt/vuemonitor/xhs-cloud/../  # 或
#   cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main
#   sudo bash /path/to/safe-sync-plan-a.sh
#
# 原则（对齐 LifeOS 架构：失败不得覆盖 last-known-good）:
# 1. 不同步整个 cloud_deploy（避免冲掉生产独有模块，如 sync/upload-session）
# 2. 先校验源文件存在，再写入目标
# 3. 同步后做健康与路由冒烟；失败则打印诊断，不继续乱重启循环

set -u

REPO="${REPO:-/opt/vuemonitor}"
DEST="${DEST:-/opt/xhs-cloud}"
API_UNIT="${API_UNIT:-xhs-cloud-api}"

SRC_API="$REPO/xhs-cloud/cloud_deploy/cloud_api"
SRC_ASSETS="$REPO/xhs-cloud/cloud_deploy/assets"
DST_API="$DEST/cloud_deploy/cloud_api"
DST_ASSETS="$DEST/cloud_deploy/assets"

red() { echo -e "\033[0;31m$*\033[0m"; }
green() { echo -e "\033[0;32m$*\033[0m"; }
cyan() { echo -e "\033[0;36m$*\033[0m"; }

fail() { red "✗ $*"; exit 1; }

need() {
  [ -f "$1" ] || fail "缺少源文件: $1"
}

copy_one() {
  local src="$1" dst="$2"
  need "$src"
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
  echo "  synced $(basename "$src") -> $dst"
}

cyan "==== Plan A safe sync ===="
echo "repo=$REPO"
echo "dest=$DEST"
echo "commit=$(cd "$REPO" && git log -1 --oneline 2>/dev/null || echo unknown)"

# —— 白名单 ——

# channel board ingest：constants / routes（缺 ARCHIVE_CHANNEL_BOARD 会导致 commit 500）
copy_one "/xhs-cloud/cloud_deploy/reporting/constants.py" "/cloud_deploy/reporting/constants.py"
copy_one "/channel_board_routes.py" "/channel_board_routes.py"

copy_one "$SRC_API/portal_admin.py" "$DST_API/portal_admin.py"
copy_one "$SRC_API/public_catalog.py" "$DST_API/public_catalog.py"
# main.py 含 admin 静态路由与 portal_admin include；若生产有独有补丁，先备份再覆盖
if [ -f "$DST_API/main.py" ]; then
  cp -f "$DST_API/main.py" "$DST_API/main.py.bak.$(date +%Y%m%d%H%M%S)" || true
fi
copy_one "$SRC_API/main.py" "$DST_API/main.py"

mkdir -p "$DST_ASSETS/admin_portal" "$DST_ASSETS/saas_shelf"
copy_one "$SRC_ASSETS/admin_portal/index.html" "$DST_ASSETS/admin_portal/index.html"
if [ -f "$SRC_ASSETS/saas_shelf/index.html" ]; then
  copy_one "$SRC_ASSETS/saas_shelf/index.html" "$DST_ASSETS/saas_shelf/index.html"
fi
if [ -f "$SRC_ASSETS/saas_shelf/public_apps.json" ]; then
  copy_one "$SRC_ASSETS/saas_shelf/public_apps.json" "$DST_ASSETS/saas_shelf/public_apps.json"
fi

# digit-hub 兜底（admin 若仍被默认站接住）
if [ -d /opt/digit-hub/apps/web ]; then
  mkdir -p /opt/digit-hub/apps/web/admin
  cp -f "$DST_ASSETS/admin_portal/index.html" /opt/digit-hub/apps/web/admin/index.html
  echo "  synced digit-hub/apps/web/admin/index.html"
fi

# nginx admin 反代（若尚未存在）
if [ ! -f /etc/nginx/conf.d/admin.xhs365.cn.conf ]; then
  cat >/etc/nginx/conf.d/admin.xhs365.cn.conf <<'NGX'
upstream xhs_admin_api {
    server 127.0.0.1:8080;
    keepalive 8;
}
server {
    listen 80;
    server_name admin.xhs365.cn;
    client_max_body_size 32m;
    add_header Cache-Control "no-store" always;
    location / {
        proxy_pass http://xhs_admin_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $http_cf_connecting_ip;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120s;
    }
}
NGX
  echo "  wrote /etc/nginx/conf.d/admin.xhs365.cn.conf"
fi

nginx -t && systemctl reload nginx || red "! nginx reload skipped"

systemctl restart "$API_UNIT"
ok_health=0
for i in $(seq 1 20); do
  code=$(curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/v1/health 2>/dev/null || echo 000)
  echo "  health try $i -> $code"
  if [ "$code" = "200" ]; then ok_health=1; break; fi
  sleep 1
done
[ "$ok_health" = "1" ] || fail "API 健康检查失败，请 journalctl -u $API_UNIT -n 50"

cyan "==== smoke ===="
for p in /admin /admin/ /admin/index.html; do
  curl -sS -o /tmp/plan_a_smoke.html -w "  8080$p %{http_code} size=%{size_download}\n" "http://127.0.0.1:8080$p"
done
grep -q "自用运营栈" /tmp/plan_a_smoke.html || fail "admin HTML 缺少「自用运营栈」"
curl -sS -o /dev/null -w "  ops-stack %{http_code}\n" http://127.0.0.1:8080/api/v1/portal/admin/ops-stack
curl -sS -o /dev/null -w "  internal-apps %{http_code}\n" http://127.0.0.1:8080/api/v1/public/internal-apps
curl -sS -o /dev/null -w "  hub %{http_code}\n" http://127.0.0.1:8080/hub
curl -sS -o /dev/null -w "  public-apps %{http_code}\n" http://127.0.0.1:8080/api/v1/public/apps

green "✓ Plan A safe sync 完成"
echo "浏览器: https://admin.xhs365.cn/admin/  (admin / 你设置的密码)"
echo "注意: 禁止对本目录使用 rsync --delete 全量覆盖"
