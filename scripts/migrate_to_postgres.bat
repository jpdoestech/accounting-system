@echo off
setlocal
REM ============================================================
REM  Philippine Accounting System - Migrate SQLite -> PostgreSQL
REM
REM  Two steps:
REM    1. Apply the schema to Postgres via Alembic (same
REM       migrations already used for SQLite -- no changes needed,
REM       see docs/DATABASE.md).
REM    2. Copy the existing SQLite data into that schema via
REM       scripts/migrate_sqlite_to_postgres.py.
REM
REM  Run this from a working setup (scripts\setup.bat already run).
REM ============================================================

cd /d "%~dp0.."
set ROOT=%CD%

if not exist "%ROOT%\backend\.venv" (
    echo [ERROR] Backend virtual environment not found. Run scripts\setup.bat first.
    pause
    exit /b 1
)

echo.
echo === Migrate to PostgreSQL ===
echo.
echo This will:
echo   1. Apply the database schema to a PostgreSQL database you specify.
echo   2. Copy all data from backend\dev.db into it.
echo.
echo Make sure the target PostgreSQL database already EXISTS and is EMPTY
echo before continuing (this script creates tables in it but not the
echo database itself).
echo.

set /p PG_URL="Enter the PostgreSQL connection URL (e.g. postgresql+psycopg2://user:pass@localhost:5432/phaccounting): "
if "%PG_URL%"=="" (
    echo [ERROR] No connection URL entered. Aborting.
    pause
    exit /b 1
)

if not exist "%ROOT%\backend\dev.db" (
    echo [ERROR] backend\dev.db not found -- nothing to migrate. Run scripts\setup.bat and use the app first.
    pause
    exit /b 1
)

cd /d "%ROOT%\backend"
call .venv\Scripts\activate.bat

echo.
echo [1/2] Applying schema to PostgreSQL via Alembic...
set DATABASE_URL=%PG_URL%
python -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Schema migration failed. See the output above.
    pause
    exit /b 1
)

echo.
echo [2/2] Copying data from dev.db into PostgreSQL...
cd /d "%ROOT%"
python scripts\migrate_sqlite_to_postgres.py --sqlite-path "%ROOT%\backend\dev.db" --postgres-url "%PG_URL%"
if errorlevel 1 (
    echo [ERROR] Data copy failed. See the output above.
    pause
    exit /b 1
)

echo.
echo Done. To make the app use PostgreSQL going forward, set DATABASE_URL
echo in backend\.env to the same connection URL you entered above, then
echo restart the backend.
echo.
pause
