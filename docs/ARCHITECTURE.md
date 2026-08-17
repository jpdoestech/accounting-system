# Architecture

## Layers

```
USER INTERFACE (Vue 3 / Pinia / Vue Router)
        │  HTTP (JSON, JWT bearer)
APPLICATION API (FastAPI routers, app/api/v1)
        │
BUSINESS / DOMAIN LOGIC (app/accounting, app/tax, app/bir, app/services)
        │
DATABASE (SQLAlchemy models, Alembic migrations)
```

The frontend never talks to the database directly and never computes
accounting or tax results — it calls the API, which delegates to the
domain layer. This is enforced by convention today; Phase 2 introduces
a dedicated posting service so the accounting engine is the *only*
code path that can write a `JournalEntry`.

## Why the engines are separated

- **Accounting engine** (`app/accounting`): double-entry bookkeeping,
  posting rules, ledger, periods. This should rarely change.
- **Tax engine** (`app/tax`): VAT, withholding, ATCs, tax rules with
  effective-dated versions. This changes whenever BIR regulations
  change.
- **BIR engine** (`app/bir`): books of accounts, BIR forms, mappings,
  exports. This changes whenever BIR reporting requirements change.

Keeping these independent means a tax-rate change or a new BIR form
never requires touching the accounting core, and vice versa.

## Multi-business isolation

Every business-owned table carries a `business_id` foreign key.
`UserBusinessRole` grants a user access to specific businesses. All
API endpoints that return business-scoped data filter by the
requesting user's granted businesses (see
`app/api/v1/business.py::_get_authorized_business`) — a user can never
retrieve another business's data by guessing an ID (covered by
`tests/test_business.py::test_user_cannot_see_other_users_business`).

## Money

All monetary values are Python `Decimal`, stored as SQLAlchemy
`Numeric`/`DECIMAL` — never `float`. See `app/utils/money.py`.

## Configuration over hard-coding

Per the project's core requirement, tax rates, tax rules, BIR
mappings, document numbering, chart of accounts, and business settings
are all data administrators can edit — not constants in Python code.
Phase 1 establishes `BusinessSettings` as the first example of this
pattern; Phase 3 (tax engine) extends it to versioned, effective-dated
tax rules.

## Rule versioning (future phases)

Every tax/regulatory rule will carry: rule code, version, rate/value,
effective_from, effective_to, status, legal basis, source reference.
Historical transactions always use the rule version that was in force
at the transaction date — rules are never retroactively reapplied to
posted transactions.
