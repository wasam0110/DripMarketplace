"""Admin bulk corrections: native transaction failures and stored results."""

import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_marketplace_regressions import market as marketplace_fixture
from test_release_native import db as committed_db
from test_resource_ownership import request

from app.api.v1.inventory import BulkStockUpdateItem, BulkStockUpdateRequest
from app.models.product import Product, ProductInventory, ProductVariant, SizeType
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.repositories.inventory_repo import InventoryRepository
from app.services.inventory_service import InventoryService

pytestmark = pytest.mark.integration
db = committed_db
market = marketplace_fixture
PATH = "/admin/inventory/bulk-update"


@pytest.fixture
async def variants(db, market):
    ids = [market.variant.id]
    for size in ("L", "XL"):
        variant = ProductVariant(
            product_id=market.product.id,
            sku=f"BULK-{size}",
            size_type=SizeType.alpha,
            size_value=size,
            colour="Ivory",
        )
        db.add(variant)
        await db.flush()
        db.add(ProductInventory(variant_id=variant.id, stock=8, reserved=0))
        ids.append(variant.id)
    await db.commit()
    return sorted(ids)


def items(ids, stocks):
    return [
        BulkStockUpdateItem(variant_id=key, stock=value)
        for key, value in zip(ids, stocks, strict=True)
    ]


async def stored(engine, ids):
    async with async_sessionmaker(engine)() as session:
        rows = (
            await session.execute(
                select(
                    ProductInventory.variant_id,
                    ProductInventory.stock,
                    ProductInventory.reserved,
                    ProductInventory.reorder_point,
                ).where(ProductInventory.variant_id.in_(ids))
            )
        ).all()
        return {row[0]: tuple(row[1:]) for row in rows}


async def test_database_row_failure_preserves_other_successes(
    db,
    market,
    variants,
    client,
    isolated_redis,
    test_engine,
):
    # Test-schema-only constraint forces an actual PostgreSQL statement failure.
    await db.execute(
        text(
            "ALTER TABLE product_inventory ADD CONSTRAINT audit_reject_thirteen CHECK (stock <> 13)"
        )
    )
    await db.commit()
    response = await request(
        client,
        isolated_redis,
        market.admin,
        "POST",
        PATH,
        json={"updates": [item.model_dump(mode="json") for item in items(variants, [11, 13, 12])]},
    )
    assert response.status_code == 200, response.text
    saved = await stored(test_engine, variants)
    assert saved[variants[0]][0] == 11, (response.json(), saved)
    assert response.json() == {
        "updated": 2,
        "failed": 1,
        "errors": [{"variant_id": str(variants[1]), "error": "Inventory update failed"}],
    }
    assert await stored(test_engine, variants) == {
        variants[0]: (11, 0, 5),
        variants[1]: (8, 0, 5),
        variants[2]: (12, 0, 5),
    }


async def test_mixed_results_and_repeated_absolute_updates(
    db,
    market,
    variants,
    client,
    isolated_redis,
    test_engine,
):
    inv = await db.scalar(
        select(ProductInventory).where(ProductInventory.variant_id == variants[1])
    )
    inv.reserved = 6
    inv.reorder_point = 9
    await db.commit()
    missing = uuid4()
    payload = {
        "updates": [
            item.model_dump(mode="json")
            for item in items([missing, variants[2], variants[1], variants[0]], [5, 0, 3, 999_999])
        ]
    }
    for _ in range(2):
        response = await request(client, isolated_redis, market.admin, "POST", PATH, json=payload)
        assert response.status_code == 200, response.text
        result = response.json()
        assert (result["updated"], result["failed"]) == (2, 2)
        assert [error["variant_id"] for error in result["errors"]] == [
            str(missing),
            str(variants[1]),
        ]
        assert await stored(test_engine, variants) == {
            variants[0]: (999_999, 0, 5),
            variants[1]: (8, 6, 9),
            variants[2]: (0, 0, 5),
        }


@pytest.mark.parametrize(
    "invalid",
    [
        "duplicate",
        "empty",
        "oversized",
        "negative",
        "too_large",
        "fractional",
        "bad_uuid",
        "reserved",
        "reorder_point",
        "seller_id",
        "unknown_batch_field",
    ],
)
async def test_invalid_batch_is_rejected_before_any_write(
    invalid,
    market,
    client,
    isolated_redis,
    test_engine,
):
    key = str(market.variant.id)
    row = {"variant_id": key, "stock": 11}
    payload = {"updates": [row]}
    if invalid == "duplicate":
        payload["updates"].append({"variant_id": key, "stock": 12})
    elif invalid == "empty":
        payload["updates"] = []
    elif invalid == "oversized":
        payload["updates"] += [{"variant_id": str(uuid4()), "stock": 2} for _ in range(500)]
    elif invalid in ("negative", "too_large", "fractional", "bad_uuid"):
        bad = {"variant_id": str(uuid4()), "stock": 2}
        bad["variant_id" if invalid == "bad_uuid" else "stock"] = {
            "negative": -1,
            "too_large": 1_000_000,
            "fractional": 1.5,
            "bad_uuid": "invalid",
        }[invalid]
        payload["updates"].append(bad)
    elif invalid == "unknown_batch_field":
        payload["force"] = True
    else:
        row[invalid] = str(uuid4()) if invalid == "seller_id" else 0
    response = await request(client, isolated_redis, market.admin, "POST", PATH, json=payload)
    assert response.status_code == 422, response.text
    assert await stored(test_engine, [market.variant.id]) == {market.variant.id: (8, 0, 5)}


