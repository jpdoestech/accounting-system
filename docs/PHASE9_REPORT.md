# Phase 9 Development Report — Fixed Assets

## Completed

- `FixedAsset` model: each linked to three configurable GL accounts — the Asset account,
  an Accumulated Depreciation contra-asset account, and a Depreciation Expense account —
  never hard-coded.
- `DepreciationEntry` model: one immutable row per posted monthly depreciation run, mirroring
  `StockMovement` (Phase 8) and `JournalEntry` (Phase 2) — a record of what was posted, never
  edited afterward. A uniqueness constraint on `(asset_id, period_year, period_month)`
  prevents double-posting the same asset/period at the database level, not just in
  application logic.
- **Straight-line depreciation** (`app/services/fixed_assets.py`): monthly amount =
  `(acquisition_cost − salvage_value) / useful_life_months`, held constant except the final
  month, which is capped so accumulated depreciation never exceeds the depreciable base —
  avoiding the classic rounding overshoot from computing every month independently.
  Verified by test: a ₱36,000 asset over 36 months produces exactly ₱1,000/month and the
  36-month schedule ends at exactly ₱0.00 book value, not ₱0.03 or similar.
- `preview_depreciation_schedule()`: computes the full schedule from acquisition without
  posting anything, so a bookkeeper can review before any entries exist.
- `post_monthly_depreciation()` composes the accounting engine (Phase 2) exactly like every
  other posting service in this project — Debit Depreciation Expense, Credit Accumulated
  Depreciation — no new posting mechanism.
- An asset's status automatically moves to "Fully Depreciated" once accumulated depreciation
  reaches the depreciable base; further depreciation posting is then rejected with a clear
  error, as is posting to a non-Active asset (e.g. one already fully depreciated).
- Full API for asset creation/listing, schedule preview, posting, and depreciation entry
  history.
- Frontend: Fixed Assets view (create with account pickers, list showing cost/accumulated
  depreciation/book value, one-click "Post Depreciation" for the current month).

## Files Created

**Backend**:
`app/models/fixed_asset.py`, `app/models/depreciation_entry.py`,
`app/services/fixed_assets.py`, `app/schemas/fixed_assets.py`, `app/api/v1/fixed_assets.py`,
`migrations/versions/76e50e5c8f64_phase9_fixed_assets.py`,
`tests/test_fixed_assets.py`, `tests/test_fixed_assets_api.py`.

**Frontend**: `src/views/FixedAssetsView.vue`.

## Files Modified

- `app/api/router.py`, `app/main.py`, `migrations/env.py`, `tests/conftest.py` — registered
  the fixed assets router and imported the two new models.
- `src/router/index.js`, `src/layouts/DefaultLayout.vue` — added the Fixed Assets route and
  nav link.

## Database Changes

Migration `76e50e5c8f64_phase9_fixed_assets` adds `fixed_assets` and
`depreciation_entries` — both new tables, no existing table needed an `ALTER`, so unlike
Phases 4, 5, and 8 there was no SQLite batch-mode fix needed this time. Verified with a full
`rm -f dev.db && alembic upgrade head` from empty, running all nine migrations
(Phases 1–9) in sequence without error.

## Tax/Accounting Rules Added

None — depreciation is an accounting calculation, not a tax rule, and doesn't touch the
Phase 3 tax engine.

## Tests

`pytest -v` in `backend/`: **57 passed, 0 failed** (51 carried over from Phases 1–8, 5
domain tests + 1 HTTP acceptance test new this phase).

- `test_fixed_assets.py` (domain-layer, direct calls): the monthly depreciation amount is
  correctly straight-line (₱36,000 / 36 = ₱1,000.00 exactly); the full schedule preview has
  the right length (36 rows), starts the month *after* acquisition (not the acquisition
  month itself), and ends at exactly ₱0.00 accumulated/book value; posting depreciation
  creates a genuinely balanced journal entry verified against the trial balance
  (Depreciation Expense ₱1,000 debit = Accumulated Depreciation ₱1,000 credit);
  double-posting the same asset/period is rejected; accumulated depreciation correctly
  compounds to ₱2,000 across two separate monthly postings while the asset stays Active.
- `test_fixed_assets_api.py` (HTTP acceptance test): the complete flow — three-account setup,
  asset creation (with a duplicate-asset-code rejection check), the 36-row schedule preview,
  posting January's depreciation, confirming the trial balance reflects it, confirming a
  second post attempt for the same period is rejected with 422, and confirming the
  depreciation entry appears in the asset's history.

The running server was smoke-tested live (uvicorn + curl) for fixed asset creation
specifically — a ₱12,000 asset over 12 months, implying exactly ₱1,000/month straight-line,
matching what the domain and HTTP tests already verified with real numbers. The frontend was
rebuilt with `npx vite build` after adding the Fixed Assets view — 105 modules, no errors.

**Passed:** 57/57 automated tests, live smoke test, frontend build. **Failed:** none.

## Known Issues

- Straight-line depreciation only — no declining-balance, units-of-production, or other
  methods. Straight-line is the simplest to implement correctly and the most common method
  for PH SME fixed assets, but a business using an accelerated method would need this
  extended.
- No asset disposal/write-off workflow — an asset can reach "Fully Depreciated" status
  automatically, but there's no "Disposed" transition or gain/loss-on-disposal posting yet
  (the `FIXED_ASSET_STATUSES` constant already reserves "Disposed" for this, but no code
  path reaches it).
- Depreciation must be posted one asset, one month at a time via the UI — no bulk "run
  depreciation for all active assets this month" batch operation, which a business with many
  assets would want. The underlying service function supports being called in a loop; only
  the batch-triggering UI/endpoint doesn't exist yet.
- No partial-month depreciation for assets acquired mid-month — the schedule assumes a full
  month's depreciation starting the month after acquisition, regardless of which day within
  the acquisition month the asset was actually placed in service.
- Like every transactional module so far (sales, purchases, banking), there's no
  reversal/void workflow for a posted depreciation entry — correcting a mistake would
  currently require a manual offsetting journal entry outside this module.

## Next Phase

**Phase 10 — Advanced Features**: budgeting, multi-currency support, and financial
statement generation (Balance Sheet, Income Statement, Cash Flow Statement) built from data
every prior phase has already posted — this is the phase where the trial balance the
accounting engine has produced since Phase 2 finally gets organized into the standard
reports a business owner or BIR examiner actually reads, rather than a flat list of account
balances.
