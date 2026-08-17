"""
Tests for Phase 11's global exception handlers: every error response
(expected 4xx, or an unhandled 5xx) comes back as consistent JSON
rather than a stack trace or inconsistent shape.
"""
def test_404_returns_consistent_json_shape(client):
    resp = client.get("/api/v1/this-route-does-not-exist")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_validation_error_returns_422_with_detail(client):
    # Missing required fields on registration.
    resp = client.post("/api/v1/auth/register", json={"email": "not-an-email"})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_request_id_header_present_on_every_response(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers


def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
