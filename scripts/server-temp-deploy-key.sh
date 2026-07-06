#!/bin/bash
# 一次性临时 Deploy Key（服务器 git pull 用）
# 用法: bash scripts/server-temp-deploy-key.sh
# 完成后把【公钥】发给运维核对；私钥勿外传。
# 用完后: bash scripts/server-destroy-temp-deploy-key.sh

set -euo pipefail

KEY="$HOME/.ssh/vuemonitor_temp_deploy_ed25519"
MARKER="$HOME/.ssh/.vuemonitor_temp_deploy_created"

if [ -f "$KEY" ]; then
  echo "临时密钥已存在: $KEY"
else
  ssh-keygen -t ed25519 -C "vuemonitor-temp-deploy-$(date +%Y%m%d)" -f "$KEY" -N ""
  chmod 600 "$KEY"
  chmod 644 "${KEY}.pub"
  date -Iseconds > "$MARKER"
  echo "已生成临时密钥"
fi

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if ! grep -q 'Host github.com-vuemonitor-temp' "$HOME/.ssh/config" 2>/dev/null; then
  cat >> "$HOME/.ssh/config" <<EOF

Host github.com-vuemonitor-temp
    HostName github.com
    User git
    IdentityFile $KEY
    IdentitiesOnly yes
EOF
  chmod 600 "$HOME/.ssh/config"
fi

echo ""
echo "========== 复制下面公钥 → GitHub Deploy keys =========="
cat "${KEY}.pub"
echo "======================================================="
echo ""
echo "GitHub: 仓库 Settings → Deploy keys → Add（只读即可）"
echo "测试: ssh -T git@github.com-vuemonitor-temp"
echo ""
echo "拉代码:"
echo "  cd /opt/vuemonitor"
echo "  git remote set-url origin git@github.com-vuemonitor-temp:haha222ha/vuemonitor.git"
echo "  git fetch origin main && git reset --hard origin/main"
echo "  bash scripts/host-update.sh"
echo ""
echo "⚠ 私钥路径: $KEY （勿发送给他人）"
echo "用完后销毁: bash scripts/server-destroy-temp-deploy-key.sh"
