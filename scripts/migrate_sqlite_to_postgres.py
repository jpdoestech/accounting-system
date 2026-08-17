"""
Copy data from an existing SQLite database into a PostgreSQL database
that already has the schema applied (via `alembic upgrade head`
against the Postgres DATABASE_URL -- see scripts/migrate_to_postgres.bat,
which runs this script as its second step).

This script does NOT create or alter schema -- Alembic already owns
that (see docs/DATABASE.md). It only copies row data, table by table,
in an order that respects foreign keys (parents before children), so
this is safe to run once against a freshly-migrated, empty Postgres
database.

Usage:
    python scripts/migrate_sqlite_to_postgres.py \\
        --sqlite-path backend/dev.db \\
        --postgres-url postgresql+psycopg2://user:pass@host:5432/dbname

Safe to interrupt and re-run IF the target tables are still empty --
this script does not upsert; re-running against a partially-populated
Postgres database will raise a primary-key violation, which is
intentional (better to fail loudly than silently duplicate rows).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.orm import sessionmaker

# Insertion order matters: a table must come after every table it has
# a foreign key into. This mirrors the dependency order of the
# Alembic migrations across all 11 phases.
#
# Caveat: accounts.parent_id and account_groups.parent_id are
# self-referential (an account/group can have a parent within the
# same table). Rows are inserted as a single batch per table without
# a topological sort within that table, so a self-referential row
# whose parent appears later in the same batch could fail. In
# practice this is a non-issue for data produced by this system
# today, since no current API/UI endpoint sets parent_id for accounts
# or account groups -- but if you've set one manually, insert that
# table's rows in parent-before-child order by hand.
TABLE_ORDER = [
    "users",
    "roles",
    "businesses",
    "business_settings",
    "user_business_roles",
    "account_groups",
    "accounts",
    "fiscal_years",
    "accounting_periods",
    "journal_entries",
    "journal_lines",
    "tax_rules",
    "customers",
    "sales_invoices",
    "sales_invoice_lines",
    "vendors",
    "purchase_bills",
    "purchase_bill_lines",
    "bank_accounts",
    "cash_receipts",
    "cash_receipt_allocations",
    "cash_disbursements",
    "cash_disbursement_allocations",
    "bank_reconciliations",
    "withholding_tax_certificates",
    "inventory_items",
    "stock_movements",
    "fixed_assets",
    "depreciation_entries",
    "budgets",
    "budget_lines",
    "refresh_tokens",
]


def migrate(sqlite_path: str, postgres_url: str) -> None:
    sqlite_url = f"sqlite:///{Path(sqlite_path).resolve()}"
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)

    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    postgres_meta = MetaData()
    postgres_meta.reflect(bind=postgres_engine)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()

    with postgres_engine.begin() as pg_conn:
        for table_name in TABLE_ORDER:
            if table_name not in sqlite_meta.tables:
                print(f"  (skip) '{table_name}' not present in source SQLite database.")
                continue
            if table_name not in postgres_meta.tables:
                print(f"  [WARN] '{table_name}' not found in target Postgres schema -- "
                      f"did you run 'alembic upgrade head' against postgres_url first?")
                continue

            sqlite_table = sqlite_meta.tables[table_name]
            pg_table = postgres_meta.tables[table_name]

            rows = sqlite_session.execute(select(sqlite_table)).mappings().all()
            if not rows:
                print(f"  (empty) '{table_name}': 0 rows.")
                continue

            pg_conn.execute(pg_table.insert(), [dict(row) for row in rows])
            print(f"  Copied {len(rows)} row(s) into '{table_name}'.")

    sqlite_session.close()
    print("\nDone. Verify row counts in Postgres before decommissioning the SQLite file.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sqlite-path", required=True, help="Path to the source SQLite .db file")
    parser.add_argument("--postgres-url", required=True, help="SQLAlchemy URL for the target Postgres database")
    args = parser.parse_args()

    if not Path(args.sqlite_path).exists():
        print(f"[ERROR] SQLite file not found: {args.sqlite_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Copying data from {args.sqlite_path} -> {args.postgres_url}\n")
    migrate(args.sqlite_path, args.postgres_url)


if __name__ == "__main__":
    main()
