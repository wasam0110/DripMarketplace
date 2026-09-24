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
import os

# Never load application credentials or services for a test process.
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_original_database_url = os.environ.get("DATABASE_URL", "")
_test_database_url = os.environ.get("TEST_DATABASE_URL", "")
_test_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
os.environ.update({
    "ENVIRONMENT": "test",
    "DATABASE_URL": _test_database_url or "postgresql+asyncpg://test:test@127.0.0.1:55432/wearhowz_test",
    "REDIS_URL": "redis://127.0.0.1:56379/15",
    "JWT_PRIVATE_KEY": _test_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(),
    "JWT_PUBLIC_KEY": _test_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode(),
    "SUPABASE_URL": "https://storage.example.invalid",
    "SUPABASE_SERVICE_ROLE_KEY": "test-only-placeholder",
    "RESEND_API_KEY": "",
    "PAYFAST_MERCHANT_ID": "",
    "PAYFAST_SECURED_KEY": "",
})
from collections.abc import AsyncGenerator
from typing import Any
from sqlalchemy import text
from sqlalchemy.pool import NullPool

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
TEST_DATABASE_URL = _test_database_url


# Each database test owns a disposable schema, never the public schema.
@pytest_asyncio.fixture
async def test_engine():
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated database ending in _test")
    from sqlalchemy.engine import make_url
    from uuid import uuid4
    target = make_url(TEST_DATABASE_URL)
    if target.drivername != "postgresql+asyncpg" or not target.database or not target.database.endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must be PostgreSQL and use a database ending in _test")
    if _original_database_url:
        original = make_url(_original_database_url)
        if (target.host, target.port, target.database) == (original.host, original.port, original.database):
            raise RuntimeError("Refusing to run tests against DATABASE_URL")
    schema = "test_" + uuid4().hex
    setup = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool, connect_args={"timeout": 15, "command_timeout": 20})
    async with setup.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool, connect_args={"timeout": 15, "command_timeout": 20, "server_settings": {"search_path": schema + ",public"}})
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()
        async with setup.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await setup.dispose()


@pytest_asyncio.fixture
async def db(test_engine):
    # SAVEPOINT keeps service-level commits isolated inside the outer transaction.
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False, autoflush=False, join_transaction_mode="create_savepoint") as session:
            yield session
        await transaction.rollback()


@pytest_asyncio.fixture(autouse=True)
async def isolated_redis(monkeypatch):
    import fakeredis.aioredis
    import app.core.redis as redis_module
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_module, "_redis", client)
    yield client
    await client.aclose()


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
