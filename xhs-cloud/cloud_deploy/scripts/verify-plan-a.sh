#!/bin/bash
# Plan A 现网验收（本机 :8080 + 可选公网）
set -u
BASE="${BASE:-http://127.0.0.1:8080}"
PUBLIC_ADMIN="${PUBLIC_ADMIN:-https://admin.xhs365.cn}"
PUBLIC_WWW="${PUBLIC_WWW:-https://www.xhs365.cn}"

check() {
  local name="$1" url="$2" expect="$3"
  code=$(curl -sS -o /tmp/vpa_body -w "%{http_code}" "$url" 2>/dev/null || echo 000)
  if [ "$code" = "$expect" ]; then
    echo "  OK  $name -> $code"
  else
    echo "  FAIL $name -> $code (want $expect)  $url"
  fi
}

echo "==== local $BASE ===="
check health "$BASE/api/v1/health" 200
check admin "$BASE/admin/" 200
check ops_noauth "$BASE/api/v1/portal/admin/ops-stack" 401
check internal_gone "$BASE/api/v1/public/internal-apps" 404
check hub_gone "$BASE/hub" 404
check apps "$BASE/api/v1/public/apps" 200

if grep -q "自用运营栈" /tmp/vpa_body 2>/dev/null || curl -sS "$BASE/admin/" | grep -q "自用运营栈"; then
  echo "  OK  admin HTML contains 自用运营栈"
else
  echo "  FAIL admin HTML missing 自用运营栈"
fi

echo "==== public (optional) ===="
check pub_admin "$PUBLIC_ADMIN/admin/" 200
check pub_hub "$PUBLIC_WWW/hub" 404
check pub_internal "$PUBLIC_WWW/api/v1/public/internal-apps" 404

echo "done"
