"""Native persistence and Redis checks for pre-ship boundary fixes."""

import asyncio
import os
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from test_marketplace_regressions import market as marketplace_fixture

from app.core import redis as redis_module
from app.core.exceptions import NotFoundError
from app.core.middleware import RateLimitMiddleware
from app.models.seller import SellerStatus
from app.services.admin_service import AdminService
from app.services.product_service import ProductService

pytestmark = pytest.mark.integration
market = marketplace_fixture


async def test_reinstatement_preserves_independent_product_moderation(db, market):
    service = AdminService(db)
    market.product.admin_hidden = True
    await db.commit()
    await service.suspend_seller(market.seller.id, market.admin.id, "Test suspension")
    await service.reinstate_seller(market.seller.id, market.admin.id)
    await db.refresh(market.product)
    await db.refresh(market.seller)
    assert market.seller.status == SellerStatus.active
    assert market.product.admin_hidden is True
    with pytest.raises(NotFoundError):
        await ProductService(db).get_product_detail(market.product.id)


async def test_suspension_hides_unmoderated_product_without_changing_moderation(db, market):
    service = AdminService(db)
    product_service = ProductService(db)
    await service.suspend_seller(market.seller.id, market.admin.id, "Test suspension")
    await db.refresh(market.seller)
    await db.refresh(market.product)
    assert market.product.admin_hidden is False
    with pytest.raises(NotFoundError):
        await product_service.get_product_detail(market.product.id)
    with pytest.raises(NotFoundError):
        await product_service.get_product_by_slug(market.product.slug)
    await service.reinstate_seller(market.seller.id, market.admin.id)
    await db.refresh(market.seller)
    assert (await product_service.get_product_detail(market.product.id)).id == market.product.id


async def test_native_rate_counter_is_atomic_and_expires(monkeypatch):
    url = os.environ.get("TEST_REDIS_URL", "")
    if not url:
        pytest.skip("Set TEST_REDIS_URL to a dedicated Redis database /15")
    parsed = urlparse(url)
    if parsed.scheme not in {"redis", "rediss"} or parsed.path != "/15":
        raise RuntimeError("Only dedicated Redis test database /15 is allowed")
    pool = Redis.from_url(url, decode_responses=True)
    key = "preship:rate:" + uuid4().hex
    monkeypatch.setattr(redis_module, "_redis", pool)
    try:
        results = await asyncio.gather(*[
            RateLimitMiddleware._check(key, 5, 60) for _ in range(30)
        ])
        assert sum(allowed for allowed, _ in results) == 5
        assert await pool.get(key) == "30"
        assert 0 < await pool.ttl(key) <= 60
        await pool.expire(key, 10)
        await RateLimitMiddleware._check(key, 5, 60)
        assert 0 < await pool.ttl(key) <= 10
    finally:
        await pool.delete(key)
        await pool.aclose()
