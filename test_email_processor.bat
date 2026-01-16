@echo off
chcp 65001 >nul
set PYTHONUTF8=1
setlocal

echo ========================================
echo Email Processor Testing Script
echo ========================================
echo.

REM Check if virtual environment exists and use it
if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=.venv\Scripts\python.exe
) else (
    set PYTHON_CMD=py
)

REM Step 1: Test email receiving (default mode)
echo [1/3] Testing email receiving (default mode)...
echo ----------------------------------------
%PYTHON_CMD% -m email_processor
if errorlevel 1 (
    echo ERROR: Email receiving failed!
    pause
    exit /b 1
)
echo.
echo Email receiving completed successfully!
echo.

REM Step 2: Create test file for sending
echo [2/3] Creating test file for sending...
echo ----------------------------------------

REM Ensure send_folder exists
if not exist "send_folder" (
    echo Creating send_folder directory...
    mkdir send_folder
)

REM Create test file with timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TEST_FILE=send_folder\test_%datetime:~0,8%_%datetime:~8,6%.txt

echo Test file content > "%TEST_FILE%"
echo Created at: %date% %time% >> "%TEST_FILE%"
echo This is a test file for email sending functionality. >> "%TEST_FILE%"
echo File path: %TEST_FILE% >> "%TEST_FILE%"
echo.

if not exist "%TEST_FILE%" (
    echo ERROR: Failed to create test file!
    pause
    exit /b 1
)
echo Test file created: %TEST_FILE%
echo.

REM Step 3: Test email sending
echo [3/3] Testing email sending...
echo ----------------------------------------
%PYTHON_CMD% -m email_processor --send-folder send_folder
if errorlevel 1 (
    echo ERROR: Email sending failed!
    pause
    exit /b 1
)
echo.
echo Email sending completed successfully!
echo.

echo ========================================
echo All tests completed successfully!
echo ========================================
pause
