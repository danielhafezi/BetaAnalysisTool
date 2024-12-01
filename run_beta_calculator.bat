@echo off
echo Starting Beta Calculator...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH!
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Create cache directory if it doesn't exist
if not exist "cache" mkdir cache

REM Run the Streamlit app
echo Loading application...
start "" http://localhost:8501
streamlit run main.py

pause 