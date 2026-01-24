@echo off
REM Run pytest over the test suite (quick run, no coverage).
REM For coverage, use: py -m tests.run_all_tests or pytest with --cov.
chcp 65001 >nul
set PYTHONUTF8=1
echo Running tests...
py -m pytest tests/ -v
pause
