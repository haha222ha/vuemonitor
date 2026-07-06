#!/bin/bash
# 在【云主机】上生成「本机 scp 上传」用的密钥对
# 用法: bash scripts/server-setup-pc-upload-key.sh
#
# 流程:
#   1. 本脚本生成公钥+私钥
#   2. 公钥写入 ~/.ssh/authorized_keys（允许本机免密登录）
#   3. 你用【一次性密码】把私钥下载到 Windows，勿发给 AI
#   4. 私钥下载后在本机执行: bash scripts/server-remove-pc-upload-private-key.sh
#
# 私钥路径: ~/.ssh/xhs365_pc_upload_ed25519

set -euo pipefail

KEY="$HOME/.ssh/xhs365_pc_upload_ed25519"
AUTH="$HOME/.ssh/authorized_keys"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [ -f "$KEY" ]; then
  echo "密钥已存在: $KEY"
else
  ssh-keygen -t ed25519 -C "xhs365-pc-upload-$(date +%Y%m%d)" -f "$KEY" -N ""
  chmod 600 "$KEY"
  chmod 644 "${KEY}.pub"
  echo "已生成密钥对"
fi

PUB_LINE="$(cat "${KEY}.pub")"
if [ -f "$AUTH" ] && grep -qF "$PUB_LINE" "$AUTH" 2>/dev/null; then
  echo "公钥已在 authorized_keys 中"
else
  echo "$PUB_LINE" >> "$AUTH"
  chmod 600 "$AUTH"
  echo "公钥已追加到 authorized_keys"
fi

echo ""
echo "========== 第 1 步：把【私钥】下载到你的 Windows =========="
echo "在 Windows PowerShell 执行（会提示输入一次服务器密码）:"
echo ""
echo "  mkdir \$env:USERPROFILE\\.ssh -Force"
echo "  scp $(whoami)@$(hostname -I 2>/dev/null | awk '{print $1}' || echo '47.239.181.111'):$KEY \$env:USERPROFILE\\.ssh\\xhs365_pc_upload"
echo ""
echo "若 IP 不对，把上面命令里的 IP 改成你的云主机公网 IP。"
echo ""
echo "========== 第 2 步：私钥下载成功后，在云主机删除私钥 =========="
echo "  bash scripts/server-remove-pc-upload-private-key.sh"
echo ""
echo "========== 第 3 步：打开本机可视化推送工具 =========="
echo "  cd E:\\vuemonitor"
echo "  py -3.11 scripts\\dev_deploy_gui.py"
echo "  在界面里选择私钥: %USERPROFILE%\\.ssh\\xhs365_pc_upload"
echo ""
echo "公钥指纹（便于核对）:"
ssh-keygen -lf "${KEY}.pub"
echo ""
echo "⚠ 私钥 $KEY 下载到本机后请从服务器删除，切勿发给 AI 或贴到聊天"
