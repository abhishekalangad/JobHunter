@echo off
echo ============================================
echo  AI Job Hunter - Frontend Start
echo ============================================

cd /d "%~dp0"

:: Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js 18+ first.
    pause & exit /b 1
)

:: Install deps if needed
if not exist "node_modules\" (
    echo [INFO] Installing npm packages...
    npm install
)

echo.
echo [INFO] Starting Next.js dev server at http://localhost:3000
echo [INFO] Press Ctrl+C to stop
echo.

npm run dev
