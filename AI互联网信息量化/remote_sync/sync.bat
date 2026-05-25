@echo off
cd /d "%~dp0"
pip install -r requirements.txt -q
python full_sync.py %*
pause
