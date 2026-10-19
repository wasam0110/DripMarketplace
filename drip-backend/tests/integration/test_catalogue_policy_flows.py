"""Native image/count/price boundaries; external storage is mocked, auth is real."""

import io
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.core.catalogue_policy import MAX_IMAGE_BYTES
from app.core.exceptions import BusinessRuleError
from app.integrations.supabase_storage import SupabaseStorage
from app.models.product import ProductImage
from app.services.product_service import ProductService

pytestmark = pytest.mark.integration
market = marketplace_fixture


@pytest.fixture
def storage(monkeypatch):
    async def upload(**kwargs):
        return f"https://example.test/{kwargs['path']}"

    mock = AsyncMock(side_effect=upload)
    monkeypatch.setattr(SupabaseStorage, "upload", mock)
    return mock


def files(count=1, oversized=False):
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), "red").save(buf, format="PNG")
    data = b"x" * (MAX_IMAGE_BYTES + 1) if oversized else buf.getvalue()
    return [("images", (f"test-{i}.png", data, "image/png")) for i in range(count)]


async def snapshot(db):
    return sorted(
        tuple(map(str, row))
        for row in (await db.execute(select(*ProductImage.__table__.columns))).all()
    )


@pytest.mark.parametrize("count,oversized", [(7, False), (6, False), (1, True)])
async def test_upload_rejects_limits_without_storage_or_rows(
    client, db, market, storage, count, oversized
):
    client.headers.pop("Content-Type", None)
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1/seller/products/{market.product.id}/images",
        headers=headers(market.seller_user),
        files=files(count, oversized),
    )
    assert response.status_code == 422, response.text
    storage.assert_not_awaited()
    assert await snapshot(db) == before


async def test_upload_to_six_then_reorder_preserves_cap(client, db, market, storage):
    client.headers.pop("Content-Type", None)
    path = f"/api/v1/seller/products/{market.product.id}/images"
    response = await client.post(path, headers=headers(market.seller_user), files=files(5))
    assert response.status_code == 201, response.text
    assert len(response.json()["images"]) == storage.await_count == 5
    rows = (await db.scalars(select(ProductImage).order_by(ProductImage.sort_order))).all()
    assert len(rows) == 6
    assert sum(row.is_primary for row in rows) == 1
    before = await snapshot(db)
    rejected = await client.post(path, headers=headers(market.seller_user), files=files())
    assert rejected.status_code == 422, rejected.text
    assert storage.await_count == 5
    assert await snapshot(db) == before
    ids = [str(row.id) for row in reversed(rows)]
    ordered = await client.put(
        path + "/order", headers=headers(market.seller_user), json={"image_ids": ids}
    )
    assert ordered.status_code == 200, ordered.text
    actual = (await db.scalars(select(ProductImage).order_by(ProductImage.sort_order))).all()
    assert [str(row.id) for row in actual] == ids
    rejected = await client.put(
        path + "/order", headers=headers(market.seller_user), json={"image_ids": ids + ids[:1]}
    )
    assert rejected.status_code == 422, rejected.text


async def test_service_cap_rejects_direct_call_without_rows(db, market):
    service = ProductService(db)
    await service.add_images(
        market.seller.id, market.product.id, [f"https://example.test/{i}.webp" for i in range(5)]
    )
    before = await snapshot(db)
    assert len(before) == 6
    with pytest.raises(BusinessRuleError, match="Maximum 6"):
        await service.add_images(
            market.seller.id, market.product.id, ["https://example.test/extra.webp"]
        )
    assert await snapshot(db) == before


@pytest.mark.parametrize("actor,status", [(None, 401), ("buyer", 403), ("admin", 403)])
async def test_upload_roles_preserved(client, db, market, storage, actor, status):
    client.headers.pop("Content-Type", None)
    before = await snapshot(db)
    response = await client.post(
        f"/api/v1/seller/products/{market.product.id}/images",
        headers=headers(getattr(market, actor)) if actor else {},
        files=files(),
    )
    assert response.status_code == status, response.text
    storage.assert_not_awaited()
    assert await snapshot(db) == before


async def test_banner_oversize_keeps_413(client, market, storage):
    client.headers.pop("Content-Type", None)
    response = await client.post(
        "/api/v1/admin/content/banners",
        headers=headers(market.admin),
        data={"title": "Synthetic banner", "position": "homepage_hero"},
        files={"image": ("large.png", b"x" * (MAX_IMAGE_BYTES + 1), "image/png")},
    )
    assert response.status_code == 413, response.text
    storage.assert_not_awaited()


@pytest.mark.parametrize(
    "amount,valid", [(99, False), (100, True), (500000, True), (500001, False)]
)
async def test_native_price_constraints_still_match_policy(db, market, amount, valid):
    async def update():
        async with db.begin_nested():
            market.product.sale_price = None
            market.product.price = Decimal(amount)
            await db.flush()

    if valid:
        await update()
    else:
        with pytest.raises(IntegrityError):
            await update()


@pytest.mark.parametrize("maximum,status", [(500000, 200), (500001, 422)])
async def test_catalogue_filter_policy_preserved(client, market, maximum, status):
    response = await client.get(f"/api/v1/products?min_price=0&max_price={maximum}")
    assert response.status_code == status, response.text
