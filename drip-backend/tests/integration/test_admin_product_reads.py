"""Native admin catalogue reads retain filters, visibility and exact stored prices."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_marketplace_regressions import market as marketplace_fixture
from test_resource_ownership import headers

from app.models.product import Product
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole

pytestmark = pytest.mark.integration
market = marketplace_fixture
WHEN = datetime(2026, 10, 19, 1, 0, tzinfo=UTC)


@pytest.fixture
async def catalogue(db, market):
    user = User(
        email="admin-list-other@example.com",
        password_hash="synthetic-only",
        role=UserRole.seller,
        has_verified_email=True,
    )
    db.add(user)
    await db.flush()
    seller = Seller(
        user_id=user.id,
        brand_name="Other Brand",
        slug="admin-list-other",
        status=SellerStatus.active,
        total_slots=50,
    )
    db.add(seller)
    await db.flush()
    market.product.price, market.product.sale_price = Decimal("1500.25"), Decimal("1200.75")
    market.product.created_at = WHEN
    rows = {"visible": market.product}
    for name, owner, price, published, hidden, deleted in [
        ("draft", market.seller.id, "200.20", False, False, False),
        ("hidden", market.seller.id, "300.05", True, True, False),
        ("other", seller.id, "700.10", True, False, False),
        ("other_hidden", seller.id, "800.99", False, True, False),
        ("deleted", seller.id, "900.30", True, False, True),
    ]:
        item = Product(
            seller_id=owner,
            name=name,
            slug=f"admin-list-{name}",
            price=Decimal(price),
            is_published=published,
            admin_hidden=hidden,
            created_at=WHEN,
            deleted_at=WHEN if deleted else None,
        )
        db.add(item)
        rows[name] = item
    await db.commit()
    return SimpleNamespace(rows=rows, other=seller)


async def product_snapshot(db):
    return sorted(
        tuple(map(str, row)) for row in (await db.execute(select(*Product.__table__.columns))).all()
    )


@pytest.mark.parametrize(
    "seller,hidden,names",
    [
        (None, None, {"visible", "draft", "hidden", "other", "other_hidden"}),
        ("own", None, {"visible", "draft", "hidden"}),
        ("other", None, {"other", "other_hidden"}),
        (None, "true", {"hidden", "other_hidden"}),
        (None, "false", {"visible", "draft", "other"}),
        ("own", "true", {"hidden"}),
        ("missing", None, set()),
    ],
)
async def test_admin_filters_exact_money_and_no_mutation(
    client, db, market, catalogue, seller, hidden, names
):
    params = {}
    if seller:
        params["seller_id"] = str(
            market.seller.id
            if seller == "own"
            else catalogue.other.id
            if seller == "other"
            else uuid4()
        )
    if hidden is not None:
        params["admin_hidden"] = hidden
    before = await product_snapshot(db)
    response = await client.get(
        "/api/v1/admin/products", params=params, headers=headers(market.admin)
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"data", "pagination"}
    assert payload["pagination"] == {"page": 1, "per_page": 25, "total": len(names)}
    expected = sorted((catalogue.rows[name] for name in names), key=lambda p: p.id, reverse=True)
    assert payload["data"] == [
        {
            "id": str(p.id),
            "seller_id": str(p.seller_id),
            "name": p.name,
            "price": format(p.price, ".2f"),
            "slug": p.slug,
            "is_published": p.is_published,
            "admin_hidden": p.admin_hidden,
        }
        for p in expected
    ]
    assert await product_snapshot(db) == before


@pytest.mark.parametrize("actor,status", [(None, 401), ("buyer", 403), ("seller_user", 403)])
async def test_non_admin_cannot_read_admin_catalogue(client, db, market, catalogue, actor, status):
    before = await product_snapshot(db)
    response = await client.get(
        "/api/v1/admin/products", headers=headers(getattr(market, actor)) if actor else {}
    )
    assert response.status_code == status, response.text
    assert "price" not in response.json()["error"]
    assert await product_snapshot(db) == before


@pytest.mark.parametrize("query", ["page=0", "seller_id=invalid", "admin_hidden=invalid"])
async def test_invalid_filters_reject_before_reads(client, market, query):
    response = await client.get(f"/api/v1/admin/products?{query}", headers=headers(market.admin))
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_equal_timestamp_pagination_has_no_gaps_or_duplicates(client, db, market, catalogue):
    for index in range(22):
        db.add(
            Product(
                seller_id=market.seller.id,
                name=f"Page {index}",
                slug=f"admin-page-{index}",
                price=Decimal("100.25"),
                created_at=WHEN,
            )
        )
    await db.commit()
    expected_ids = sorted(
        (await db.scalars(select(Product.id).where(Product.deleted_at.is_(None)))).all(),
        reverse=True,
    )
    before = await product_snapshot(db)
    result = []
    for page, count in [(1, 25), (2, 2), (3, 0)]:
        response = await client.get(
            f"/api/v1/admin/products?page={page}", headers=headers(market.admin)
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["pagination"] == {"page": page, "per_page": 25, "total": 27}
        assert len(payload["data"]) == count
        result.extend(UUID(item["id"]) for item in payload["data"])
    assert result == expected_ids
    assert len(set(result)) == 27
    assert await product_snapshot(db) == before
