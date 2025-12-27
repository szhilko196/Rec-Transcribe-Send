@echo off
REM List available audio devices for ffmpeg DirectShow
REM This helps configure the correct audio device name for recording

echo.
echo ============================================================
echo Listing DirectShow Audio Devices for ffmpeg
echo ============================================================
echo.

set FFMPEG_PATH=C:\prj\Rec-Transcribe-Send\tools\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe

if not exist "%FFMPEG_PATH%" (
    echo [ERROR] ffmpeg not found at: %FFMPEG_PATH%
    echo Please update the path in this script.
    pause
    exit /b 1
)

echo Running: %FFMPEG_PATH% -list_devices true -f dshow -i dummy
echo.
echo ============================================================
echo.

"%FFMPEG_PATH%" -list_devices true -f dshow -i dummy 2>&1 | findstr /C:"DirectShow audio devices" /C:"Alternative name" /A

echo.
echo ============================================================
echo.
echo Copy the EXACT name of your audio device (including quotes if present)
echo and add it to your .env file as:
echo MAC_AUDIO_DEVICE=audio="Your Device Name Here"
echo.
echo Or edit browser_joiner.py line 255 to use your device name
echo ============================================================
pause
