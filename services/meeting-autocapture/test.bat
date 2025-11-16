@echo off
REM ========================================
REM Meeting Auto Capture - Test Script
REM ========================================

echo.
echo ============================================================
echo   Meeting Auto Capture - Running Tests
echo ============================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup first: setup.bat
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run tests
python test_installation.py

echo.
pause
