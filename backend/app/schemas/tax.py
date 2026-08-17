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
