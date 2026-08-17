"""
Domain-layer tests for Phase 8: inventory receiving on purchase,
moving-average costing, COGS posting on sale, and stock adjustments.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.accounting.ledger.queries import get_trial_balance
from app.models.account import Account
from app.models.business import Business, BusinessSettings
from app.models.customer import Customer
from app.models.inventory_item import InventoryItem
from app.models.period import AccountingPeriod, FiscalYear
from app.models.vendor import Vendor
from app.services.inventory import InventoryError, issue_stock, receive_stock
from app.services.purchases import BillLineInput, create_draft_bill, post_bill
from app.services.sales import InvoiceLineInput, SalesPostingError, create_draft_invoice
from app.services.sales import post_invoice as post_sales_invoice


@pytest.fixture()
def inventory_fixture(db_session):
    business = Business(registered_name="Inventory Test Co")
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
        name="2026-08",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
    )
    db_session.add(period)

    ar = Account(business_id=business.id, code="1200", name="Accounts Receivable", account_type="Asset")
    ap = Account(business_id=business.id, code="2000", name="Accounts Payable", account_type="Liability")
    revenue = Account(business_id=business.id, code="4000", name="Sales Revenue", account_type="Revenue")
    inventory_asset = Account(business_id=business.id, code="1300", name="Merchandise Inventory", account_type="Asset")
    cogs = Account(business_id=business.id, code="5000", name="Cost of Goods Sold", account_type="Cost of Sales")
    db_session.add_all([ar, ap, revenue, inventory_asset, cogs])
    db_session.flush()

    settings = BusinessSettings(business_id=business.id, ar_account_id=ar.id, ap_account_id=ap.id)
    db_session.add(settings)

    customer = Customer(business_id=business.id, name="Juan Dela Cruz")
    vendor = Vendor(business_id=business.id, name="Wholesale Supplier Inc")
    db_session.add_all([customer, vendor])
    db_session.flush()

    item = InventoryItem(
        business_id=business.id,
        sku="WIDGET-001",
        name="Widget",
        inventory_account_id=inventory_asset.id,
        cogs_account_id=cogs.id,
    )
    db_session.add(item)
    db_session.commit()

    return {
        "business": business,
        "revenue": revenue,
        "inventory_asset": inventory_asset,
        "cogs": cogs,
        "customer": customer,
        "vendor": vendor,
        "item": item,
    }


def test_purchase_receives_stock_and_sets_moving_average(db_session, inventory_fixture):
    fx = inventory_fixture

    bill = create_draft_bill(
        db_session,
        business_id=fx["business"].id,
        vendor_id=fx["vendor"].id,
        bill_number="OR-1001",
        bill_date=date(2026, 8, 5),
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=fx["inventory_asset"].id,  # unused when item_id is set
                description="Widget purchase",
                quantity=Decimal("100"),
                unit_price=Decimal("10.00"),
                item_id=fx["item"].id,
            )
        ],
    )
    post_bill(db_session, bill=bill)

    db_session.refresh(fx["item"])
    assert fx["item"].quantity_on_hand == Decimal("100.0000")
    assert fx["item"].average_cost == Decimal("10.0000")

    # Journal entry debited Inventory Asset, not a plain expense account.
    tb = get_trial_balance(db_session, business_id=fx["business"].id)
    by_code = {row.account_code: row for row in tb}
    assert by_code["1300"].debit == Decimal("1000.00")
    assert "5000" not in by_code  # nothing sold yet, so no COGS


def test_second_purchase_recalculates_weighted_average(db_session, inventory_fixture):
    fx = inventory_fixture

    for qty, price in [(Decimal("100"), Decimal("10.00")), (Decimal("50"), Decimal("13.00"))]:
        bill = create_draft_bill(
            db_session,
            business_id=fx["business"].id,
            vendor_id=fx["vendor"].id,
            bill_number=f"OR-{price}",
            bill_date=date(2026, 8, 5),
            due_date=None,
            lines=[
                BillLineInput(
                    expense_account_id=fx["inventory_asset"].id,
                    description="Widget purchase",
                    quantity=qty,
                    unit_price=price,
                    item_id=fx["item"].id,
                )
            ],
        )
        post_bill(db_session, bill=bill)

    db_session.refresh(fx["item"])
    # (100*10 + 50*13) / 150 = 1650/150 = 11.00
    assert fx["item"].quantity_on_hand == Decimal("150.0000")
    assert fx["item"].average_cost == Decimal("11.0000")


def test_sale_issues_stock_and_posts_cogs_in_same_entry(db_session, inventory_fixture):
    fx = inventory_fixture

    bill = create_draft_bill(
        db_session,
        business_id=fx["business"].id,
        vendor_id=fx["vendor"].id,
        bill_number="OR-1001",
        bill_date=date(2026, 8, 5),
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=fx["inventory_asset"].id,
                description="Widget purchase",
                quantity=Decimal("100"),
                unit_price=Decimal("10.00"),
                item_id=fx["item"].id,
            )
        ],
    )
    post_bill(db_session, bill=bill)

    invoice = create_draft_invoice(
        db_session,
        business_id=fx["business"].id,
        customer_id=fx["customer"].id,
        invoice_number="INV-0001",
        invoice_date=date(2026, 8, 10),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=fx["revenue"].id,
                description="Widget sale",
                quantity=Decimal("30"),
                unit_price=Decimal("25.00"),  # sale price, unrelated to cost
                item_id=fx["item"].id,
            )
        ],
    )
    posted = post_sales_invoice(db_session, invoice=invoice)
    assert posted.status == "Posted"

    db_session.refresh(fx["item"])
    assert fx["item"].quantity_on_hand == Decimal("70.0000")
    assert fx["item"].average_cost == Decimal("10.0000")  # unchanged by an issue

    tb = get_trial_balance(db_session, business_id=fx["business"].id)
    by_code = {row.account_code: row for row in tb}

    assert by_code["4000"].credit == Decimal("750.00")  # revenue: 30 * 25
    assert by_code["5000"].debit == Decimal("300.00")  # COGS: 30 * 10 (cost, not sale price)
    assert by_code["1300"].debit == Decimal("700.00")  # inventory: 1000 received - 300 issued

    total_debit = sum((r.debit for r in tb), Decimal("0.00"))
    total_credit = sum((r.credit for r in tb), Decimal("0.00"))
    assert total_debit == total_credit  # whole entry (revenue + COGS legs) still balances


def test_cannot_sell_more_than_on_hand(db_session, inventory_fixture):
    fx = inventory_fixture

    invoice = create_draft_invoice(
        db_session,
        business_id=fx["business"].id,
        customer_id=fx["customer"].id,
        invoice_number="INV-0002",
        invoice_date=date(2026, 8, 10),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=fx["revenue"].id,
                description="Widget sale",
                quantity=Decimal("5"),
                unit_price=Decimal("25.00"),
                item_id=fx["item"].id,
            )
        ],
    )

    with pytest.raises(SalesPostingError, match="only 0"):
        post_sales_invoice(db_session, invoice=invoice)


def test_manual_stock_adjustment_receive_and_issue(db_session, inventory_fixture):
    item = inventory_fixture["item"]

    receive_stock(
        db_session, item=item, quantity=Decimal("20"), unit_cost=Decimal("5.00"), movement_date=date(2026, 8, 1)
    )
    assert item.quantity_on_hand == Decimal("20.0000")
    assert item.average_cost == Decimal("5.0000")

    result = issue_stock(db_session, item=item, quantity=Decimal("5"), movement_date=date(2026, 8, 2))
    assert item.quantity_on_hand == Decimal("15.0000")
    assert result.total_cost == Decimal("25.00")

    with pytest.raises(InventoryError, match="only 15"):
        issue_stock(db_session, item=item, quantity=Decimal("100"), movement_date=date(2026, 8, 3))
