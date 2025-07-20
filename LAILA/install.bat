@echo off
REM LAAI Installation Script for Windows
REM This script sets up the LAAI platform for immediate use

echo 🚀 LAILA - Learn AI and LA Platform Installation
echo ===============================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python found

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

echo.
echo ✅ Installation completed successfully!
echo.
echo 🎯 Next Steps:
echo 1. Configure your API keys in config.py (optional)
echo 2. Run the application:
echo    venv\Scripts\activate.bat
echo    python app.py
echo 3. Open http://localhost:5001 in your browser
echo.
echo 📚 For detailed instructions, see README.md
echo.
echo 🎉 Happy researching with LAILA!
pause
