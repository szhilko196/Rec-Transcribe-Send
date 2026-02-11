@echo off
echo Starting FileToRag Service...
cd /d "%~dp0services\file-to-rag"

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

if not exist .env (
    if exist config\.env.example (
        copy config\.env.example .env
        echo.
        echo WARNING: .env file created from template!
        echo Please edit .env and set your OPENWEBUI_API_KEY.
        echo.
        pause
        exit /b 1
    )
)

REM Create watch folder if not exists
if not exist "..\..\data\FileToRag" mkdir "..\..\data\FileToRag"

echo Starting file watcher...
python -m src.main
