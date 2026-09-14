"""Unit tests for authentication security primitives."""

from __future__ import annotations

import pyotp
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import security
from app.core.config import settings


@pytest.fixture
def rsa_keys(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    monkeypatch.setattr(settings, "JWT_PRIVATE_KEY", private_pem)
    monkeypatch.setattr(settings, "JWT_PUBLIC_KEY", public_pem)

    return private_pem, public_pem


@pytest.mark.unit
def test_password_hash_and_verify() -> None:
    password = "StrongPassword123"
    hashed = security.hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert security.verify_password(password, hashed) is True
    assert security.verify_password("WrongPassword123", hashed) is False


@pytest.mark.unit
def test_refresh_token_generation_and_hashing() -> None:
    first = security.generate_refresh_token()
    second = security.generate_refresh_token()

    assert first != second
    assert len(first) > 70
    assert security.hash_refresh_token(first) != first
    assert security.hash_refresh_token(first) == security.hash_refresh_token(first)
    assert len(security.hash_refresh_token(first)) == 64


@pytest.mark.unit
def test_rs256_access_token_encode_decode(
    rsa_keys: tuple[str, str],
) -> None:
    token, jti = security.create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        role="customer",
    )

    payload = security.decode_access_token(token)

    assert payload["sub"] == "00000000-0000-0000-0000-000000000001"
    assert payload["role"] == "customer"
    assert payload["jti"] == jti
    assert payload["iss"] == "drip-api"
    assert payload["aud"] == "drip-client"


@pytest.mark.unit
def test_email_verification_token(
    rsa_keys: tuple[str, str],
) -> None:
    user_id = "00000000-0000-0000-0000-000000000001"
    token = security.create_email_verify_token(user_id)

    assert security.decode_email_verify_token(token) == user_id


@pytest.mark.unit
def test_password_reset_token(
    rsa_keys: tuple[str, str],
) -> None:
    user_id = "00000000-0000-0000-0000-000000000001"
    token = security.create_password_reset_token(user_id)

    assert security.decode_password_reset_token(token) == user_id


@pytest.mark.unit
def test_totp_generation_and_verification() -> None:
    secret = security.generate_totp_secret()
    code = pyotp.TOTP(secret).now()

    assert len(secret) == 32
    assert security.verify_totp(secret, code) is True


@pytest.mark.unit
def test_invalid_totp_raises() -> None:
    secret = security.generate_totp_secret()

    with pytest.raises(Exception):
        security.verify_totp(secret, "000000")


@pytest.mark.unit
def test_refresh_cookie_parameters() -> None:
    params = security.get_cookie_params()

    assert params["key"] == security.REFRESH_TOKEN_COOKIE_NAME
    assert params["httponly"] is True
    assert params["samesite"] == "strict"
    assert params["path"] == "/api/v1/auth"
    assert params["max_age"] == settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
