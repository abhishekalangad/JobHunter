@echo off
cd /d "%~dp0"

echo ===================================================
echo   AI Job Hunter - Launching Backend ^& Frontend
echo ===================================================
echo.

if not exist "%~dp0backend\venv\Scripts\python.exe" (
    echo [ERROR] Backend Python virtualenv not found!
    echo Please ensure backend\venv exists.
    pause
    exit /b 1
)

echo [1/2] Launching Backend (http://localhost:8000)...
start "Backend - AI Job Hunter" /D "%~dp0backend" cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

echo [2/2] Launching Frontend (http://localhost:3000)...
start "Frontend - AI Job Hunter" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo Opening app at http://localhost:3000 in browser...
ping 127.0.0.1 -n 6 >nul
start http://localhost:3000
