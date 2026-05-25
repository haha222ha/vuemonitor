#!/bin/bash
set -euo pipefail

TARGET=${1:-https://api.xhs365.cn}
REPORT_DIR="./security/reports"
mkdir -p "$REPORT_DIR"

echo "============================================"
echo "  XHS365 安全头验证"
echo "  目标: $TARGET"
echo "============================================"

check_header() {
    local url=$1
    local header=$2
    local expected=$3

    value=$(curl -sI "$url" | grep -i "^$header:" | head -1 | sed "s/^$header: //i" | tr -d '\r')
    if [ -z "$value" ]; then
        echo "  [FAIL] $header 缺失"
    elif [ -n "$expected" ] && [ "$value" != "$expected" ]; then
        echo "  [WARN] $header = '$value' (期望: '$expected')"
    else
        echo "  [OK]   $header = '$value'"
    fi
}

echo ""
echo "--- HTTPS 重定向检查 ---"
http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://${TARGET#https://}")
if [ "$http_code" = "301" ] || [ "$http_code" = "302" ]; then
    echo "  [OK] HTTP → HTTPS 重定向 ($http_code)"
else
    echo "  [FAIL] HTTP 未重定向到 HTTPS (状态码: $http_code)"
fi

echo ""
echo "--- 安全响应头检查 ---"
check_header "$TARGET" "Strict-Transport-Security" ""
check_header "$TARGET" "X-Content-Type-Options" "nosniff"
check_header "$TARGET" "X-Frame-Options" ""
check_header "$TARGET" "X-XSS-Protection" ""
check_header "$TARGET" "Referrer-Policy" ""
check_header "$TARGET" "Permissions-Policy" ""

echo ""
echo "--- API文档暴露检查 ---"
docs_code=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/docs")
redoc_code=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/redoc")
openapi_code=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/openapi.json")

if [ "$docs_code" = "404" ]; then
    echo "  [OK] /docs 返回 404 (生产环境不应暴露)"
else
    echo "  [FAIL] /docs 返回 $docs_code (应返回404)"
fi

if [ "$redoc_code" = "404" ]; then
    echo "  [OK] /redoc 返回 404"
else
    echo "  [FAIL] /redoc 返回 $redoc_code (应返回404)"
fi

if [ "$openapi_code" = "404" ]; then
    echo "  [OK] /openapi.json 返回 404"
else
    echo "  [FAIL] /openapi.json 返回 $openapi_code (应返回404)"
fi

echo ""
echo "--- 敏感端点访问控制检查 ---"
metrics_code=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/metrics")
if [ "$metrics_code" = "403" ] || [ "$metrics_code" = "404" ]; then
    echo "  [OK] /metrics 不可公网访问 ($metrics_code)"
else
    echo "  [WARN] /metrics 返回 $metrics_code (应限制内网访问)"
fi

echo ""
echo "--- CORS 检查 ---"
cors_origin=$(curl -sI -H "Origin: https://evil.com" "$TARGET/api/v1/health" | grep -i "^Access-Control-Allow-Origin:" | head -1)
if [ -z "$cors_origin" ]; then
    echo "  [OK] 非法Origin被拒绝"
else
    echo "  [WARN] CORS 允许: $cors_origin"
fi

echo ""
echo "============================================"
echo "  安全头验证完成"
echo "============================================"
