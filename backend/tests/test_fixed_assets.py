"""
Domain-layer tests for Phase 9: straight-line depreciation scheduling
and monthly posting.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.accounting.ledger.queries import get_trial_balance
from app.models.account import Account
from app.models.business import Business
from app.models.fixed_asset import FixedAsset
from app.models.period import AccountingPeriod, FiscalYear
from app.services.fixed_assets import (
    FixedAssetError,
    monthly_depreciation_amount,
    post_monthly_depreciation,
    preview_depreciation_schedule,
)


@pytest.fixture()
def asset_fixture(db_session):
    business = Business(registered_name="Fixed Asset Test Co")
    db_session.add(business)
    db_session.flush()

    fiscal_year = FiscalYear(
        business_id=business.id, name="FY2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
    )
    db_session.add(fiscal_year)
    db_session.flush()

    # Create periods for the months we'll test depreciation across.
    for month, (start, end) in enumerate(
        [
            (date(2026, 1, 1), date(2026, 1, 31)),
            (date(2026, 2, 1), date(2026, 2, 28)),
            (date(2026, 3, 1), date(2026, 3, 31)),
        ],
        start=1,
    ):
        db_session.add(
            AccountingPeriod(
                business_id=business.id,
                fiscal_year_id=fiscal_year.id,
                name=f"2026-{month:02d}",
                start_date=start,
                end_date=end,
            )
        )

    asset_account = Account(business_id=business.id, code="1500", name="Office Equipment", account_type="Asset")
    accum_dep = Account(
        business_id=business.id, code="1510", name="Accumulated Depreciation", account_type="Asset"
    )
    dep_expense = Account(
        business_id=business.id, code="6100", name="Depreciation Expense", account_type="Expense"
    )
    db_session.add_all([asset_account, accum_dep, dep_expense])
    db_session.flush()

    asset = FixedAsset(
        business_id=business.id,
        asset_account_id=asset_account.id,
        accumulated_depreciation_account_id=accum_dep.id,
        depreciation_expense_account_id=dep_expense.id,
        asset_code="FA-0001",
        name="Laptop",
        acquisition_date=date(2026, 1, 1),
        acquisition_cost=Decimal("36000.00"),
        salvage_value=Decimal("0.00"),
        useful_life_months=36,
    )
    db_session.add(asset)
    db_session.commit()

    return {"business": business, "asset": asset, "accum_dep": accum_dep, "dep_expense": dep_expense}


def test_monthly_depreciation_amount_is_straight_line(db_session, asset_fixture):
    amount = monthly_depreciation_amount(asset_fixture["asset"])
    assert amount == Decimal("1000.00")  # 36000 / 36


def test_schedule_preview_has_correct_length_and_final_book_value(db_session, asset_fixture):
    schedule = preview_depreciation_schedule(asset_fixture["asset"])
    assert len(schedule) == 36
    assert schedule[0].period_year == 2026
    assert schedule[0].period_month == 2  # first depreciation the month AFTER acquisition
    assert schedule[-1].accumulated_depreciation_after == Decimal("36000.00")
    assert schedule[-1].book_value_after == Decimal("0.00")


def test_posting_depreciation_creates_balanced_entry(db_session, asset_fixture):
    entry = post_monthly_depreciation(
        db_session,
        asset=asset_fixture["asset"],
        period_year=2026,
        period_month=1,
        entry_date=date(2026, 1, 31),
    )

    assert entry.depreciation_amount == Decimal("1000.00")
    assert entry.accumulated_depreciation_after == Decimal("1000.00")
    assert entry.book_value_after == Decimal("35000.00")

    tb = get_trial_balance(db_session, business_id=asset_fixture["business"].id)
    by_code = {row.account_code: row for row in tb}
    assert by_code["6100"].debit == Decimal("1000.00")
    assert by_code["1510"].credit == Decimal("1000.00")


def test_cannot_double_post_same_asset_period(db_session, asset_fixture):
    post_monthly_depreciation(
        db_session, asset=asset_fixture["asset"], period_year=2026, period_month=1, entry_date=date(2026, 1, 31)
    )

    with pytest.raises(FixedAssetError, match="already been posted"):
        post_monthly_depreciation(
            db_session, asset=asset_fixture["asset"], period_year=2026, period_month=1, entry_date=date(2026, 1, 31)
        )


def test_accumulated_depreciation_updates_across_months(db_session, asset_fixture):
    post_monthly_depreciation(
        db_session, asset=asset_fixture["asset"], period_year=2026, period_month=1, entry_date=date(2026, 1, 31)
    )
    post_monthly_depreciation(
        db_session, asset=asset_fixture["asset"], period_year=2026, period_month=2, entry_date=date(2026, 2, 28)
    )

    db_session.refresh(asset_fixture["asset"])
    assert asset_fixture["asset"].accumulated_depreciation == Decimal("2000.00")
    assert asset_fixture["asset"].status == "Active"

    tb = get_trial_balance(db_session, business_id=asset_fixture["business"].id)
    by_code = {row.account_code: row for row in tb}
    assert by_code["1510"].credit == Decimal("2000.00")
    assert by_code["6100"].debit == Decimal("2000.00")
