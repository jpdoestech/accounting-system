"""
Bank reconciliation service.

Marks specific cash receipts/disbursements as cleared (matched against
a bank statement line), then computes whether the book-side balance
(opening balance + all cleared receipts - all cleared disbursements,
as of the statement date) agrees with the statement's ending balance.
A reconciliation is only marked Completed when the difference is
exactly zero -- a nonzero difference is recorded, not hidden, so a
bookkeeper can see exactly how far off things are and keep
investigating.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bank import BankAccount
from app.models.bank_reconciliation import BankReconciliation
from app.models.cash_disbursement import CashDisbursement
from app.models.cash_receipt import CashReceipt
from app.utils.money import to_money, zero


class ReconciliationError(Exception):
    """Raised when a reconciliation cannot be performed."""


def reconcile_bank_account(
    db: Session,
    *,
    business_id: str,
    bank_account_id: str,
    statement_date: date,
    statement_ending_balance: Decimal,
    receipt_ids_to_clear: list[str],
    disbursement_ids_to_clear: list[str],
) -> BankReconciliation:
    bank_account = db.get(BankAccount, bank_account_id)
    if not bank_account or bank_account.business_id != business_id:
        raise ReconciliationError("Bank account not found for this business.")

    statement_ending_balance = to_money(statement_ending_balance)

    # Mark the specified transactions cleared. Only Posted transactions
    # can be cleared -- a Draft receipt/disbursement has no cash
    # movement yet, so it can't correspond to a bank statement line.
    for receipt_id in receipt_ids_to_clear:
        receipt = db.get(CashReceipt, receipt_id)
        if not receipt or receipt.business_id != business_id or receipt.bank_account_id != bank_account_id:
            raise ReconciliationError(f"Cash receipt {receipt_id} not found for this bank account.")
        if receipt.status != "Posted":
            raise ReconciliationError(f"Cash receipt {receipt.receipt_number} is not Posted; cannot clear it.")
        receipt.is_cleared = True
        receipt.cleared_date = statement_date

    for disb_id in disbursement_ids_to_clear:
        disbursement = db.get(CashDisbursement, disb_id)
        if not disbursement or disbursement.business_id != business_id or disbursement.bank_account_id != bank_account_id:
            raise ReconciliationError(f"Cash disbursement {disb_id} not found for this bank account.")
        if disbursement.status != "Posted":
            raise ReconciliationError(
                f"Cash disbursement {disbursement.payment_number} is not Posted; cannot clear it."
            )
        disbursement.is_cleared = True
        disbursement.cleared_date = statement_date

    db.flush()

    # Book balance = opening balance + all cleared receipts - all
    # cleared disbursements, dated on or before the statement date.
    cleared_receipts = (
        db.query(CashReceipt)
        .filter(
            CashReceipt.business_id == business_id,
            CashReceipt.bank_account_id == bank_account_id,
            CashReceipt.is_cleared.is_(True),
            CashReceipt.receipt_date <= statement_date,
        )
        .all()
    )
    cleared_disbursements = (
        db.query(CashDisbursement)
        .filter(
            CashDisbursement.business_id == business_id,
            CashDisbursement.bank_account_id == bank_account_id,
            CashDisbursement.is_cleared.is_(True),
            CashDisbursement.payment_date <= statement_date,
        )
        .all()
    )

    total_cleared_receipts = sum((r.amount for r in cleared_receipts), zero())
    total_cleared_disbursements = sum((d.amount for d in cleared_disbursements), zero())

    book_balance = to_money(bank_account.opening_balance + total_cleared_receipts - total_cleared_disbursements)
    difference = to_money(statement_ending_balance - book_balance)

    reconciliation = BankReconciliation(
        business_id=business_id,
        bank_account_id=bank_account_id,
        statement_date=statement_date,
        statement_ending_balance=statement_ending_balance,
        book_balance=book_balance,
        difference=difference,
        status="Completed" if difference == 0 else "Draft",
    )
    db.add(reconciliation)
    db.commit()
    db.refresh(reconciliation)
    return reconciliation
