@echo off
setlocal enabledelayedexpansion
REM ================================================================================
REM Automatic Meeting Media Processor
REM ================================================================================
REM
REM This script starts automatic monitoring of the input/ folder
REM to process new video and audio files.
REM
REM The path to the data folder is configured via DATA_PATH variable in .env file.
REM Default is ./data
REM

echo.
echo ================================================================================
echo           AUTOMATIC MEETING MEDIA PROCESSOR
echo ================================================================================
echo.
echo Checking environment...
echo.

REM Read configuration from .env file
set "DATA_PATH=data"
set "ENABLE_SPEAKER_RECOGNITION=false"
set "ENABLE_OPENWEBUI_RAG=false"
set "RECOGNITION_THRESHOLD=0.75"
set "MAX_UNRECOGNIZED_SPEAKERS_FOR_RAG=2"

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if /i "%%a"=="DATA_PATH" (
            set "DATA_PATH=%%b"
            REM Replace forward slashes with backslashes for Windows
            set "DATA_PATH=!DATA_PATH:/=\!"
        )
        if /i "%%a"=="ENABLE_SPEAKER_RECOGNITION" set "ENABLE_SPEAKER_RECOGNITION=%%b"
        if /i "%%a"=="ENABLE_OPENWEBUI_RAG" set "ENABLE_OPENWEBUI_RAG=%%b"
        if /i "%%a"=="RECOGNITION_THRESHOLD" set "RECOGNITION_THRESHOLD=%%b"
        if /i "%%a"=="MAX_UNRECOGNIZED_SPEAKERS_FOR_RAG" set "MAX_UNRECOGNIZED_SPEAKERS_FOR_RAG=%%b"
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

REM Check if Python 3.11 venv exists for speaker recognition
set "ORCHESTRATOR_PYTHON=python"
if exist "services\transcription_orchestrator\venv\Scripts\python.exe" (
    set "ORCHESTRATOR_PYTHON=services\transcription_orchestrator\venv\Scripts\python.exe"
    echo [INFO] Using Python 3.11 venv for orchestrator - speaker recognition enabled
) else (
    echo [INFO] Python 3.11 venv not found. Using system Python.
    echo [INFO] Speaker recognition will not be available.
    echo [INFO] To enable, run: services\transcription_orchestrator\setup.bat
)

REM Create necessary folders
if not exist "!DATA_PATH!\input" mkdir "!DATA_PATH!\input"
if not exist "!DATA_PATH!\results" mkdir "!DATA_PATH!\results"
if not exist "!DATA_PATH!\audio" mkdir "!DATA_PATH!\audio"
if not exist "!DATA_PATH!\transcripts" mkdir "!DATA_PATH!\transcripts"

REM Create speaker_profiles directory for speaker recognition
if not exist "!DATA_PATH!\speaker_profiles" (
    mkdir "!DATA_PATH!\speaker_profiles"
    mkdir "!DATA_PATH!\speaker_profiles\embeddings"
    echo [INFO] Created speaker_profiles directory
)

echo.
echo [OK] All checks passed!
echo.
echo ================================================================================
echo                         FEATURE STATUS
echo ================================================================================
echo.

REM Display Speaker Recognition status
if /i "!ENABLE_SPEAKER_RECOGNITION!"=="true" (
    if exist "services\transcription_orchestrator\venv\Scripts\python.exe" (
        echo   [ON]  Speaker Recognition    - Enabled ^(threshold: !RECOGNITION_THRESHOLD!^)
    ) else (
        echo   [OFF] Speaker Recognition    - Enabled in .env but venv not found!
        echo         Run: services\transcription_orchestrator\setup.bat
    )
) else (
    echo   [OFF] Speaker Recognition    - Disabled in .env
)

REM Display OpenWebUI RAG status
if /i "!ENABLE_OPENWEBUI_RAG!"=="true" (
    echo   [ON]  OpenWebUI RAG Indexing - Enabled
    echo         RAG Speaker Threshold   - Max !MAX_UNRECOGNIZED_SPEAKERS_FOR_RAG! unrecognized speakers
) else (
    echo   [OFF] OpenWebUI RAG Indexing - Disabled in .env
)

echo.
echo ================================================================================
echo Starting automatic monitoring...
echo ================================================================================
echo.
echo Monitoring folder: !DATA_PATH!\input
echo Supported video: .mp4 .avi .mov .mkv .webm .flv .wmv
echo Supported audio: .wav .m4a .mp3 .ogg .flac .aac .wma
echo Logs: !DATA_PATH!\video_processor.log
echo Database: !DATA_PATH!\processed_videos.json
echo.
echo Press Ctrl+C to stop
echo.
echo ================================================================================
echo.

REM Start monitoring (use venv Python if available)
%ORCHESTRATOR_PYTHON% services\transcription_orchestrator\watch_input_folder.py

echo.
echo ================================================================================
echo Monitoring stopped
echo ================================================================================
pause
