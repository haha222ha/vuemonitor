#!/bin/bash
# 根目录快捷入口（与 HOST_UPDATE.md 中一键命令等价）
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
