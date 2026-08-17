@echo off
setlocal
REM ============================================================
REM  Philippine Accounting System - Build Windows Executable
REM
REM  Builds the frontend, copies it into the backend so a single
REM  process can serve both the UI and the API, then packages the
REM  backend (including a bundled SQLite runtime + all Alembic
REM  migrations) into a standalone Windows .exe with PyInstaller.
REM
REM  Output: backend\dist\PhilippineAccountingSystem\PhilippineAccountingSystem.exe
REM  Ship the WHOLE "PhilippineAccountingSystem" folder (the .exe
REM  needs the _internal folder next to it) -- don't copy just the
REM  .exe file on its own.
REM
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

echo.
echo === Building Windows executable ===
echo.

echo [1/4] Building frontend (production bundle)...
cd /d "%ROOT%\frontend"
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed. See the output above.
    pause
    exit /b 1
)

echo.
echo [2/4] Copying frontend build into backend\app\static ...
if exist "%ROOT%\backend\app\static" rmdir /s /q "%ROOT%\backend\app\static"
xcopy /e /i /y "%ROOT%\frontend\dist" "%ROOT%\backend\app\static" >nul

echo.
echo [3/4] Installing PyInstaller (build-only dependency)...
cd /d "%ROOT%\backend"
call .venv\Scripts\activate.bat
pip install -r requirements-build.txt
if errorlevel 1 (
    echo [ERROR] Could not install PyInstaller. See the output above.
    pause
    exit /b 1
)

echo.
echo [4/4] Running PyInstaller (this can take a few minutes)...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist PhilippineAccountingSystem.spec del /q PhilippineAccountingSystem.spec

REM NOTE: --add-data uses ';' as the separator on Windows (PyInstaller
REM uses ':' on Linux/macOS instead) -- this script is Windows-only.
pyinstaller --noconfirm --onedir --name PhilippineAccountingSystem ^
    --add-data "migrations;migrations" ^
    --add-data "alembic.ini;." ^
    --add-data "app\static;app\static" ^
    --hidden-import "app.models.account" ^
    --hidden-import "app.models.bank" ^
    --hidden-import "app.models.bank_reconciliation" ^
    --hidden-import "app.models.budget" ^
    --hidden-import "app.models.business" ^
    --hidden-import "app.models.cash_disbursement" ^
    --hidden-import "app.models.cash_receipt" ^
    --hidden-import "app.models.customer" ^
    --hidden-import "app.models.depreciation_entry" ^
    --hidden-import "app.models.fixed_asset" ^
    --hidden-import "app.models.inventory_item" ^
    --hidden-import "app.models.journal" ^
    --hidden-import "app.models.period" ^
    --hidden-import "app.models.purchase" ^
    --hidden-import "app.models.refresh_token" ^
    --hidden-import "app.models.sales" ^
    --hidden-import "app.models.stock_movement" ^
    --hidden-import "app.models.tax_rule" ^
    --hidden-import "app.models.user" ^
    --hidden-import "app.models.vendor" ^
    --hidden-import "app.models.withholding_certificate" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.protocols.websockets.auto" ^
    --hidden-import "uvicorn.lifespan.on" ^
    --hidden-import "email_validator" ^
    run_desktop.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed. See the output above.
    pause
    exit /b 1
)

echo.
echo === Build complete ===
echo.
echo   Output folder: backend\dist\PhilippineAccountingSystem\
echo   Run it:        backend\dist\PhilippineAccountingSystem\PhilippineAccountingSystem.exe
echo.
echo   Ship the ENTIRE "PhilippineAccountingSystem" folder to end users --
echo   the .exe needs the "_internal" folder alongside it to run.
echo   On first launch it creates its own dev.db (SQLite) next to the .exe
echo   and opens your browser automatically once the server is ready.
echo   To use PostgreSQL instead, place a .env file next to the .exe with
echo   DATABASE_URL set (see docs\POSTGRES_MIGRATION.md).
echo.
cd /d "%ROOT%"
pause
