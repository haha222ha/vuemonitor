@echo off
chcp 65001 >nul
echo ========================================
echo  重新打开 GitHub 登录（Git 凭据）
echo ========================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 git，请先安装 Git for Windows:
    echo   https://git-scm.com/download/win
    echo  安装时勾选 "Git Credential Manager"
    pause
    exit /b 1
)

echo 方式1: Git Credential Manager 登录窗口...
git credential-manager github login 2>nul
if errorlevel 1 (
    git-credential-manager.exe github login 2>nul
)

echo.
echo 方式2: 若未弹窗，将触发 push 登录...
cd /d E:\vuemonitor
git push origin main

echo.
echo 若浏览器要求输入设备码，请打开:
echo   https://github.com/login/device
pause
