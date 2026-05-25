#!/bin/bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && exec bash scripts/host-update.sh "$@"