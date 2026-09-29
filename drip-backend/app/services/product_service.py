from __future__ import annotations

import re
import uuid
from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models.analytics import AnalyticsEvent
from sqlalchemy.orm import selectinload
from app.models.product import ProductVariant, ProductImage, Category
from app.models.seller import Seller

from app.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ConflictError,
    BusinessRuleError,
)
from app.models.product import Product, SizeType
from app.models.seller import SellerStatus
from app.repositories.product_repo import ProductRepository, VariantRepository
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.seller_repo import SellerRepository
from app.schemas.product import (
    CreateProductRequest,
    UpdateProductRequest,
    ProductCardResponse,
    ProductDetailResponse,
    CataloguePage,
    CursorPagination,
    SellerProductRowResponse,
    SellerProductsPage,
    SlotInfoResponse,
    VariantWithStockResponse,
    ProductImageResponse,
    SellerSummaryResponse,
    CategoryResponse,
    SearchSuggestionsResponse,
    SearchSuggestion,
    BrandSuggestion,
)

MAX_IMAGES_PER_PRODUCT = 6


def _slugify(text: str) -> str:
    text = text.lower().strip().encode("ascii", errors="ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:250]


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.product_repo = ProductRepository(db)
        self.variant_repo = VariantRepository(db)
        self.inv_repo = InventoryRepository(db)
        self.seller_repo = SellerRepository(db)

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create_product(
        self, seller_id: UUID, payload: CreateProductRequest
    ) -> ProductDetailResponse:
        await self.db.execute(select(Seller.id).where(Seller.id == seller_id).with_for_update())
        seller = await self.seller_repo.get_by_id(seller_id)
        if not seller or seller.status != SellerStatus.active:
            raise PermissionDeniedError("Seller account is not active")

        await self._validate_category(payload.category_id)
        # If trying to publish immediately, check slot
        if payload.is_published:
            if seller.slots_used >= seller.total_slots:
                raise BusinessRuleError("No product slots available. Purchase extra slots.")

        slug = await self._unique_slug(payload.name)

        product = await self.product_repo.create(
            seller_id=seller_id,
            category_id=payload.category_id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            price=Decimal(payload.price),
            sale_price=Decimal(payload.sale_price) if payload.sale_price else None,
            is_published=False,  # always start draft; publish separately
            meta_title=payload.meta_title,
            meta_description=payload.meta_description,
        )

        # Create variants + inventory
        for v in payload.variants:
            sku = (
                v.sku or f"WHZ-{str(product.id)[:8].upper()}-{v.size_value}-{v.colour[:3].upper()}"
            )
            variant = await self.variant_repo.create(
                product_id=product.id,
                sku=sku,
                size_type=SizeType(v.size_type),
                size_value=v.size_value,
                colour=v.colour,
                price_override=Decimal(v.price_override) if v.price_override else None,
            )
            await self.inv_repo.create(variant.id, stock=v.stock)

        # Publish now if requested
        if payload.is_published and payload.variants:
            await self.product_repo.set_published(product.id, True)
            await self.seller_repo.increment_slots_used(seller_id)

        await self.db.commit()
        product = await self.product_repo.get_by_id(product.id, load_full=True)
        return self._to_detail(product)  # type: ignore[arg-type]

    # ── Update ─────────────────────────────────────────────────────────────────

    async def update_product(
        self, seller_id: UUID, product_id: UUID, payload: UpdateProductRequest
    ) -> ProductDetailResponse:
        product = await self._require_owned(seller_id, product_id)
        data = payload.model_dump(exclude_unset=True)
        for required in ("name", "description", "price"):
            if required in data and data[required] is None:
                raise BusinessRuleError(f"{required} cannot be null")
        if "category_id" in data:
            await self._validate_category(data["category_id"])
        price = data.get("price", product.price)
        sale = data.get("sale_price", product.sale_price)
        if sale is not None and sale >= price:
            raise BusinessRuleError("Sale price must be below the regular price")
        if "price" in data:
            data["price"] = Decimal(data["price"])
        if data.get("sale_price") is not None:
            data["sale_price"] = Decimal(data["sale_price"])
        await self.product_repo.update(product_id, **data)
        await self.db.commit()
        updated = await self.product_repo.get_by_id(product_id, load_full=True)
        return self._to_detail(updated)  # type: ignore[arg-type]

    # ── Publish / Unpublish ────────────────────────────────────────────────────

    async def publish_product(self, seller_id: UUID, product_id: UUID) -> dict:
        product = await self._require_owned(seller_id, product_id)
        seller = await self.seller_repo.get_by_id(seller_id)

        if product.is_published:
            raise BusinessRuleError("Product is already published")
        if not product.variants:
            raise BusinessRuleError("Add at least one variant before publishing")
        if not product.images:
            raise BusinessRuleError("Add at least one image before publishing")
        if seller.slots_used >= seller.total_slots:  # type: ignore[union-attr]
            raise BusinessRuleError(
                f"No slots available ({seller.slots_used}/{seller.total_slots}). "  # type: ignore[union-attr]
                "Purchase extra slots at PKR 50 each."
            )

        await self.product_repo.set_published(product_id, True)
        await self.seller_repo.increment_slots_used(seller_id)
        await self.db.commit()
        return {"message": "Product published successfully"}

    async def unpublish_product(self, seller_id: UUID, product_id: UUID) -> dict:
        product = await self._require_owned(seller_id, product_id)
        if not product.is_published:
            raise BusinessRuleError("Product is already unpublished")
        await self.product_repo.set_published(product_id, False)
        await self.seller_repo.decrement_slots_used(seller_id)
        await self.db.commit()
        return {"message": "Product unpublished. Slot freed."}

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete_product(self, seller_id: UUID, product_id: UUID) -> None:
        product = await self._require_owned(seller_id, product_id)
        if product.is_published:
            await self.seller_repo.decrement_slots_used(seller_id)
        await self.product_repo.soft_delete(product_id)
        await self.db.commit()

    # ── Image upload ───────────────────────────────────────────────────────────

    async def add_images(
        self,
        seller_id: UUID,
        product_id: UUID,
        image_urls: list[str],
    ) -> list[ProductImageResponse]:
        product = await self._require_owned(seller_id, product_id)
        current = await self.product_repo.get_image_count(product_id)
        remaining = MAX_IMAGES_PER_PRODUCT - current

        if len(image_urls) > remaining:
            raise BusinessRuleError(f"Maximum {MAX_IMAGES_PER_PRODUCT} images allowed per product")

        images = []
        for i, url in enumerate(image_urls):
            is_primary = current == 0 and i == 0
            img = await self.product_repo.add_image(
                product_id,
                url=url,
                sort_order=current + i,
                is_primary=is_primary,
            )
            images.append(ProductImageResponse.model_validate(img))

        await self.db.commit()
        return images

    # ── Public catalogue ───────────────────────────────────────────────────────

    async def get_catalogue(self, **filters) -> CataloguePage:
        rows, next_cursor = await self.product_repo.list_catalogue(**filters)
        if filters.get("q") and not filters.get("cursor"):
            self.db.add(
                AnalyticsEvent(
                    kind="search",
                    query=" ".join(filters["q"].lower().split())[:200],
                    result_count=len(rows),
                )
            )
            await self.db.commit()
        return CataloguePage(
            data=[self._to_card(p) for p in rows],
            pagination=CursorPagination(
                next_cursor=next_cursor,
                has_next=next_cursor is not None,
                limit=filters.get("limit", 20),
            ),
        )

    async def get_product_detail(self, product_id: UUID) -> ProductDetailResponse:
        product = await self.product_repo.get_by_id(product_id, load_full=True)
        if not self._is_public(product):
            raise NotFoundError("Product not found")
        self.db.add(AnalyticsEvent(kind="product_view", product_id=product_id))
        await self.product_repo.increment_view_count(product_id)
        await self.db.commit()
        return self._to_detail(product)

    async def get_product_by_slug(self, slug: str) -> ProductDetailResponse:
        product = await self.product_repo.get_by_slug(slug)
        if not self._is_public(product):
            raise NotFoundError("Product not found")
        self.db.add(AnalyticsEvent(kind="product_view", product_id=product.id))
        await self.product_repo.increment_view_count(product.id)
        await self.db.commit()
        return self._to_detail(product)

    async def get_variants(self, product_id: UUID) -> list[VariantWithStockResponse]:
        product = await self.product_repo.get_by_id(product_id, load_full=True)
        if not self._is_public(product):
            raise NotFoundError("Product not found")
        return [self._to_variant(v) for v in product.variants if v.is_active]

    async def search_suggestions(self, q: str) -> SearchSuggestionsResponse:
        products, sellers = await self.product_repo.search_suggestions(q)
        return SearchSuggestionsResponse(
            products=[
                SearchSuggestion(
                    id=p.id,
                    name=p.name,
                    primary_image=next((i.url for i in p.images if i.is_primary), None),
                    price=int(p.effective_price),
                    brand_name=p.seller.brand_name,
                )
                for p in products
            ],
            brands=[
                BrandSuggestion(id=s.id, brand_name=s.brand_name, logo_url=s.logo_url, slug=s.slug)
                for s in sellers
            ],
        )

    # ── Seller product list ────────────────────────────────────────────────────

    async def get_seller_products(
        self, seller_id: UUID, status: str = "all", page: int = 1
    ) -> SellerProductsPage:
        seller = await self.seller_repo.get_by_id(seller_id)
        if not seller:
            raise NotFoundError("Seller not found")

        products, _ = await self.product_repo.get_seller_products(seller_id, status, page)

        return SellerProductsPage(
            data=[
                SellerProductRowResponse(
                    id=p.id,
                    name=p.name,
                    slug=p.slug,
                    category=p.category.name if p.category else None,
                    price=int(p.price),
                    total_stock=sum((v.inventory.stock if v.inventory else 0) for v in p.variants),
                    is_published=p.is_published,
                    avg_rating=float(p.avg_rating),
                    review_count=p.review_count,
                    image_count=len(p.images),
                )
                for p in products
            ],
            slot_info=SlotInfoResponse(
                total_slots=seller.total_slots,
                slots_used=seller.slots_used,
                slots_available=seller.slots_available,
            ),
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _require_owned(self, seller_id: UUID, product_id: UUID) -> Product:
        await self.db.execute(select(Seller.id).where(Seller.id == seller_id).with_for_update())
        product = await self.product_repo.get_by_id(product_id, load_full=True, lock=True)
        if not product:
            raise NotFoundError("Product not found")
        if product.seller_id != seller_id:
            raise PermissionDeniedError("Product does not belong to this seller")
        return product

    async def _unique_slug(self, name: str) -> str:
        base = _slugify(name)
        candidate = base
        counter = 1
        while await self.product_repo.slug_exists(candidate):
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    @staticmethod
    def _to_card(p: Product) -> ProductCardResponse:
        primary_image = next((i.url for i in p.images if i.is_primary), None)
        if not primary_image and p.images:
            primary_image = p.images[0].url

        colours = list({v.colour for v in p.variants if v.is_active})
        alpha = list(
            {v.size_value for v in p.variants if v.is_active and v.size_type.value == "alpha"}
        )
        numeric = list(
            {v.size_value for v in p.variants if v.is_active and v.size_type.value == "numeric"}
        )

        from datetime import datetime, timezone, timedelta

        is_new = (datetime.now(timezone.utc) - p.created_at.replace(tzinfo=timezone.utc)).days < 14

        return ProductCardResponse(
            id=p.id,
            seller_id=p.seller_id,
            brand_name=p.seller.brand_name if p.seller else "",
            brand_color=p.seller.brand_color if p.seller else "#DFFF00",
            name=p.name,
            slug=p.slug,
            price=int(p.price),
            sale_price=int(p.sale_price) if p.sale_price else None,
            primary_image=primary_image,
            colours=colours,
            alpha_sizes=alpha,
            numeric_sizes=numeric,
            avg_rating=float(p.avg_rating),
            review_count=p.review_count,
            is_new=is_new,
            has_stock=p.has_stock,
        )

    @staticmethod
    def _to_variant(v) -> VariantWithStockResponse:
        inv = v.inventory
        return VariantWithStockResponse(
            id=v.id,
            sku=v.sku,
            size_type=v.size_type.value,
            size_value=v.size_value,
            colour=v.colour,
            price=int(
                v.price_override if v.price_override is not None else v.product.effective_price
            ),
            stock=inv.stock if inv else 0,
            available_stock=inv.available_stock if inv else 0,
            is_active=v.is_active,
        )

    def _to_detail(self, p: Product) -> ProductDetailResponse:
        card = self._to_card(p)
        return ProductDetailResponse(
            **card.model_dump(),
            description=p.description,
            meta_title=p.meta_title,
            meta_description=p.meta_description,
            images=[ProductImageResponse.model_validate(i) for i in p.images],
            variants=[self._to_variant(v) for v in p.variants],
            seller=SellerSummaryResponse(
                id=p.seller.id,
                brand_name=p.seller.brand_name,
                slug=p.seller.slug,
                logo_url=p.seller.logo_url,
                brand_color=p.seller.brand_color,
                return_policy=p.seller.return_policy,
                whatsapp_number=p.seller.whatsapp_number,
            ),
            category=CategoryResponse.model_validate(p.category) if p.category else None,
            created_at=p.created_at,
        )

    @staticmethod
    def _is_public(product):
        return bool(
            product
            and product.is_published
            and not product.admin_hidden
            and not product.deleted_at
            and product.seller
            and product.seller.status == SellerStatus.active
            and not product.seller.deleted_at
        )

    async def _validate_category(self, category_id):
        if category_id:
            category = await self.db.get(Category, category_id)
            if not category or not category.is_active:
                raise BusinessRuleError("Category is not available")

    async def get_seller_detail(self, seller_id, product_id):
        return self._to_detail(await self._require_owned(seller_id, product_id))

    async def add_variant(self, seller_id, product_id, payload):
        product = await self._require_owned(seller_id, product_id)
        sku = payload.sku or f"WHZ-{uuid.uuid4().hex[:16].upper()}"
        exists = await self.db.scalar(select(ProductVariant.id).where(ProductVariant.sku == sku))
        if exists:
            raise ConflictError("SKU already exists")
        variant = await self.variant_repo.create(
            product_id=product.id,
            sku=sku,
            size_type=SizeType(payload.size_type),
            size_value=payload.size_value,
            colour=payload.colour,
            price_override=payload.price_override,
        )
        await self.inv_repo.create(variant.id, payload.stock)
        await self.db.commit()
        return await self.get_seller_detail(seller_id, product.id)

    async def update_variant(self, seller_id, product_id, variant_id, payload):
        product = await self._require_owned(seller_id, product_id)
        variant = next((v for v in product.variants if v.id == variant_id), None)
        if not variant:
            raise NotFoundError("Variant not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            if value is None and key != "price_override":
                raise BusinessRuleError(f"{key} cannot be null")
            setattr(variant, key, SizeType(value) if key == "size_type" else value)
        await self.db.commit()
        return self._to_variant(variant)

    async def reorder_images(self, seller_id, product_id, image_ids):
        product = await self._require_owned(seller_id, product_id)
        if len(image_ids) != len(set(image_ids)) or set(image_ids) != {
            i.id for i in product.images
        }:
            raise BusinessRuleError("Supply every product image once in the desired order")
        by_id = {i.id: i for i in product.images}
        for position, image_id in enumerate(image_ids):
            by_id[image_id].sort_order = position
        await self.db.commit()
        return {"message": "Image order saved"}

    async def primary_image(self, seller_id, product_id, image_id):
        product = await self._require_owned(seller_id, product_id)
        if image_id not in {i.id for i in product.images}:
            raise NotFoundError("Image not found")
        await self.product_repo.set_primary_image(product_id, image_id)
        await self.db.commit()
        return {"message": "Primary image saved"}

    async def delete_image(self, seller_id, product_id, image_id):
        product = await self._require_owned(seller_id, product_id)
        image = next((i for i in product.images if i.id == image_id), None)
        if not image:
            raise NotFoundError("Image not found")
        if product.is_published and len(product.images) == 1:
            raise BusinessRuleError("Unpublish the product before removing its last image")
        remaining = [i for i in product.images if i.id != image_id]
        if image.is_primary and remaining:
            remaining[0].is_primary = True
        await self.db.delete(image)
        await self.db.commit()
        from app.services.image_service import ImageService

        try:
            await ImageService().delete(image.url)
        except Exception:
            from app.core.logging import get_logger

            get_logger(__name__).warning("storage.orphan_cleanup_required", image_id=str(image_id))

    async def admin_list(self, seller_id=None, admin_hidden=None, page=1):
        query = select(Product).where(Product.deleted_at.is_(None))
        if seller_id:
            query = query.where(Product.seller_id == seller_id)
        if admin_hidden is not None:
            query = query.where(Product.admin_hidden == admin_hidden)
        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = (
            await self.db.scalars(
                query.order_by(Product.created_at.desc(), Product.id.desc())
                .offset((page - 1) * 25)
                .limit(25)
            )
        ).all()
        return {
            "data": [
                {
                    "id": p.id,
                    "seller_id": p.seller_id,
                    "name": p.name,
                    "price": p.price,
                    "slug": p.slug,
                    "is_published": p.is_published,
                    "admin_hidden": p.admin_hidden,
                }
                for p in rows
            ],
            "pagination": {"page": page, "per_page": 25, "total": total},
        }

    async def set_hidden(self, product_id, hidden):
        product = await self.product_repo.get_by_id(product_id, lock=True)
        if not product:
            raise NotFoundError("Product not found")
        product.admin_hidden = hidden
        await self.db.commit()
        return {"id": product.id, "admin_hidden": product.admin_hidden}
