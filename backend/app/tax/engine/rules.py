"""
Tax rule lookup.

Finds the tax rule that was in force for a given business, rule code,
and transaction date. Business-specific rules override global (system
default) rules with the same rule_code. This is the only place that
decides "which rate applies" -- calculation (tax_engine.py) and
posting never re-derive it themselves.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.tax_rule import TaxRule


class TaxRuleNotFoundError(Exception):
    """Raised when no active rule covers the given rule_code and date."""


def find_effective_rule(
    db: Session,
    *,
    business_id: str,
    rule_code: str,
    as_of_date: date,
) -> TaxRule:
    """
    Look up the rule in force for `rule_code` on `as_of_date`.

    Precedence: a business-specific rule (business_id matches) is
    preferred over a global default rule (business_id is NULL) when
    both would otherwise apply -- a business can override a system
    default without changing it for everyone else.
    """
    base_query = (
        db.query(TaxRule)
        .filter(
            TaxRule.rule_code == rule_code,
            TaxRule.status == "Active",
            TaxRule.effective_from <= as_of_date,
        )
        .filter((TaxRule.effective_to.is_(None)) | (TaxRule.effective_to >= as_of_date))
    )

    business_rule = base_query.filter(TaxRule.business_id == business_id).first()
    if business_rule is not None:
        return business_rule

    global_rule = base_query.filter(TaxRule.business_id.is_(None)).first()
    if global_rule is not None:
        return global_rule

    raise TaxRuleNotFoundError(
        f"No active tax rule '{rule_code}' covers {as_of_date.isoformat()} "
        f"for this business or as a system default."
    )
