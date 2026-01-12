@echo off
chcp 65001 >nul
set PYTHONUTF8=1
echo Running tests...
pytest -v
pause
