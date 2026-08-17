"""
HTTP-level acceptance test for Phase 3: creates a business-specific
tax rule via the API and calculates tax through the API, mirroring
how a real client will use it.
"""
def _register_and_login(client, email="tax@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Tax User", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_tax_rule_create_and_calculate_flow(client):
    headers = _register_and_login(client)

    business_id = client.post(
        "/api/v1/businesses", headers=headers, json={"registered_name": "Tax API Co"}
    ).json()["id"]

    rule_resp = client.post(
        f"/api/v1/businesses/{business_id}/tax-rules",
        headers=headers,
        json={
            "rule_code": "VAT_STANDARD",
            "name": "Standard VAT",
            "tax_type": "VAT",
            "rate_percent": "12.0000",
            "effective_from": "2024-01-01",
            "legal_basis": "NIRC Sec. 106",
        },
    )
    assert rule_resp.status_code == 201
    rule = rule_resp.json()
    assert rule["rate_percent"] == "12.0000"

    calc_resp = client.post(
        f"/api/v1/businesses/{business_id}/tax-rules/calculate",
        headers=headers,
        json={"rule_code": "VAT_STANDARD", "taxable_amount": "5000.00", "as_of_date": "2026-08-11"},
    )
    assert calc_resp.status_code == 200
    calc = calc_resp.json()
    assert calc["tax_amount"] == "600.00"
    assert calc["rate_percent"] == "12.0000"

    # Calculating with a rule_code that has no matching rule is a clear 422
    bad_calc = client.post(
        f"/api/v1/businesses/{business_id}/tax-rules/calculate",
        headers=headers,
        json={"rule_code": "DOES_NOT_EXIST", "taxable_amount": "100.00", "as_of_date": "2026-08-11"},
    )
    assert bad_calc.status_code == 422

    # Retiring the rule means it's no longer used for calculation
    retire_resp = client.patch(
        f"/api/v1/businesses/{business_id}/tax-rules/{rule['id']}/retire", headers=headers
    )
    assert retire_resp.status_code == 200
    assert retire_resp.json()["status"] == "Retired"

    post_retire_calc = client.post(
        f"/api/v1/businesses/{business_id}/tax-rules/calculate",
        headers=headers,
        json={"rule_code": "VAT_STANDARD", "taxable_amount": "100.00", "as_of_date": "2026-08-11"},
    )
    assert post_retire_calc.status_code == 422

    rules_list = client.get(f"/api/v1/businesses/{business_id}/tax-rules", headers=headers).json()
    assert len(rules_list) == 1
