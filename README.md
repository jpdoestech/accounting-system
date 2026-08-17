# Accounting System

A Philippines-first, configurable double-entry accounting system.
Independent implementation — not affiliated with or derived from any
commercial accounting product.

> Designed to support Philippine BIR requirements. Certification or
> registration requirements remain subject to applicable BIR
> procedures and approvals.

## Status: Phase 11 — Production Hardening (complete) — All 11 phases delivered

See `docs/` for architecture and engine documentation. Phases 1–10 delivered the full
accounting system: foundation, double-entry accounting engine, tax engine, sales,
purchases, banking, Philippine compliance/BIR reporting, inventory, fixed assets, and
financial statements/budgeting. Phase 11 hardens it for production: refresh tokens with
single-use rotation, environment-driven CORS, gated schema bootstrapping (Alembic-only in
production), global exception handling, structured logging with request tracing, security
headers, rate limiting, and a CI workflow. See `docs/PHASE1_REPORT.md` through
`docs/PHASE11_REPORT.md` for the detailed development reports — each documents what was
built, every test run, and every issue caught along the way (including a handful of real
bugs found and fixed before delivery, not glossed over).

## Architecture

```
USER INTERFACE (Vue 3)
        │
APPLICATION API (FastAPI)
        │
BUSINESS / DOMAIN LOGIC
        │
  ┌─────┼─────┐
ACCOUNTING  TAX   BIR
 ENGINE   ENGINE ENGINE
        │
    DATABASE
```

The accounting engine, tax engine, and BIR reporting engine are kept
independently maintainable so Philippine tax/regulatory changes can be
made through configuration and versioned rules, without rewriting the
accounting core. See `docs/ARCHITECTURE.md`.

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic,
  PostgreSQL (production) / SQLite (development), `Decimal` for all
  money math.
- **Frontend:** Vue 3, Vite, Bootstrap 5, Vue Router, Pinia, Axios.
- **Auth:** Argon2id password hashing, JWT sessions.

## Quick start (Windows)

1. Double-click `scripts\setup.bat` (or run it from a terminal) — installs everything and
   creates a local SQLite database automatically. Safe to re-run.
2. Double-click `scripts\run.bat` — starts the backend and frontend, each in its own
   window. The app opens at http://localhost:5173 (API docs at http://localhost:8000/docs).
3. To package a single distributable Windows executable (bundles the backend + built
   frontend into one process, no Python/Node install needed on the target machine), run
   `scripts\build_exe.bat`. Output: `backend\dist\PhilippineAccountingSystem\` — ship the
   whole folder. See "Windows executable" below for details.
4. To move from the local SQLite database to PostgreSQL, run
   `scripts\migrate_to_postgres.bat`, or see `docs\POSTGRES_MIGRATION.md`.

## Windows executable

`scripts\build_exe.bat` builds the frontend, copies it into the backend so a single process
can serve both the UI and the API, then packages everything (including all Alembic
migrations) with PyInstaller into a standalone folder —
`backend\dist\PhilippineAccountingSystem\PhilippineAccountingSystem.exe`. On first launch it
creates its own `dev.db` (SQLite) next to the `.exe`, applies all migrations automatically,
starts the server, and opens your browser once it's ready. To point it at PostgreSQL instead
of the bundled SQLite, place a `.env` file next to the `.exe` with `DATABASE_URL` set (see
`docs\POSTGRES_MIGRATION.md`).

Ship the **entire** `PhilippineAccountingSystem` folder to end users, not just the `.exe` —
PyInstaller's `--onedir` build keeps its bundled Python runtime and dependencies in an
`_internal` folder alongside the executable, and the `.exe` needs that folder present to run.

*Verification note:* this build was developed and its core logic (path resolution for
bundled resources vs. the writable data directory, and the Alembic migration override
needed inside a frozen bundle) was validated against a simulated PyInstaller runtime layout
in this environment — but PyInstaller does not cross-compile, so a genuine Windows `.exe`
has not been produced or run end-to-end in this Linux sandbox. Run `build_exe.bat` on an
actual Windows machine and verify the resulting `.exe` launches correctly before relying on
it for distribution.



### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit as needed
alembic upgrade head          # creates dev.db (SQLite) or your Postgres schema
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/health

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (proxies `/api` to the backend on :8000)

### Tests

```bash
cd backend
pytest -v
```

## Running with Docker Compose

```bash
docker compose up --build
```

This starts PostgreSQL, the backend (auto-runs migrations), and the
frontend dev server.

## Continuous Integration

`.github/workflows/ci.yml` runs the full backend test suite (against a fresh SQLite
database with Alembic migrations applied) and the frontend production build on every push
or pull request to `main`.

## Production notes

Set `ENVIRONMENT=production` and provide a real, random `SECRET_KEY` — the app refuses to
start otherwise. In production mode the app also skips the SQLite/dev `create_all()`
convenience (Alembic migrations are the sole source of schema truth), and enables basic
per-process rate limiting. Set `CORS_ORIGINS` to your real frontend origin(s) — the default
only allows the local Vite dev server. See `docs/PHASE11_REPORT.md` for the full hardening
details and known limitations (e.g. rate limiting doesn't coordinate across multiple
processes without an external store).

## Development phases

Phase 1 (foundation) → Phase 2 (accounting engine) → Phase 3 (tax engine) → Phase 4
(sales) → Phase 5 (purchases) → Phase 6 (banking) → Phase 7 (Philippine compliance/BIR) →
Phase 8 (inventory) → Phase 9 (fixed assets) → Phase 10 (advanced features) → **Phase 11
(production hardening, this delivery — final phase)**.

All 11 phases are complete. 71 automated tests pass; see `docs/PHASE11_REPORT.md` for the
full closing summary.

Each phase is implemented, tested, and verified before the next
begins — invoices and other transactional features are deliberately
not built until the accounting and tax engines exist under them.
