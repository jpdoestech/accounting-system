"""
HTTP-level acceptance test for Phase 9: asset creation, schedule
preview, and monthly depreciation posting entirely through the API.
"""
def _register_and_login(client, email="assets@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Assets User", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_fixed_assets_acceptance_flow(client):
    headers = _register_and_login(client)

    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Fixed Assets API Co"}
    ).json()["id"]

    asset_acct = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1500", "name": "Office Equipment", "account_type": "Asset"},
    ).json()
    accum_dep = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "1510", "name": "Accumulated Depreciation", "account_type": "Asset"},
    ).json()
    dep_expense = client.post(
        f"/api/v1/businesses/{business_id}/accounts",
        headers=headers,
        json={"code": "6100", "name": "Depreciation Expense", "account_type": "Expense"},
    ).json()

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
            "name": "2026-01",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
    )

    asset_resp = client.post(
        f"/api/v1/businesses/{business_id}/fixed-assets",
        headers=headers,
        json={
            "asset_code": "FA-0001",
            "name": "Laptop",
            "acquisition_date": "2026-01-01",
            "acquisition_cost": "36000.00",
            "salvage_value": "0.00",
            "useful_life_months": 36,
            "asset_account_id": asset_acct["id"],
            "accumulated_depreciation_account_id": accum_dep["id"],
            "depreciation_expense_account_id": dep_expense["id"],
        },
    )
    assert asset_resp.status_code == 201
    asset = asset_resp.json()
    assert asset["status"] == "Active"

    # Duplicate asset code rejected
    dup_resp = client.post(
        f"/api/v1/businesses/{business_id}/fixed-assets",
        headers=headers,
        json={
            "asset_code": "FA-0001",
            "name": "Laptop Again",
            "acquisition_date": "2026-01-01",
            "acquisition_cost": "1000.00",
            "useful_life_months": 12,
            "asset_account_id": asset_acct["id"],
            "accumulated_depreciation_account_id": accum_dep["id"],
            "depreciation_expense_account_id": dep_expense["id"],
        },
    )
    assert dup_resp.status_code == 400

    # Schedule preview: 36 months, ₱1000/mo, ending at zero book value
    schedule_resp = client.get(
        f"/api/v1/businesses/{business_id}/fixed-assets/{asset['id']}/schedule", headers=headers
    )
    assert schedule_resp.status_code == 200
    schedule = schedule_resp.json()
    assert len(schedule) == 36
    assert schedule[0]["depreciation_amount"] == "1000.00"
    assert schedule[-1]["book_value_after"] == "0.00"

    # Post January depreciation
    post_resp = client.post(
        f"/api/v1/businesses/{business_id}/fixed-assets/{asset['id']}/depreciate",
        headers=headers,
        json={"period_year": 2026, "period_month": 1, "entry_date": "2026-01-31"},
    )
    assert post_resp.status_code == 200
    dep_entry = post_resp.json()
    assert dep_entry["depreciation_amount"] == "1000.00"
    assert dep_entry["accumulated_depreciation_after"] == "1000.00"

    # Trial balance reflects it
    tb = client.get(f"/api/v1/businesses/{business_id}/reports/trial-balance", headers=headers).json()
    by_code = {row["account_code"]: row for row in tb}
    assert by_code["6100"]["debit"] == "1000.00"
    assert by_code["1510"]["credit"] == "1000.00"

    # Double-posting the same period is rejected
    repost_resp = client.post(
        f"/api/v1/businesses/{business_id}/fixed-assets/{asset['id']}/depreciate",
        headers=headers,
        json={"period_year": 2026, "period_month": 1, "entry_date": "2026-01-31"},
    )
    assert repost_resp.status_code == 422

    # Depreciation entry history
    entries_resp = client.get(
        f"/api/v1/businesses/{business_id}/fixed-assets/{asset['id']}/depreciation-entries", headers=headers
    )
    assert entries_resp.status_code == 200
    assert len(entries_resp.json()) == 1
