"""
HTTP-level acceptance test for Phase 7: books of accounts, VAT
summary, and withholding tax certificate issuance, entirely through
the API, building on a posted sales invoice and purchase bill.
"""
def _register_and_login(client, email="bir@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "BIR User", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_bir_acceptance_flow(client):
    headers = _register_and_login(client)

    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "BIR API Co"}
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
    expense = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "6000", "name": "Professional Fees", "account_type": "Expense"},
    ).json()
    output_vat = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "2200", "name": "Output VAT Payable", "account_type": "Liability"},
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

    client.patch(
        f"/api/v1/businesses/{business_id}/settings",
        headers=headers,
        json={
            "ar_account_id": ar["id"],
            "ap_account_id": ap["id"],
            "output_vat_account_id": output_vat["id"],
            "input_vat_account_id": input_vat["id"],
            "withholding_tax_payable_account_id": wt_payable["id"],
        },
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

    customer = client.post(
        f"/api/v1/businesses/{business_id}/customers", headers=headers, json={"name": "Juan Dela Cruz"}
    ).json()
    vendor = client.post(
        f"/api/v1/businesses/{business_id}/vendors", headers=headers, json={"name": "ABC Consulting"}
    ).json()

    invoice = client.post(
        f"/api/v1/businesses/{business_id}/sales-invoices",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "invoice_number": "INV-0001",
            "invoice_date": "2026-08-05",
            "lines": [
                {
                    "revenue_account_id": revenue["id"],
                    "description": "Services",
                    "quantity": "1",
                    "unit_price": "1000.00",
                    "tax_rule_code": "VAT_STANDARD",
                }
            ],
        },
    ).json()
    client.post(f"/api/v1/businesses/{business_id}/sales-invoices/{invoice['id']}/post", headers=headers)

    bill = client.post(
        f"/api/v1/businesses/{business_id}/purchase-bills",
        headers=headers,
        json={
            "vendor_id": vendor["id"],
            "bill_number": "OR-1001",
            "bill_date": "2026-08-10",
            "lines": [
                {
                    "expense_account_id": expense["id"],
                    "description": "Consulting",
                    "quantity": "1",
                    "unit_price": "500.00",
                    "tax_rule_code": "VAT_STANDARD",
                    "withholding_tax_rule_code": "WT_EWT_PROF_FEES",
                }
            ],
        },
    ).json()
    client.post(f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}/post", headers=headers)

    # General journal has both entries
    gj_resp = client.get(f"/api/v1/businesses/{business_id}/bir/books/general-journal", headers=headers)
    assert gj_resp.status_code == 200
    assert len(gj_resp.json()) == 2

    # Sales book / purchase book each have exactly the posted document
    sales_book_resp = client.get(f"/api/v1/businesses/{business_id}/bir/books/sales-book", headers=headers)
    assert len(sales_book_resp.json()) == 1
    purchase_book_resp = client.get(
        f"/api/v1/businesses/{business_id}/bir/books/purchase-book", headers=headers
    )
    assert len(purchase_book_resp.json()) == 1

    # VAT summary: output 120, input 60, net payable 60
    vat_resp = client.get(
        f"/api/v1/businesses/{business_id}/bir/vat-summary",
        headers=headers,
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    )
    assert vat_resp.status_code == 200
    vat = vat_resp.json()
    assert vat["output_vat"] == "120.00"
    assert vat["input_vat"] == "60.00"
    assert vat["net_vat_payable"] == "60.00"

    # Withholding certificate preview and issuance
    preview_resp = client.get(
        f"/api/v1/businesses/{business_id}/bir/withholding-certificates/preview",
        headers=headers,
        params={"vendor_id": vendor["id"], "period_start": "2026-08-01", "period_end": "2026-08-31"},
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["total_tax_withheld"] == "50.00"
    assert preview["breakdown"][0]["atc_code"] == "WC010"

    issue_resp = client.post(
        f"/api/v1/businesses/{business_id}/bir/withholding-certificates",
        headers=headers,
        json={
            "vendor_id": vendor["id"],
            "certificate_number": "2307-2026-08-0001",
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
        },
    )
    assert issue_resp.status_code == 201
    certificate = issue_resp.json()
    assert certificate["status"] == "Issued"
    assert certificate["total_tax_withheld"] == "50.00"

    list_resp = client.get(f"/api/v1/businesses/{business_id}/bir/withholding-certificates", headers=headers)
    assert len(list_resp.json()) == 1
