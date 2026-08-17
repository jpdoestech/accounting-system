"""
Purchase bill posting service.

Mirrors app/services/sales.py, composing the accounting engine
(app/accounting/engine/posting.py) and tax engine
(app/tax/engine/calculator.py) rather than reimplementing either.

Journal entry shape for a posted bill (see module docstring in
app/models/purchase.py for the withholding tax reasoning):

    Debit  Expense account(s)          subtotal (per line's expense account)
    Debit  Input VAT                   input_vat_total (if any line had VAT)
    Credit Accounts Payable            amount_due_to_vendor (grand_total - withholding_tax_total)
    Credit Withholding Tax Payable     withholding_tax_total (if any line had withholding)

Total debits = subtotal + input_vat_total = grand_total
Total credits = (grand_total - withholding_tax_total) + withholding_tax_total = grand_total
-- balances by construction; the accounting engine still re-validates it.
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
from app.models.purchase import PurchaseBill, PurchaseBillLine
from app.services.inventory import receive_stock
from app.tax.engine.calculator import calculate_tax
from app.tax.engine.rules import TaxRuleNotFoundError
from app.utils.money import to_money, zero


class PurchasePostingError(Exception):
    """Raised when a purchase bill cannot be posted."""


@dataclass
class BillLineInput:
    expense_account_id: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rule_code: str | None = None
    withholding_tax_rule_code: str | None = None
    item_id: str | None = None


def create_draft_bill(
    db: Session,
    *,
    business_id: str,
    vendor_id: str,
    bill_number: str,
    bill_date: date,
    due_date: date | None,
    lines: list[BillLineInput],
    memo: str | None = None,
    as_of_date_for_tax: date | None = None,
) -> PurchaseBill:
    """
    Creates a Draft bill with computed line/tax/withholding/total
    amounts. Does NOT post to the general ledger -- see post_bill().
    """
    tax_date = as_of_date_for_tax or bill_date

    bill = PurchaseBill(
        business_id=business_id,
        vendor_id=vendor_id,
        bill_number=bill_number,
        bill_date=bill_date,
        due_date=due_date,
        memo=memo,
        status="Draft",
    )
    db.add(bill)
    db.flush()

    subtotal = zero()
    input_vat_total = zero()
    withholding_tax_total = zero()

    for i, line in enumerate(lines, start=1):
        line_amount = to_money(line.quantity * line.unit_price)
        tax_amount = zero()
        withholding_amount = zero()

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
                raise PurchasePostingError(str(exc))

        if line.withholding_tax_rule_code:
            try:
                calc = calculate_tax(
                    db,
                    business_id=business_id,
                    rule_code=line.withholding_tax_rule_code,
                    taxable_amount=line_amount,
                    as_of_date=tax_date,
                )
                withholding_amount = calc.tax_amount
            except TaxRuleNotFoundError as exc:
                raise PurchasePostingError(str(exc))

        db.add(
            PurchaseBillLine(
                bill_id=bill.id,
                expense_account_id=line.expense_account_id,
                item_id=line.item_id,
                line_number=i,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rule_code=line.tax_rule_code,
                withholding_tax_rule_code=line.withholding_tax_rule_code,
                line_amount=line_amount,
                tax_amount=tax_amount,
                withholding_tax_amount=withholding_amount,
            )
        )

        subtotal += line_amount
        input_vat_total += tax_amount
        withholding_tax_total += withholding_amount

    bill.subtotal = subtotal
    bill.input_vat_total = input_vat_total
    bill.withholding_tax_total = withholding_tax_total
    bill.grand_total = subtotal + input_vat_total
    bill.amount_due_to_vendor = bill.grand_total - withholding_tax_total

    db.commit()
    db.refresh(bill)
    return bill


def post_bill(
    db: Session,
    *,
    bill: PurchaseBill,
    created_by_user_id: str | None = None,
) -> PurchaseBill:
    """
    Post a Draft bill to the general ledger. Raises PurchasePostingError
    if the business hasn't configured its AP/Input VAT/Withholding
    control accounts (only the ones actually needed by this bill), or
    if the accounting engine rejects the resulting entry.
    """
    if bill.status != "Draft":
        raise PurchasePostingError(f"Bill is {bill.status}; only a Draft bill can be posted.")
    if not bill.lines:
        raise PurchasePostingError("Cannot post a bill with no lines.")

    settings = db.query(BusinessSettings).filter(BusinessSettings.business_id == bill.business_id).first()
    if settings is None or not settings.ap_account_id:
        raise PurchasePostingError(
            "This business has no Accounts Payable control account configured "
            "(BusinessSettings.ap_account_id). Set it before posting purchase bills."
        )
    if bill.input_vat_total > 0 and not settings.input_vat_account_id:
        raise PurchasePostingError(
            "This bill has input VAT but the business has no Input VAT control account "
            "configured (BusinessSettings.input_vat_account_id)."
        )
    if bill.withholding_tax_total > 0 and not settings.withholding_tax_payable_account_id:
        raise PurchasePostingError(
            "This bill has withholding tax but the business has no Withholding Tax Payable "
            "control account configured (BusinessSettings.withholding_tax_payable_account_id)."
        )

    expense_by_account: dict[str, Decimal] = defaultdict(lambda: zero())
    for line in bill.lines:
        # Inventory-tracked lines debit the item's Inventory Asset
        # account instead of the line's chosen expense account -- the
        # cost sits on the balance sheet as stock until it's sold
        # (see app/services/sales.py, which moves it to COGS then).
        if line.item_id:
            item = db.get(InventoryItem, line.item_id)
            if not item or item.business_id != bill.business_id:
                raise PurchasePostingError(f"Inventory item {line.item_id} not found for this business.")
            expense_by_account[item.inventory_account_id] += line.line_amount
        else:
            expense_by_account[line.expense_account_id] += line.line_amount

    journal_lines = [LineInput(account_id=account_id, debit=amount) for account_id, amount in expense_by_account.items()]
    if bill.input_vat_total > 0:
        journal_lines.append(LineInput(account_id=settings.input_vat_account_id, debit=bill.input_vat_total))

    journal_lines.append(LineInput(account_id=settings.ap_account_id, credit=bill.amount_due_to_vendor))
    if bill.withholding_tax_total > 0:
        journal_lines.append(
            LineInput(account_id=settings.withholding_tax_payable_account_id, credit=bill.withholding_tax_total)
        )

    try:
        entry = post_journal_entry(
            db,
            business_id=bill.business_id,
            entry_date=bill.bill_date,
            lines=journal_lines,
            reference=bill.bill_number,
            memo=f"Purchase Bill {bill.bill_number}" + (f" — {bill.memo}" if bill.memo else ""),
            source="Purchase Bill",
            created_by_user_id=created_by_user_id,
        )
    except PostingError as exc:
        raise PurchasePostingError(str(exc))

    # Receive stock for inventory-tracked lines only after the journal
    # entry has posted successfully -- a rejected posting (e.g. closed
    # period) should never leave stock movements behind with nothing
    # to back them.
    for line in bill.lines:
        if line.item_id:
            item = db.get(InventoryItem, line.item_id)
            receive_stock(
                db,
                item=item,
                quantity=line.quantity,
                unit_cost=line.unit_price,
                movement_date=bill.bill_date,
                reference_type="PurchaseBill",
                reference_id=bill.id,
            )

    bill.status = "Posted"
    bill.journal_entry_id = entry.id
    db.commit()
    db.refresh(bill)
    return bill
