def _register_and_login(client, email="biz@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Biz Owner", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_business_and_settings_flow(client):
    headers = _register_and_login(client)

    resp = client.post(
        "/api/v1/businesses",
        headers=headers,
        json={
            "registered_name": "Juan Dela Cruz Trading",
            "business_name": "JDC Trading",
            "tin": "123-456-789-000",
            "vat_registration_status": "VAT Registered",
            "currency_code": "PHP",
        },
    )
    assert resp.status_code == 201
    business = resp.json()
    assert business["registered_name"] == "Juan Dela Cruz Trading"
    business_id = business["id"]

    # Business isolation: appears in my list
    resp = client.get("/api/v1/businesses", headers=headers)
    assert resp.status_code == 200
    assert any(b["id"] == business_id for b in resp.json())

    # Default settings were auto-created
    resp = client.get(f"/api/v1/businesses/{business_id}/settings", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["decimal_precision"] == 2

    # Settings are configurable without code changes (spec Section 2)
    resp = client.patch(
        f"/api/v1/businesses/{business_id}/settings",
        headers=headers,
        json={"invoice_number_prefix": "INV-", "default_payment_terms_days": 15},
    )
    assert resp.status_code == 200
    assert resp.json()["invoice_number_prefix"] == "INV-"
    assert resp.json()["default_payment_terms_days"] == 15


def test_business_access_requires_auth(client):
    resp = client.get("/api/v1/businesses")
    assert resp.status_code == 401


def test_user_cannot_see_other_users_business(client):
    headers_a = _register_and_login(client, email="a@example.com")
    headers_b = _register_and_login(client, email="b@example.com")

    resp = client.post(
        "/api/v1/businesses",
        headers=headers_a,
        json={"registered_name": "A Only Business"},
    )
    business_id = resp.json()["id"]

    resp = client.get(f"/api/v1/businesses/{business_id}", headers=headers_b)
    assert resp.status_code == 404
