@echo off
echo Starting Painting Tracker...
echo Please wait while the app loads.
echo.
echo Do not close this window while using the app.
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed.
    echo Please install Python from https://python.org/downloads
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit
)

pip install streamlit pandas plotly fpdf2 colorthief --quiet

streamlit run app.py

pause