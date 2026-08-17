"""
Money handling utilities.

Spec Section 129: "Never use floating point for money." All monetary
values in this system are Python Decimal, backed by SQLAlchemy
Numeric/DECIMAL columns -- never float.
"""
from decimal import Decimal, ROUND_HALF_UP

MONEY_DECIMAL_PLACES = 2
MONEY_QUANTIZE = Decimal(10) ** -MONEY_DECIMAL_PLACES


def to_money(value) -> Decimal:
    """Coerce any numeric input into a properly quantized Decimal amount."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)


def zero() -> Decimal:
    return Decimal("0.00")
