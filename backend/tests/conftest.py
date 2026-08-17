"""
Test fixtures: isolated in-memory SQLite DB per test, with the FastAPI
app's get_db dependency overridden to use it. Keeps tests fast and
independent of any developer's local dev.db.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.main import app
from app.models import account, bank, bank_reconciliation, budget, business, cash_disbursement, cash_receipt, customer, depreciation_entry, fixed_asset, inventory_item, journal, period, purchase, refresh_token, sales, stock_movement, tax_rule, user, vendor, withholding_certificate  # noqa: F401

TEST_DATABASE_URL = "sqlite:///:memory:"


def _make_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def client():
    engine = _make_engine()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session():
    """
    A bare SQLAlchemy session against a fresh in-memory DB, for tests
    that call domain-layer functions (e.g. the posting engine)
    directly rather than going through HTTP.
    """
    engine = _make_engine()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
