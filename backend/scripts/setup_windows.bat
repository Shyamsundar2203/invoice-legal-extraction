@echo off
REM One-click setup for Windows: creates a virtual environment and installs
REM everything the backend needs. Run this from inside the `backend` folder:
REM     scripts\setup_windows.bat
REM (or double-click it from File Explorer)

echo ==============================================
echo  Invoice ^& Legal Doc Extraction - Windows Setup
echo ==============================================

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher 'py' not found. Install Python from
    echo https://www.python.org/downloads/ and check "Add Python to PATH".
    pause
    exit /b 1
)

echo.
echo Creating virtual environment (venv)...
py -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ==============================================
echo  Setup complete!
echo  Next steps:
echo    1. Make sure Tesseract OCR is installed:
echo       https://github.com/UB-Mannheim/tesseract/wiki
echo    2. Start the server with:
echo       venv\Scripts\activate
echo       uvicorn app.main:app --reload
echo ==============================================
pause
