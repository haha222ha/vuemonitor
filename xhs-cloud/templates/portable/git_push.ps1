# D 盘 — 提交并 push xhs-cloud 改动（首次 push 需 GitHub 登录，见 §0.5.4）
# 用法:
#   powershell -ExecutionPolicy Bypass -File D:\vuemonitor\xhs-cloud\templates\portable\git_push.ps1
#   powershell -ExecutionPolicy Bypass -File ...\git_push.ps1 -Message "feat(xhs-cloud): 说明"

param(
    [string]$Message = "feat(xhs-cloud): 便携工作区更新"
)

$ErrorActionPreference = "Stop"
$repo = "D:\vuemonitor"
Set-Location $repo

$gitCmd = $null
$gitExe = Get-Command git -ErrorAction SilentlyContinue
if ($gitExe) { $gitCmd = $gitExe.Source }
if (-not $gitCmd) {
    foreach ($p in @("D:\PortableGit\cmd\git.exe", "C:\Program Files\Git\cmd\git.exe")) {
        if (Test-Path $p) { $gitCmd = $p; break }
    }
}
if (-not $gitCmd) {
    Write-Host "未找到 git。见需求文档 §0.5.2" -ForegroundColor Red
    exit 1
}
function git { & $gitCmd @args }

Write-Host "=== Git Push: xhs-cloud/ ===" -ForegroundColor Cyan
git status -sb
git add xhs-cloud/ scripts/push-xhs-cloud.ps1 scripts/reopen-git-login.bat `
    xhs-cloud/templates/portable/git_pull.ps1 xhs-cloud/templates/portable/git_push.ps1
$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "没有 xhs-cloud 相关改动需要提交。" -ForegroundColor Yellow
    exit 0
}
git commit -m $Message
Write-Host "正在 push 到 origin main ..." -ForegroundColor Cyan
git push origin main
Write-Host ""
Write-Host "Push 完成。云主机执行 §0.5.5: cd /opt/vuemonitor && git pull && rsync ..." -ForegroundColor Green
