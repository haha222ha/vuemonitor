$Wsh = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Repo = Split-Path $PSScriptRoot -Parent
$Shortcut = $Wsh.CreateShortcut((Join-Path $Desktop "XHS本地采集配置.lnk"))
$Shortcut.TargetPath = Join-Path $Repo "tools\启动本地采集配置.bat"
$Shortcut.WorkingDirectory = $Repo
$Shortcut.IconLocation = "shell32.dll,13"
$Shortcut.Description = "XHS 本地 risk 采集配置"
$Shortcut.Save()
Write-Host "桌面快捷方式已创建: XHS本地采集配置.lnk" -ForegroundColor Green
