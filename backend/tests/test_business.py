def _register_and_login(client, email="biz@example.com", password="s3cret-pass"):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Biz Owner", "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_team_management_flow(client):
    owner_headers = _register_and_login(client, email="owner@example.com")
    business_id = client.post(
        "/api/v1/businesses", headers=owner_headers, json={"registered_name": "Team Co"}
    ).json()["id"]

    # The creator is auto-granted Admin.
    members = client.get(f"/api/v1/businesses/{business_id}/users", headers=owner_headers).json()
    assert len(members) == 1
    assert members[0]["role_name"] == "Admin"
    assert members[0]["is_self"] is True

    # Roles list is available for the UI's dropdown.
    roles = client.get(f"/api/v1/businesses/{business_id}/roles", headers=owner_headers).json()
    assert {r["name"] for r in roles} == {"Admin", "Accountant", "Viewer"}

    # Can't invite someone who hasn't registered yet.
    not_found = client.post(
        f"/api/v1/businesses/{business_id}/users", headers=owner_headers,
        json={"email": "nobody@example.com", "role_name": "Accountant"},
    )
    assert not_found.status_code == 404

    # Register a second real user, then invite them.
    _register_and_login(client, email="teammate@example.com")
    invite = client.post(
        f"/api/v1/businesses/{business_id}/users", headers=owner_headers,
        json={"email": "teammate@example.com", "role_name": "Accountant"},
    )
    assert invite.status_code == 201
    assert invite.json()["role_name"] == "Accountant"
    membership_id = invite.json()["id"]

    # Can't invite the same person twice.
    dup = client.post(
        f"/api/v1/businesses/{business_id}/users", headers=owner_headers,
        json={"email": "teammate@example.com", "role_name": "Viewer"},
    )
    assert dup.status_code == 400

    # The invited user now has access to the business through their own login.
    teammate_token = client.post(
        "/api/v1/auth/login", data={"username": "teammate@example.com", "password": "s3cret-pass"}
    ).json()["access_token"]
    teammate_headers = {"Authorization": f"Bearer {teammate_token}"}
    their_businesses = client.get("/api/v1/businesses", headers=teammate_headers).json()
    assert any(b["id"] == business_id for b in their_businesses)

    # A non-Admin can't manage the team.
    forbidden = client.post(
        f"/api/v1/businesses/{business_id}/users", headers=teammate_headers,
        json={"email": "owner@example.com", "role_name": "Viewer"},
    )
    assert forbidden.status_code == 403

    # Admin changes the teammate's role.
    updated = client.patch(
        f"/api/v1/businesses/{business_id}/users/{membership_id}", headers=owner_headers,
        json={"role_name": "Viewer"},
    )
    assert updated.status_code == 200
    assert updated.json()["role_name"] == "Viewer"

    # Can't demote/remove the last Admin.
    owner_membership_id = next(
        m["id"] for m in client.get(f"/api/v1/businesses/{business_id}/users", headers=owner_headers).json() if m["is_self"]
    )
    blocked_demote = client.patch(
        f"/api/v1/businesses/{business_id}/users/{owner_membership_id}", headers=owner_headers,
        json={"role_name": "Viewer"},
    )
    assert blocked_demote.status_code == 400
    blocked_remove = client.delete(f"/api/v1/businesses/{business_id}/users/{owner_membership_id}", headers=owner_headers)
    assert blocked_remove.status_code == 400

    # Admin removes the teammate entirely.
    removed = client.delete(f"/api/v1/businesses/{business_id}/users/{membership_id}", headers=owner_headers)
    assert removed.status_code == 204
    final_members = client.get(f"/api/v1/businesses/{business_id}/users", headers=owner_headers).json()
    assert len(final_members) == 1


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
