# D 盘移动硬盘 — 一键从 GitHub 拉最新代码（通常无需 GitHub 登录）
# 用法:
#   powershell -ExecutionPolicy Bypass -File D:\vuemonitor\xhs-cloud\templates\portable\git_pull.ps1

$ErrorActionPreference = "Stop"
$repo = "D:\vuemonitor"

$gitCmd = $null
$gitExe = Get-Command git -ErrorAction SilentlyContinue
if ($gitExe) { $gitCmd = $gitExe.Source }
if (-not $gitCmd) {
    foreach ($p in @("D:\PortableGit\cmd\git.exe", "C:\Program Files\Git\cmd\git.exe")) {
        if (Test-Path $p) { $gitCmd = $p; break }
    }
}
if (-not $gitCmd) {
    Write-Host "未找到 git。请复制 PortableGit 到 D:\PortableGit\ 或安装 Git for Windows。" -ForegroundColor Red
    exit 1
}
function git { & $gitCmd @args }

if (-not (Test-Path (Join-Path $repo ".git"))) {
    Write-Host "未找到 $repo\.git — 请确认移动硬盘含完整 vuemonitor 仓库。" -ForegroundColor Red
    exit 1
}

Write-Host "=== Git Pull: $repo ===" -ForegroundColor Cyan
Write-Host "git: $gitCmd" -ForegroundColor DarkGray

git -C $repo remote -v
git -C $repo fetch origin main
git -C $repo pull origin main
Write-Host ""
Write-Host "当前 HEAD:" -ForegroundColor Green
git -C $repo log -1 --oneline
Write-Host ""
Write-Host "Pull 完成。若需 push，见需求文档 §0.5.4" -ForegroundColor Green
