@echo off
chcp 65001 >nul
cd /d D:\vuemonitor\xhs-cloud
powershell -ExecutionPolicy Bypass -File tools\git_push_agent.ps1
pause
