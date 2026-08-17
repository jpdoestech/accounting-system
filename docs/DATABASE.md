# Database

## Engines

- **Development:** SQLite (`sqlite:///./dev.db`), zero setup.
- **Production:** PostgreSQL, set via `DATABASE_URL` in `.env`. No
  application code changes are required to switch — SQLAlchemy and
  Alembic handle both identically for the schema defined so far.

## Migrations

Alembic is the source of truth for schema changes from Phase 1
onward. To create a new migration after changing models:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

`app/main.py` also calls `Base.metadata.create_all()` on startup as a
convenience for fast local bootstrapping — this is safe alongside
Alembic (it's a no-op once tables exist) but Alembic migrations are
what should be reviewed and run in any shared or production
environment.

## Phase 1 schema

| Table | Purpose |
|---|---|
| `businesses` | Philippine business profile (Section 11) |
| `business_settings` | Per-business configurable settings (Section 2) |
| `users` | Login accounts (email + Argon2id password hash) |
| `roles` | Configurable roles (Admin created automatically on first business) |
| `user_business_roles` | Grants a user a role within a specific business — the multi-business access control table (Section 12) |

## Conventions

- Primary keys: UUID strings, generated in Python (`app/models/mixins.py`).
- Every table has `created_at` / `updated_at` timestamps.
- Money columns: `Numeric`/`DECIMAL`, never `Float` (see
  `app/utils/money.py`). No monetary columns exist yet in Phase 1 —
  this convention takes effect starting with the accounting engine in
  Phase 2.
