$Wsh = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Repo = Split-Path $PSScriptRoot -Parent
$Bat = Join-Path $Repo "tools\open_agent_config.bat"

# 删除旧快捷方式（含乱码/中文名）
@(
    "XHS本地采集配置.lnk",
    "XHS-Agent-Config.lnk",
    "XHS鏈地閲囬泦閰嶇疆.lnk"
) | ForEach-Object {
    $p = Join-Path $Desktop $_
    if (Test-Path $p) { Remove-Item $p -Force }
}
Get-ChildItem $Desktop -Filter "*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $sc = $Wsh.CreateShortcut($_.FullName)
        if ($sc.TargetPath -like "*启动本地采集配置.bat" -or $sc.TargetPath -like "*open_agent_config.bat") {
            if ($_.Name -ne "XHS-Agent-Config.lnk") { Remove-Item $_.FullName -Force }
        }
    } catch {}
}

$Shortcut = $Wsh.CreateShortcut((Join-Path $Desktop "XHS-Agent-Config.lnk"))
$Shortcut.TargetPath = $Bat
$Shortcut.WorkingDirectory = $Repo
$Shortcut.IconLocation = "shell32.dll,13"
$Shortcut.Description = "XHS local risk agent config (optional)"
$Shortcut.Save()
Write-Host "OK: Desktop shortcut -> XHS-Agent-Config.lnk" -ForegroundColor Green
