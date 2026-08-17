"""
HTTP-level acceptance test for Phase 8: an inventory item, a purchase
that receives stock, and a sale that issues stock and posts COGS --
entirely through the API.
"""
def _register_and_login(client, email="inventory@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Inventory User", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_inventory_item_update(client):
    headers = _register_and_login(client, email="inventory-edit@example.com")
    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Inventory Edit Co"}
    ).json()["id"]
    inv_account = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1300", "name": "Inventory", "account_type": "Asset"},
    ).json()
    cogs_account = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "5100", "name": "COGS", "account_type": "Expense"},
    ).json()

    item = client.post(
        f"/api/v1/businesses/{business_id}/inventory-items",
        headers=headers,
        json={
            "sku": "SKU-001",
            "name": "Widget",
            "inventory_account_id": inv_account["id"],
            "cogs_account_id": cogs_account["id"],
        },
    ).json()

    updated = client.put(
        f"/api/v1/businesses/{business_id}/inventory-items/{item['id']}",
        headers=headers,
        json={"name": "Widget (Deluxe)", "unit_of_measure": "pcs"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Widget (Deluxe)"
    assert updated.json()["unit_of_measure"] == "pcs"


def test_full_inventory_acceptance_flow(client):
    headers = _register_and_login(client)

    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Inventory API Co"}
    ).json()["id"]

    ar = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1200", "name": "Accounts Receivable", "account_type": "Asset"},
    ).json()
    ap = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "2000", "name": "Accounts Payable", "account_type": "Liability"},
    ).json()
    revenue = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "4000", "name": "Sales Revenue", "account_type": "Revenue"},
    ).json()
    inventory_asset = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1300", "name": "Merchandise Inventory", "account_type": "Asset"},
    ).json()
    cogs = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "5000", "name": "Cost of Goods Sold", "account_type": "Cost of Sales"},
    ).json()

    client.patch(
        f"/api/v1/businesses/{business_id}/settings",
        headers=headers,
        json={"ar_account_id": ar["id"], "ap_account_id": ap["id"]},
    )

    fy = client.post(
        f"/api/v1/businesses/{business_id}/fiscal-years",
        headers=headers,
        json={"name": "FY2026", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    ).json()
    client.post(
        f"/api/v1/businesses/{business_id}/periods",
        headers=headers,
        json={
            "fiscal_year_id": fy["id"],
            "name": "2026-08",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
        },
    )

    vendor = client.post(
        f"/api/v1/businesses/{business_id}/vendors", headers=headers, json={"name": "Wholesale Supplier"}
    ).json()
    customer = client.post(
        f"/api/v1/businesses/{business_id}/customers", headers=headers, json={"name": "Retail Customer"}
    ).json()

    item_resp = client.post(
        f"/api/v1/businesses/{business_id}/inventory-items",
        headers=headers,
        json={
            "sku": "WIDGET-001",
            "name": "Widget",
            "inventory_account_id": inventory_asset["id"],
            "cogs_account_id": cogs["id"],
        },
    )
    assert item_resp.status_code == 201
    item = item_resp.json()
    assert item["quantity_on_hand"] == "0.0000"

    # Duplicate SKU rejected
    dup_resp = client.post(
        f"/api/v1/businesses/{business_id}/inventory-items",
        headers=headers,
        json={
            "sku": "WIDGET-001",
            "name": "Widget Again",
            "inventory_account_id": inventory_asset["id"],
            "cogs_account_id": cogs["id"],
        },
    )
    assert dup_resp.status_code == 400

    # Purchase 100 units at 10.00 each -> receives stock
    bill = client.post(
        f"/api/v1/businesses/{business_id}/purchase-bills",
        headers=headers,
        json={
            "vendor_id": vendor["id"],
            "bill_number": "OR-1001",
            "bill_date": "2026-08-05",
            "lines": [
                {
                    "expense_account_id": inventory_asset["id"],
                    "description": "Widget stock-in",
                    "quantity": "100",
                    "unit_price": "10.00",
                    "item_id": item["id"],
                }
            ],
        },
    ).json()
    client.post(f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}/post", headers=headers)

    item_after_purchase = client.get(
        f"/api/v1/businesses/{business_id}/inventory-items", headers=headers
    ).json()[0]
    assert item_after_purchase["quantity_on_hand"] == "100.0000"
    assert item_after_purchase["average_cost"] == "10.0000"

    # Sell 30 units at 25.00 each -> issues stock, posts COGS at cost (10.00), not sale price
    invoice = client.post(
        f"/api/v1/businesses/{business_id}/sales-invoices",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "invoice_number": "INV-0001",
            "invoice_date": "2026-08-10",
            "lines": [
                {
                    "revenue_account_id": revenue["id"],
                    "description": "Widget sale",
                    "quantity": "30",
                    "unit_price": "25.00",
                    "item_id": item["id"],
                }
            ],
        },
    ).json()
    post_resp = client.post(f"/api/v1/businesses/{business_id}/sales-invoices/{invoice['id']}/post", headers=headers)
    assert post_resp.status_code == 200

    item_after_sale = client.get(
        f"/api/v1/businesses/{business_id}/inventory-items", headers=headers
    ).json()[0]
    assert item_after_sale["quantity_on_hand"] == "70.0000"
    assert item_after_sale["average_cost"] == "10.0000"

    tb = client.get(f"/api/v1/businesses/{business_id}/reports/trial-balance", headers=headers).json()
    by_code = {row["account_code"]: row for row in tb}
    assert by_code["4000"]["credit"] == "750.00"
    assert by_code["5000"]["debit"] == "300.00"
    assert by_code["1300"]["debit"] == "700.00"

    # Stock movements are traceable
    movements_resp = client.get(
        f"/api/v1/businesses/{business_id}/inventory-items/{item['id']}/movements", headers=headers
    )
    assert movements_resp.status_code == 200
    movements = movements_resp.json()
    assert len(movements) == 2
    assert movements[0]["movement_type"] == "Purchase"
    assert movements[1]["movement_type"] == "Sale"

    # Attempting to sell more than on hand is rejected
    overSell_resp = client.post(
        f"/api/v1/businesses/{business_id}/sales-invoices",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "invoice_number": "INV-0002",
            "invoice_date": "2026-08-11",
            "lines": [
                {
                    "revenue_account_id": revenue["id"],
                    "description": "Widget oversell",
                    "quantity": "500",
                    "unit_price": "25.00",
                    "item_id": item["id"],
                }
            ],
        },
    ).json()
    oversell_post = client.post(
        f"/api/v1/businesses/{business_id}/sales-invoices/{overSell_resp['id']}/post", headers=headers
    )
    assert oversell_post.status_code == 422