@pytest.mark.parametrize("role", ["buyer", "seller_user", "anonymous"])
async def test_only_admin_can_bulk_correct_stock(
    role,
    market,
    client,
    isolated_redis,
    test_engine,
):
    payload = {"updates": [{"variant_id": str(market.variant.id), "stock": 11}]}
    if role == "anonymous":
        response = await client.post("/api/v1" + PATH, json=payload)
        assert response.status_code == 401
    else:
        response = await request(
            client, isolated_redis, getattr(market, role), "POST", PATH, json=payload
        )
        assert response.status_code == 403, response.text
    assert await stored(test_engine, [market.variant.id]) == {market.variant.id: (8, 0, 5)}


@pytest.mark.parametrize("failure", ["commit", "unexpected_statement"])
async def test_fatal_failure_rolls_back_batch_without_success_response(
    failure,
    db,
    variants,
    test_engine,
    monkeypatch,
):
    original_execute = db.execute
    calls = 0

    async def fail_commit():
        raise RuntimeError("injected commit failure")

    async def fail_second_statement(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected statement failure")
        return await original_execute(*args, **kwargs)

    if failure == "commit":
        monkeypatch.setattr(db, "commit", fail_commit)
    else:
        monkeypatch.setattr(db, "execute", fail_second_statement)
    with pytest.raises(RuntimeError, match="injected"):
        await InventoryService(db).bulk_update_stock(items(variants, [11, 12, 14]))
    assert not db.in_transaction()
    assert await stored(test_engine, variants) == dict.fromkeys(variants, (8, 0, 5))


@pytest.mark.parametrize("winner", ["bulk", "reservation"])
async def test_bulk_correction_and_reservation_serialize(
    winner,
    market,
    test_engine,
):
    key = market.variant.id
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def bulk(session):
        return await InventoryService(session).bulk_update_stock(items([key], [3]))

    async def reserve(session):
        result = await InventoryRepository(session).reserve(key, 6)
        await session.commit()
        return result

    async def competitor():
        async with factory() as session:
            return await (reserve(session) if winner == "bulk" else bulk(session))

    async with factory() as first:
        await first.execute(
            select(ProductInventory).where(ProductInventory.variant_id == key).with_for_update()
        )
        task = asyncio.create_task(competitor())
        try:
            await asyncio.sleep(0.1)
            assert not task.done()
            result = await (bulk(first) if winner == "bulk" else reserve(first))
            other = await asyncio.wait_for(task, 10)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    if winner == "bulk":
        assert result.updated == 1 and other is False
        expected = (3, 0, 5)
    else:
        assert result is True and other.updated == 0 and other.failed == 1
        expected = (8, 6, 5)
    assert await stored(test_engine, [key]) == {key: expected}


async def test_opposite_order_batches_lock_consistently(db, variants, test_engine, monkeypatch):
    # Record actual UPDATE order, then exercise overlapping independent transactions.
    original = db.execute
    order = []

    async def record(statement, *args, **kwargs):
        if getattr(statement, "is_update", False):
            order.append(statement.compile().params["variant_id_1"])
        return await original(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", record)
    await InventoryService(db).bulk_update_stock(items(list(reversed(variants)), [10, 10, 10]))
    assert order == variants
    gate = asyncio.Event()

    async def run(keys, stock):
        async with async_sessionmaker(test_engine)() as session:
            await gate.wait()
            return await InventoryService(session).bulk_update_stock(
                items(keys, [stock] * len(keys))
            )

    tasks = [
        asyncio.create_task(run(variants, 20)),
        asyncio.create_task(run(list(reversed(variants)), 30)),
    ]
    gate.set()
    results = await asyncio.wait_for(asyncio.gather(*tasks), 15)
    assert all(result.updated == 3 and result.failed == 0 for result in results)
    saved = await stored(test_engine, variants)
    assert {value[0] for value in saved.values()} in ({20}, {30})


async def test_admin_batch_can_update_two_sellers(
    db,
    market,
    client,
    isolated_redis,
    test_engine,
):
    user = User(email="bulk-other@example.com", password_hash="test", role=UserRole.seller)
    db.add(user)
    await db.flush()
    seller = Seller(
        user_id=user.id,
        brand_name="Bulk Other",
        slug="bulk-other",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(seller)
    await db.flush()
    product = Product(
        seller_id=seller.id, name="Other", slug="bulk-other-product", price=Decimal("500")
    )
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="BULK-OTHER",
        size_type=SizeType.alpha,
        size_value="M",
        colour="Blue",
    )
    db.add(variant)
    await db.flush()
    db.add(ProductInventory(variant_id=variant.id, stock=4, reserved=1))
    await db.commit()
    keys = [market.variant.id, variant.id]
    response = await request(
        client,
        isolated_redis,
        market.admin,
        "POST",
        PATH,
        json={"updates": [item.model_dump(mode="json") for item in items(keys, [12, 20])]},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"updated": 2, "failed": 0, "errors": []}
    assert await stored(test_engine, keys) == {keys[0]: (12, 0, 5), keys[1]: (20, 1, 5)}


@pytest.mark.parametrize("invalid", ["duplicate", "too_large"])
async def test_internal_call_validates_before_writing(invalid, db, market, test_engine):
    key = market.variant.id
    updates = [{"variant_id": key, "stock": 11}]
    updates.append(
        {
            "variant_id": key if invalid == "duplicate" else uuid4(),
            "stock": 12 if invalid == "duplicate" else 1_000_000,
        }
    )
    with pytest.raises(ValidationError):
        await InventoryService(db).bulk_update_stock(updates)
    assert not db.in_transaction()
    assert await stored(test_engine, [key]) == {key: (8, 0, 5)}


def test_contract_accepts_exactly_500_unique_updates():
    batch = BulkStockUpdateRequest(
        updates=[{"variant_id": uuid4(), "stock": "999999"} for _ in range(500)]
    )
    assert len(batch.updates) == 500
    assert all(item.stock == 999_999 for item in batch.updates)
