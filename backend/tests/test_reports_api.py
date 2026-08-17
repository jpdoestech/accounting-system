"""
HTTP-level acceptance test for Phase 10: Balance Sheet, Income
Statement, and budget variance, entirely through the API.
"""
def _register_and_login(client, email="reports@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Reports User", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_reports_acceptance_flow(client):
    headers = _register_and_login(client)

    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Reports API Co"}
    ).json()["id"]

    cash = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1000", "name": "Cash", "account_type": "Asset"},
    ).json()
    ar = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1200", "name": "Accounts Receivable", "account_type": "Asset"},
    ).json()
    equity = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "3000", "name": "Owner's Capital", "account_type": "Equity"},
    ).json()
    revenue = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "4000", "name": "Sales Revenue", "account_type": "Revenue"},
    ).json()

    client.patch(
        f"/api/v1/businesses/{business_id}/settings", headers=headers, json={"ar_account_id": ar["id"]}
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

    # Owner contributes cash
    client.post(
        f"/api/v1/businesses/{business_id}/journal-entries",
        headers=headers,
        json={
            "entry_date": "2026-08-01",
            "memo": "Owner contribution",
            "lines": [
                {"account_id": cash["id"], "debit": "5000.00", "credit": "0.00"},
                {"account_id": equity["id"], "debit": "0.00", "credit": "5000.00"},
            ],
        },
    )

    customer = client.post(
        f"/api/v1/businesses/{business_id}/customers", headers=headers, json={"name": "Customer A"}
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
                }
            ],
        },
    ).json()
    client.post(f"/api/v1/businesses/{business_id}/sales-invoices/{invoice['id']}/post", headers=headers)

    # Balance sheet: 5000 cash + 1000 AR = 6000 assets; 5000 capital + 1000 net income = 6000 equity
    bs_resp = client.get(
        f"/api/v1/businesses/{business_id}/reports/balance-sheet",
        headers=headers,
        params={"as_of_date": "2026-08-31"},
    )
    assert bs_resp.status_code == 200
    bs = bs_resp.json()
    assert bs["total_assets"] == "6000.00"
    assert bs["total_equity"] == "6000.00"
    assert bs["is_balanced"] is True

    # Income statement
    is_resp = client.get(
        f"/api/v1/businesses/{business_id}/reports/income-statement",
        headers=headers,
        params={"period_start": "2026-08-01", "period_end": "2026-08-31"},
    )
    assert is_resp.status_code == 200
    income_statement = is_resp.json()
    assert income_statement["total_revenue"] == "1000.00"
    assert income_statement["net_income"] == "1000.00"

    # Budget + variance
    budget_resp = client.post(
        f"/api/v1/businesses/{business_id}/budgets",
        headers=headers,
        json={
            "fiscal_year_id": fy["id"],
            "name": "FY2026 Budget",
            "lines": [{"account_id": revenue["id"], "budgeted_amount": "1200.00"}],
        },
    )
    assert budget_resp.status_code == 201
    budget = budget_resp.json()

    variance_resp = client.get(
        f"/api/v1/businesses/{business_id}/budgets/{budget['id']}/variance", headers=headers
    )
    assert variance_resp.status_code == 200
    variance = variance_resp.json()
    assert variance["rows"][0]["budgeted_amount"] == "1200.00"
    assert variance["rows"][0]["actual_amount"] == "1000.00"
    assert variance["rows"][0]["variance"] == "-200.00"
