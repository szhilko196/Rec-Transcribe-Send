@echo off
REM ================================================================================
REM Speaker Recognition Setup - Python 3.11 Virtual Environment
REM ================================================================================
REM
REM This script sets up the Python 3.11 environment for speaker recognition
REM

echo.
echo ================================================================================
echo   SPEAKER RECOGNITION SETUP (Python 3.11)
echo ================================================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python 3.11 is installed
if not exist "C:\Python311\python.exe" (
    echo [ERROR] Python 3.11 not found at C:\Python311\python.exe
    echo.
    echo Please install Python 3.11.9 64-bit from:
    echo https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo.
    pause
    exit /b 1
)

echo [1/4] Checking Python 3.11 installation...
C:\Python311\python.exe --version
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to run Python 3.11
    pause
    exit /b 1
)

echo.
echo [2/4] Creating virtual environment...
if exist "venv\Scripts\pip.exe" (
    echo [INFO] Virtual environment already exists, skipping creation...
) else (
    if exist "venv" (
        echo [INFO] Removing incomplete venv...
        rmdir /s /q venv 2>nul
        timeout /t 2 /nobreak >nul
    )

    echo [INFO] Creating new virtual environment...
    C:\Python311\python.exe -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo.
echo [3/4] Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip

echo.
echo [4/4] Installing dependencies (this may take 5-10 minutes)...
venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo [SUCCESS] Speaker recognition environment setup complete!
echo ================================================================================
echo.
echo Virtual environment location: %~dp0venv
echo.
echo To enable speaker recognition, set in .env:
echo   ENABLE_SPEAKER_RECOGNITION=true
echo.
pause
