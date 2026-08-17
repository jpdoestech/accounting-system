"""
HTTP-level acceptance test for Phase 2: exercises the accounting
engine entirely through the API, the way the real frontend/clients
will use it -- not by calling the domain layer directly.
"""
def _register_and_login(client, email="acct@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Accountant", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_accounting_acceptance_flow(client):
    headers = _register_and_login(client)

    resp = client.post(
        "/api/v1/businesses",
        headers=headers,
        json={"registered_name": "Acceptance Test Co", "currency_code": "PHP"},
    )
    business_id = resp.json()["id"]

    # Chart of accounts
    cash = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1000", "name": "Cash", "account_type": "Asset"},
    ).json()
    revenue = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "4000", "name": "Sales Revenue", "account_type": "Revenue"},
    ).json()

    # Duplicate account code rejected
    dup_resp = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1000", "name": "Cash Again", "account_type": "Asset"},
    )
    assert dup_resp.status_code == 400

    # Fiscal year + period
    fy = client.post(
        f"/api/v1/businesses/{business_id}/fiscal-years",
        headers=headers,
        json={"name": "FY2026", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    ).json()

    period = client.post(
        f"/api/v1/businesses/{business_id}/periods",
        headers=headers,
        json={
            "fiscal_year_id": fy["id"],
            "name": "2026-01",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
    ).json()
    assert period["status"] == "Open"

    # Post a balanced journal entry
    entry_resp = client.post(
        f"/api/v1/businesses/{business_id}/journal-entries",
        headers=headers,
        json={
            "entry_date": "2026-01-15",
            "memo": "Cash sale",
            "lines": [
                {"account_id": cash["id"], "debit": "1500.00", "credit": "0.00"},
                {"account_id": revenue["id"], "debit": "0.00", "credit": "1500.00"},
            ],
        },
    )
    assert entry_resp.status_code == 201
    entry = entry_resp.json()
    assert entry["status"] == "Posted"

    # An unbalanced entry is rejected with 422, not silently accepted
    unbalanced_resp = client.post(
        f"/api/v1/businesses/{business_id}/journal-entries",
        headers=headers,
        json={
            "entry_date": "2026-01-16",
            "lines": [
                {"account_id": cash["id"], "debit": "100.00", "credit": "0.00"},
                {"account_id": revenue["id"], "debit": "0.00", "credit": "50.00"},
            ],
        },
    )
    assert unbalanced_resp.status_code == 422

    # Trial balance reflects the posted entry and stays balanced
    tb = client.get(f"/api/v1/businesses/{business_id}/reports/trial-balance", headers=headers).json()
    total_debit = sum(float(r["debit"]) for r in tb)
    total_credit = sum(float(r["credit"]) for r in tb)
    assert total_debit == total_credit == 1500.00

    # General ledger for the cash account shows the posting
    ledger = client.get(
        f"/api/v1/businesses/{business_id}/accounts/{cash['id']}/ledger", headers=headers
    ).json()
    assert ledger["closing_balance"] == "1500.00"
    assert len(ledger["lines"]) == 1

    # Reversal of the original entry works and nets back to zero
    reversal_resp = client.post(
        f"/api/v1/businesses/{business_id}/journal-entries/{entry['id']}/reverse", headers=headers
    )
    assert reversal_resp.status_code == 200

    tb_after_reversal = client.get(
        f"/api/v1/businesses/{business_id}/reports/trial-balance", headers=headers
    ).json()
    assert tb_after_reversal == []

    # Close the period, then confirm further posting into it is rejected
    close_resp = client.patch(
        f"/api/v1/businesses/{business_id}/periods/{period['id']}/close", headers=headers
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "Closed"

    blocked_resp = client.post(
        f"/api/v1/businesses/{business_id}/journal-entries",
        headers=headers,
        json={
            "entry_date": "2026-01-20",
            "lines": [
                {"account_id": cash["id"], "debit": "10.00", "credit": "0.00"},
                {"account_id": revenue["id"], "debit": "0.00", "credit": "10.00"},
            ],
        },
    )
    assert blocked_resp.status_code == 422
