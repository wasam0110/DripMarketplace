"""Protected review moderation, private metadata and versioned rating updates."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.api.v1.admin.reviews import ModerateReviewRequest, moderate_review
from app.core.exceptions import ConflictError
from app.models.product import Product
from app.models.review import Review, ReviewImage, ReviewStatus
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole
from app.schemas.user import ReviewResponse

pytestmark = pytest.mark.integration
market = marketplace_fixture
WHEN = datetime(2026, 10, 28, tzinfo=UTC)


@pytest.fixture
async def review(db, market):
    item = Review(
        user_id=market.buyer.id,
        product_id=market.product.id,
        rating=4,
        title="Linen review",
        body="Customer content stays unchanged.",
        status=ReviewStatus.pending,
        created_at=WHEN,
        updated_at=WHEN,
    )
    db.add(item)
    await db.flush()
    db.add(ReviewImage(review_id=item.id, url="https://example.test/review.webp", sort_order=0))
    await db.commit()
    return item


@pytest.mark.parametrize("role", ["guest", "buyer", "seller_user", "unverified"])
@pytest.mark.parametrize("operation", ["list", "detail", "patch"])
async def test_admin_only(client, db, market, review, role, operation):
    if role == "unverified":
        market.admin.has_verified_email = False
        await db.commit()
    auth = (
        {}
        if role == "guest"
        else headers(market.admin if role == "unverified" else getattr(market, role))
    )
    path = "/api/v1/admin/reviews" + ("" if operation == "list" else f"/{review.id}")
    response = (
        await client.patch(path, headers=auth, json={"status": "approved"})
        if operation == "patch"
        else await client.get(path, headers=auth)
    )
    assert response.status_code in (401, 403), response.text
    await db.refresh(review)
    assert review.status == ReviewStatus.pending
    assert review.moderated_at is None


async def test_private_detail_list_and_aggregate(client, db, market, review):
    auth = headers(market.admin)
    path = f"/api/v1/admin/reviews/{review.id}"
    before = (await client.get(path, headers=auth)).json()
    assert before["images"][0]["url"] == "https://example.test/review.webp"
    assert before["admin_note"] is None and before["moderated_at"] is None
    assert before["status"] == "pending"
    for status, note, expected_count in [
        ("approved", "  Checked purchase  ", 1),
        ("hidden", "Hold for inspection", 0),
        ("rejected", "Not eligible", 0),
        ("approved", " ", 1),
    ]:
        result = await client.patch(
            path,
            headers=auth,
            json={
                "status": status,
                "admin_note": note,
                "expected_updated_at": before["updated_at"],
            },
        )
        assert result.status_code == 200, result.text
        after = result.json()
        assert after["status"] == status and after["admin_note"] == (note.strip() or None)
        assert after["moderated_at"] and after["updated_at"] != before["updated_at"]
        assert after["body"] == before["body"] and after["images"] == before["images"]
        assert (await client.get(path, headers=auth)).json() == after
        listed = (
            await client.get("/api/v1/admin/reviews", headers=auth, params={"status": status})
        ).json()
        assert listed == {"data": [after], "page": 1, "per_page": 25, "total": 1}
        await db.refresh(market.product)
        assert market.product.review_count == expected_count
        assert market.product.avg_rating == Decimal(4 if expected_count else 0)
        before = after
    assert "admin_note" not in ReviewResponse.model_fields
    assert "moderated_at" not in ReviewResponse.model_fields


async def test_stale_version_conflicts_without_overwrite(client, db, market, review):
    auth, path = headers(market.admin), f"/api/v1/admin/reviews/{review.id}"
    old = (await client.get(path, headers=auth)).json()
    first = await client.patch(
        path,
        headers=auth,
        json={
            "status": "hidden",
            "admin_note": "First decision",
            "expected_updated_at": old["updated_at"],
        },
    )
    second = await client.patch(
        path,
        headers=auth,
        json={
            "status": "approved",
            "admin_note": "Stale decision",
            "expected_updated_at": old["updated_at"],
        },
    )
    assert first.status_code == 200 and second.status_code == 409
    assert (await client.get(path, headers=auth)).json() == first.json()
    await db.refresh(market.product)
    assert market.product.review_count == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "pending"},
        {"status": "delete"},
        {"status": "approved", "admin_note": "x" * 1001},
        {"status": "approved", "expected_updated_at": "2026-10-28T00:00:00"},
    ],
)
async def test_invalid_decisions(client, market, review, payload):
    response = await client.patch(
        f"/api/v1/admin/reviews/{review.id}", headers=headers(market.admin), json=payload
    )
    assert response.status_code == 422


async def test_missing_and_invalid_queries(client, market, review):
    auth = headers(market.admin)
    for method in (client.get, client.patch):
        kwargs = {"json": {"status": "approved"}} if method == client.patch else {}
        assert (
            await method(f"/api/v1/admin/reviews/{uuid4()}", headers=auth, **kwargs)
        ).status_code == 404
    for params in ({"page": 0}, {"status": "unknown"}):
        assert (
            await client.get("/api/v1/admin/reviews", headers=auth, params=params)
        ).status_code == 422
    page = (await client.get("/api/v1/admin/reviews?page=2", headers=auth)).json()
    assert page == {"data": [], "total": 1, "page": 2, "per_page": 25}


async def test_tied_dates_are_stably_paginated(client, db, market, review):
    for index in range(26):
        user = User(
            email=f"review-{index}@example.test",
            password_hash="synthetic-only",
            role=UserRole.customer,
        )
        db.add(user)
        await db.flush()
        db.add(
            Review(
                user_id=user.id,
                product_id=market.product.id,
                rating=3,
                created_at=WHEN,
                updated_at=WHEN,
            )
        )
    await db.commit()
    results = [
        (
            await client.get(
                "/api/v1/admin/reviews", params={"page": page}, headers=headers(market.admin)
            )
        ).json()
        for page in (1, 2)
    ]
    ids = [row["id"] for result in results for row in result["data"]]
    assert len(ids) == len(set(ids)) == 27
    assert ids == sorted(ids)
    assert [len(result["data"]) for result in results] == [25, 2]


async def test_concurrent_versioned_decisions_have_one_winner(test_engine):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sessions() as db:
        user = User(
            email="race-review@example.test", password_hash="synthetic-only", role=UserRole.customer
        )
        db.add(user)
        await db.flush()
        seller = Seller(
            user_id=user.id,
            brand_name="Race Brand",
            slug="race-review-brand",
            status=SellerStatus.active,
        )
        db.add(seller)
        await db.flush()
        product = Product(
            seller_id=seller.id, name="Race product", slug="race-review-product", price=100
        )
        db.add(product)
        await db.flush()
        item = Review(user_id=user.id, product_id=product.id, rating=5, updated_at=WHEN)
        db.add(item)
        await db.commit()
        review_id, product_id = item.id, product.id

    loaded_count = 0
    ready = asyncio.Event()

    async def decide(status):
        nonlocal loaded_count
        async with sessions() as db:
            # Deliberately preload both identity maps before either lock is acquired.
            loaded = await db.scalar(select(Review).where(Review.id == review_id))
            assert loaded.updated_at == WHEN
            loaded_count += 1
            if loaded_count == 2:
                ready.set()
            await ready.wait()
            try:
                return await moderate_review(
                    review_id,
                    ModerateReviewRequest(status=status, expected_updated_at=WHEN),
                    db,
                    {},
                )
            except ConflictError:
                await db.rollback()
                return None

    tasks = [asyncio.create_task(decide(status)) for status in ("approved", "hidden")]
    results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=20)
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    async with sessions() as db:
        product = await db.get(Product, product_id)
        assert product.review_count == (1 if winners[0].status == "approved" else 0)
