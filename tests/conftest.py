"""
tests/conftest.py
─────────────────
Shared pytest fixtures for all test blocks.

Provides:
  • Async test client (httpx)
  • Isolated test database session (rolls back after each test)
  • Auth header factories (customer, seller, admin)
  • Common model factories
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.base import Base
from main import app

# ── Test database URL (separate DB to avoid polluting development data) ────────
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/drip", "/drip_test")


# ── Event loop ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ── Test database ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test engine and apply the schema once per session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional test database session.
    All changes made in a test are rolled back after the test completes.
    This keeps tests isolated and the database clean.
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ── HTTP test client ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client pointing at the FastAPI test app.
    Overrides the get_db dependency to use the transactional test session.
    """
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Content-Type": "application/json"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Auth header factories ─────────────────────────────────────────────────────

def _make_auth_headers(user_id: str, role: str, extra: dict | None = None) -> dict[str, str]:
    token, _ = create_access_token(subject=user_id, role=role, extra_claims=extra)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer_headers() -> dict[str, str]:
    """Auth headers for a generic customer user."""
    return _make_auth_headers("00000000-0000-0000-0000-000000000001", "customer")


@pytest.fixture
def seller_headers() -> dict[str, str]:
    """Auth headers for a generic seller user."""
    return _make_auth_headers(
        "00000000-0000-0000-0000-000000000002",
        "seller",
        {"seller_id": "00000000-0000-0000-0000-000000000010"},
    )


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Auth headers for an admin user."""
    return _make_auth_headers("00000000-0000-0000-0000-000000000003", "admin")


# ── Common test data ──────────────────────────────────────────────────────────

@pytest.fixture
def valid_contact_payload() -> dict[str, Any]:
    return {
        "name":  "Test User",
        "email": "test@example.com",
        "phone": "03001234567",
    }


@pytest.fixture
def valid_address_payload() -> dict[str, Any]:
    return {
        "street":   "House 12, Block A, DHA Phase 6",
        "city":     "Karachi",
        "province": "Sindh",
    }