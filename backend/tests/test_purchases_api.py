"""
HTTP-level acceptance test for Phase 5: exercises vendor creation,
draft bill creation (with input VAT and withholding tax computed via
the tax engine), and posting entirely through the API.
"""
def _register_and_login(client, email="purchases@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Purchases User", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_vendor_update_and_delete(client):
    headers = _register_and_login(client, email="vendors@example.com")
    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Vendor Edit Co"}
    ).json()["id"]

    vendor = client.post(
        f"/api/v1/businesses/{business_id}/vendors",
        headers=headers,
        json={"name": "Original Supplier", "is_vat_registered": True},
    ).json()

    updated = client.put(
        f"/api/v1/businesses/{business_id}/vendors/{vendor['id']}",
        headers=headers,
        json={"name": "Renamed Supplier", "is_vat_registered": False},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed Supplier"
    assert updated.json()["is_vat_registered"] is False

    deleted = client.delete(
        f"/api/v1/businesses/{business_id}/vendors/{vendor['id']}", headers=headers
    )
    assert deleted.status_code == 204

    listing_after_delete = client.get(
        f"/api/v1/businesses/{business_id}/vendors", headers=headers
    ).json()
    assert listing_after_delete == []


def test_purchase_bill_draft_edit_locks_after_posting(client):
    headers = _register_and_login(client, email="draft-bill@example.com")
    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Draft Bill Co"}
    ).json()["id"]
    ap = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "2000", "name": "AP", "account_type": "Liability"},
    ).json()
    expense = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "6000", "name": "Expense", "account_type": "Expense"},
    ).json()
    client.patch(f"/api/v1/businesses/{business_id}/settings", headers=headers, json={"ap_account_id": ap["id"]})
    vendor = client.post(f"/api/v1/businesses/{business_id}/vendors", headers=headers, json={"name": "Supplier"}).json()
    fy = client.post(
        f"/api/v1/businesses/{business_id}/fiscal-years",
        headers=headers,
        json={"name": "FY2026", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    ).json()
    client.post(
        f"/api/v1/businesses/{business_id}/periods",
        headers=headers,
        json={"fiscal_year_id": fy["id"], "name": "Aug", "start_date": "2026-08-01", "end_date": "2026-08-31"},
    )

    bill = client.post(
        f"/api/v1/businesses/{business_id}/purchase-bills",
        headers=headers,
        json={
            "vendor_id": vendor["id"],
            "bill_number": "BILL-1",
            "bill_date": "2026-08-17",
            "lines": [{"expense_account_id": expense["id"], "description": "x", "quantity": "1", "unit_price": "100"}],
        },
    ).json()

    edited = client.put(
        f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}",
        headers=headers,
        json={
            "vendor_id": vendor["id"],
            "bill_number": "BILL-1-EDITED",
            "bill_date": "2026-08-17",
            "lines": [{"expense_account_id": expense["id"], "description": "y", "quantity": "2", "unit_price": "40"}],
        },
    )
    assert edited.status_code == 200
    assert edited.json()["bill_number"] == "BILL-1-EDITED"

    client.post(f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}/post", headers=headers)

    blocked = client.put(
        f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}",
        headers=headers,
        json={
            "vendor_id": vendor["id"],
            "bill_number": "SHOULD-NOT-APPLY",
            "bill_date": "2026-08-17",
            "lines": [{"expense_account_id": expense["id"], "description": "z", "quantity": "1", "unit_price": "1"}],
        },
    )
    assert blocked.status_code == 400
    assert client.delete(f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}", headers=headers).status_code == 400


def test_full_purchases_acceptance_flow(client):
    headers = _register_and_login(client)

    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Purchases API Co"}
    ).json()["id"]

    ap = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "2000", "name": "Accounts Payable", "account_type": "Liability"},
    ).json()
    expense = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "6000", "name": "Professional Fees", "account_type": "Expense"},
    ).json()
    input_vat = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1400", "name": "Input VAT", "account_type": "Asset"},
    ).json()
    wt_payable = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "2300", "name": "Withholding Tax Payable", "account_type": "Liability"},
    ).json()

    settings_resp = client.patch(
        f"/api/v1/businesses/{business_id}/settings",
        headers=headers,
        json={
            "ap_account_id": ap["id"],
            "input_vat_account_id": input_vat["id"],
            "withholding_tax_payable_account_id": wt_payable["id"],
        },
    )
    assert settings_resp.status_code == 200

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

    client.post(
        f"/api/v1/businesses/{business_id}/tax-rules",
        headers=headers,
        json={
            "rule_code": "VAT_STANDARD",
            "name": "Standard VAT",
            "tax_type": "VAT",
            "rate_percent": "12.0000",
            "effective_from": "2024-01-01",
        },
    )
    client.post(
        f"/api/v1/businesses/{business_id}/tax-rules",
        headers=headers,
        json={
            "rule_code": "WT_EWT_PROF_FEES",
            "name": "EWT - Professional Fees",
            "tax_type": "Withholding",
            "atc_code": "WC010",
            "rate_percent": "10.0000",
            "effective_from": "2020-01-01",
        },
    )

    vendor = client.post(
        f"/api/v1/businesses/{business_id}/vendors",
        headers=headers,
        json={"name": "ABC Consulting Services", "tin": "987-654-321-000"},
    ).json()

    bill_resp = client.post(
        f"/api/v1/businesses/{business_id}/purchase-bills",
        headers=headers,
        json={
            "vendor_id": vendor["id"],
            "bill_number": "OR-1001",
            "bill_date": "2026-08-11",
            "lines": [
                {
                    "expense_account_id": expense["id"],
                    "description": "Consulting fee",
                    "quantity": "1",
                    "unit_price": "1000.00",
                    "tax_rule_code": "VAT_STANDARD",
                    "withholding_tax_rule_code": "WT_EWT_PROF_FEES",
                }
            ],
        },
    )
    assert bill_resp.status_code == 201
    bill = bill_resp.json()
    assert bill["status"] == "Draft"
    assert bill["subtotal"] == "1000.00"
    assert bill["input_vat_total"] == "120.00"
    assert bill["withholding_tax_total"] == "100.00"
    assert bill["grand_total"] == "1120.00"
    assert bill["amount_due_to_vendor"] == "1020.00"

    post_resp = client.post(
        f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}/post", headers=headers
    )
    assert post_resp.status_code == 200
    posted = post_resp.json()
    assert posted["status"] == "Posted"
    assert posted["journal_entry_id"] is not None

    tb = client.get(f"/api/v1/businesses/{business_id}/reports/trial-balance", headers=headers).json()
    by_code = {row["account_code"]: row for row in tb}
    assert by_code["6000"]["debit"] == "1000.00"
    assert by_code["1400"]["debit"] == "120.00"
    assert by_code["2000"]["credit"] == "1020.00"
    assert by_code["2300"]["credit"] == "100.00"

    repost_resp = client.post(
        f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}/post", headers=headers
    )
    assert repost_resp.status_code == 422
