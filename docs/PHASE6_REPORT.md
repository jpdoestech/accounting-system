# Phase 6 Development Report — Banking

## Completed

- `BankAccount` model: each linked to a GL account in the chart of accounts (not a
  hard-coded "Cash" code), with its own opening balance and date. A business can have
  multiple bank accounts.
- `CashReceipt` / `CashReceiptAllocation` and `CashDisbursement` / `CashDisbursementAllocation`
  models: money in from customers and money out to vendors, each with Draft → Posted
  lifecycle. Allocations track which sales invoice(s) or purchase bill(s) a payment covers
  — for reporting, not because the journal entry needs more lines: a receipt's entry is
  always exactly Debit Bank / Credit AR, and a disbursement's is always exactly Debit AP /
  Credit Bank, regardless of how many documents it's applied to. This is the phase where AR
  and AP balances opened in Phases 4–5 actually get reduced, closing the loop.
- Banking posting service (`app/services/banking.py`) composing the accounting engine — no
  new posting logic, same `post_journal_entry()` from Phase 2.
- Allocation validation: the sum of a receipt's/disbursement's allocations can be less than
  the payment amount (an on-account/advance payment, tracked but not forcibly applied) but
  is rejected if it would exceed the payment amount — verified by test.
- Bank reconciliation (`app/services/reconciliation.py`): marks specific posted
  receipts/disbursements as cleared against a bank statement, then computes
  `book_balance = opening_balance + cleared receipts − cleared disbursements` as of the
  statement date and compares it to the statement's ending balance. A reconciliation with a
  zero difference is marked Completed; a nonzero difference is still recorded (not hidden),
  so a bookkeeper can see exactly how far off things are rather than getting a silent
  false-positive.
- A Draft receipt/disbursement cannot be cleared during reconciliation — only Posted
  transactions correspond to actual cash movement a bank statement could show.
- API endpoints for bank accounts, cash receipts (create draft/list/post), cash
  disbursements (create draft/list/post), and reconciliation (reconcile/list history).
- Frontend: Bank Accounts view, Cash Receipts view (with invoice allocation dropdown), Cash
  Disbursements view (with bill allocation dropdown).

## Files Created

**Backend**:
`app/models/bank.py`, `app/models/cash_receipt.py`, `app/models/cash_disbursement.py`,
`app/models/bank_reconciliation.py`, `app/services/banking.py`,
`app/services/reconciliation.py`, `app/schemas/banking.py`, `app/api/v1/banking.py`,
`migrations/versions/3ca5f8e2a407_phase6_banking.py`,
`tests/test_banking.py`, `tests/test_banking_api.py`.

**Frontend**: `src/views/BankAccountsView.vue`, `src/views/CashReceiptsView.vue`,
`src/views/CashDisbursementsView.vue`.

## Files Modified

- `app/api/router.py`, `app/main.py`, `migrations/env.py`, `tests/conftest.py` — registered
  the banking router and imported the four new models.
- `src/router/index.js`, `src/layouts/DefaultLayout.vue` — added Bank Accounts/Cash
  Receipts/Payments routes and nav links.

## Database Changes

Migration `3ca5f8e2a407_phase6_banking` adds `bank_accounts`, `cash_receipts`,
`cash_receipt_allocations`, `cash_disbursements`, `cash_disbursement_allocations`, and
`bank_reconciliations`. All six new tables — no existing table needed an `ALTER`, so unlike
Phases 4 and 5 there was no SQLite batch-mode fix needed this time. Verified with a full
`rm -f dev.db && alembic upgrade head` from empty, running all six migrations (Phases 1–6)
in sequence without error.

## Tax/Accounting Rules Added

None — banking doesn't introduce new tax logic; it settles balances that Phases 4–5 already
computed and posted.

## Tests

`pytest -v` in `backend/`: **38 passed, 0 failed** (31 carried over from Phases 1–5, 7 new).

- `test_banking.py` (domain-layer, direct calls): a posted receipt reduces AR to zero and
  increases the bank GL account (verified against the trial balance — AR drops off the
  report entirely once it nets to zero, exactly as expected for a fully-paid invoice); a
  posted disbursement does the same for AP; an allocation exceeding the payment amount is
  rejected with a clear error; a reconciliation with matching balances computes the correct
  book balance and difference and is marked Completed; a reconciliation with a genuine
  discrepancy reports the nonzero difference rather than silently accepting it; attempting
  to clear a Draft (unposted) receipt during reconciliation is rejected.
- `test_banking_api.py` (HTTP acceptance test): the full realistic flow — bank account
  setup, a posted sales invoice, a posted purchase bill, a cash receipt applied to the
  invoice, a cash disbursement applied to the bill, confirming AR and AP both net to zero
  in the trial balance, and a bank reconciliation that ties out exactly
  (opening ₱10,000 + ₱1,000 receipt − ₱500 disbursement = ₱10,500, matching the statement).

The running server was smoke-tested live (uvicorn + curl) for the new bank account
endpoints specifically (the full receipt/disbursement/reconciliation flow was already
verified end-to-end by the HTTP acceptance test, so the live check focused on confirming
the newly-added endpoints respond correctly over real HTTP rather than re-running the
entire flow a second time). The frontend was rebuilt with `npx vite build` after adding the
three new views — 102 modules, no errors.

**Passed:** 38/38 automated tests, live smoke test, frontend build. **Failed:** none.

## Known Issues

- No receipt/disbursement void or reversal workflow yet — same gap as sales invoices and
  purchase bills in Phases 4–5.
- The top navigation bar now has twelve links (Dashboard through Payments) and is starting
  to feel cluttered on a standard screen width; it hasn't been reorganized into grouped
  menus yet. Purely a UX polish item — every route still works, nothing is hidden or
  broken, but a nav redesign (dropdown groups: Accounting / Sales / Purchases / Banking) is
  worth doing before Phase 7 adds even more sections.
- Reconciliation only compares a single point-in-time balance (opening + cleared
  transactions vs. statement ending balance) — there's no bank statement import/matching UI
  (e.g. upload a CSV and auto-suggest matches); a bookkeeper currently has to know which
  receipt/disbursement IDs to pass in.
- No support for bank transfers between two of the business's own bank accounts (which
  would need a receipt-like and disbursement-like pair without touching AR/AP at all) — a
  reasonable Phase 6.x addition.
- `is_vat_registered` on Vendor (Phase 5) and this phase's allocation tracking don't yet
  connect to any AR/AP aging report — "how much does this customer still owe" requires
  manually comparing an invoice's `grand_total` to the sum of its receipt allocations; no
  computed "amount outstanding" field exists yet on `SalesInvoice`/`PurchaseBill`.

## Next Phase

**Phase 7 — Philippine Compliance / BIR**: books of accounts, BIR-format reports, and
withholding tax certificates (BIR Form 2307), drawing on data this and earlier phases
already capture — the `withholding_tax_amount` tracked per purchase bill line since Phase
5, the tax rules and calculations from Phase 3, and the posted journal entries from Phase
2. This is a reporting/compliance layer over what already exists, not a new transactional
module, so it shouldn't require new posting logic — only new read-side queries and
document generation.
