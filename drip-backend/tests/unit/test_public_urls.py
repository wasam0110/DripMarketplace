"""Canonical public links are independent of CORS and encode query values."""

from html import unescape
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.public_urls import api_url, frontend_url, normalize_origin
from app.integrations import resend_client

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("origins", [[], ["https://admin.example.test"]])
@pytest.mark.parametrize(
    "kind,path", [("verification", "/verify-email"), ("password_reset", "/reset-password")]
)
async def test_auth_email_uses_canonical_frontend_and_encoded_token(
    origins, kind, path, monkeypatch
):
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://shop.example.test/")
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", origins)
    sender = AsyncMock(return_value=True)
    monkeypatch.setattr(resend_client, "send_email", sender)
    token = 'signed+value/&another=1#fragment"'
    await getattr(resend_client, f"send_{kind}_email")("buyer@example.test", "Buyer", token)
    html = sender.await_args.kwargs["html"]
    link = unescape(html.split('href="', 1)[1].split('"', 1)[0])
    parsed = urlsplit(link)
    assert (parsed.scheme, parsed.netloc, parsed.path) == ("https", "shop.example.test", path)
    assert parse_qs(parsed.query) == {"token": [token]}
    assert not parsed.fragment
    assert "admin.example.test" not in html


def configured(**overrides):
    return Settings(_env_file=None, **{**settings.model_dump(), **overrides})


@pytest.mark.parametrize("field", ["FRONTEND_URL", "API_BASE_URL"])
@pytest.mark.parametrize(
    "value",
    [
        "",
        "//example.test",
        "https:///example.test",
        "javascript:alert(1)",
        "https://user:secret@example.test",
        "https://example.test/subpath",
        "https://example.test?token=secret",
        "https://example.test#fragment",
        "https://example.test/\n",
        "https://example.test\\evil",
        "https://example.test:99999",
    ],
)
def test_invalid_public_origin_fails_configuration(field, value):
    with pytest.raises(ValidationError):
        configured(**{field: value})


@pytest.mark.parametrize(
    "value,expected",
    [
        ("http://localhost:3000/", "http://localhost:3000"),
        ("https://SHOP.example.test:443/", "https://shop.example.test"),
        ("https://shop.example.test:8443/", "https://shop.example.test:8443"),
        ("http://[::1]:8000/", "http://[::1]:8000"),
    ],
)
def test_origin_normalization(value, expected):
    assert normalize_origin(value) == expected
    result = configured(FRONTEND_URL=value)
    assert expected == result.FRONTEND_URL


@pytest.mark.parametrize("field", ["FRONTEND_URL", "API_BASE_URL"])
def test_production_requires_https_even_with_payfast_disabled(field):
    values = {
        "ENVIRONMENT": "production",
        "PAYFAST_ENABLED": False,
        "RESEND_API_KEY": "test-only",
        "FROM_EMAIL": "orders@example.test",
        "FRONTEND_URL": "https://shop.example.test",
        "API_BASE_URL": "https://api.example.test",
    }
    assert configured(**values).is_production
    values[field] = "http://example.test"
    with pytest.raises(ValidationError, match=field):
        configured(**values)


@pytest.mark.parametrize("origin", ["*", "https://site.example.test/path", "null"])
def test_credentialed_cors_requires_explicit_origins(origin):
    with pytest.raises(ValidationError):
        configured(ALLOWED_ORIGINS=[origin])


def test_cors_is_normalized_deduplicated_and_can_be_empty():
    assert configured(ALLOWED_ORIGINS=[]).ALLOWED_ORIGINS == []
    assert configured(
        ALLOWED_ORIGINS=["https://SHOP.example.test/", "https://shop.example.test"]
    ).ALLOWED_ORIGINS == ["https://shop.example.test"]
    assert (
        Settings.model_fields["FRONTEND_URL"].default
        in Settings.model_fields["ALLOWED_ORIGINS"].default
    )


@pytest.mark.parametrize("prefix", ["/api/v2", "/api/v1/"])
def test_unsupported_api_prefix_fails_instead_of_breaking_callback_cookie(prefix):
    with pytest.raises(ValidationError, match="API_PREFIX"):
        configured(API_PREFIX=prefix)


@pytest.mark.parametrize(
    "path", ["https://evil.test", "//evil.test", "/../escape", "/x?y=1", "/x#y", "/x\\y"]
)
def test_link_builder_rejects_non_local_paths(path):
    with pytest.raises(ValueError):
        frontend_url(path)


def test_builders_keep_frontend_and_api_origins_separate(monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://shop.example.test/")
    monkeypatch.setattr(settings, "API_BASE_URL", "https://api.example.test/")
    assert frontend_url("/auth/callback") == "https://shop.example.test/auth/callback"
    assert (
        api_url("/api/v1/auth/google/callback")
        == "https://api.example.test/api/v1/auth/google/callback"
    )
