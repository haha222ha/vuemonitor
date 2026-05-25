#!/bin/bash
set -euo pipefail

TARGET=${1:-http://localhost:8000}
REPORT_DIR="./security/reports"
mkdir -p "$REPORT_DIR"

echo "============================================"
echo "  XHS365 OWASP ZAP 安全扫描"
echo "  目标: $TARGET"
echo "============================================"

if ! command -v zap-cli &>/dev/null && ! command -v zap.sh &>/dev/null; then
    echo "[ERROR] ZAP 未安装"
    echo "安装方法: docker pull zaproxy/zap-stable"
    echo "运行方法: docker run -t zaproxy/zap-stable zap-baseline.py -t $TARGET"
    exit 1
fi

if command -v docker &>/dev/null; then
    echo "使用 Docker 运行 ZAP 扫描..."

    docker run --rm \
        -v "$(pwd)/$REPORT_DIR:/zap/wrk" \
        zaproxy/zap-stable \
        zap-baseline.py \
        -t "$TARGET" \
        -r "baseline_report.html" \
        -w "baseline_report.md" \
        -j \
        -a \
        --hook=/zap/scripts/hooks.py \
        -z "-config api.disablekey=true" \
        || true

    echo ""
    echo "扫描报告已生成:"
    echo "  HTML: $REPORT_DIR/baseline_report.html"
    echo "  Markdown: $REPORT_DIR/baseline_report.md"
else
    echo "[ERROR] Docker 未安装，无法运行 ZAP"
    exit 1
fi
