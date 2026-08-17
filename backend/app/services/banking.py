"""
Banking posting service: cash receipts (customer payments against AR)
and cash disbursements (vendor payments against AP).

Composes the accounting engine (app/accounting/engine/posting.py) --
this is the only code path allowed to create a receipt's or
disbursement's JournalEntry. Both postings are simple two-line
entries regardless of how many invoices/bills the payment is applied
to; allocations are bookkeeping detail, not additional journal lines.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.engine.posting import LineInput, PostingError, post_journal_entry
from app.models.bank import BankAccount
from app.models.business import BusinessSettings
from app.models.cash_disbursement import CashDisbursement, CashDisbursementAllocation
from app.models.cash_receipt import CashReceipt, CashReceiptAllocation
from app.models.purchase import PurchaseBill
from app.models.sales import SalesInvoice
from app.utils.money import to_money, zero


class BankingPostingError(Exception):
    """Raised when a cash receipt or disbursement cannot be created/posted."""


@dataclass
class AllocationInput:
    document_id: str  # sales_invoice_id or purchase_bill_id, depending on context
    amount_applied: Decimal


# --------------------------------------------------------------- receipts

def create_draft_receipt(
    db: Session,
    *,
    business_id: str,
    bank_account_id: str,
    customer_id: str,
    receipt_number: str,
    receipt_date: date,
    amount: Decimal,
    allocations: list[AllocationInput],
    memo: str | None = None,
) -> CashReceipt:
    amount = to_money(amount)
    allocated_total = zero()
    for alloc in allocations:
        invoice = db.get(SalesInvoice, alloc.document_id)
        if not invoice or invoice.business_id != business_id:
            raise BankingPostingError(f"Sales invoice {alloc.document_id} not found for this business.")
        allocated_total += to_money(alloc.amount_applied)

    if allocated_total > amount:
        raise BankingPostingError(
            f"Allocated total {allocated_total} exceeds the receipt amount {amount}."
        )

    receipt = CashReceipt(
        business_id=business_id,
        bank_account_id=bank_account_id,
        customer_id=customer_id,
        receipt_number=receipt_number,
        receipt_date=receipt_date,
        amount=amount,
        memo=memo,
        status="Draft",
    )
    db.add(receipt)
    db.flush()

    for alloc in allocations:
        db.add(
            CashReceiptAllocation(
                receipt_id=receipt.id,
                sales_invoice_id=alloc.document_id,
                amount_applied=to_money(alloc.amount_applied),
            )
        )

    db.commit()
    db.refresh(receipt)
    return receipt


def post_receipt(db: Session, *, receipt: CashReceipt, created_by_user_id: str | None = None) -> CashReceipt:
    if receipt.status != "Draft":
        raise BankingPostingError(f"Receipt is {receipt.status}; only a Draft receipt can be posted.")

    bank_account = db.get(BankAccount, receipt.bank_account_id)
    if not bank_account or bank_account.business_id != receipt.business_id:
        raise BankingPostingError("Bank account not found for this business.")

    settings = db.query(BusinessSettings).filter(BusinessSettings.business_id == receipt.business_id).first()
    if settings is None or not settings.ar_account_id:
        raise BankingPostingError(
            "This business has no Accounts Receivable control account configured. "
            "Set BusinessSettings.ar_account_id before posting cash receipts."
        )

    try:
        entry = post_journal_entry(
            db,
            business_id=receipt.business_id,
            entry_date=receipt.receipt_date,
            lines=[
                LineInput(account_id=bank_account.gl_account_id, debit=receipt.amount),
                LineInput(account_id=settings.ar_account_id, credit=receipt.amount),
            ],
            reference=receipt.receipt_number,
            memo=f"Cash Receipt {receipt.receipt_number}" + (f" — {receipt.memo}" if receipt.memo else ""),
            source="Cash Receipt",
            created_by_user_id=created_by_user_id,
        )
    except PostingError as exc:
        raise BankingPostingError(str(exc))

    receipt.status = "Posted"
    receipt.journal_entry_id = entry.id
    db.commit()
    db.refresh(receipt)
    return receipt


# ---------------------------------------------------------- disbursements

def create_draft_disbursement(
    db: Session,
    *,
    business_id: str,
    bank_account_id: str,
    vendor_id: str,
    payment_number: str,
    payment_date: date,
    amount: Decimal,
    allocations: list[AllocationInput],
    memo: str | None = None,
) -> CashDisbursement:
    amount = to_money(amount)
    allocated_total = zero()
    for alloc in allocations:
        bill = db.get(PurchaseBill, alloc.document_id)
        if not bill or bill.business_id != business_id:
            raise BankingPostingError(f"Purchase bill {alloc.document_id} not found for this business.")
        allocated_total += to_money(alloc.amount_applied)

    if allocated_total > amount:
        raise BankingPostingError(
            f"Allocated total {allocated_total} exceeds the payment amount {amount}."
        )

    disbursement = CashDisbursement(
        business_id=business_id,
        bank_account_id=bank_account_id,
        vendor_id=vendor_id,
        payment_number=payment_number,
        payment_date=payment_date,
        amount=amount,
        memo=memo,
        status="Draft",
    )
    db.add(disbursement)
    db.flush()

    for alloc in allocations:
        db.add(
            CashDisbursementAllocation(
                disbursement_id=disbursement.id,
                purchase_bill_id=alloc.document_id,
                amount_applied=to_money(alloc.amount_applied),
            )
        )

    db.commit()
    db.refresh(disbursement)
    return disbursement


def post_disbursement(
    db: Session, *, disbursement: CashDisbursement, created_by_user_id: str | None = None
) -> CashDisbursement:
    if disbursement.status != "Draft":
        raise BankingPostingError(f"Payment is {disbursement.status}; only a Draft payment can be posted.")

    bank_account = db.get(BankAccount, disbursement.bank_account_id)
    if not bank_account or bank_account.business_id != disbursement.business_id:
        raise BankingPostingError("Bank account not found for this business.")

    settings = db.query(BusinessSettings).filter(BusinessSettings.business_id == disbursement.business_id).first()
    if settings is None or not settings.ap_account_id:
        raise BankingPostingError(
            "This business has no Accounts Payable control account configured. "
            "Set BusinessSettings.ap_account_id before posting cash disbursements."
        )

    try:
        entry = post_journal_entry(
            db,
            business_id=disbursement.business_id,
            entry_date=disbursement.payment_date,
            lines=[
                LineInput(account_id=settings.ap_account_id, debit=disbursement.amount),
                LineInput(account_id=bank_account.gl_account_id, credit=disbursement.amount),
            ],
            reference=disbursement.payment_number,
            memo=f"Payment {disbursement.payment_number}" + (f" — {disbursement.memo}" if disbursement.memo else ""),
            source="Cash Disbursement",
            created_by_user_id=created_by_user_id,
        )
    except PostingError as exc:
        raise BankingPostingError(str(exc))

    disbursement.status = "Posted"
    disbursement.journal_entry_id = entry.id
    db.commit()
    db.refresh(disbursement)
    return disbursement
