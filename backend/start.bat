@echo off
echo ============================================
echo  AI Job Hunter - Backend Setup ^& Start
echo ============================================

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause & exit /b 1
)

:: Create venv if it doesn't exist
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install dependencies
echo [INFO] Installing dependencies (this may take a few minutes first time)...
pip install -r requirements.txt --quiet

:: Copy .env if it doesn't exist
if not exist ".env" (
    echo [INFO] Creating .env from template...
    copy .env.example .env
    echo [WARN] Please edit .env with your credentials!
)

:: Create directories
if not exist "resumes\" mkdir resumes
if not exist "chroma_db\" mkdir chroma_db
if not exist "logs\" mkdir logs

:: Fix Windows Unicode encoding (allows emoji in logs)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: Start the server
echo.
echo [INFO] Starting FastAPI server at http://localhost:8000
echo [INFO] API Docs: http://localhost:8000/docs
echo [INFO] Press Ctrl+C to stop
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
