#!/bin/bash
echo "Starting Painting Tracker..."
echo "Please wait while the app loads."
echo ""
echo "Do not close this window while using the app."
echo ""

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/streamlit" ]; then
    echo "First-time setup: creating virtual environment..."
    if ! command -v python3 &> /dev/null; then
        echo "Python is not installed."
        echo "Please install Python from https://python.org/downloads"
        read -p "Press Enter to exit."
        exit 1
    fi
    python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt --quiet
.venv/bin/streamlit run app.py

read -p "Press Enter to exit."
