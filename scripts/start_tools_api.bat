@echo off
REM Start the Tools API (run in one terminal)
cd /d "%~dp0.."

netstat -ano | findstr ":8100" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo Tools API is already running on http://127.0.0.1:8100
    echo To restart, stop the existing process first:
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8100" ^| findstr "LISTENING"') do echo   taskkill /PID %%a /F
    exit /b 0
)

call venv\Scripts\activate.bat
python -m tools_api.main
