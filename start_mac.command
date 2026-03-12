#!/bin/bash
echo "Starting Painting Tracker..."
echo "Please wait while the app loads."
echo ""
echo "Do not close this window while using the app."
echo ""

if ! command -v python3 &> /dev/null; then
    echo "Python is not installed."
    echo "Please install Python from https://python.org/downloads"
    read -p "Press Enter to exit."
    exit
fi

pip3 install streamlit pandas plotly fpdf2 colorthief --quiet

cd "$(dirname "$0")"
streamlit run app.py

read -p "Press Enter to exit."