@echo off
REM ========================================
REM Meeting Auto Capture - Launch Script
REM ========================================

echo.
echo ============================================================
echo   Meeting Auto Capture - Starting...
echo ============================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run setup first:
    echo   setup.bat
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/4] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist "config\.env" (
    echo.
    echo [WARNING] Configuration file not found!
    echo.
    echo Creating config\.env from template...
    copy config\.env.example config\.env
    echo.
    echo Please edit config\.env with your credentials:
    echo   notepad config\.env
    echo.
    echo Then run this script again.
    pause
    exit /b 1
)

REM Check Python
echo [2/4] Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found in virtual environment!
    pause
    exit /b 1
)

REM Check ffmpeg
echo [3/4] Checking ffmpeg...
set "FFMPEG_PATH=..\..\tools\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe"
if exist "%FFMPEG_PATH%" (
    echo ffmpeg found: %FFMPEG_PATH%
    "%FFMPEG_PATH%" -version >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] ffmpeg found but not working correctly!
        echo Please reinstall ffmpeg: run setup.bat
        pause
    )
) else (
    echo.
    echo [ERROR] ffmpeg not found!
    echo.
    echo ffmpeg is required for screen + audio capture.
    echo Expected location: %FFMPEG_PATH%
    echo.
    echo Please run setup.bat to install ffmpeg automatically
    echo or install manually from: https://www.gyan.dev/ffmpeg/builds/
    echo.
    pause
    exit /b 1
)

REM Start the service
echo [4/4] Starting Meeting Auto Capture service...
echo.
echo ============================================================
echo   Service is starting...
echo   Press Ctrl+C to stop
echo ============================================================
echo.

python src\main.py

REM If Python exits with error
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   Service stopped with error!
    echo ============================================================
    pause
    exit /b 1
)

REM Normal exit
echo.
echo ============================================================
echo   Service stopped
echo ============================================================
pause
