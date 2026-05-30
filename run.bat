@echo off
title RAG Document Q&A
color 0A
cd /d "%~dp0"

echo.
echo  ================================================
echo    RAG Document Q&A  (Llama 3 + Groq)
echo  ================================================
echo.

set VENV=C:\rag-venv

if not exist "%VENV%\Scripts\python.exe" (
    echo  Creating virtual environment...
    python -m venv %VENV%
)

%VENV%\Scripts\python.exe -c "import fastapi,langchain_groq,chromadb,fastembed" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing dependencies...
    %VENV%\Scripts\python.exe -m pip install -r requirements.txt --quiet
)

if not exist ".env" copy ".env.example" ".env" >nul 2>&1
findstr /C:"your-groq" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo  [ERROR] Add your GROQ_API_KEY to .env
    echo  Get free key: https://console.groq.com/keys
    notepad .env
    pause & exit /b 1
)

echo  Starting server...
echo  Open browser at: http://localhost:8080
echo  Press Ctrl+C to stop.
echo.

start "" "http://localhost:8080"
%VENV%\Scripts\uvicorn.exe app:api --host 127.0.0.1 --port 8080 --reload
