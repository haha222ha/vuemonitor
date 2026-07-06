#!/bin/bash
# 私钥已下载到本机后，在云主机删除私钥（公钥保留在 authorized_keys）
# 用法: bash scripts/server-remove-pc-upload-private-key.sh

set -euo pipefail

KEY="$HOME/.ssh/xhs365_pc_upload_ed25519"

if [ -f "$KEY" ]; then
  echo "删除私钥: $KEY"
  rm -f "$KEY"
else
  echo "私钥已不存在: $KEY"
fi

if [ -f "${KEY}.pub" ]; then
  echo "保留公钥: ${KEY}.pub（authorized_keys 中仍有效）"
fi

echo "完成。本机推送请使用 dev_deploy_gui.py 配置私钥路径。"
