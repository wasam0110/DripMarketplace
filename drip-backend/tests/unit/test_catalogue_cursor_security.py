"""Malformed catalogue cursors must fail before executing SQL."""

import base64
import json
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import BusinessRuleError
from app.repositories.product_repo import ProductRepository


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    [], None, 42, "text", {},
    {"sort": "newest", "id": 42, "value": "2026-01-01"},
    {"sort": "newest", "id": "bad", "value": "2026-01-01"},
    {"sort": "newest", "id": "00000000-0000-0000-0000-000000000001", "value": "2026-01-01"},
    {"sort": "rating", "id": "00000000-0000-0000-0000-000000000001", "value": "not-money"},
    {"sort": "rating", "id": "00000000-0000-0000-0000-000000000001", "value": "NaN"},
])
async def test_invalid_cursor_is_client_error(payload):
    db = AsyncMock()
    cursor = base64.b64encode(json.dumps(payload).encode()).decode()
    sort = payload.get("sort", "newest") if isinstance(payload, dict) else "newest"
    with pytest.raises(BusinessRuleError, match="Invalid catalogue cursor"):
        await ProductRepository(db).list_catalogue(cursor=cursor, sort=sort)
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("cursor", ["%%%", "a" * 2049, "/w=="])
async def test_invalid_cursor_encoding_is_client_error(cursor):
    db = AsyncMock()
    with pytest.raises(BusinessRuleError, match="Invalid catalogue cursor"):
        await ProductRepository(db).list_catalogue(cursor=cursor)
    db.execute.assert_not_awaited()
