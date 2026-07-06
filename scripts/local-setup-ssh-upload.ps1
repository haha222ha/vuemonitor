# 在【你的 Windows 电脑】上运行：配置上传安装包到服务器（scp）
# 用法（PowerShell）:
#   cd E:\vuemonitor
#   powershell -ExecutionPolicy Bypass -File scripts\local-setup-ssh-upload.ps1
#
# 只需把【公钥】加到服务器 root 的 authorized_keys。
# 私钥留在本机，不要发给 AI 或任何人。

param(
    [string]$ServerHost = "47.239.181.111",
    [string]$ServerUser = "root"
)

$ErrorActionPreference = "Stop"
$sshDir = Join-Path $env:USERPROFILE ".ssh"
$keyPath = Join-Path $sshDir "id_ed25519_xhs365_upload"
$pubPath = "$keyPath.pub"
$configPath = Join-Path $sshDir "config"

New-Item -ItemType Directory -Force -Path $sshDir | Out-Null

if (-not (Test-Path $keyPath)) {
    Write-Host "生成密钥: $keyPath" -ForegroundColor Cyan
    ssh-keygen -t ed25519 -C "xhs365-upload-from-pc" -f $keyPath -N '""'
} else {
    Write-Host "密钥已存在: $keyPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========== 第 1 步：把下面【公钥】加到服务器 ==========" -ForegroundColor Green
Get-Content $pubPath
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "在服务器执行（需输入一次 root 密码）:" -ForegroundColor Cyan
Write-Host @"
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo '$(Get-Content $pubPath -Raw).Trim()' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
"@

Write-Host ""
Write-Host "或本机一条命令（会提示输入密码）:" -ForegroundColor Cyan
Write-Host "  type `"$pubPath`" | ssh ${ServerUser}@${ServerHost} `"mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`"" -ForegroundColor White

# 写入 SSH config
$block = @"

Host xhs365
    HostName $ServerHost
    User $ServerUser
    IdentityFile $keyPath
    IdentitiesOnly yes
"@

if (Test-Path $configPath) {
    $cfg = Get-Content $configPath -Raw
    if ($cfg -notmatch 'Host xhs365') {
        Add-Content -Path $configPath -Value $block
        Write-Host "已追加 Host xhs365 到 $configPath" -ForegroundColor Green
    }
} else {
    Set-Content -Path $configPath -Value $block.TrimStart()
    Write-Host "已创建 $configPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "========== 第 2 步：测试免密登录 ==========" -ForegroundColor Green
Write-Host "  ssh xhs365 `"echo OK`"" -ForegroundColor White
Write-Host ""
Write-Host "看到 OK 后，告诉 Cursor：SSH 已配好 Host=xhs365" -ForegroundColor Green
Write-Host "⚠ 私钥 $keyPath 切勿发送给他人" -ForegroundColor Red
