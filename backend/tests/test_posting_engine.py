"""
Unit tests for the posting engine -- exercised directly against the
domain layer (not through HTTP) so these test accounting correctness
in isolation from the API.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.accounting.engine.posting import LineInput, PostingError, post_journal_entry, reverse_entry
from app.accounting.ledger.queries import get_trial_balance
from app.models.account import Account
from app.models.business import Business
from app.models.period import AccountingPeriod, FiscalYear


@pytest.fixture()
def business_with_period(db_session):
    business = Business(registered_name="Test Co")
    db_session.add(business)
    db_session.flush()

    fiscal_year = FiscalYear(
        business_id=business.id, name="FY2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
    )
    db_session.add(fiscal_year)
    db_session.flush()

    period = AccountingPeriod(
        business_id=business.id,
        fiscal_year_id=fiscal_year.id,
        name="2026-01",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    db_session.add(period)

    cash = Account(business_id=business.id, code="1000", name="Cash", account_type="Asset")
    revenue = Account(business_id=business.id, code="4000", name="Sales Revenue", account_type="Revenue")
    db_session.add_all([cash, revenue])
    db_session.commit()

    return business, period, cash, revenue


def test_balanced_entry_posts_successfully(db_session, business_with_period):
    business, period, cash, revenue = business_with_period

    entry = post_journal_entry(
        db_session,
        business_id=business.id,
        entry_date=date(2026, 1, 15),
        lines=[
            LineInput(account_id=cash.id, debit=Decimal("1000.00")),
            LineInput(account_id=revenue.id, credit=Decimal("1000.00")),
        ],
        memo="Cash sale",
    )

    assert entry.status == "Posted"
    assert entry.total_debits() == entry.total_credits() == Decimal("1000.00")


def test_unbalanced_entry_is_rejected(db_session, business_with_period):
    business, period, cash, revenue = business_with_period

    with pytest.raises(PostingError, match="not balanced"):
        post_journal_entry(
            db_session,
            business_id=business.id,
            entry_date=date(2026, 1, 15),
            lines=[
                LineInput(account_id=cash.id, debit=Decimal("1000.00")),
                LineInput(account_id=revenue.id, credit=Decimal("900.00")),
            ],
        )


def test_line_with_both_debit_and_credit_rejected(db_session, business_with_period):
    business, period, cash, revenue = business_with_period

    with pytest.raises(PostingError, match="both a debit and a credit"):
        post_journal_entry(
            db_session,
            business_id=business.id,
            entry_date=date(2026, 1, 15),
            lines=[
                LineInput(account_id=cash.id, debit=Decimal("100.00"), credit=Decimal("50.00")),
                LineInput(account_id=revenue.id, credit=Decimal("50.00")),
            ],
        )


def test_posting_into_closed_period_rejected(db_session, business_with_period):
    business, period, cash, revenue = business_with_period
    period.status = "Closed"
    db_session.commit()

    with pytest.raises(PostingError, match="Closed"):
        post_journal_entry(
            db_session,
            business_id=business.id,
            entry_date=date(2026, 1, 15),
            lines=[
                LineInput(account_id=cash.id, debit=Decimal("100.00")),
                LineInput(account_id=revenue.id, credit=Decimal("100.00")),
            ],
        )


def test_posting_with_no_covering_period_rejected(db_session, business_with_period):
    business, period, cash, revenue = business_with_period

    with pytest.raises(PostingError, match="No accounting period"):
        post_journal_entry(
            db_session,
            business_id=business.id,
            entry_date=date(2027, 6, 1),
            lines=[
                LineInput(account_id=cash.id, debit=Decimal("100.00")),
                LineInput(account_id=revenue.id, credit=Decimal("100.00")),
            ],
        )


def test_trial_balance_stays_balanced_after_multiple_postings(db_session, business_with_period):
    business, period, cash, revenue = business_with_period

    post_journal_entry(
        db_session,
        business_id=business.id,
        entry_date=date(2026, 1, 10),
        lines=[
            LineInput(account_id=cash.id, debit=Decimal("500.00")),
            LineInput(account_id=revenue.id, credit=Decimal("500.00")),
        ],
    )
    post_journal_entry(
        db_session,
        business_id=business.id,
        entry_date=date(2026, 1, 20),
        lines=[
            LineInput(account_id=cash.id, debit=Decimal("250.00")),
            LineInput(account_id=revenue.id, credit=Decimal("250.00")),
        ],
    )

    tb = get_trial_balance(db_session, business_id=business.id)
    total_debit = sum((r.debit for r in tb), Decimal("0.00"))
    total_credit = sum((r.credit for r in tb), Decimal("0.00"))

    assert total_debit == total_credit == Decimal("750.00")


def test_reversal_flips_lines_and_marks_original_reversed(db_session, business_with_period):
    business, period, cash, revenue = business_with_period

    entry = post_journal_entry(
        db_session,
        business_id=business.id,
        entry_date=date(2026, 1, 10),
        lines=[
            LineInput(account_id=cash.id, debit=Decimal("300.00")),
            LineInput(account_id=revenue.id, credit=Decimal("300.00")),
        ],
    )

    reversal = reverse_entry(db_session, original_entry=entry, reversal_date=date(2026, 1, 11))

    assert entry.status == "Reversed"
    assert reversal.status == "Posted"

    # After the reversal, the net effect on the trial balance is zero.
    tb = get_trial_balance(db_session, business_id=business.id)
    assert tb == []
