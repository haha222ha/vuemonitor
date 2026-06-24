# D 盘移动硬盘结构验证 — 插入任意电脑后运行:
#   powershell -ExecutionPolicy Bypass -File D:\vuemonitor\xhs-cloud\templates\portable\verify_d_drive.ps1

$paths = @(
    "D:\vuemonitor\xhs-cloud\docs\需求规格书_精品库双向同步_v1.md",
    "D:\0622小红薯备份\jiekoufenxi\小红书多设备爬虫\xhs_premium_schema.py",
    "D:\0622小红薯备份\jiekoufenxi\小红书多设备爬虫\crawl_data",
    "D:\关键词搜索\最终版_实体产品搜索词库.txt",
    "D:\关键词搜索\最终版_虚拟产品搜索词库.txt",
    "D:\选品报告"
)

Write-Host "=== D 盘便携工作区验证 ===" -ForegroundColor Cyan
$ok = 0
$fail = 0
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "OK   $p" -ForegroundColor Green
        $ok++
    } else {
        Write-Host "缺失 $p" -ForegroundColor Red
        $fail++
    }
}
Write-Host ""
Write-Host "通过 $ok / $($paths.Count)" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
if ($fail -eq 0) {
    Write-Host "可打开 Cursor 文件夹: D:\vuemonitor" -ForegroundColor Green
}
