@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  Philippine Accounting System - Windows Setup
REM
REM  One-time setup: creates a Python virtual environment,
REM  installs backend and frontend dependencies, creates .env
REM  from the example file if missing, and runs database
REM  migrations to create a local SQLite dev database.
REM
REM  Safe to re-run: existing venv/node_modules/.env are reused
REM  rather than recreated.
REM ============================================================

cd /d "%~dp0.."
set ROOT=%CD%

echo.
echo === Philippine Accounting System - Setup ===
echo.

REM --- Check prerequisites ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH. Install Python 3.12+ from https://www.python.org/downloads/
    echo         and make sure "Add python.exe to PATH" is checked during install.
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js was not found on PATH. Install Node 20+ from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version

echo.
echo [2/5] Setting up backend virtual environment...
cd /d "%ROOT%\backend"
if not exist ".venv" (
    python -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo Installing backend dependencies (this can take a few minutes on first run)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Backend dependency installation failed. See the output above.
    pause
    exit /b 1
)

if not exist ".env" (
    echo Creating backend\.env from .env.example ...
    copy /y ".env.example" ".env" >nul
) else (
    echo backend\.env already exists, leaving it as-is.
)

echo.
echo [3/5] Running database migrations (creates/updates dev.db)...
python -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Migrations failed. See the output above.
    pause
    exit /b 1
)

echo.
echo [4/5] Installing frontend dependencies (this can take a few minutes on first run)...
cd /d "%ROOT%\frontend"
call npm install
if errorlevel 1 (
    echo [ERROR] Frontend dependency installation failed. See the output above.
    pause
    exit /b 1
)

echo.
echo [5/5] Setup complete.
echo.
echo   Next steps:
echo     - Run scripts\run.bat to start the backend and frontend for local development.
echo     - Run scripts\build_exe.bat to build a single-file Windows executable.
echo     - See docs\POSTGRES_MIGRATION.md to switch from SQLite to PostgreSQL.
echo.
cd /d "%ROOT%"
pause
