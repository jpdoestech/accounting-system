# Phase 7 Development Report — Philippine Compliance / BIR

## Completed

Exactly as scoped at the end of Phase 6: a reporting/compliance layer over data already
captured — no new posting logic anywhere in this phase.

- **Books of Accounts** (`app/bir/books/queries.py`): General Journal (every posted journal
  entry, chronological, from every module — manual, sales, purchases, banking, all in one
  place), Sales Book, Purchase Book, Cash Receipts Book, Cash Disbursements Book — each
  filterable by date range and showing only Posted documents (a Draft invoice/bill never
  appears in a book, verified by test). The General Ledger itself isn't duplicated here —
  it already existed since Phase 2 (`app/accounting/ledger/queries.py::get_account_ledger`).
- **VAT Summary** (`app/bir/books/vat_summary.py`): aggregates Output VAT (from posted sales
  invoices) and Input VAT (from posted purchase bills) for a period into Output VAT, Input
  VAT, and Net VAT Payable — the figures a BIR VAT return needs. Pure aggregation; no tax
  calculation happens here, only summing what Phase 3's tax engine already calculated and
  Phases 4–5 already posted.
- **Withholding Tax Certificates / BIR Form 2307** (`app/bir/books/withholding.py`):
  aggregates `PurchaseBillLine.withholding_tax_amount` (tracked since Phase 5) for one
  vendor across a period, grouped by ATC code (looked up from the `TaxRule` each line used —
  Phase 3), into a preview a bookkeeper can review before issuing, and a persisted
  `WithholdingTaxCertificate` record once issued. Issuing a certificate with zero
  withholding tax to certify is rejected — an empty 2307 would be a data-quality error, not
  a valid document.
- Full API under `/businesses/{id}/bir/...` for all of the above.
- Frontend: a BIR Reports view with VAT summary (date-range query), books-of-accounts
  buttons (rendering the raw JSON result for now — see Known Issues), and withholding
  certificate preview/issue/list.
- **Nav reorganization**: the top nav had grown to 12 flat links by the end of Phase 6
  (flagged as a known issue in that report). Regrouped into dropdown menus — Accounting,
  Sales, Purchases, Banking — plus Dashboard and BIR as top-level links. Required adding
  Bootstrap's JS bundle to `index.html` (only the CSS was loaded before; dropdowns need the
  JS component).

## Files Created

**Backend**:
`app/models/withholding_certificate.py`, `app/bir/books/queries.py`,
`app/bir/books/vat_summary.py`, `app/bir/books/withholding.py`, `app/schemas/bir.py`,
`app/api/v1/bir.py`, `migrations/versions/96f2ad795f3f_phase7_bir_compliance.py`,
`tests/test_bir.py`, `tests/test_bir_api.py`.

**Frontend**: `src/views/BirReportsView.vue`.

## Files Modified

- `app/api/router.py`, `app/main.py`, `migrations/env.py`, `tests/conftest.py` — registered
  the BIR router and imported the new `withholding_certificate` model.
- `src/router/index.js` — added the `/bir` route.
- `src/layouts/DefaultLayout.vue` — regrouped the nav into dropdown menus.
- `frontend/index.html` — added the Bootstrap JS bundle (dropdowns require it).

## Database Changes

Migration `96f2ad795f3f_phase7_bir_compliance` adds `withholding_tax_certificates` — the
only new table this phase, since books and VAT summary are pure read-side queries over
existing tables with nothing new to persist. Verified with a full
`rm -f dev.db && alembic upgrade head` from empty, running all seven migrations
(Phases 1–7) in sequence without error.

## Tax/Accounting Rules Added

None — this phase reports on tax already calculated by Phase 3's engine and posted by
Phases 4–5. No new rates, rules, or posting logic.

## Tests

`pytest -v` in `backend/`: **45 passed, 0 failed** (38 carried over from Phases 1–6, 7 new).

- `test_bir.py` (domain-layer, direct calls): the General Journal includes every posted
  entry across modules in chronological order with correct `source` labels ("Sales
  Invoice", "Purchase Bill"); the Sales Book and Purchase Book only include Posted
  documents — a Draft invoice created alongside a Posted one is confirmed absent from the
  Sales Book; the VAT summary correctly nets Output VAT (₱120 from a ₱1,000 sale) against
  Input VAT (₱60 from a ₱500 purchase) to a ₱60 net payable; a withholding certificate
  preview correctly aggregates two separate bills (₱100 + ₱200 withheld) into one ATC
  breakdown row totaling ₱300; issuing a certificate persists it with `status="Issued"`;
  issuing a certificate for a vendor/period with zero withholding tax is rejected with a
  clear "nothing to certify" error rather than producing an empty document.
- `test_bir_api.py` (HTTP acceptance test): the complete flow — full chart of accounts and
  control-account setup, a posted sales invoice (₱1,000 + 12% VAT) and a posted purchase
  bill (₱500 + 12% VAT + 10% withholding), then querying the General Journal (2 entries),
  Sales Book (1) and Purchase Book (1), VAT summary (output ₱120, input ₱60, net payable
  ₱60), a withholding certificate preview (₱50 withheld, ATC "WC010"), issuing that
  certificate, and confirming it appears in the certificate list.

The running server was smoke-tested live (uvicorn + curl) for the new BIR endpoints
specifically — confirmed the General Journal and VAT Summary endpoints respond correctly
with sensible empty-state values (`[]` and all-zero figures) for a brand-new business with
no transactions yet, rather than erroring. The full realistic flow with actual transactions
was already verified end-to-end by the HTTP acceptance test, so the live check focused on
confirming the new routes are reachable and well-behaved rather than re-running the entire
flow a second time. The frontend was rebuilt with `npx vite build` after adding the BIR view
and regrouping the nav — 103 modules, no errors.

**Passed:** 45/45 automated tests, live smoke test, frontend build. **Failed:** none.

## Known Issues

- The frontend's "Books of Accounts" buttons currently render raw JSON in a `<pre>` block
  rather than a formatted table — functional for verifying the data is correct, but not a
  presentable book format. Proper tabular rendering (and eventually PDF/print export, since
  BIR-registered books of accounts are physical/printable documents) is a reasonable
  Phase 7.x or Phase 11 addition.
- No BIR Form 2307 PDF generation — the certificate is a database record with the correct
  figures, not yet a printable/downloadable document matching the actual BIR form layout.
  The `pdf` skill available in this environment could produce that in a follow-up pass.
- No Summary List of Sales and Purchases (SLSP) or Quarterly/Annual ITR-adjacent reports —
  this phase covers VAT summary and withholding certificates specifically, which were the
  two compliance artifacts most directly enabled by data already captured; broader BIR
  return preparation is a larger scope than one phase.
- Certificate numbering is manual (the frontend generates a semi-random suggestion, but
  nothing enforces sequential, gap-free numbering the way an actual BIR-compliant document
  series would need) — same category of gap as sales invoice/purchase bill numbering flagged
  in Phases 4–5.
- The VAT summary doesn't yet distinguish zero-rated, exempt, and standard-rated sales/
  purchases separately (it only has "taxable" vs. total) — a business with mixed VAT
  treatment would need a more granular breakdown than this phase provides.

## Next Phase

**Phase 8 — Inventory**: items, stock levels, and cost of goods sold, integrating with the
Sales and Purchases modules (Phases 4–5) so a sales invoice line can reduce stock and a
purchase bill line can increase it, with COGS posted through the same accounting engine
posting pattern used throughout every phase so far.
