"""
Test for the rate limiting middleware, built on its own tiny FastAPI
app rather than the shared test `client` fixture -- avoids the
cross-test state contamination that a shared, process-lifetime `app`
singleton would cause (see app/main.py's comment on why rate limiting
itself is production-only).
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimitMiddleware


def _build_test_app(max_requests: int) -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, max_requests=max_requests, window_seconds=60)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def test_requests_under_limit_succeed():
    client = _build_test_app(max_requests=5)
    for _ in range(5):
        resp = client.get("/ping")
        assert resp.status_code == 200


def test_requests_over_limit_are_rejected():
    client = _build_test_app(max_requests=3)
    for _ in range(3):
        assert client.get("/ping").status_code == 200

    over_limit = client.get("/ping")
    assert over_limit.status_code == 429
    assert "Too many requests" in over_limit.json()["detail"]
