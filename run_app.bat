@echo off
echo ============================================================
echo Starting DocuExtract AI - Document Extraction Pipeline
echo ============================================================
echo.
cd /d "%~dp0"

echo Starting Unified Application Server on http://127.0.0.1:8000 ...
start "DocuExtract Server" cmd /k "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo.
echo Opening Web Application in your default browser...
start http://127.0.0.1:8000

echo.
echo ============================================================
echo Application is running!
echo Web UI:      http://127.0.0.1:8000
echo API Docs:    http://127.0.0.1:8000/docs
echo ============================================================
echo.
pause
