#!/bin/bash
# 在【服务器】上运行：生成 GitHub 拉代码用的 Deploy Key（只读）
# 用法:
#   cd /opt/vuemonitor && bash scripts/server-setup-github-deploy-key.sh
#
# 完成后把屏幕上的【公钥】添加到 GitHub:
#   仓库 Settings → Deploy keys → Add deploy key（勾选 Allow read access）
# 私钥留在服务器，不要发给任何人。

set -euo pipefail

KEY="$HOME/.ssh/vuemonitor_deploy_ed25519"
REPO="${1:-git@github.com:haha222ha/vuemonitor.git}"

if [ -f "$KEY" ]; then
  echo "密钥已存在: $KEY"
else
  ssh-keygen -t ed25519 -C "vuemonitor-server-deploy" -f "$KEY" -N ""
  chmod 600 "$KEY"
  chmod 644 "${KEY}.pub"
  echo "已生成: $KEY"
fi

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if ! grep -q 'Host github.com-vuemonitor' "$HOME/.ssh/config" 2>/dev/null; then
  cat >> "$HOME/.ssh/config" <<EOF

Host github.com-vuemonitor
    HostName github.com
    User git
    IdentityFile $KEY
    IdentitiesOnly yes
EOF
  chmod 600 "$HOME/.ssh/config"
  echo "已写入 ~/.ssh/config → Host github.com-vuemonitor"
fi

echo ""
echo "========== 请复制下面【整行公钥】到 GitHub Deploy keys =========="
cat "${KEY}.pub"
echo "================================================================="
echo ""
echo "GitHub 添加 Deploy Key 后，在服务器测试:"
echo "  ssh -T git@github.com-vuemonitor"
echo ""
echo "若仓库 remote 仍是 github.com，可改为:"
echo "  cd /opt/vuemonitor"
echo "  git remote set-url origin git@github.com-vuemonitor:haha222ha/vuemonitor.git"
echo "  git fetch origin main && git reset --hard origin/main"
echo ""
echo "⚠ 私钥文件 $KEY 切勿复制给他人或贴到聊天里。"
