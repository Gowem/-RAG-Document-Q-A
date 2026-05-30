@echo off
setlocal enabledelayedexpansion
title RAG Document Q&A
color 0A
cd /d "%~dp0"

echo.
echo  +==================================================+
echo  ^|       RAG Document Q^&A  ^|  Llama 3 + Groq       ^|
echo  +==================================================+
echo.

:: ─────────────────────────────────────────────────────────
:: STEP 1  Clear port 8181
:: ─────────────────────────────────────────────────────────
echo  [1/4] Clearing port 8181...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8181"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: ─────────────────────────────────────────────────────────
:: STEP 2  Find Python (Anaconda first, then system python)
:: ─────────────────────────────────────────────────────────
echo  [2/4] Locating Python...
set "PYTHON="

if exist "%USERPROFILE%\anaconda3\python.exe"    set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if exist "%USERPROFILE%\Anaconda3\python.exe"    set "PYTHON=%USERPROFILE%\Anaconda3\python.exe"
if exist "C:\ProgramData\anaconda3\python.exe"   set "PYTHON=C:\ProgramData\anaconda3\python.exe"

if "!PYTHON!" == "" (
    where python >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON=python"
)

if "!PYTHON!" == "" (
    echo.
    echo  [ERROR] Python not found.
    echo  Install Anaconda from https://www.anaconda.com/download
    pause & exit /b 1
)
echo  [2/4] Found: !PYTHON!

:: Ensure uvicorn is available
"!PYTHON!" -c "import uvicorn" >nul 2>&1
if !errorlevel! neq 0 (
    echo  [INFO] Installing dependencies - please wait...
    "!PYTHON!" -m pip install -r "%~dp0requirements.txt" --quiet
    if !errorlevel! neq 0 (
        echo  [ERROR] Dependency install failed.
        pause & exit /b 1
    )
)

:: ─────────────────────────────────────────────────────────
:: STEP 3  Validate .env / GROQ_API_KEY
:: ─────────────────────────────────────────────────────────
echo  [3/4] Checking GROQ_API_KEY...

if not exist "%~dp0.env" (
    if exist "%~dp0.env.example" copy "%~dp0.env.example" "%~dp0.env" >nul
    echo  [ERROR] Add your GROQ_API_KEY to .env
    echo  Get a free key: https://console.groq.com/keys
    notepad "%~dp0.env"
    pause & exit /b 1
)

findstr /C:"your-groq" "%~dp0.env" >nul 2>&1
if !errorlevel! equ 0 (
    echo  [ERROR] Replace the placeholder key in .env with your real GROQ_API_KEY.
    notepad "%~dp0.env"
    pause & exit /b 1
)

:: ─────────────────────────────────────────────────────────
:: STEP 4  Start server + open browser
:: ─────────────────────────────────────────────────────────
echo  [4/4] Starting server...
echo.
echo  +------------------------------------------+
echo  ^|  Open: http://localhost:8181             ^|
echo  ^|  Press Ctrl+C here to stop the server.  ^|
echo  +------------------------------------------+
echo.

:: Give server ~3 sec to start, then open browser
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8181"

:: Run the server (this line blocks until stopped)
"!PYTHON!" -m uvicorn app:api --host 127.0.0.1 --port 8181

echo.
echo  Server stopped. Press any key to close.
pause >nul
endlocal
