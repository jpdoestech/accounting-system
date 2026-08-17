"""
Books of Accounts.

Read-only reports assembled entirely from data already posted in
earlier phases -- no new posting logic. Covers the standard BIR-
required books: General Journal, Sales Book, Purchase Book, Cash
Receipts Book, Cash Disbursements Book. The General Ledger itself
already exists as app.accounting.ledger.queries.get_account_ledger
(Phase 2); this module doesn't duplicate it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models.cash_disbursement import CashDisbursement
from app.models.cash_receipt import CashReceipt
from app.models.journal import JournalEntry
from app.models.purchase import PurchaseBill
from app.models.sales import SalesInvoice


@dataclass
class GeneralJournalLineView:
    account_id: str
    description: str | None
    debit: str
    credit: str


@dataclass
class GeneralJournalEntryView:
    entry_date: date
    reference: str | None
    memo: str | None
    source: str
    status: str
    lines: list[GeneralJournalLineView] = field(default_factory=list)


def get_general_journal(
    db: Session, *, business_id: str, date_from: date | None = None, date_to: date | None = None
) -> list[GeneralJournalEntryView]:
    """All journal entries (from every module -- manual, sales, purchases,
    banking) in chronological order, with their lines. This is the
    master record every other book/report is derived from."""
    query = db.query(JournalEntry).filter(JournalEntry.business_id == business_id)
    if date_from is not None:
        query = query.filter(JournalEntry.entry_date >= date_from)
    if date_to is not None:
        query = query.filter(JournalEntry.entry_date <= date_to)

    entries = query.order_by(JournalEntry.entry_date, JournalEntry.created_at).all()

    return [
        GeneralJournalEntryView(
            entry_date=e.entry_date,
            reference=e.reference,
            memo=e.memo,
            source=e.source,
            status=e.status,
            lines=[
                GeneralJournalLineView(
                    account_id=l.account_id,
                    description=l.description,
                    debit=str(l.debit),
                    credit=str(l.credit),
                )
                for l in e.lines
            ],
        )
        for e in entries
    ]


def get_sales_book(
    db: Session, *, business_id: str, date_from: date | None = None, date_to: date | None = None
) -> list[SalesInvoice]:
    """All Posted sales invoices in the period -- the BIR Sales Book."""
    query = db.query(SalesInvoice).filter(
        SalesInvoice.business_id == business_id, SalesInvoice.status == "Posted"
    )
    if date_from is not None:
        query = query.filter(SalesInvoice.invoice_date >= date_from)
    if date_to is not None:
        query = query.filter(SalesInvoice.invoice_date <= date_to)
    return query.order_by(SalesInvoice.invoice_date).all()


def get_purchase_book(
    db: Session, *, business_id: str, date_from: date | None = None, date_to: date | None = None
) -> list[PurchaseBill]:
    """All Posted purchase bills in the period -- the BIR Purchase Book."""
    query = db.query(PurchaseBill).filter(
        PurchaseBill.business_id == business_id, PurchaseBill.status == "Posted"
    )
    if date_from is not None:
        query = query.filter(PurchaseBill.bill_date >= date_from)
    if date_to is not None:
        query = query.filter(PurchaseBill.bill_date <= date_to)
    return query.order_by(PurchaseBill.bill_date).all()


def get_cash_receipts_book(
    db: Session, *, business_id: str, date_from: date | None = None, date_to: date | None = None
) -> list[CashReceipt]:
    query = db.query(CashReceipt).filter(
        CashReceipt.business_id == business_id, CashReceipt.status == "Posted"
    )
    if date_from is not None:
        query = query.filter(CashReceipt.receipt_date >= date_from)
    if date_to is not None:
        query = query.filter(CashReceipt.receipt_date <= date_to)
    return query.order_by(CashReceipt.receipt_date).all()


def get_cash_disbursements_book(
    db: Session, *, business_id: str, date_from: date | None = None, date_to: date | None = None
) -> list[CashDisbursement]:
    query = db.query(CashDisbursement).filter(
        CashDisbursement.business_id == business_id, CashDisbursement.status == "Posted"
    )
    if date_from is not None:
        query = query.filter(CashDisbursement.payment_date >= date_from)
    if date_to is not None:
        query = query.filter(CashDisbursement.payment_date <= date_to)
    return query.order_by(CashDisbursement.payment_date).all()
