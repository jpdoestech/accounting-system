from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.account import ACCOUNT_TYPES


class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str
    parent_id: str | None = None
    description: str | None = None
    default_tax_treatment: str | None = None

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        if v not in ACCOUNT_TYPES:
            raise ValueError(f"account_type must be one of {ACCOUNT_TYPES}")
        return v


class AccountUpdate(BaseModel):
    """
    Deliberately narrower than AccountCreate: code and account_type are
    excluded because journal lines and financial-statement grouping key
    off them, so changing either after the account has postings would
    silently reclassify historical transactions. Renaming, adding a
    description, or toggling is_active never touches the ledger.
    """

    name: str | None = None
    description: str | None = None
    default_tax_treatment: str | None = None
    is_active: bool | None = None


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    account_type: str
    parent_id: str | None = None
    description: str | None = None
    is_active: bool
    is_system_account: bool
    is_control_account: bool


class FiscalYearCreate(BaseModel):
    name: str
    start_date: date
    end_date: date


class FiscalYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    start_date: date
    end_date: date
    status: str


class AccountingPeriodCreate(BaseModel):
    fiscal_year_id: str
    name: str
    start_date: date
    end_date: date


class AccountingPeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fiscal_year_id: str
    name: str
    start_date: date
    end_date: date
    status: str


class JournalLineInput(BaseModel):
    account_id: str
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    description: str | None = None


class JournalEntryCreate(BaseModel):
    entry_date: date
    reference: str | None = None
    memo: str | None = None
    lines: list[JournalLineInput]


class JournalLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    line_number: int
    description: str | None = None
    debit: Decimal
    credit: Decimal


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    period_id: str
    entry_date: date
    reference: str | None = None
    memo: str | None = None
    source: str
    status: str
    lines: list[JournalLineRead]


class LedgerLineRead(BaseModel):
    entry_date: date
    journal_entry_id: str
    reference: str | None = None
    memo: str | None = None
    description: str | None = None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class AccountLedgerRead(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    opening_balance: Decimal
    closing_balance: Decimal
    lines: list[LedgerLineRead]


class TrialBalanceRowRead(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    account_type: str
    debit: Decimal
    credit: Decimal
