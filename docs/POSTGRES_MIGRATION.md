# Migrating from SQLite to PostgreSQL

The application works identically against SQLite (the local development default) and
PostgreSQL (recommended for production) -- every model, migration, and query in this
codebase uses SQLAlchemy/Alembic in a database-agnostic way (see `docs/DATABASE.md`). No
application code changes are required to switch; only configuration and a one-time data
copy if you already have data in SQLite you want to keep.

## Quick path (Windows): `scripts\migrate_to_postgres.bat`

1. Create an empty PostgreSQL database (e.g. `phaccounting`) on your target server.
2. Run `scripts\migrate_to_postgres.bat` from the project root.
3. When prompted, enter the connection URL, e.g.:
   ```
   postgresql+psycopg2://phaccounting:yourpassword@localhost:5432/phaccounting
   ```
4. The script applies the schema (via Alembic) and copies your existing SQLite data
   into it, table by table, in dependency order.
5. Update `DATABASE_URL` in `backend\.env` to the same connection URL, then restart the
   backend (`scripts\run.bat`, or your production process manager).

## Manual path (any OS)

```bash
# 1. Apply the schema to Postgres (creates all tables/constraints)
cd backend
DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/dbname" python -m alembic upgrade head

# 2. Copy existing SQLite data into it (skip this step for a brand-new install with no data yet)
cd ..
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path backend/dev.db \
    --postgres-url postgresql+psycopg2://user:pass@host:5432/dbname

# 3. Point the app at Postgres going forward
#    Edit backend/.env: DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
```

## What the data-copy script does and doesn't do

`scripts/migrate_sqlite_to_postgres.py` copies row data only -- it never creates or alters
schema (that's Alembic's job, run first). It inserts tables in an order that respects
foreign keys (parent tables before the tables that reference them), covering all 32 tables
across all 11 phases.

**Verification note:** the table ordering was verified by cross-checking every
`ForeignKey(...)` declaration across every model file in `backend/app/models/` by hand
(one FK ordering bug — `accounts` referencing `account_groups` — was caught and fixed this
way before shipping). It has **not** been exercised against a live PostgreSQL instance in
this environment, because this sandbox's network policy doesn't permit installing
PostgreSQL packages. Test it against a real (ideally disposable/staging) PostgreSQL
database before relying on it for a production cutover, the same way you would test any
migration tooling before running it against data that matters.

**Known limitation:** `accounts.parent_id` and `account_groups.parent_id` are
self-referential foreign keys (an account or account group can have a parent within the
same table). The script inserts each table's rows as a single batch without a topological
sort within that table, so a self-referential row whose parent appears later in the same
batch could fail. This is a non-issue for data produced by the current API/UI, since no
endpoint in this system sets `parent_id` for accounts or account groups today — but if
you've set one by hand (e.g. directly in the database), insert that table's rows in
parent-before-child order manually.

**Safety:** the script does not upsert. Running it a second time against a Postgres
database that already has data will fail with a primary-key violation rather than silently
duplicate rows -- that's intentional; re-running against a partially-populated target is not
a supported flow, and failing loudly is safer than an inconsistent result.

## Production deployment notes

- `docker-compose.yml` already runs PostgreSQL 16 by default when you use
  `docker compose up --build` — no extra steps needed in that path, since the backend
  container's `DATABASE_URL` is already set to point at the `db` service.
- Set `ENVIRONMENT=production` and a real `SECRET_KEY` alongside `DATABASE_URL` — see
  `docs/PHASE11_REPORT.md` for the full production-readiness checklist (the app refuses to
  start in production with the default insecure secret key).
