@echo off
echo ============================================================
echo Starting Invoice & Legal Document Extraction Pipeline
echo ============================================================
echo.
cd /d "%~dp0"

echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "Backend Server" cmd /k "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Frontend Server on http://127.0.0.1:3000 ...
start "Frontend Server" cmd /k "cd frontend && python -m http.server 3000"

timeout /t 1 /nobreak >nul

echo.
echo Opening Web Application in your default browser...
start http://127.0.0.1:3000

echo.
echo Both servers are running!
echo Frontend: http://127.0.0.1:3000
echo API Docs: http://127.0.0.1:8000/docs
echo.
pause
