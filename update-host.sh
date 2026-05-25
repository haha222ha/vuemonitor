#!/bin/bash
# 根目录快捷入口（与 HOST_UPDATE.md 中一键命令等价）
cd /opt/vuemonitor && sudo rm -rf client/node_modules/.vite 2>/dev/null; git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
