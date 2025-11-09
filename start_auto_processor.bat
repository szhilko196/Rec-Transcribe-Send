@echo off
setlocal enabledelayedexpansion
REM ================================================================================
REM Automatic Meeting Video Processor
REM ================================================================================
REM
REM This script starts automatic monitoring of the input/ folder
REM to process new video files.
REM
REM The path to the data folder is configured via DATA_PATH variable in .env file.
REM Default is ./data
REM

echo.
echo ================================================================================
echo           AUTOMATIC MEETING VIDEO PROCESSOR
echo ================================================================================
echo.
echo Checking environment...
echo.

REM Read DATA_PATH from .env file
set "DATA_PATH=data"
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if /i "%%a"=="DATA_PATH" (
            set "DATA_PATH=%%b"
            REM Replace forward slashes with backslashes for Windows
            set "DATA_PATH=!DATA_PATH:/=\!"
        )
    )
)

echo [INFO] Using data path: !DATA_PATH!
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

REM Check Docker services
echo Checking Docker services...
docker-compose ps | findstr "meeting-ffmpeg" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FFmpeg service is not running
    echo Starting Docker services...
    docker-compose up -d
    timeout /t 5 >nul
)

REM Check dependencies
python -c "import watchdog" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing watchdog...
    pip install watchdog
)

python -c "from dotenv import load_dotenv" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing python-dotenv...
    pip install python-dotenv
)

python -c "import anthropic" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing anthropic...
    pip install anthropic
)

REM Create necessary folders
if not exist "!DATA_PATH!\input" mkdir "!DATA_PATH!\input"
if not exist "!DATA_PATH!\results" mkdir "!DATA_PATH!\results"
if not exist "!DATA_PATH!\audio" mkdir "!DATA_PATH!\audio"
if not exist "!DATA_PATH!\transcripts" mkdir "!DATA_PATH!\transcripts"

echo.
echo [OK] All checks passed!
echo.
echo ================================================================================
echo Starting automatic monitoring...
echo ================================================================================
echo.
echo Monitoring folder: !DATA_PATH!\input
echo Logs: !DATA_PATH!\video_processor.log
echo Database: !DATA_PATH!\processed_videos.json
echo.
echo Press Ctrl+C to stop
echo.
echo ================================================================================
echo.

REM Start monitoring
python scripts\watch_input_folder.py

echo.
echo ================================================================================
echo Monitoring stopped
echo ================================================================================
pause
