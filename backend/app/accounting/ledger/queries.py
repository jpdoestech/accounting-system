"""
General ledger and trial balance queries.

Read-only: this module never writes JournalEntry/JournalLine rows --
see app/accounting/engine/posting.py for that. It only aggregates what
has already been posted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import NORMAL_BALANCE, Account
from app.models.journal import JournalEntry, JournalLine
from app.utils.money import zero


@dataclass
class LedgerLineView:
    entry_date: date
    journal_entry_id: str
    reference: str | None
    memo: str | None
    description: str | None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


@dataclass
class AccountLedger:
    account_id: str
    account_code: str
    account_name: str
    opening_balance: Decimal
    closing_balance: Decimal
    lines: list[LedgerLineView] = field(default_factory=list)


@dataclass
class TrialBalanceRow:
    account_id: str
    account_code: str
    account_name: str
    account_type: str
    debit: Decimal
    credit: Decimal


def get_account_ledger(
    db: Session,
    *,
    business_id: str,
    account_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> AccountLedger:
    account = db.get(Account, account_id)
    if account is None or account.business_id != business_id:
        raise ValueError("Account not found for this business.")

    normal_side = NORMAL_BALANCE[account.account_type]

    query = (
        db.query(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .filter(
            JournalLine.account_id == account_id,
            JournalEntry.business_id == business_id,
            JournalEntry.status != "Draft",
        )
    )

    opening_balance = zero()
    if date_from is not None:
        opening_query = query.filter(JournalEntry.entry_date < date_from)
        for line, _ in opening_query.all():
            delta = line.debit - line.credit if normal_side == "debit" else line.credit - line.debit
            opening_balance += delta
        query = query.filter(JournalEntry.entry_date >= date_from)

    if date_to is not None:
        query = query.filter(JournalEntry.entry_date <= date_to)

    rows = query.order_by(JournalEntry.entry_date, JournalEntry.created_at).all()

    running = opening_balance
    lines: list[LedgerLineView] = []
    for line, entry in rows:
        delta = line.debit - line.credit if normal_side == "debit" else line.credit - line.debit
        running += delta
        lines.append(
            LedgerLineView(
                entry_date=entry.entry_date,
                journal_entry_id=entry.id,
                reference=entry.reference,
                memo=entry.memo,
                description=line.description,
                debit=line.debit,
                credit=line.credit,
                running_balance=running,
            )
        )

    return AccountLedger(
        account_id=account.id,
        account_code=account.code,
        account_name=account.name,
        opening_balance=opening_balance,
        closing_balance=running,
        lines=lines,
    )


def get_trial_balance(
    db: Session,
    *,
    business_id: str,
    as_of_date: date | None = None,
) -> list[TrialBalanceRow]:
    """
    Returns one row per account with a non-zero balance, expressed as
    a debit or credit per the account's normal balance side, as of the
    given date (or all posted history if no date given).
    """
    accounts = db.query(Account).filter(Account.business_id == business_id).all()

    rows: list[TrialBalanceRow] = []
    for account in accounts:
        query = (
            db.query(JournalLine)
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .filter(
                JournalLine.account_id == account.id,
                JournalEntry.business_id == business_id,
                JournalEntry.status != "Draft",
            )
        )
        if as_of_date is not None:
            query = query.filter(JournalEntry.entry_date <= as_of_date)

        total_debit = zero()
        total_credit = zero()
        for line in query.all():
            total_debit += line.debit
            total_credit += line.credit

        net = total_debit - total_credit
        if net == 0:
            continue

        # Report the raw net in whichever column it actually falls on --
        # a positive net (debits > credits) goes in the debit column, a
        # negative net goes in the credit column, regardless of the
        # account's normal side. An account sitting on its abnormal side
        # (e.g. a liability with a debit balance) is still shown
        # correctly rather than hidden.
        debit_balance = net if net > 0 else zero()
        credit_balance = -net if net < 0 else zero()

        rows.append(
            TrialBalanceRow(
                account_id=account.id,
                account_code=account.code,
                account_name=account.name,
                account_type=account.account_type,
                debit=debit_balance,
                credit=credit_balance,
            )
        )

    rows.sort(key=lambda r: r.account_code)
    return rows


def get_period_activity(
    db: Session,
    *,
    business_id: str,
    date_from: date,
    date_to: date,
) -> list[TrialBalanceRow]:
    """
    Like get_trial_balance, but restricted to activity WITHIN
    [date_from, date_to] rather than cumulative since inception.
    Needed for the Income Statement (Phase 10): revenue and expense
    accounts are never closed to equity in this system (there's no
    period-close step), so a plain trial balance as-of a date shows
    cumulative-since-inception revenue/expense, not just the current
    period's. This function isolates just the period's movement.
    """
    accounts = db.query(Account).filter(Account.business_id == business_id).all()

    rows: list[TrialBalanceRow] = []
    for account in accounts:
        lines = (
            db.query(JournalLine)
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .filter(
                JournalLine.account_id == account.id,
                JournalEntry.business_id == business_id,
                JournalEntry.status != "Draft",
                JournalEntry.entry_date >= date_from,
                JournalEntry.entry_date <= date_to,
            )
            .all()
        )

        total_debit = zero()
        total_credit = zero()
        for line in lines:
            total_debit += line.debit
            total_credit += line.credit

        net = total_debit - total_credit
        if net == 0:
            continue

        debit_balance = net if net > 0 else zero()
        credit_balance = -net if net < 0 else zero()

        rows.append(
            TrialBalanceRow(
                account_id=account.id,
                account_code=account.code,
                account_name=account.name,
                account_type=account.account_type,
                debit=debit_balance,
                credit=credit_balance,
            )
        )

    rows.sort(key=lambda r: r.account_code)
    return rows
