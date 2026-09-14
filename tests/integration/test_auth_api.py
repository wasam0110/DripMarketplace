"""HTTP integration tests for the Block 2 authentication API."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.middleware import RateLimitMiddleware
from app.core.security import hash_password
from app.models.user import User, UserRole


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_returns_created(client: AsyncClient) -> None:
    email = f"register-{uuid.uuid4()}@example.com"

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "StrongPassword123",
            "phone": "03001234567",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "verify" in body["message"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_sets_refresh_cookie(client: AsyncClient, db) -> None:
    email = f"login-{uuid.uuid4()}@example.com"

    user = User(
        email=email,
        password_hash=hash_password("StrongPassword123"),
        role=UserRole.customer,
        first_name="Login",
        last_name="User",
        has_verified_email=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == email
    assert "drip_refresh_token" in response.cookies


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_rejects_invalid_password(client: AsyncClient, db) -> None:
    email = f"bad-password-{uuid.uuid4()}@example.com"

    user = User(
        email=email,
        password_hash=hash_password("StrongPassword123"),
        role=UserRole.customer,
        first_name="Bad",
        last_name="Password",
        has_verified_email=True,
    )
    db.add(user)
    await db.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_forgot_password_does_not_enumerate_accounts(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "does-not-exist@example.com"},
    )

    assert response.status_code == 200
    assert "if an account exists" in response.json()["message"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_validation_rejects_weak_password(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "validation@example.com",
            "password": "weak",
        },
    )

    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limit_middleware_returns_429(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def deny_all(
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int]:
        return False, 0

    monkeypatch.setattr(
        RateLimitMiddleware,
        "_check",
        staticmethod(deny_all),
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "rate-limit@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "300"
