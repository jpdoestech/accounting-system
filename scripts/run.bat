@echo off
REM ============================================================
REM  Philippine Accounting System - Run (development mode)
REM
REM  Starts the backend (uvicorn, with auto-reload) and the
REM  frontend (Vite dev server) each in their own window.
REM  Requires scripts\setup.bat to have been run first.
REM ============================================================

cd /d "%~dp0.."
set ROOT=%CD%

if not exist "%ROOT%\backend\.venv" (
    echo [ERROR] Backend virtual environment not found. Run scripts\setup.bat first.
    pause
    exit /b 1
)

if not exist "%ROOT%\frontend\node_modules" (
    echo [ERROR] Frontend dependencies not found. Run scripts\setup.bat first.
    pause
    exit /b 1
)

echo Starting backend (FastAPI) on http://localhost:8000 ...
start "Philippine Accounting System - Backend" cmd /k ^
    "cd /d "%ROOT%\backend" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Starting frontend (Vite) on http://localhost:5173 ...
start "Philippine Accounting System - Frontend" cmd /k ^
    "cd /d "%ROOT%\frontend" && npm run dev"

echo.
echo Both servers are starting in separate windows.
echo   Backend API docs: http://localhost:8000/docs
echo   Frontend app:     http://localhost:5173
echo.
echo Close each window (or Ctrl+C inside it) to stop that server.
