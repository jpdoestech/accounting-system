"""
Posting engine.

This is the ONLY code path allowed to create a JournalEntry (spec
Section 9: "Never allow the frontend to directly manipulate accounting
balances. All accounting posting must go through the accounting/domain
layer."). The API layer calls into this module; it never constructs
JournalEntry/JournalLine rows itself.

Enforces:
- Total debits == total credits (rejects unbalanced entries).
- Each line has exactly one of debit/credit non-zero and non-negative.
- The entry date falls inside an Open accounting period (Section 117 --
  never silently post into a closed period).
- Posted entries are immutable: correcting one means posting a
  reversing entry (see reverse_entry), never editing lines in place.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.journal import JournalEntry, JournalLine
from app.models.period import AccountingPeriod
from app.utils.money import to_money, zero


class PostingError(Exception):
    """Raised when a proposed journal entry violates accounting rules."""


@dataclass
class LineInput:
    account_id: str
    debit: Decimal | float | str = Decimal("0.00")
    credit: Decimal | float | str = Decimal("0.00")
    description: str | None = None


def _find_open_period(db: Session, business_id: str, entry_date: date) -> AccountingPeriod:
    period = (
        db.query(AccountingPeriod)
        .filter(
            AccountingPeriod.business_id == business_id,
            AccountingPeriod.start_date <= entry_date,
            AccountingPeriod.end_date >= entry_date,
        )
        .first()
    )
    if period is None:
        raise PostingError(f"No accounting period covers {entry_date.isoformat()}.")
    if period.status != "Open":
        raise PostingError(
            f"Period '{period.name}' is {period.status}; cannot post into a closed/locked period."
        )
    return period


def _validate_lines(db: Session, business_id: str, lines: list[LineInput]) -> list[LineInput]:
    if len(lines) < 2:
        raise PostingError("A journal entry needs at least two lines.")

    total_debit = zero()
    total_credit = zero()

    for line in lines:
        debit = to_money(line.debit)
        credit = to_money(line.credit)
        line.debit = debit
        line.credit = credit

        if debit < 0 or credit < 0:
            raise PostingError("Debit/credit amounts cannot be negative.")
        if debit > 0 and credit > 0:
            raise PostingError("A journal line cannot have both a debit and a credit amount.")
        if debit == 0 and credit == 0:
            raise PostingError("A journal line must have a non-zero debit or credit.")

        account = db.get(Account, line.account_id)
        if account is None or account.business_id != business_id:
            raise PostingError(f"Account {line.account_id} does not belong to this business.")
        if not account.is_active:
            raise PostingError(f"Account '{account.name}' is inactive and cannot be posted to.")

        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise PostingError(
            f"Journal entry is not balanced: total debits {total_debit} != total credits {total_credit}."
        )
    if total_debit == 0:
        raise PostingError("Journal entry has a zero total; nothing to post.")

    return lines


def post_journal_entry(
    db: Session,
    *,
    business_id: str,
    entry_date: date,
    lines: list[LineInput],
    reference: str | None = None,
    memo: str | None = None,
    source: str = "Manual",
    created_by_user_id: str | None = None,
) -> JournalEntry:
    """
    Validate and post a balanced journal entry. Raises PostingError on
    any rule violation -- callers (API routes) should translate that
    into an HTTP 400/422, never swallow it.
    """
    period = _find_open_period(db, business_id, entry_date)
    validated_lines = _validate_lines(db, business_id, lines)

    entry = JournalEntry(
        business_id=business_id,
        period_id=period.id,
        entry_date=entry_date,
        reference=reference,
        memo=memo,
        source=source,
        status="Posted",
        created_by_user_id=created_by_user_id,
    )
    db.add(entry)
    db.flush()

    for i, line in enumerate(validated_lines, start=1):
        db.add(
            JournalLine(
                journal_entry_id=entry.id,
                account_id=line.account_id,
                line_number=i,
                description=line.description,
                debit=line.debit,
                credit=line.credit,
            )
        )

    db.commit()
    db.refresh(entry)
    return entry


def reverse_entry(
    db: Session,
    *,
    original_entry: JournalEntry,
    reversal_date: date,
    memo: str | None = None,
    created_by_user_id: str | None = None,
) -> JournalEntry:
    """
    Post a reversing entry that flips every line's debit/credit.
    This is how a posted entry is "corrected" -- the original is never
    edited or deleted (Section 117: no silent changes to posted data).
    """
    if original_entry.status == "Reversed":
        raise PostingError("This journal entry has already been reversed.")

    reversal_lines = [
        LineInput(
            account_id=line.account_id,
            debit=line.credit,
            credit=line.debit,
            description=f"Reversal of entry {original_entry.id}: {line.description or ''}".strip(),
        )
        for line in original_entry.lines
    ]

    reversal = post_journal_entry(
        db,
        business_id=original_entry.business_id,
        entry_date=reversal_date,
        lines=reversal_lines,
        reference=original_entry.reference,
        memo=memo or f"Reversal of entry {original_entry.id}",
        source="Reversal",
        created_by_user_id=created_by_user_id,
    )

    original_entry.status = "Reversed"
    db.commit()
    return reversal
