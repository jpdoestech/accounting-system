# Phase 10 Development Report — Advanced Features

## Completed

- **`get_period_activity()`** added to the accounting ledger module (`app/accounting/ledger/queries.py`):
  isolates revenue/expense activity within a specific date range, as distinct from the
  existing `get_trial_balance()`, which is cumulative since inception. This distinction
  matters because the system has no period-close step (see Phase 2's design) — revenue and
  expense accounts are never zeroed out and swept into Retained Earnings, so an Income
  Statement needs period-only figures while a Balance Sheet needs cumulative ones.
- **Balance Sheet** (`app/reports/financial/statements.py::get_balance_sheet`): Assets,
  Liabilities, and Equity as of a date, with cumulative net income folded into Equity as a
  single line so `Assets == Liabilities + Equity` holds true without requiring a formal
  period-close — the standard approach for interim (non-year-end) balance sheets. Verified
  by test with a genuine two-transaction scenario (₱5,000 owner contribution + ₱1,000 sale
  on credit): total assets ₱6,000, total equity ₱6,000, `is_balanced: true`.
- **Income Statement** (`get_income_statement`): Revenue, Cost of Sales, Expenses, Other
  Income, Other Expenses for a period, rolling up to Gross Profit, Operating Income, and Net
  Income. Verified by test that a July invoice is correctly excluded from an August-only
  income statement, while an August invoice and an August expense are both included.
- **Budgeting** (`Budget`/`BudgetLine` models, `app/reports/financial/budget_variance.py`):
  an annual (not monthly-granular — see Known Issues) per-account budget for a fiscal year,
  compared against actual activity for the same fiscal year via `get_period_activity()`.
  Budgets never affect posting or the accounting engine — purely a comparison target.
  Verified by test: a ₱1,000 budget against ₱800 actual revenue correctly reports a
  −₱200 (−20%) variance.
- Full API for both statements and for budget creation/listing/variance.
- Frontend: a Financial Statements view with Balance Sheet, Income Statement, and Budget
  Variance sections, each independently runnable by date range.

## Scope decision: multi-currency deferred

The original Phase 10 scope (per the Phase 9 report's "Next Phase" note) mentioned
multi-currency support alongside budgeting and financial statements. I deliberately did not
implement it this phase. Genuine multi-currency support — FX rate tracking, functional vs.
transaction currency, revaluation of foreign-currency balances, and FX gain/loss postings —
would require touching every posting service already built across Phases 2–9 (accounting,
sales, purchases, banking, fixed assets), each of which currently assumes a single
functional currency throughout. Doing that shallowly (e.g. just adding a currency field that
isn't actually used in any calculation) would be worse than not doing it at all — it would
look supported without being correct, which is a bigger risk than an honestly-documented
gap. `Business.currency_code` and `BusinessSettings.default_currency_code` already exist
from Phase 1 as the seed for this if a later phase takes it on properly.

## Files Created

**Backend**:
`app/reports/financial/statements.py`, `app/reports/financial/budget_variance.py`,
`app/models/budget.py`, `app/schemas/reports.py`, `app/api/v1/reports.py`,
`migrations/versions/f7fa9b2b599f_phase10_advanced_features.py`,
`tests/test_financial_statements.py`, `tests/test_reports_api.py`.

**Frontend**: `src/views/FinancialStatementsView.vue`.

## Files Modified

- `app/accounting/ledger/queries.py` — added `get_period_activity()`.
- `app/api/router.py`, `app/main.py`, `migrations/env.py`, `tests/conftest.py` — registered
  the reports router and imported the new `budget` model.
- `src/router/index.js`, `src/layouts/DefaultLayout.vue` — added the Statements route and
  nav link.

## Database Changes

Migration `f7fa9b2b599f_phase10_advanced_features` adds `budgets` and `budget_lines` — both
new tables, no existing table needed an `ALTER`, consistent with Phase 9. Verified with a
full `rm -f dev.db && alembic upgrade head` from empty, running all ten migrations
(Phases 1–10) in sequence without error.

## Tax/Accounting Rules Added

None — this phase is entirely reporting and budgeting; no posting logic, tax logic, or
accounting rules were added or changed.

## Tests

`pytest -v` in `backend/`: **61 passed, 0 failed** (57 carried over from Phases 1–9, 3
domain tests + 1 HTTP acceptance test new this phase).

- `test_financial_statements.py` (domain-layer, direct calls): the Balance Sheet balances
  correctly with net income folded into equity across two real transactions; the Income
  Statement correctly isolates period-only activity, excluding a prior-period invoice while
  including current-period revenue and expense; budget variance correctly computes a
  ₱200/−20% shortfall against a stated ₱1,000 budget.
- `test_reports_api.py` (HTTP acceptance test): the complete flow — chart of accounts, an
  owner-contribution journal entry, a posted sales invoice, then querying the Balance Sheet
  (confirming ₱6,000 total assets and equity, balanced), the Income Statement (confirming
  ₱1,000 revenue and net income), budget creation, and budget variance (confirming the
  −₱200 shortfall against a ₱1,200 budget).

**A test-writing bug caught along the way, not a product bug:** the first version of the
Income Statement test's fixture only created an accounting period for August, but the test
posts an invoice dated in July (to prove it's correctly excluded from an August-only
report). Posting into a month with no covering accounting period is correctly rejected by
the Phase 2 posting engine — exactly as designed — so the test failed with a
"No accounting period covers 2026-07-15" error on the first run. Fixed by adding a July
period to the fixture; re-ran and all tests passed. Documented here in the same spirit as
Phase 2's reversal bug: the test suite (and the engine's own validation) caught a gap
before it reached anyone.

The running server was smoke-tested live (uvicorn + curl) for both statement endpoints on
a brand-new business with no transactions — confirmed sensible all-zero, `is_balanced: true`
empty states rather than errors. The full realistic flow with actual transactions was
already verified end-to-end by the HTTP acceptance test. The frontend was rebuilt with
`npx vite build` after adding the Financial Statements view — 106 modules, no errors.

**Passed:** 61/61 automated tests, live smoke test, frontend build. **Failed:** none in the
final test suite — the one fixture issue above was caught and fixed before this report was
written.

## Known Issues

- **Multi-currency deferred** — see the Scope decision section above.
- Budgets are annual only, one amount per account per fiscal year — no monthly/quarterly
  budget granularity, which a business tracking budget-vs-actual more frequently than
  year-end would want. The `Budget`/`BudgetLine` schema would need a `period_month` column
  and the variance query would need to filter by it; deferred to keep this phase's scope
  aligned with what the tests actually exercise.
- No cash flow statement — the Phase 9 report's stated Phase 10 scope mentioned Balance
  Sheet, Income Statement, *and* Cash Flow Statement; only the first two were built. A cash
  flow statement (indirect method, starting from net income and adjusting for non-cash
  items and working-capital changes) is meaningfully more complex to get right than the
  other two and was cut to keep this phase's delivered scope fully tested rather than
  partially built.
- No budget approval workflow — `Budget.status` already has a `Draft`/`Approved` distinction
  in the model, but nothing in the API enforces or transitions it; a budget is usable in
  variance reporting regardless of status.
- No comparative statements (e.g. this year vs. last year, or budget-vs-actual-vs-prior-year
  side by side) — each report run is a single point-in-time or single-period query.
- The Balance Sheet's `is_balanced` field is close to tautological given how the accounting
  engine enforces debits = credits on every posting (Phase 2) — a `false` result would
  actually indicate something has gone wrong at a level below this report (e.g. direct
  database tampering bypassing the ORM), which is a reasonable safety net rather than
  redundant, but it's not testing anything Phase 10 itself could break.

## Next Phase

**Phase 11 — Production Hardening**: this is the last phase in the original roadmap. Likely
scope: CI configuration, structured logging and error tracking, rate limiting, refresh
tokens (flagged as a gap since Phase 1), removing the `Base.metadata.create_all()`
convenience call from `app/main.py` in favor of Alembic-only schema management in
shared/production environments (flagged since Phase 1), tightening CORS beyond the
hard-coded `localhost:5173` origin, and a review pass across every phase's "Known Issues"
section to decide which remaining gaps are worth closing versus documenting as
intentionally out of scope for this delivery.
