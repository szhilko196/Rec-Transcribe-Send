@echo off
REM ============================================================
REM Complete Virtual Environment Rebuild Script
REM ============================================================
REM This script completely removes and recreates the venv with Python 3.11

echo.
echo ============================================================
echo   REBUILDING VIRTUAL ENVIRONMENT WITH PYTHON 3.11
echo ============================================================
echo.

cd /d "%~dp0"

REM Step 1: Check Python 3.11
echo [1/6] Checking Python 3.11 availability...
py -3.11 --version
if errorlevel 1 (
    echo.
    echo ERROR: Python 3.11 not found!
    echo Please install Python 3.11 64-bit from https://www.python.org/
    pause
    exit /b 1
)
echo.

REM Step 2: Remove old venv
echo [2/6] Removing old virtual environment...
if exist "venv" (
    echo Deleting venv folder...
    rd /s /q venv
    if exist "venv" (
        echo ERROR: Failed to delete venv folder!
        echo Please close any programs using it and try again.
        pause
        exit /b 1
    )
    echo Old venv removed successfully
) else (
    echo No existing venv found
)
echo.

REM Step 3: Create new venv with Python 3.11
echo [3/6] Creating new virtual environment with Python 3.11...
py -3.11 -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment!
    pause
    exit /b 1
)
echo Virtual environment created successfully
echo.

REM Step 4: Verify Python version
echo [4/6] Verifying Python version in venv...
venv\Scripts\python.exe --version
echo Expected: Python 3.11.x
echo.

REM Step 5: Upgrade pip
echo [5/6] Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip
echo.

REM Step 6: Install all requirements
echo [6/6] Installing all dependencies...
echo This may take a few minutes...
venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)
echo.

REM Step 7: Install Playwright browsers
echo [7/7] Installing Playwright Chromium browser...
echo This may take a few minutes and download ~300MB...
venv\Scripts\playwright.exe install chromium
if errorlevel 1 (
    echo WARNING: Playwright browser installation may have failed
    echo You can retry manually: venv\Scripts\playwright.exe install chromium
)
echo.

REM Final verification
echo.
echo ============================================================
echo   VERIFICATION
echo ============================================================
echo.

echo Checking Python version:
venv\Scripts\python.exe --version
echo.

echo Checking pydantic installation:
venv\Scripts\python.exe -c "import pydantic; print(f'pydantic {pydantic.__version__} - OK')"
if errorlevel 1 (
    echo ERROR: pydantic check failed!
    pause
    exit /b 1
)
echo.

echo Checking pydantic_core:
venv\Scripts\python.exe -c "from pydantic_core import __version__; print(f'pydantic_core {__version__} - OK')"
if errorlevel 1 (
    echo ERROR: pydantic_core check failed!
    pause
    exit /b 1
)
echo.

echo Checking playwright:
venv\Scripts\python.exe -c "import playwright; print(f'playwright {playwright.__version__} - OK')"
if errorlevel 1 (
    echo WARNING: playwright check failed!
)
echo.

echo ============================================================
echo   SUCCESS! Virtual environment is ready.
echo ============================================================
echo.
echo You can now run: start.bat
echo.
pause
