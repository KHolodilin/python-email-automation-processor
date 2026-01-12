@echo off
chcp 65001 >nul
set PYTHONUTF8=1
py -m email_processor
pause