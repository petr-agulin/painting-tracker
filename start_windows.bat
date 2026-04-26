@echo off
echo Starting Painting Tracker...
echo Please wait while the app loads.
echo.
echo Do not close this window while using the app.
echo.

cd /d "%~dp0"

if not exist .venv\Scripts\streamlit.exe (
    echo First-time setup: creating virtual environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo Python is not installed.
            echo Please install Python from https://python.org/downloads
            echo Make sure to check "Add Python to PATH" during installation.
            pause
            exit /b 1
        )
        python -m venv .venv
    )
)

.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
.venv\Scripts\streamlit.exe run app.py

pause
