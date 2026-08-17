from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FixedAssetCreate(BaseModel):
    asset_code: str
    name: str
    acquisition_date: date
    acquisition_cost: Decimal
    salvage_value: Decimal = Decimal("0.00")
    useful_life_months: int
    asset_account_id: str
    accumulated_depreciation_account_id: str
    depreciation_expense_account_id: str


class FixedAssetUpdate(BaseModel):
    """
    Only asset_code and name are editable. acquisition_cost,
    salvage_value, useful_life_months, and acquisition_date all feed
    the depreciation schedule (app/reports/... depreciation logic) --
    changing them after depreciation entries have already been posted
    would desync the schedule from the ledger, so those stay locked
    once created.
    """

    asset_code: str | None = None
    name: str | None = None


class FixedAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_code: str
    name: str
    acquisition_date: date
    acquisition_cost: Decimal
    salvage_value: Decimal
    useful_life_months: int
    asset_account_id: str
    accumulated_depreciation_account_id: str
    depreciation_expense_account_id: str
    accumulated_depreciation: Decimal
    status: str


class DepreciationScheduleRowRead(BaseModel):
    period_year: int
    period_month: int
    depreciation_amount: Decimal
    accumulated_depreciation_after: Decimal
    book_value_after: Decimal


class DepreciationPostRequest(BaseModel):
    period_year: int
    period_month: int
    entry_date: date


class DepreciationEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    journal_entry_id: str
    period_year: int
    period_month: int
    entry_date: date
    depreciation_amount: Decimal
    accumulated_depreciation_after: Decimal
    book_value_after: Decimal
