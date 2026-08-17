# Phase 2 Development Report — Accounting Engine

## Completed

- Chart of Accounts: hierarchical accounts with configurable type, system/control-account
  flags, and account groups (Section 13).
- Fiscal years and accounting periods, with an explicit Open/Closed/Locked status.
- Journal entries and journal lines, posted exclusively through a single domain-layer
  posting engine (`app/accounting/engine/posting.py`) — the API layer never constructs a
  `JournalEntry`/`JournalLine` directly (Section 9: "never allow the frontend to directly
  manipulate accounting balances").
- Posting engine enforces: total debits == total credits, no line with both a debit and a
  credit, no negative or zero-only lines, minimum two lines, entry date must fall inside an
  **Open** period (posting into a Closed/Locked period is rejected), and accounts must
  belong to the requesting business and be active.
- Reversal, not editing: `reverse_entry()` posts an offsetting entry and marks the original
  `Reversed`. There is deliberately no endpoint to edit or delete a posted line (Section 117
  — no silent changes to posted data).
- Read-only ledger and trial balance queries (`app/accounting/ledger/queries.py`), kept
  separate from the posting engine so reporting code can never accidentally write data.
- API endpoints under `/businesses/{business_id}/...` for accounts, fiscal years, periods
  (incl. close), journal entries (incl. reverse), account ledger, and trial balance — all
  re-verifying business access per request (same isolation pattern as Phase 1).
- Frontend: Chart of Accounts view (create + list), manual Journal Entry form with live
  balance/imbalance indicator, Account Ledger view, Trial Balance report, nav links added to
  the authenticated layout.

## Files Created

**Backend**:
`app/models/account.py`, `app/models/period.py`, `app/models/journal.py`,
`app/accounting/engine/posting.py`, `app/accounting/ledger/queries.py`,
`app/schemas/accounting.py`, `app/api/v1/accounting.py`,
`migrations/versions/2fae50917d25_phase2_accounting_engine.py`,
`tests/test_posting_engine.py`, `tests/test_accounting_api.py`,
plus package `__init__.py` stubs for `app/accounting/{engine,posting,ledger,periods}`.

**Frontend**:
`src/views/ChartOfAccountsView.vue`, `src/views/TrialBalanceView.vue`,
`src/views/AccountLedgerView.vue`, `src/views/JournalEntryFormView.vue`.

## Files Modified

- `app/api/router.py` — registered the new accounting router.
- `app/main.py` — imports the new models so `create_all`/Alembic see them.
- `migrations/env.py` — imports the new models for autogenerate.
- `tests/conftest.py` — added a `db_session` fixture for tests that call the domain layer
  directly (in addition to the existing HTTP `client` fixture).
- `src/router/index.js` — added routes for accounts, journal entry form, account ledger,
  trial balance.
- `src/layouts/DefaultLayout.vue` — added nav links to the new sections.

## Database Changes

Migration `2fae50917d25_phase2_accounting_engine` adds: `account_groups`, `accounts`,
`fiscal_years`, `accounting_periods`, `journal_entries`, `journal_lines`. Applied and
verified against SQLite; unchanged for Postgres.

## Tax/Accounting Rules Added

None yet — Phase 2 is the accounting engine only. No tax rates, withholding rules, or BIR
mappings exist in the system at this point (Phase 3 and Phase 7).

## Tests

`pytest -v` in `backend/`: **13 passed, 0 failed.**

- `test_auth.py`, `test_business.py` (Phase 1, still passing): 5 tests.
- `test_posting_engine.py` (new, domain-layer tests against the posting engine directly):
  balanced entry posts; unbalanced entry rejected; a line with both debit and credit
  rejected; posting into a closed period rejected; posting with no covering period
  rejected; trial balance stays balanced across multiple postings; reversal flips lines,
  marks the original `Reversed`, and nets the trial balance back to zero. 7 tests.
- `test_accounting_api.py` (new, full HTTP acceptance test): registers a user, creates a
  business, creates two accounts (and confirms a duplicate code is rejected), creates a
  fiscal year and period, posts a balanced entry, confirms an unbalanced entry is rejected
  with 422, checks the trial balance and account ledger reflect the posting, reverses the
  entry and confirms the trial balance nets to zero, then closes the period and confirms
  further posting into it is rejected. 1 test covering the whole flow end-to-end.

In addition, the running server was smoke-tested live over HTTP (uvicorn + curl) through
the full flow — register, login, create business, create two accounts, create fiscal
year + period, post a ₱2,000 journal entry, and pull the trial balance — confirming totals
balance in a real request/response cycle, not just in-process. The frontend was rebuilt
with `npx vite build` after adding the four new views — compiled cleanly, 94 modules, no
errors.

**A bug the tests caught before this report was written:** the first version of the
reversal logic excluded `Reversed`-status entries from the ledger/trial-balance queries,
which made a reversed entry's original postings vanish instead of netting against its
reversal — leaving the trial balance one-sided. `test_reversal_flips_lines_and_marks_original_reversed`
failed on the first run, which is exactly the kind of accounting-correctness bug this test
suite exists to catch. Fixed by changing the ledger/trial-balance filters from
`status == "Posted"` to `status != "Draft"`, so reversed entries remain part of history and
correctly net against their reversal. Re-ran the full suite after the fix: 13/13 passing.

## Known Issues

- No support yet for multi-currency journal entries (all amounts assumed to be in the
  business's base currency) — deferred to a later phase per the spec's phased plan.
- No UI for creating/managing fiscal years and periods yet (only the API exists); the
  frontend currently only exposes accounts, journal entry creation, ledger, and trial
  balance. Period management screens should be added alongside Phase 7 (BIR books require
  period close discipline).
- `AccountGroup` model exists in the schema but has no API endpoints or UI yet — reserved
  for when the chart-of-accounts UI needs grouping/headings.
- No default/starter chart of accounts is seeded for a new business — every account must be
  created manually right now. A Philippine-standard starter COA template would reduce setup
  friction and is a reasonable Phase 2.5/3 addition.
- Journal entry creation UI lets the user type raw debit/credit numbers per line; there's no
  autocomplete/search on the account dropdown yet, which will matter once a business has a
  large chart of accounts.

## Next Phase

**Phase 3 — Tax Engine**: configurable, effective-dated tax rules (VAT rates, withholding
tax / ATCs, exemptions), stored as versioned data rather than hard-coded — historical
transactions must always use the rule version in force on their transaction date, never a
rule retroactively applied. This sits alongside the accounting engine (Phase 2) without
modifying it: tax calculations produce journal lines that get posted through the same
`post_journal_entry()` function built in this phase.
