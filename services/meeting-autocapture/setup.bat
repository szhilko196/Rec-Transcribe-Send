@echo off
REM ========================================
REM Meeting Auto Capture - Setup Script
REM ========================================

echo.
echo ============================================================
echo   Meeting Auto Capture - Setup
echo ============================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check Python
echo [1/7] Checking Python installation...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

REM Create virtual environment
echo.
echo [2/7] Creating virtual environment...
if exist "venv" (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)

REM Activate virtual environment
echo.
echo [3/7] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo [4/7] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo [5/7] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

REM Install Playwright browsers
echo.
echo [6/7] Installing Playwright browsers...
echo This may take a few minutes...
playwright install chromium
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright browsers!
    pause
    exit /b 1
)

REM Install ffmpeg
echo.
echo [7/7] Installing ffmpeg for screen capture...
echo.

REM Check if ffmpeg is already installed in project tools folder
set "FFMPEG_PATH=..\..\tools\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe"
if exist "%FFMPEG_PATH%" (
    echo ffmpeg already installed at %FFMPEG_PATH%
    echo Verifying installation...
    "%FFMPEG_PATH%" -version >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] ffmpeg found but not working correctly
        echo Please reinstall ffmpeg manually
    ) else (
        echo ffmpeg is working correctly
    )
) else (
    echo ffmpeg not found in project tools folder
    echo.
    echo ============================================================
    echo   ffmpeg Installation Required
    echo ============================================================
    echo.
    echo ffmpeg is required for screen + audio capture.
    echo.
    echo Option 1: Automatic download ^(recommended^)
    echo   We will download ffmpeg essentials build from gyan.dev
    echo.
    echo Option 2: Manual installation
    echo   Download from: https://www.gyan.dev/ffmpeg/builds/
    echo   Extract to: C:\prj\Rec-Transcribe-Send\tools\
    echo.
    choice /C YN /M "Download and install ffmpeg automatically"
    if errorlevel 2 (
        echo.
        echo Skipping automatic ffmpeg installation.
        echo Please install ffmpeg manually before running the service.
        echo See README.md for instructions.
        echo.
    ) else (
        echo.
        echo Downloading ffmpeg...

        REM Create tools directory
        if not exist "..\..\tools" mkdir "..\..\tools"

        REM Download ffmpeg
        echo Downloading from https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
        curl -L "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -o "..\..\tools\ffmpeg.zip"

        if errorlevel 1 (
            echo [ERROR] Failed to download ffmpeg!
            echo Please download manually from https://www.gyan.dev/ffmpeg/builds/
            pause
        ) else (
            echo.
            echo Extracting ffmpeg...
            tar -xf "..\..\tools\ffmpeg.zip" -C "..\..\tools"

            if errorlevel 1 (
                echo [ERROR] Failed to extract ffmpeg!
                pause
            ) else (
                echo.
                echo Cleaning up...
                del "..\..\tools\ffmpeg.zip"

                echo.
                echo Verifying ffmpeg installation...
                "%FFMPEG_PATH%" -version >nul 2>&1
                if errorlevel 1 (
                    echo [WARNING] ffmpeg installation may be incomplete
                ) else (
                    echo ffmpeg installed successfully!
                )
            )
        )
    )
)

echo.
echo NOTE: Update audio device name in src\browser_joiner.py line 231
echo       Run: ffmpeg -list_devices true -f dshow -i dummy
echo       to list available audio devices
echo.

REM Create directories
echo.
echo Creating data directories...
if not exist "data\meetings\pending" mkdir data\meetings\pending
if not exist "data\meetings\in_progress" mkdir data\meetings\in_progress
if not exist "data\meetings\completed" mkdir data\meetings\completed
if not exist "data\browser_profiles" mkdir data\browser_profiles
if not exist "logs" mkdir logs

REM Create .env if doesn't exist
echo.
echo Checking configuration...
if not exist "config\.env" (
    echo Creating config\.env from template...
    copy config\.env.example config\.env
    echo.
    echo ============================================================
    echo   IMPORTANT: Configure your environment
    echo ============================================================
    echo.
    echo Please edit config\.env with your credentials:
    echo   - Email settings (IMAP - use App Password)
    echo   - Video output folder (default: ../../data/input)
    echo   - Timing settings (optional)
    echo.
    echo Opening config\.env in notepad...
    timeout /t 2 /nobreak >nul
    notepad config\.env
)

REM Run tests
echo.
echo Running installation tests...
python test_installation.py
if errorlevel 1 (
    echo.
    echo [WARNING] Some tests failed. Please review the output above.
    echo You can still try to run the service, but it may not work correctly.
) else (
    echo.
    echo ============================================================
    echo   Setup completed successfully!
    echo ============================================================
    echo.
    echo You can now start the service:
    echo   start.bat
)

echo.
pause
