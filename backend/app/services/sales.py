"""
Sales invoice posting service.

Composes the accounting engine (app/accounting/engine/posting.py) and
tax engine (app/tax/engine/calculator.py) rather than reimplementing
either. This is the only code path allowed to post a SalesInvoice's
journal entry -- the API layer calls into this module, never
constructs the JournalEntry itself.

Journal entry shape for a posted invoice:
    Debit  Accounts Receivable         grand_total
    Credit Revenue account(s)          subtotal (per line's revenue account)
    Credit Output VAT Payable          tax_total (if any line had tax)

Requires the business to have configured its AR and Output VAT
control accounts (BusinessSettings.ar_account_id /
output_vat_account_id) -- raises a clear error rather than guessing
which account to use.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.engine.posting import LineInput, PostingError, post_journal_entry
from app.models.business import BusinessSettings
from app.models.inventory_item import InventoryItem
from app.models.sales import SalesInvoice, SalesInvoiceLine
from app.services.inventory import InventoryError, issue_stock
from app.tax.engine.calculator import calculate_tax
from app.tax.engine.rules import TaxRuleNotFoundError
from app.utils.money import to_money, zero


class SalesPostingError(Exception):
    """Raised when a sales invoice cannot be posted."""


@dataclass
class InvoiceLineInput:
    revenue_account_id: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rule_code: str | None = None
    item_id: str | None = None


def create_draft_invoice(
    db: Session,
    *,
    business_id: str,
    customer_id: str,
    invoice_number: str,
    invoice_date: date,
    due_date: date | None,
    lines: list[InvoiceLineInput],
    memo: str | None = None,
    as_of_date_for_tax: date | None = None,
) -> SalesInvoice:
    """
    Creates a Draft invoice with computed line/tax/grand totals. Does
    NOT post to the general ledger -- see post_invoice() for that.
    Tax is calculated now (using the tax engine) so the draft shows
    accurate totals, and recalculated at posting time in case the
    invoice sat as a draft across a rate change.
    """
    tax_date = as_of_date_for_tax or invoice_date

    invoice = SalesInvoice(
        business_id=business_id,
        customer_id=customer_id,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        memo=memo,
        status="Draft",
    )
    db.add(invoice)
    db.flush()

    subtotal = zero()
    tax_total = zero()

    for i, line in enumerate(lines, start=1):
        line_amount = to_money(line.quantity * line.unit_price)
        tax_amount = zero()

        if line.tax_rule_code:
            try:
                calc = calculate_tax(
                    db,
                    business_id=business_id,
                    rule_code=line.tax_rule_code,
                    taxable_amount=line_amount,
                    as_of_date=tax_date,
                )
                tax_amount = calc.tax_amount
            except TaxRuleNotFoundError as exc:
                raise SalesPostingError(str(exc))

        db.add(
            SalesInvoiceLine(
                invoice_id=invoice.id,
                revenue_account_id=line.revenue_account_id,
                item_id=line.item_id,
                line_number=i,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rule_code=line.tax_rule_code,
                line_amount=line_amount,
                tax_amount=tax_amount,
            )
        )

        subtotal += line_amount
        tax_total += tax_amount

    invoice.subtotal = subtotal
    invoice.tax_total = tax_total
    invoice.grand_total = subtotal + tax_total

    db.commit()
    db.refresh(invoice)
    return invoice


def update_draft_invoice(
    db: Session,
    *,
    invoice: SalesInvoice,
    customer_id: str,
    invoice_number: str,
    invoice_date: date,
    due_date: date | None,
    lines: list[InvoiceLineInput],
    memo: str | None = None,
    as_of_date_for_tax: date | None = None,
) -> SalesInvoice:
    """
    Replaces a Draft invoice's header fields and line items in place,
    recomputing totals exactly the way create_draft_invoice does.
    Only ever called on a Draft (the API layer checks status first) --
    a Posted invoice has already generated a journal entry, and
    editing it after the fact would desync the ledger from what the
    invoice claims to say, so posted invoices can't reach this path.
    """
    tax_date = as_of_date_for_tax or invoice_date

    invoice.customer_id = customer_id
    invoice.invoice_number = invoice_number
    invoice.invoice_date = invoice_date
    invoice.due_date = due_date
    invoice.memo = memo

    for old_line in list(invoice.lines):
        db.delete(old_line)
    db.flush()

    subtotal = zero()
    tax_total = zero()

    for i, line in enumerate(lines, start=1):
        line_amount = to_money(line.quantity * line.unit_price)
        tax_amount = zero()

        if line.tax_rule_code:
            try:
                calc = calculate_tax(
                    db,
                    business_id=invoice.business_id,
                    rule_code=line.tax_rule_code,
                    taxable_amount=line_amount,
                    as_of_date=tax_date,
                )
                tax_amount = calc.tax_amount
            except TaxRuleNotFoundError as exc:
                raise SalesPostingError(str(exc))

        db.add(
            SalesInvoiceLine(
                invoice_id=invoice.id,
                revenue_account_id=line.revenue_account_id,
                item_id=line.item_id,
                line_number=i,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rule_code=line.tax_rule_code,
                line_amount=line_amount,
                tax_amount=tax_amount,
            )
        )

        subtotal += line_amount
        tax_total += tax_amount

    invoice.subtotal = subtotal
    invoice.tax_total = tax_total
    invoice.grand_total = subtotal + tax_total

    db.commit()
    db.refresh(invoice)
    return invoice


def post_invoice(
    db: Session,
    *,
    invoice: SalesInvoice,
    created_by_user_id: str | None = None,
) -> SalesInvoice:
    """
    Post a Draft invoice to the general ledger: Debit AR for the
    grand total, credit each revenue account for its line subtotal,
    credit Output VAT Payable for the tax total (if any). Raises
    SalesPostingError if the business hasn't configured its AR/Output
    VAT control accounts, or if the underlying journal entry would be
    rejected by the accounting engine (e.g. period closed).
    """
    if invoice.status != "Draft":
        raise SalesPostingError(f"Invoice is {invoice.status}; only a Draft invoice can be posted.")
    if not invoice.lines:
        raise SalesPostingError("Cannot post an invoice with no lines.")

    settings = db.query(BusinessSettings).filter(BusinessSettings.business_id == invoice.business_id).first()
    if settings is None or not settings.ar_account_id:
        raise SalesPostingError(
            "This business has no Accounts Receivable control account configured "
            "(BusinessSettings.ar_account_id). Set it before posting sales invoices."
        )
    if invoice.tax_total > 0 and not settings.output_vat_account_id:
        raise SalesPostingError(
            "This invoice has tax but the business has no Output VAT control account "
            "configured (BusinessSettings.output_vat_account_id)."
        )

    revenue_by_account: dict[str, Decimal] = defaultdict(lambda: zero())
    for line in invoice.lines:
        revenue_by_account[line.revenue_account_id] += line.line_amount

    journal_lines = [LineInput(account_id=settings.ar_account_id, debit=invoice.grand_total)]
    for account_id, amount in revenue_by_account.items():
        journal_lines.append(LineInput(account_id=account_id, credit=amount))
    if invoice.tax_total > 0:
        journal_lines.append(LineInput(account_id=settings.output_vat_account_id, credit=invoice.tax_total))

    # Inventory-tracked lines also move cost from the balance sheet
    # (Inventory Asset) to the income statement (COGS) -- computed via
    # the moving-average cost on file for each item *before* this sale
    # reduces it. These lines join the SAME journal entry as the
    # revenue/AR/VAT lines above, so the whole invoice posts as one
    # atomic, balanced entry rather than two separate ones.
    cogs_by_account: dict[str, Decimal] = defaultdict(lambda: zero())
    inventory_by_account: dict[str, Decimal] = defaultdict(lambda: zero())
    items_to_issue: list[tuple[InventoryItem, Decimal]] = []

    for line in invoice.lines:
        if not line.item_id:
            continue
        item = db.get(InventoryItem, line.item_id)
        if not item or item.business_id != invoice.business_id:
            raise SalesPostingError(f"Inventory item {line.item_id} not found for this business.")
        if line.quantity > item.quantity_on_hand:
            raise SalesPostingError(
                f"Cannot sell {line.quantity} of '{item.name}': only {item.quantity_on_hand} on hand."
            )
        cost = to_money(line.quantity * item.average_cost)
        cogs_by_account[item.cogs_account_id] += cost
        inventory_by_account[item.inventory_account_id] += cost
        items_to_issue.append((item, line.quantity))

    for account_id, amount in cogs_by_account.items():
        journal_lines.append(LineInput(account_id=account_id, debit=amount))
    for account_id, amount in inventory_by_account.items():
        journal_lines.append(LineInput(account_id=account_id, credit=amount))

    try:
        entry = post_journal_entry(
            db,
            business_id=invoice.business_id,
            entry_date=invoice.invoice_date,
            lines=journal_lines,
            reference=invoice.invoice_number,
            memo=f"Sales Invoice {invoice.invoice_number}" + (f" — {invoice.memo}" if invoice.memo else ""),
            source="Sales Invoice",
            created_by_user_id=created_by_user_id,
        )
    except PostingError as exc:
        raise SalesPostingError(str(exc))

    # Issue stock only after the journal entry posted successfully --
    # same ordering reasoning as the purchases side (Phase 8): a
    # rejected posting should never leave stock movements with nothing
    # backing them.
    for item, quantity in items_to_issue:
        try:
            issue_stock(
                db,
                item=item,
                quantity=quantity,
                movement_date=invoice.invoice_date,
                reference_type="SalesInvoice",
                reference_id=invoice.id,
            )
        except InventoryError as exc:
            raise SalesPostingError(str(exc))

    invoice.status = "Posted"
    invoice.journal_entry_id = entry.id
    db.commit()
    db.refresh(invoice)
    return invoice
