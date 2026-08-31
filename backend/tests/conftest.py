"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.pricing_item import PricingItem
from app.models.proposal import Proposal
from app.schemas.proposal import ScopeExtraction, ScopeItem


@pytest.fixture()
def db_session():
    """In-memory SQLite session for unit tests (pricing, models, transitions)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient bound to the in-memory SQLite session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_client(seeded_db):
    """FastAPI TestClient bound to a DB already seeded with pricing items."""

    def override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_scope() -> ScopeExtraction:
    """A valid scope extraction for deterministic pricing tests."""
    return ScopeExtraction(
        project_summary="Backyard paver patio and turf refresh.",
        scope_items=[
            ScopeItem(
                requested_work="Install paver patio",
                catalog_item_name="Paver Patio Installation",
                quantity=500,
                confidence=0.9,
                notes="Main backyard patio.",
            ),
            ScopeItem(
                requested_work="Artificial turf side yard",
                catalog_item_name="Artificial Turf Installation",
                quantity=300,
                confidence=0.85,
                notes="Side yard turf.",
            ),
        ],
        assumptions=["Area measurements are estimates from site walk."],
        clarifying_questions=[],
        risk_flags=[],
    )


@pytest.fixture()
def seeded_db(db_session):
    """db_session with a minimal pricing catalog for API workflow tests."""
    from app.seed.pricing_catalog import seed_pricing_catalog

    seed_pricing_catalog(db_session)
    return db_session
