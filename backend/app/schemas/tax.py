from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.tax_rule import TAX_TYPES


class TaxRuleCreate(BaseModel):
    rule_code: str
    name: str
    tax_type: str
    atc_code: str | None = None
    rate_percent: Decimal
    effective_from: date
    effective_to: date | None = None
    legal_basis: str | None = None
    source_reference: str | None = None

    @field_validator("tax_type")
    @classmethod
    def validate_tax_type(cls, v: str) -> str:
        if v not in TAX_TYPES:
            raise ValueError(f"tax_type must be one of {TAX_TYPES}")
        return v


class TaxRuleUpdate(BaseModel):
    """
    rule_code, tax_type, and effective_from are excluded: invoice and
    bill lines reference a rule by its code (tax_rule_code), and the
    effective date range is what makes a rule the *correct* one for a
    transaction's date. Everything else -- name, rate, ATC code,
    end date, citations -- is safe to correct after the fact, since a
    posted line's tax_amount is already a fixed snapshot and doesn't
    get recalculated from the rule.
    """

    name: str | None = None
    atc_code: str | None = None
    rate_percent: Decimal | None = None
    effective_to: date | None = None
    legal_basis: str | None = None
    source_reference: str | None = None


class TaxRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str | None
    rule_code: str
    name: str
    tax_type: str
    atc_code: str | None
    rate_percent: Decimal
    effective_from: date
    effective_to: date | None
    status: str
    legal_basis: str | None
    source_reference: str | None


class TaxCalculationRequest(BaseModel):
    rule_code: str
    taxable_amount: Decimal
    as_of_date: date


class TaxCalculationResponse(BaseModel):
    rule_code: str
    rule_name: str
    tax_type: str
    rate_percent: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    rule_id: str
    atc_code: str | None = None
