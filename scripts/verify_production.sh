#!/bin/bash
# 生产域名快速验收（可选环境变量覆盖）
set -euo pipefail

API_URL="${API_URL:-https://api.xhs365.cn/health}"
WWW_URL="${WWW_URL:-https://www.xhs365.cn}"
ADMIN_URL="${ADMIN_URL:-https://admin.xhs365.cn}"
INTEL_URL="${INTEL_URL:-https://intel.xhs365.cn}"

check() {
  local name="$1" url="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$url" || echo "000")
  if [[ "$code" =~ ^(200|301|302)$ ]]; then
    echo "  OK  $name HTTP $code  $url"
  else
    echo "  FAIL $name HTTP $code  $url"
    return 1
  fi
}

echo "=== XHS365 production verify ==="
FAIL=0
check "API" "$API_URL" || FAIL=1
check "WWW" "$WWW_URL" || FAIL=1
check "ADMIN" "$ADMIN_URL" || FAIL=1
if curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$INTEL_URL" 2>/dev/null | grep -qE '^(200|301|302)$'; then
  echo "  OK  INTEL  $INTEL_URL"
else
  echo "  SKIP INTEL (optional) $INTEL_URL"
fi

if [ "$FAIL" -eq 0 ]; then
  echo "=== All required checks passed ==="
  exit 0
fi
echo "=== Some checks failed ==="
exit 1
