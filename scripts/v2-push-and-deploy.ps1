# V2 开发机：commit/push xhs-cloud → SSH 云主机 v2-oneclick-deploy.sh
#
# 用法:
#   cd E:\vuemonitor
#   $env:XHS_DEPLOY_SSH = 'root@你的ECS'          # 必填（远程 SSH）
#   $env:XHS_MEMBER_TOKEN = 'eyJ...'              # 可选，冒烟用
#   $env:XHS_SMOKE_EXPECT = 'legacy_dual'         # 可选
#   powershell -ExecutionPolicy Bypass -File scripts\v2-push-and-deploy.ps1 -Message "fix: radar UI"
#
# 仅 push 不 SSH:
#   ... -SkipDeploy
# 仅 SSH 不 commit（已 push 过）:
#   ... -SkipCommit -SkipPush
#
param(
    [string]$Message = "chore(xhs-cloud): V2 deploy",
    [switch]$SkipCommit,
    [switch]$SkipPush,
    [switch]$SkipDeploy,
    [string]$DeployHost = $env:XHS_DEPLOY_SSH,
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Find-Git {
    $gitExe = Get-Command git -ErrorAction SilentlyContinue
    if ($gitExe) { return $gitExe.Source }
    foreach ($p in @("D:\PortableGit\cmd\git.exe", "C:\Tools\PortableGit\cmd\git.exe")) {
        if (Test-Path $p) { return $p }
    }
    throw "未找到 git，请安装 Git for Windows"
}

$gitCmd = Find-Git
function git { & $gitCmd @args }

$paths = @(
    "xhs-cloud/",
    "projects/ai-market-intelligence-v2/docs/28-MASTER-TODO-TRACKER.md",
    "projects/ai-market-intelligence-v2/docs/29-V2-ONECLICK-DEPLOY-RUNBOOK.md",
    "projects/ai-market-intelligence-v2/docs/26-T0-SHADOW-RUNBOOK.md",
    "projects/ai-market-intelligence-v2/docs/01-DOCUMENT-INDEX.md",
    ".cursor/rules/xhs-cloud-deploy.mdc",
    "scripts/v2-push-and-deploy.ps1"
)

if (-not $SkipCommit) {
    Write-Host "`n>>> git status" -ForegroundColor Cyan
    & git status -sb
    & git add @paths
    $staged = & git diff --cached --name-only
    if (-not $staged) {
        Write-Host "无 xhs-cloud 相关改动，跳过 commit" -ForegroundColor Yellow
    } else {
        Write-Host ">>> commit: $Message" -ForegroundColor Cyan
        & git commit -m $Message
    }
}

if (-not $SkipPush) {
    Write-Host ">>> push origin $Branch" -ForegroundColor Cyan
    & git push -u origin $Branch
    & git log -1 --oneline
}

if ($SkipDeploy) {
    Write-Host "`nSkipDeploy=1，请在云主机执行:" -ForegroundColor Yellow
    Write-Host @"
export XHS_MEMBER_TOKEN='...'
export XHS_SMOKE_EXPECT=legacy_dual
bash /opt/xhs-cloud/cloud_deploy/scripts/v2-oneclick-deploy.sh
"@ -ForegroundColor Gray
    exit 0
}

if (-not $DeployHost) {
    Write-Host "`n未设置 XHS_DEPLOY_SSH / -DeployHost，跳过远程部署。" -ForegroundColor Yellow
    Write-Host "云主机手动执行 v2-oneclick-deploy.sh（见 doc 29）" -ForegroundColor Yellow
    exit 0
}

$ssh = Get-Command ssh -ErrorAction SilentlyContinue
if (-not $ssh) {
    throw "需要 OpenSSH 客户端 (ssh.exe)"
}

$token = $env:XHS_MEMBER_TOKEN
$expect = if ($env:XHS_SMOKE_EXPECT) { $env:XHS_SMOKE_EXPECT } else { "legacy_dual" }
$remoteEnv = "export XHS_SMOKE_EXPECT='$expect'"
if ($token) {
    $escaped = $token -replace "'", "'\\''"
    $remoteEnv += "; export XHS_MEMBER_TOKEN='$escaped'"
} else {
    $remoteEnv += "; export SKIP_SMOKE=1"
    Write-Host "未设置 XHS_MEMBER_TOKEN，远程将 SKIP_SMOKE=1" -ForegroundColor Yellow
}

$remoteScript = @'
set -euo pipefail
ONECLICK=/opt/xhs-cloud/cloud_deploy/scripts/v2-oneclick-deploy.sh
if [[ ! -x "$ONECLICK" ]]; then
  echo "==> bootstrap oneclick script"
  cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main
  rsync -a /opt/vuemonitor/xhs-cloud/cloud_deploy/scripts/v2-oneclick-deploy.sh /opt/xhs-cloud/cloud_deploy/scripts/
  chmod +x "$ONECLICK"
fi
__REMOTE_ENV__
bash "$ONECLICK"
'@ -replace '__REMOTE_ENV__', $remoteEnv

Write-Host "`n>>> SSH deploy @ $DeployHost" -ForegroundColor Cyan
& ssh $DeployHost $remoteScript

Write-Host "`n>>> 完成。浏览器 Ctrl+Shift+R: https://monitor.xhs365.cn/member" -ForegroundColor Green
