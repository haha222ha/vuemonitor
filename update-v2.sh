#!/bin/bash
cd /opt/vuemonitor && sudo rm -rf client/node_modules/.vite 2>/dev/null; git fetch origin main && git reset --hard origin/main && exec bash scripts/host-update.sh "$@"