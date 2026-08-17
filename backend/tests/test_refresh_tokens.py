"""
Tests for Phase 11's refresh token flow: issuance on login, exchange
for a new token pair, rotation (single-use), and rejection of an
invalid/already-used token.
"""
def test_login_issues_refresh_token(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "refresh1@example.com", "full_name": "R1", "password": "s3cret-pass"},
    )
    resp = client.post(
        "/api/v1/auth/login", data={"username": "refresh1@example.com", "password": "s3cret-pass"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["refresh_token"] is not None


def test_refresh_token_exchanges_for_new_pair(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "refresh2@example.com", "full_name": "R2", "password": "s3cret-pass"},
    )
    login_resp = client.post(
        "/api/v1/auth/login", data={"username": "refresh2@example.com", "password": "s3cret-pass"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"]
    assert new_tokens["refresh_token"] != refresh_token

    # The new access token actually works for an authenticated call.
    headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    me_resp = client.get("/api/v1/businesses", headers=headers)
    assert me_resp.status_code == 200


def test_refresh_token_is_single_use(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "refresh3@example.com", "full_name": "R3", "password": "s3cret-pass"},
    )
    login_resp = client.post(
        "/api/v1/auth/login", data={"username": "refresh3@example.com", "password": "s3cret-pass"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    first_use = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first_use.status_code == 200

    second_use = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert second_use.status_code == 401


def test_invalid_refresh_token_rejected(client):
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401
