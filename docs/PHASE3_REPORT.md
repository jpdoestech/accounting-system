# Phase 3 Development Report — Tax Engine

## Completed

- `TaxRule` model: versioned, effective-dated tax rules covering both PH tax families this
  phase supports — VAT (rate-based) and Withholding (rate-based, identified by an ATC —
  Alphanumeric Tax Code). Rate, effective_from/effective_to, status, legal_basis, and
  source_reference are all data, never hard-coded in Python.
- Rule lookup (`app/tax/engine/rules.py`): given a business, a `rule_code`, and a date,
  finds the rule that was actually in force on that date. A business-specific rule (its own
  `business_id`) overrides a global/system-default rule (`business_id IS NULL`) with the
  same code, so a business can have a negotiated rate without changing the system default
  for everyone else.
- Calculation (`app/tax/engine/calculator.py`): pure calculation against an already-resolved
  rule — never decides which rule applies itself, and never posts journal entries. Includes
  both a straightforward rate × amount calculation and a VAT-inclusive gross → net/VAT
  breakdown (common in PH VAT-inclusive pricing).
- Historical correctness: a transaction dated in the past always uses the rate that was in
  force on *that* date, even after the rate has since changed — verified directly by test
  (`test_rule_versioning_uses_rate_in_force_at_transaction_date`).
- Retiring a rule (not deleting it) removes it from future lookups while keeping it on file
  for audit/history of already-posted transactions.
- API endpoints under `/businesses/{business_id}/tax-rules`: create, list, retire,
  calculate — same business-isolation pattern as Phases 1–2.
- Frontend: Tax Rules view (create rules incl. VAT/Withholding + ATC code, list with
  status, retire action), added to the nav.

## Files Created

**Backend**:
`app/models/tax_rule.py`, `app/tax/engine/rules.py`, `app/tax/engine/calculator.py`,
`app/schemas/tax.py`, `app/api/v1/tax.py`,
`migrations/versions/bb91eebf88a5_phase3_tax_engine.py`,
`tests/test_tax_engine.py`, `tests/test_tax_api.py`.

**Frontend**: `src/views/TaxRulesView.vue`.

## Files Modified

- `app/api/router.py` — registered the tax router.
- `app/main.py`, `migrations/env.py`, `tests/conftest.py` — import the new `tax_rule` model
  so `create_all`/Alembic autogenerate/tests all see it.
- `src/router/index.js`, `src/layouts/DefaultLayout.vue` — added the Tax Rules route and
  nav link.

## Database Changes

Migration `bb91eebf88a5_phase3_tax_engine` adds `tax_rules`. Applied cleanly against a
fresh SQLite database from `alembic upgrade head` (all three migrations run in sequence:
Phase 1 → Phase 2 → Phase 3).

## Tax/Accounting Rules Added

No specific rates are seeded by default — this phase delivers the *engine*, not a
pre-populated Philippine tax rate table. A business (or a future seed script) creates its
own rules through the API/UI. This was a deliberate choice: hard-coding "the" current VAT
rate into a migration would violate the same "never hard-code tax rules" principle the
engine exists to enforce, and BIR rates are exactly the kind of thing that changes.

## Tests

`pytest -v` in `backend/`: **19 passed, 0 failed** (13 carried over from Phases 1–2, 6 new).

- `test_tax_engine.py` (domain-layer, direct calls): rule versioning picks the rate in
  force at the transaction date (10% pre-2024 vs 12% from 2024 on the same rule_code);
  business-specific rule overrides the global default; a rule_code with no matching rule
  raises a clear `TaxRuleNotFoundError`; a `Retired` rule is excluded from lookup; VAT-
  inclusive gross-to-net/VAT breakdown is arithmetically correct (₱1,120 gross → ₱1,000 net
  + ₱120 VAT at 12%).
- `test_tax_api.py` (HTTP acceptance test): creates a business, creates a VAT rule via the
  API, calculates tax on ₱5,000 and confirms ₱600.00 (12%), confirms calculating against a
  nonexistent rule_code returns 422 (not a silent wrong answer), retires the rule, and
  confirms calculation against the now-retired rule also returns 422.

The running server was also smoke-tested live (uvicorn + curl): registered, logged in,
created a business, created a Standard VAT rule at 12%, and calculated tax on ₱5,000 —
returned exactly ₱600.00 over a real HTTP round trip. The frontend was rebuilt with
`npx vite build` after adding the Tax Rules view — 95 modules, no errors.

**Passed:** 19/19 automated tests, live smoke test, frontend build. **Failed:** none —
unlike Phase 2, no bug surfaced during this phase's test-writing.

## Known Issues

- No withholding-tax certificate (BIR Form 2307) generation yet — that belongs to Phase 7
  (BIR compliance), which will consume this engine's calculation output.
- No UI yet for entering a transaction and having the tax auto-calculated and posted
  in one step (e.g. "sell ₱5,000 of goods, auto-add 12% output VAT as a journal line") —
  that integration point arrives with Phase 4 (Sales), which will call
  `calculate_tax()` and then `post_journal_entry()` together.
- No seed data / starter Philippine tax rate table ships with this delivery, by design (see
  "Tax/Accounting Rules Added" above) — a business must define its own rules before any
  calculation will succeed. A seed script for common BIR rates would be a reasonable
  addition once we're ready to declare specific rates as of a specific date.
- `effective_to = NULL` meaning "still in effect" is implicit; there is no explicit
  "current/latest" flag, so listing rules in the UI relies on the date range rather than a
  single boolean — acceptable for now but worth a UX pass later (e.g. a "Current" badge is
  already shown, but it's derived from `status`, not automatically from today's date vs.
  the effective range).

## Next Phase

**Phase 4 — Sales**: customers, sales invoices/receipts, and accounts receivable. This is
the first phase where the accounting engine (Phase 2) and tax engine (Phase 3) get used
together in a real business transaction: an invoice line calculates VAT via
`calculate_tax()`, then the whole invoice (revenue + VAT + AR) posts as one balanced journal
entry via `post_journal_entry()` — no new posting path, no new tax logic, just composition
of what already exists and is already tested.
