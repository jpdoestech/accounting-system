"""
Fixed asset depreciation service.

Straight-line depreciation: monthly amount = (acquisition_cost -
salvage_value) / useful_life_months, held constant for the asset's
life except the final month, which is capped so accumulated
depreciation never exceeds (acquisition_cost - salvage_value) --
avoiding the classic off-by-a-few-centavos overshoot from rounding
every month independently.

Composes the accounting engine (app/accounting/engine/posting.py) --
this is the only code path allowed to post a depreciation entry's
JournalEntry. A DepreciationEntry uniqueness constraint
(asset_id, period_year, period_month) prevents double-posting the
same asset/period, enforced here with a clear error before the
accounting engine is even called.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounting.engine.posting import LineInput, PostingError, post_journal_entry
from app.models.depreciation_entry import DepreciationEntry
from app.models.fixed_asset import FixedAsset
from app.utils.money import to_money, zero


class FixedAssetError(Exception):
    """Raised when a fixed asset cannot be created or depreciated."""


@dataclass
class DepreciationScheduleRow:
    period_year: int
    period_month: int
    depreciation_amount: Decimal
    accumulated_depreciation_after: Decimal
    book_value_after: Decimal


def monthly_depreciation_amount(asset: FixedAsset) -> Decimal:
    depreciable_base = asset.acquisition_cost - asset.salvage_value
    if asset.useful_life_months <= 0 or depreciable_base <= 0:
        return zero()
    return to_money(depreciable_base / asset.useful_life_months)


def preview_depreciation_schedule(asset: FixedAsset) -> list[DepreciationScheduleRow]:
    """
    Computes the full straight-line schedule from acquisition without
    posting anything -- useful for showing a bookkeeper what will
    happen before any entries exist.
    """
    monthly_amount = monthly_depreciation_amount(asset)
    depreciable_base = to_money(asset.acquisition_cost - asset.salvage_value)

    schedule: list[DepreciationScheduleRow] = []
    accumulated = zero()
    year, month = asset.acquisition_date.year, asset.acquisition_date.month

    for i in range(asset.useful_life_months):
        month += 1
        if month > 12:
            month = 1
            year += 1

        remaining = depreciable_base - accumulated
        amount = monthly_amount if remaining > monthly_amount else remaining
        accumulated = to_money(accumulated + amount)
        book_value = to_money(asset.acquisition_cost - accumulated)

        schedule.append(
            DepreciationScheduleRow(
                period_year=year,
                period_month=month,
                depreciation_amount=amount,
                accumulated_depreciation_after=accumulated,
                book_value_after=book_value,
            )
        )

    return schedule


def post_monthly_depreciation(
    db: Session,
    *,
    asset: FixedAsset,
    period_year: int,
    period_month: int,
    entry_date: date,
    created_by_user_id: str | None = None,
) -> DepreciationEntry:
    if asset.status != "Active":
        raise FixedAssetError(f"Asset '{asset.name}' is {asset.status}; cannot post further depreciation.")

    existing = (
        db.query(DepreciationEntry)
        .filter(
            DepreciationEntry.asset_id == asset.id,
            DepreciationEntry.period_year == period_year,
            DepreciationEntry.period_month == period_month,
        )
        .first()
    )
    if existing:
        raise FixedAssetError(
            f"Depreciation for {period_year}-{period_month:02d} has already been posted for this asset."
        )

    depreciable_base = to_money(asset.acquisition_cost - asset.salvage_value)
    remaining = depreciable_base - asset.accumulated_depreciation
    if remaining <= 0:
        raise FixedAssetError(f"Asset '{asset.name}' is already fully depreciated.")

    monthly_amount = monthly_depreciation_amount(asset)
    amount = monthly_amount if remaining > monthly_amount else remaining

    try:
        entry = post_journal_entry(
            db,
            business_id=asset.business_id,
            entry_date=entry_date,
            lines=[
                LineInput(account_id=asset.depreciation_expense_account_id, debit=amount),
                LineInput(account_id=asset.accumulated_depreciation_account_id, credit=amount),
            ],
            reference=asset.asset_code,
            memo=f"Depreciation — {asset.name} — {period_year}-{period_month:02d}",
            source="Depreciation",
            created_by_user_id=created_by_user_id,
        )
    except PostingError as exc:
        raise FixedAssetError(str(exc))

    asset.accumulated_depreciation = to_money(asset.accumulated_depreciation + amount)
    if asset.accumulated_depreciation >= depreciable_base:
        asset.status = "Fully Depreciated"

    depreciation_entry = DepreciationEntry(
        business_id=asset.business_id,
        asset_id=asset.id,
        journal_entry_id=entry.id,
        period_year=period_year,
        period_month=period_month,
        entry_date=entry_date,
        depreciation_amount=amount,
        accumulated_depreciation_after=asset.accumulated_depreciation,
        book_value_after=to_money(asset.acquisition_cost - asset.accumulated_depreciation),
    )
    db.add(depreciation_entry)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise FixedAssetError(
            f"Depreciation for {period_year}-{period_month:02d} has already been posted for this asset."
        )

    db.refresh(depreciation_entry)
    return depreciation_entry
