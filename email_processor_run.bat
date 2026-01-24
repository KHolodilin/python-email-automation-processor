@echo off
REM Run email processor (full pipeline: fetch + send).
REM Ensure UTF-8 for log output.
chcp 65001 >nul
set PYTHONUTF8=1
py -m email_processor run
pause
