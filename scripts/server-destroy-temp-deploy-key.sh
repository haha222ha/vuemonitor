#!/bin/bash
# 销毁临时 Deploy Key（本地文件 + 提示删除 GitHub Deploy key）
# 用法: bash scripts/server-destroy-temp-deploy-key.sh

set -euo pipefail

KEY="$HOME/.ssh/vuemonitor_temp_deploy_ed25519"
MARKER="$HOME/.ssh/.vuemonitor_temp_deploy_created"
CONFIG="$HOME/.ssh/config"

echo "========== 销毁本地临时密钥 =========="

if [ -f "$KEY" ]; then
  rm -f "$KEY"
  echo "已删除: $KEY"
else
  echo "未找到: $KEY"
fi

if [ -f "${KEY}.pub" ]; then
  echo "曾使用的公钥指纹（便于在 GitHub 对照删除）:"
  ssh-keygen -lf "${KEY}.pub" 2>/dev/null || true
  rm -f "${KEY}.pub"
  echo "已删除: ${KEY}.pub"
fi

rm -f "$MARKER"

if [ -f "$CONFIG" ]; then
  # 删除 Host github.com-vuemonitor-temp 块
  awk '
    /^Host github.com-vuemonitor-temp$/ { skip=1; next }
    skip && /^Host / { skip=0 }
    skip && /^$/ { skip=0; next }
    !skip { print }
  ' "$CONFIG" > "${CONFIG}.tmp" && mv "${CONFIG}.tmp" "$CONFIG"
  chmod 600 "$CONFIG"
  echo "已从 ~/.ssh/config 移除 github.com-vuemonitor-temp"
fi

echo ""
echo "========== 请在 GitHub 手动删除 Deploy key =========="
echo "仓库 → Settings → Deploy keys → 删除标题含 vuemonitor-temp-deploy 的项"
echo ""
echo "若曾改 remote，可恢复 HTTPS（可选）:"
echo "  cd /opt/vuemonitor"
echo "  git remote set-url origin https://github.com/haha222ha/vuemonitor.git"
echo ""
echo "本地临时密钥已清理完毕。"
