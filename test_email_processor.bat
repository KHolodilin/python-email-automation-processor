@echo off
REM Manual integration test: run pipeline, then send folder.
REM Requires config.yaml and EMAIL_PROCESSOR_TEST_RECIPIENT for send step.
chcp 65001 >nul
set PYTHONUTF8=1
setlocal

echo ========================================
echo Email Processor Testing Script
echo ========================================
echo.

REM Prefer venv Python if present
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=py"
)

REM Step 1: Run full pipeline (fetch + send)
echo [1/3] Running full pipeline (fetch + send)...
echo ----------------------------------------
"%PYTHON_CMD%" -m email_processor run
if errorlevel 1 (
    echo ERROR: Pipeline failed!
    pause
    exit /b 1
)
echo.
echo Pipeline completed successfully.
echo.

REM Step 2: Create test file for send-folder step
echo [2/3] Creating test file for send-folder...
echo ----------------------------------------

if not exist "send_folder" (
    echo Creating send_folder...
    mkdir send_folder
)

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "datetime=%%I"
set "TEST_FILE=send_folder\test_%datetime:~0,8%_%datetime:~8,6%.txt"

echo Test file content > "%TEST_FILE%"
echo Created at: %date% %time% >> "%TEST_FILE%"
echo This is a test file for email sending. >> "%TEST_FILE%"
echo File path: %TEST_FILE% >> "%TEST_FILE%"
echo.

if not exist "%TEST_FILE%" (
    echo ERROR: Failed to create test file.
    pause
    exit /b 1
)
echo Test file created: %TEST_FILE%
echo.

REM Step 3: Send folder (requires --to)
echo [3/3] Sending folder via SMTP...
echo ----------------------------------------
if not defined EMAIL_PROCESSOR_TEST_RECIPIENT (
    echo ERROR: Set EMAIL_PROCESSOR_TEST_RECIPIENT before running send step.
    echo Example: set EMAIL_PROCESSOR_TEST_RECIPIENT=you@example.com
    pause
    exit /b 1
)
"%PYTHON_CMD%" -m email_processor send folder send_folder --to "%EMAIL_PROCESSOR_TEST_RECIPIENT%"
if errorlevel 1 (
    echo ERROR: Send folder failed!
    pause
    exit /b 1
)
echo.
echo Send folder completed successfully.
echo.

echo ========================================
echo All steps completed successfully.
echo ========================================
pause
