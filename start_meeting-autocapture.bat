@echo off
REM ================================================================================
REM Meeting Auto Capture - Launcher (Root Wrapper)
REM ================================================================================
REM
REM This script launches the Meeting Auto Capture service from the root folder.
REM It simply calls the start.bat script in the services/meeting-autocapture directory.
REM

echo.
echo ================================================================================
echo           MEETING AUTO CAPTURE - LAUNCHER
echo ================================================================================
echo.

REM Change to script directory (root folder)
cd /d "%~dp0"

REM Call the actual start script in the service directory
call services\meeting-autocapture\start.bat

REM Exit with the same error code
exit /b %ERRORLEVEL%
