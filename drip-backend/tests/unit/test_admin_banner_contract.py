"""Banner request validation and backward-compatible versioned contracts."""

from datetime import UTC, datetime

import pytest
from main import create_application
from pydantic import ValidationError

from app.schemas.admin import UpdateBannerRequest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "link",
    [
        "javascript:alert(1)",
        "http://example.test",
        "//example.test",
        "/\\example.test",
        "https://user:pass@example.test",
        "https://",
        "https://example.test:99999",
        "https://example.test/a b",
        "/a\nb",
    ],
)
def test_unsafe_links_are_rejected(link):
    with pytest.raises(ValidationError):
        UpdateBannerRequest(link_url=link)


@pytest.mark.parametrize(
    "link,expected",
    [
        (None, None),
        (" ", None),
        (" /clothing?sort=newest ", "/clothing?sort=newest"),
        ("https://example.test/path", "https://example.test/path"),
    ],
)
def test_safe_links_and_clearing(link, expected):
    assert UpdateBannerRequest(link_url=link).link_url == expected


@pytest.mark.parametrize(
    "payload",
    [
        {"title": " "},
        {"sort_order": -1},
        {"sort_order": 2147483648},
        {"position": "unknown"},
        {"valid_from": "2026-10-28T10:00:00"},
        {"expected_updated_at": "2026-10-28T10:00:00"},
    ],
)
def test_invalid_fields(payload):
    with pytest.raises(ValidationError):
        UpdateBannerRequest(**payload)


def test_optional_version_and_aware_dates():
    assert UpdateBannerRequest(title="  New title  ").title == "New title"
    assert UpdateBannerRequest().expected_updated_at is None
    model = UpdateBannerRequest(expected_updated_at="2026-10-28T10:00:00Z")
    assert model.expected_updated_at == datetime(2026, 10, 28, 10, tzinfo=UTC)


def test_openapi_includes_versioned_banner_contract():
    schema = create_application().openapi()
    assert "updated_at" in schema["components"]["schemas"]["BannerResponse"]["required"]
    deletion = schema["paths"]["/api/v1/admin/content/banners/{banner_id}"]["delete"]
    assert any(
        p["name"] == "expected_updated_at" and p["in"] == "query" for p in deletion["parameters"]
    )
