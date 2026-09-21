from __future__ import annotations

import base64
import json
from decimal import Decimal
from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime, timedelta

from sqlalchemy import select, update, func, and_, or_, desc, asc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.product import (
    Product, ProductImage, ProductVariant, ProductInventory, Category, Tag, product_tags
)
from app.models.seller import Seller


class ProductRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create(self, **kwargs) -> Product:
        product = Product(**kwargs)
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def add_image(self, product_id: UUID, **kwargs) -> ProductImage:
        image = ProductImage(product_id=product_id, **kwargs)
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return image

    # ── Reads ──────────────────────────────────────────────────────────────────

    async def get_by_id(
        self, product_id: UUID, *, load_full: bool = False
    ) -> Optional[Product]:
        q = select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
        if load_full:
            q = q.options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.inventory),
                selectinload(Product.seller),
                selectinload(Product.category),
                selectinload(Product.tags),
            )
        else:
            q = q.options(selectinload(Product.images), selectinload(Product.variants))
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Product]:
        result = await self.db.execute(
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.inventory),
                selectinload(Product.seller),
                selectinload(Product.category),
                selectinload(Product.tags),
            )
            .where(
                Product.slug == slug,
                Product.deleted_at.is_(None),
                Product.is_published.is_(True),
                Product.admin_hidden.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        result = await self.db.execute(
            select(Product.id).where(Product.slug == slug, Product.deleted_at.is_(None))
        )
        return result.scalar_one_or_none() is not None

    async def get_seller_products(
        self,
        seller_id: UUID,
        status: str = "all",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[Sequence[Product], int]:
        q = select(Product).where(
            Product.seller_id == seller_id,
            Product.deleted_at.is_(None),
        )
        if status == "published":
            q = q.where(Product.is_published.is_(True))
        elif status == "draft":
            q = q.where(Product.is_published.is_(False))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            q.options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.inventory),
                selectinload(Product.category),
            )
            .order_by(desc(Product.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def list_catalogue(
        self,
        *,
        category_id: Optional[UUID] = None,
        seller_id: Optional[UUID] = None,
        size_alpha: Optional[list[str]] = None,
        size_numeric: Optional[list[str]] = None,
        colours: Optional[list[str]] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        on_sale: Optional[bool] = None,
        is_new: Optional[bool] = None,
        q: Optional[str] = None,
        sort: str = "newest",
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> tuple[Sequence[Product], Optional[str]]:
        query = select(Product).where(
            Product.deleted_at.is_(None),
            Product.is_published.is_(True),
            Product.admin_hidden.is_(False),
        )

        if category_id:
            query = query.where(Product.category_id == category_id)
        if seller_id:
            query = query.where(Product.seller_id == seller_id)
        if min_price:
            query = query.where(Product.price >= min_price)
        if max_price:
            query = query.where(Product.price <= max_price)
        if on_sale:
            query = query.where(Product.sale_price.isnot(None))
        if is_new:
            cutoff = datetime.utcnow() - timedelta(days=14)
            query = query.where(Product.created_at >= cutoff)
        if q:
            search = f"%{q}%"
            query = query.where(
                or_(Product.name.ilike(search), Product.description.ilike(search))
            )
        if size_alpha or size_numeric:
            size_vals = list(size_alpha or []) + list(size_numeric or [])
            query = query.join(ProductVariant, Product.id == ProductVariant.product_id).where(
                ProductVariant.size_value.in_(size_vals),
                ProductVariant.is_active.is_(True),
            )
        if colours:
            query = query.join(ProductVariant, Product.id == ProductVariant.product_id, isouter=True).where(
                ProductVariant.colour.in_(colours)
            )

        # Cursor decode
        if cursor:
            try:
                cursor_data = json.loads(base64.b64decode(cursor))
                cursor_dt   = datetime.fromisoformat(cursor_data["created_at"])
                cursor_id   = UUID(cursor_data["id"])
                query = query.where(
                    or_(
                        Product.created_at < cursor_dt,
                        and_(Product.created_at == cursor_dt, Product.id < cursor_id),
                    )
                )
            except Exception:
                pass

        # Sort
        if sort == "price_asc":
            query = query.order_by(asc(Product.price), desc(Product.created_at))
        elif sort == "price_desc":
            query = query.order_by(desc(Product.price), desc(Product.created_at))
        elif sort == "rating":
            query = query.order_by(desc(Product.avg_rating), desc(Product.created_at))
        elif sort == "trending":
            query = query.order_by(desc(Product.view_count), desc(Product.created_at))
        else:  # newest
            query = query.order_by(desc(Product.created_at), desc(Product.id))

        query = query.options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.inventory),
            selectinload(Product.seller),
        ).distinct().limit(limit + 1)

        result  = await self.db.execute(query)
        rows    = result.scalars().all()
        has_next = len(rows) > limit
        rows     = rows[:limit]

        next_cursor = None
        if has_next and rows:
            last = rows[-1]
            next_cursor = base64.b64encode(
                json.dumps({"created_at": last.created_at.isoformat(), "id": str(last.id)}).encode()
            ).decode()

        return rows, next_cursor

    async def search_suggestions(self, q: str, limit: int = 5) -> tuple[Sequence[Product], Sequence[Seller]]:
        search = f"%{q}%"
        products = (
            await self.db.execute(
                select(Product)
                .options(selectinload(Product.images), selectinload(Product.seller))
                .where(
                    Product.name.ilike(search),
                    Product.is_published.is_(True),
                    Product.deleted_at.is_(None),
                )
                .limit(limit)
            )
        ).scalars().all()

        sellers = (
            await self.db.execute(
                select(Seller).where(
                    Seller.brand_name.ilike(search),
                    Seller.deleted_at.is_(None),
                ).limit(limit)
            )
        ).scalars().all()

        return products, sellers

    # ── Updates ────────────────────────────────────────────────────────────────

    async def update(self, product_id: UUID, **kwargs) -> Optional[Product]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.db.execute(
            update(Product).where(Product.id == product_id).values(**kwargs)
        )
        await self.db.flush()
        return await self.get_by_id(product_id)

    async def set_published(self, product_id: UUID, is_published: bool) -> None:
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(is_published=is_published, updated_at=datetime.utcnow())
        )

    async def soft_delete(self, product_id: UUID) -> None:
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(deleted_at=datetime.utcnow(), is_published=False)
        )

    async def increment_view_count(self, product_id: UUID) -> None:
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(view_count=Product.view_count + 1)
        )

    # ── Image management ───────────────────────────────────────────────────────

    async def get_image_count(self, product_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(ProductImage.id)).where(ProductImage.product_id == product_id)
        )
        return result.scalar_one() or 0

    async def set_primary_image(self, product_id: UUID, image_id: UUID) -> None:
        await self.db.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_primary=False)
        )
        await self.db.execute(
            update(ProductImage)
            .where(ProductImage.id == image_id)
            .values(is_primary=True)
        )

    # ── Category helpers ───────────────────────────────────────────────────────

    async def get_category(self, category_id: UUID) -> Optional[Category]:
        result = await self.db.execute(
            select(Category).where(Category.id == category_id, Category.is_active.is_(True))
        )
        return result.scalar_one_or_none()


class VariantRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, product_id: UUID, **kwargs) -> ProductVariant:
        variant = ProductVariant(product_id=product_id, **kwargs)
        self.db.add(variant)
        await self.db.flush()
        await self.db.refresh(variant)
        return variant

    async def get_by_product(self, product_id: UUID) -> Sequence[ProductVariant]:
        result = await self.db.execute(
            select(ProductVariant)
            .options(selectinload(ProductVariant.inventory))
            .where(ProductVariant.product_id == product_id, ProductVariant.is_active.is_(True))
        )
        return result.scalars().all()

    async def sku_exists(self, sku: str) -> bool:
        result = await self.db.execute(
            select(ProductVariant.id).where(ProductVariant.sku == sku)
        )
        return result.scalar_one_or_none() is not None