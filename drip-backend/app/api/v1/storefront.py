"""Public marketplace discovery, returning only approved storefront fields."""

from datetime import UTC, datetime
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import NotFoundError
from app.models.admin import Banner
from app.models.product import Category, Product
from app.models.seller import Seller, SellerStatus
from app.schemas.admin import BannerResponse
from app.schemas.product import CategoryResponse, CataloguePage
from app.services.product_service import ProductService

router = APIRouter(tags=["storefront"])
DB = Annotated[AsyncSession, Depends(get_db)]


def brand_response(seller):
    return {
        key: getattr(seller, key)
        for key in (
            "id",
            "slug",
            "brand_name",
            "description",
            "logo_url",
            "brand_color",
            "return_policy",
            "whatsapp_number",
            "instagram_handle",
        )
    }


@router.get("/categories")
async def categories(db: DB):
    rows = (
        await db.scalars(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order, Category.name, Category.id)
        )
    ).all()
    active_ids = {c.id for c in rows}
    visible = {}

    def is_visible(category, seen=None):
        seen = set() if seen is None else seen
        if category.id in seen:
            return False
        seen.add(category.id)
        if category.parent_id is None:
            return True
        parent = next((c for c in rows if c.id == category.parent_id), None)
        return parent is not None and is_visible(parent, seen)

    return {
        "data": [
            {
                "id": c.id,
                "parent_id": c.parent_id,
                "name": c.name,
                "slug": c.slug,
                "image_url": c.image_url,
                "sort_order": c.sort_order,
            }
            for c in rows
            if is_visible(c)
        ]
    }


@router.get("/brands")
async def brands(
    db: DB,
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
):
    query = select(Seller).where(Seller.status == SellerStatus.active, Seller.deleted_at.is_(None))
    if q:
        query = query.where(Seller.brand_name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (
        await db.scalars(
            query.order_by(Seller.brand_name, Seller.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    return {
        "data": [brand_response(s) for s in rows],
        "pagination": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/brands/{slug}")
async def brand_detail(slug: str, db: DB):
    seller = await db.scalar(
        select(Seller).where(
            Seller.slug == slug, Seller.status == SellerStatus.active, Seller.deleted_at.is_(None)
        )
    )
    if not seller:
        raise NotFoundError("Brand not found")
    return brand_response(seller)


@router.get("/brands/{slug}/products", response_model=CataloguePage)
async def brand_products(
    slug: str,
    db: DB,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|rating|trending)$"),
):
    brand = await brand_detail(slug, db)
    return await ProductService(db).get_catalogue(
        seller_id=brand["id"], limit=limit, cursor=cursor, sort=sort
    )


@router.get("/content/banners", response_model=list[BannerResponse])
async def public_banners(
    db: DB,
    position: str | None = Query(None, pattern="^(homepage_hero|homepage_secondary|category_top)$"),
):
    now = datetime.now(UTC)
    query = select(Banner).where(
        Banner.is_active.is_(True),
        or_(Banner.valid_from.is_(None), Banner.valid_from <= now),
        or_(Banner.valid_until.is_(None), Banner.valid_until > now),
    )
    if position:
        query = query.where(Banner.position == position)
    return list((await db.scalars(query.order_by(Banner.sort_order, Banner.id))).all())
