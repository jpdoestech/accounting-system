"""
HTTP-level acceptance test for Phase 4: exercises customer creation,
draft invoice creation (with tax calculated via the tax engine), and
posting (via the accounting engine) entirely through the API.
"""
def _register_and_login(client, email="sales@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Sales User", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_sales_acceptance_flow(client):
    headers = _register_and_login(client)

    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Sales API Co"}
    ).json()["id"]

    # Chart of accounts needed for the invoice
    ar = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1200", "name": "Accounts Receivable", "account_type": "Asset"},
    ).json()
    revenue = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "4000", "name": "Sales Revenue", "account_type": "Revenue"},
    ).json()
    output_vat = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "2200", "name": "Output VAT Payable", "account_type": "Liability"},
    ).json()

    # Configure control accounts on business settings
    settings_resp = client.patch(
        f"/api/v1/businesses/{business_id}/settings",
        headers=headers,
        json={"ar_account_id": ar["id"], "output_vat_account_id": output_vat["id"]},
    )
    assert settings_resp.status_code == 200

    # Fiscal year + period covering the invoice date
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

    # Tax rule
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

    # Customer
    customer = client.post(
        f"/api/v1/businesses/{business_id}/customers",
        headers=headers,
        json={"name": "Juan Dela Cruz", "tin": "123-456-789-000"},
    ).json()

    # Draft invoice -- tax computed automatically via the tax engine
    invoice_resp = client.post(
        f"/api/v1/businesses/{business_id}/sales-invoices",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "invoice_number": "INV-0001",
            "invoice_date": "2026-08-11",
            "lines": [
                {
                    "revenue_account_id": revenue["id"],
                    "description": "Consulting services",
                    "quantity": "1",
                    "unit_price": "1000.00",
                    "tax_rule_code": "VAT_STANDARD",
                }
            ],
        },
    )
    assert invoice_resp.status_code == 201
    invoice = invoice_resp.json()
    assert invoice["status"] == "Draft"
    assert invoice["subtotal"] == "1000.00"
    assert invoice["tax_total"] == "120.00"
    assert invoice["grand_total"] == "1120.00"

    # Post the invoice -- creates a balanced journal entry via the accounting engine
    post_resp = client.post(
        f"/api/v1/businesses/{business_id}/sales-invoices/{invoice['id']}/post", headers=headers
    )
    assert post_resp.status_code == 200
    posted = post_resp.json()
    assert posted["status"] == "Posted"
    assert posted["journal_entry_id"] is not None

    # Trial balance reflects the posting and stays balanced
    tb = client.get(f"/api/v1/businesses/{business_id}/reports/trial-balance", headers=headers).json()
    by_code = {row["account_code"]: row for row in tb}
    assert by_code["1200"]["debit"] == "1120.00"
    assert by_code["4000"]["credit"] == "1000.00"
    assert by_code["2200"]["credit"] == "120.00"

    # Posting the same invoice again is rejected
    repost_resp = client.post(
        f"/api/v1/businesses/{business_id}/sales-invoices/{invoice['id']}/post", headers=headers
    )
    assert repost_resp.status_code == 422
