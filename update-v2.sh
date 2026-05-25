#!/bin/bash
# 兼容旧命令：转发到 2G 优化更新脚本
set -e
ROOT="${DEPLOY_ROOT:-/opt/vuemonitor}"
cd "$ROOT"
exec bash "$ROOT/scripts/host-update.sh" "$@"