"""
HTTP-level acceptance test for Phase 6: bank account setup, a cash
receipt applied against a posted sales invoice, a cash disbursement
applied against a posted purchase bill, and a bank reconciliation --
entirely through the API.
"""
def _register_and_login(client, email="banking@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Banking User", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_bank_account_opening_balance_auto_posts_when_configured(client):
    headers = _register_and_login(client, email="opening-balance@example.com")
    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Opening Balance Co"}
    ).json()["id"]
    cash_gl = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1000", "name": "Cash", "account_type": "Asset"},
    ).json()
    equity = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "3900", "name": "Opening Balance Equity", "account_type": "Equity"},
    ).json()
    fy = client.post(
        f"/api/v1/businesses/{business_id}/fiscal-years",
        headers=headers,
        json={"name": "FY2026", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    ).json()
    client.post(
        f"/api/v1/businesses/{business_id}/periods",
        headers=headers,
        json={"fiscal_year_id": fy["id"], "name": "Jan", "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    # No opening_balance_equity_account_id configured yet -- bank account
    # is still created, but nothing gets posted to the ledger.
    client.post(
        f"/api/v1/businesses/{business_id}/bank-accounts",
        headers=headers,
        json={"name": "Unconfigured", "gl_account_id": cash_gl["id"], "opening_balance": "1000.00", "opening_balance_date": "2026-01-01"},
    )
    assert client.get(f"/api/v1/businesses/{business_id}/journal-entries", headers=headers).json() == []

    # Once configured, a new bank account's opening balance auto-posts.
    client.patch(
        f"/api/v1/businesses/{business_id}/settings",
        headers=headers,
        json={"opening_balance_equity_account_id": equity["id"]},
    )
    client.post(
        f"/api/v1/businesses/{business_id}/bank-accounts",
        headers=headers,
        json={"name": "Main Bank", "gl_account_id": cash_gl["id"], "opening_balance": "5000.00", "opening_balance_date": "2026-01-15"},
    )
    entries = client.get(f"/api/v1/businesses/{business_id}/journal-entries", headers=headers).json()
    assert len(entries) == 1
    assert entries[0]["source"] == "Bank Account Opening Balance"
    lines_by_account = {l["account_id"]: l for l in entries[0]["lines"]}
    assert lines_by_account[cash_gl["id"]]["debit"] == "5000.00"
    assert lines_by_account[equity["id"]]["credit"] == "5000.00"

    bs = client.get(
        f"/api/v1/businesses/{business_id}/reports/balance-sheet",
        headers=headers,
        params={"as_of_date": "2026-01-15"},
    ).json()
    cash_line = next(l for l in bs["assets"] if l["account_id"] == cash_gl["id"])
    assert cash_line["amount"] == "5000.00"

    # A date outside any open period fails gracefully -- the bank
    # account is still created, it just doesn't get a journal entry.
    client.post(
        f"/api/v1/businesses/{business_id}/bank-accounts",
        headers=headers,
        json={"name": "Future Bank", "gl_account_id": cash_gl["id"], "opening_balance": "200.00", "opening_balance_date": "2027-01-01"},
    )
    assert len(client.get(f"/api/v1/businesses/{business_id}/journal-entries", headers=headers).json()) == 1


def test_bank_account_update(client):
    headers = _register_and_login(client, email="bank-edit@example.com")
    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Bank Edit Co"}
    ).json()["id"]
    gl_account = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1000", "name": "Cash in Bank", "account_type": "Asset"},
    ).json()

    bank_account = client.post(
        f"/api/v1/businesses/{business_id}/bank-accounts",
        headers=headers,
        json={"name": "Main Checking", "gl_account_id": gl_account["id"]},
    ).json()

    updated = client.put(
        f"/api/v1/businesses/{business_id}/bank-accounts/{bank_account['id']}",
        headers=headers,
        json={"name": "Main Checking (BDO)", "bank_name": "BDO"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Main Checking (BDO)"
    assert updated.json()["bank_name"] == "BDO"


def test_full_banking_acceptance_flow(client):
    headers = _register_and_login(client)

    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Banking API Co"}
    ).json()["id"]

    bank_gl = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1010", "name": "BDO Checking", "account_type": "Asset"},
    ).json()
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
        json={"code": "6000", "name": "Office Supplies", "account_type": "Expense"},
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

    bank_account = client.post(
        f"/api/v1/businesses/{business_id}/bank-accounts",
        headers=headers,
        json={
            "name": "BDO Checking",
            "gl_account_id": bank_gl["id"],
            "opening_balance": "10000.00",
            "opening_balance_date": "2026-08-01",
        },
    ).json()
    assert bank_account["opening_balance"] == "10000.00"

    customer = client.post(
        f"/api/v1/businesses/{business_id}/customers", headers=headers, json={"name": "Juan Dela Cruz"}
    ).json()
    vendor = client.post(
        f"/api/v1/businesses/{business_id}/vendors", headers=headers, json={"name": "Office Depot PH"}
    ).json()

    # Sales invoice -> posted
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
                }
            ],
        },
    ).json()
    client.post(f"/api/v1/businesses/{business_id}/sales-invoices/{invoice['id']}/post", headers=headers)

    # Purchase bill -> posted
    bill = client.post(
        f"/api/v1/businesses/{business_id}/purchase-bills",
        headers=headers,
        json={
            "vendor_id": vendor["id"],
            "bill_number": "OR-1001",
            "bill_date": "2026-08-05",
            "lines": [
                {
                    "expense_account_id": expense["id"],
                    "description": "Supplies",
                    "quantity": "1",
                    "unit_price": "500.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/v1/businesses/{business_id}/purchase-bills/{bill['id']}/post", headers=headers)

    # Cash receipt applied to the invoice
    receipt_resp = client.post(
        f"/api/v1/businesses/{business_id}/cash-receipts",
        headers=headers,
        json={
            "bank_account_id": bank_account["id"],
            "customer_id": customer["id"],
            "receipt_number": "OR-2001",
            "receipt_date": "2026-08-10",
            "amount": "1000.00",
            "allocations": [{"document_id": invoice["id"], "amount_applied": "1000.00"}],
        },
    )
    assert receipt_resp.status_code == 201
    receipt = receipt_resp.json()

    post_receipt_resp = client.post(
        f"/api/v1/businesses/{business_id}/cash-receipts/{receipt['id']}/post", headers=headers
    )
    assert post_receipt_resp.status_code == 200
    assert post_receipt_resp.json()["status"] == "Posted"

    # Cash disbursement applied to the bill
    disb_resp = client.post(
        f"/api/v1/businesses/{business_id}/cash-disbursements",
        headers=headers,
        json={
            "bank_account_id": bank_account["id"],
            "vendor_id": vendor["id"],
            "payment_number": "CHK-3001",
            "payment_date": "2026-08-12",
            "amount": "500.00",
            "allocations": [{"document_id": bill["id"], "amount_applied": "500.00"}],
        },
    )
    assert disb_resp.status_code == 201
    disbursement = disb_resp.json()

    post_disb_resp = client.post(
        f"/api/v1/businesses/{business_id}/cash-disbursements/{disbursement['id']}/post", headers=headers
    )
    assert post_disb_resp.status_code == 200
    assert post_disb_resp.json()["status"] == "Posted"

    # Trial balance: AR and AP should have netted to zero (paid in full);
    # bank GL reflects the net movement (+1000 receipt, -500 disbursement)
    tb = client.get(f"/api/v1/businesses/{business_id}/reports/trial-balance", headers=headers).json()
    by_code = {row["account_code"]: row for row in tb}
    assert "1200" not in by_code  # AR fully paid
    assert "2000" not in by_code  # AP fully paid
    assert by_code["1010"]["debit"] == "500.00"  # net: 1000 debit - 500 credit

    # Reconcile: opening 10000 + cleared receipt 1000 - cleared disbursement 500 = 10500
    reconcile_resp = client.post(
        f"/api/v1/businesses/{business_id}/bank-accounts/{bank_account['id']}/reconcile",
        headers=headers,
        json={
            "statement_date": "2026-08-31",
            "statement_ending_balance": "10500.00",
            "receipt_ids_to_clear": [receipt["id"]],
            "disbursement_ids_to_clear": [disbursement["id"]],
        },
    )
    assert reconcile_resp.status_code == 200
    reconciliation = reconcile_resp.json()
    assert reconciliation["book_balance"] == "10500.00"
    assert reconciliation["difference"] == "0.00"
    assert reconciliation["status"] == "Completed"
