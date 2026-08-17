def test_register_and_login(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "full_name": "Owner", "password": "s3cret-pass"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "owner@example.com"

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "owner@example.com", "password": "s3cret-pass"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_rejected(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "u2@example.com", "full_name": "U2", "password": "correct-pass"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "u2@example.com", "password": "wrong-pass"},
    )
    assert resp.status_code == 401
