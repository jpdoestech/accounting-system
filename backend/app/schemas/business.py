from pydantic import BaseModel, ConfigDict


class BusinessCreate(BaseModel):
    registered_name: str
    business_name: str | None = None
    tin: str | None = None
    branch_code: str | None = None
    rdo_code: str | None = None
    registered_address: str | None = None
    zip_code: str | None = None
    telephone: str | None = None
    email: str | None = None
    line_of_business: str | None = None
    taxpayer_classification: str | None = None
    vat_registration_status: str | None = None
    taxpayer_type: str | None = None
    fiscal_year_start_month: int = 1
    currency_code: str = "PHP"


class BusinessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    registered_name: str
    business_name: str | None = None
    tin: str | None = None
    vat_registration_status: str | None = None
    currency_code: str
    is_active: bool


class BusinessSettingsUpdate(BaseModel):
    decimal_precision: int | None = None
    default_currency_code: str | None = None
    invoice_number_prefix: str | None = None
    default_payment_terms_days: int | None = None
    ar_account_id: str | None = None
    output_vat_account_id: str | None = None
    ap_account_id: str | None = None
    input_vat_account_id: str | None = None
    withholding_tax_payable_account_id: str | None = None


class BusinessSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: str
    decimal_precision: int
    default_currency_code: str
    invoice_number_prefix: str | None = None
    default_payment_terms_days: int
    ar_account_id: str | None = None
    output_vat_account_id: str | None = None
    ap_account_id: str | None = None
    input_vat_account_id: str | None = None
    withholding_tax_payable_account_id: str | None = None
