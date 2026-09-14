from __future__ import annotations

import re
import uuid
from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError, PermissionDeniedError, ConflictError, BusinessRuleError
)
from app.models.product import Product, SizeType
from app.models.seller import SellerStatus
from app.repositories.product_repo import ProductRepository, VariantRepository
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.seller_repo import SellerRepository
from app.schemas.product import (
    CreateProductRequest, UpdateProductRequest,
    ProductCardResponse, ProductDetailResponse, CataloguePage, CursorPagination,
    SellerProductRowResponse, SellerProductsPage, SlotInfoResponse,
    VariantWithStockResponse, ProductImageResponse,
    SellerSummaryResponse, CategoryResponse,
    SearchSuggestionsResponse, SearchSuggestion, BrandSuggestion,
)

MAX_IMAGES_PER_PRODUCT = 6


def _slugify(text: str) -> str:
    text = text.lower().strip().encode("ascii", errors="ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:250]


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db          = db
        self.product_repo = ProductRepository(db)
        self.variant_repo = VariantRepository(db)
        self.inv_repo    = InventoryRepository(db)
        self.seller_repo = SellerRepository(db)

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create_product(
        self, seller_id: UUID, payload: CreateProductRequest
    ) -> ProductDetailResponse:
        seller = await self.seller_repo.get_by_id(seller_id)
        if not seller or seller.status != SellerStatus.active:
            raise PermissionDeniedError("Seller account is not active")

        # If trying to publish immediately, check slot
        if payload.is_published:
            if seller.slots_used >= seller.total_slots:
                raise BusinessRuleError("No product slots available. Purchase extra slots.")

        slug = await self._unique_slug(payload.name)

        product = await self.product_repo.create(
            seller_id        = seller_id,
            category_id      = payload.category_id,
            name             = payload.name,
            slug             = slug,
            description      = payload.description,
            price            = Decimal(payload.price),
            sale_price       = Decimal(payload.sale_price) if payload.sale_price else None,
            is_published     = False,  # always start draft; publish separately
            meta_title       = payload.meta_title,
            meta_description = payload.meta_description,
        )

        # Create variants + inventory
        for v in payload.variants:
            sku = v.sku or f"DRIP-{str(product.id)[:8].upper()}-{v.size_value}-{v.colour[:3].upper()}"
            variant = await self.variant_repo.create(
                product_id     = product.id,
                sku            = sku,
                size_type      = SizeType(v.size_type),
                size_value     = v.size_value,
                colour         = v.colour,
                price_override = Decimal(v.price_override) if v.price_override else None,
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
        data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if "price" in data:
            data["price"] = Decimal(data["price"])
        if "sale_price" in data:
            data["sale_price"] = Decimal(data["sale_price"])
        await self.product_repo.update(product_id, **data)
        await self.db.commit()
        updated = await self.product_repo.get_by_id(product_id, load_full=True)
        return self._to_detail(updated)  # type: ignore[arg-type]

    # ── Publish / Unpublish ────────────────────────────────────────────────────

    async def publish_product(self, seller_id: UUID, product_id: UUID) -> dict:
        product = await self._require_owned(seller_id, product_id)
        seller  = await self.seller_repo.get_by_id(seller_id)

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
        product   = await self._require_owned(seller_id, product_id)
        current   = await self.product_repo.get_image_count(product_id)
        remaining = MAX_IMAGES_PER_PRODUCT - current

        if remaining <= 0:
            raise BusinessRuleError(f"Maximum {MAX_IMAGES_PER_PRODUCT} images allowed per product")

        images = []
        for i, url in enumerate(image_urls[:remaining]):
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
        if not product or not product.is_published or product.admin_hidden:
            raise NotFoundError("Product not found")
        await self.product_repo.increment_view_count(product_id)
        await self.db.commit()
        return self._to_detail(product)

    async def get_product_by_slug(self, slug: str) -> ProductDetailResponse:
        product = await self.product_repo.get_by_slug(slug)
        if not product:
            raise NotFoundError("Product not found")
        await self.product_repo.increment_view_count(product.id)
        await self.db.commit()
        return self._to_detail(product)

    async def get_variants(self, product_id: UUID) -> list[VariantWithStockResponse]:
        variants = await self.variant_repo.get_by_product(product_id)
        return [self._to_variant(v) for v in variants]

    async def search_suggestions(self, q: str) -> SearchSuggestionsResponse:
        products, sellers = await self.product_repo.search_suggestions(q)
        return SearchSuggestionsResponse(
            products=[
                SearchSuggestion(
                    id            = p.id,
                    name          = p.name,
                    primary_image = next((i.url for i in p.images if i.is_primary), None),
                    price         = int(p.effective_price),
                    brand_name    = p.seller.brand_name,
                )
                for p in products
            ],
            brands=[
                BrandSuggestion(
                    id=s.id, brand_name=s.brand_name, logo_url=s.logo_url, slug=s.slug
                )
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
                    id           = p.id,
                    name         = p.name,
                    slug         = p.slug,
                    category     = p.category.name if p.category else None,
                    price        = int(p.price),
                    total_stock  = sum(
                        (v.inventory.stock if v.inventory else 0) for v in p.variants
                    ),
                    is_published = p.is_published,
                    avg_rating   = float(p.avg_rating),
                    review_count = p.review_count,
                    image_count  = len(p.images),
                )
                for p in products
            ],
            slot_info=SlotInfoResponse(
                total_slots    = seller.total_slots,
                slots_used     = seller.slots_used,
                slots_available= seller.slots_available,
            ),
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _require_owned(self, seller_id: UUID, product_id: UUID) -> Product:
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")
        if product.seller_id != seller_id:
            raise PermissionDeniedError("Product does not belong to this seller")
        return product

    async def _unique_slug(self, name: str) -> str:
        base      = _slugify(name)
        candidate = base
        counter   = 1
        while await self.product_repo.slug_exists(candidate):
            candidate = f"{base}-{counter}"
            counter  += 1
        return candidate

    @staticmethod
    def _to_card(p: Product) -> ProductCardResponse:
        primary_image = next((i.url for i in p.images if i.is_primary), None)
        if not primary_image and p.images:
            primary_image = p.images[0].url

        colours = list({v.colour for v in p.variants if v.is_active})
        alpha   = list({v.size_value for v in p.variants if v.is_active and v.size_type.value == "alpha"})
        numeric = list({v.size_value for v in p.variants if v.is_active and v.size_type.value == "numeric"})

        from datetime import datetime, timezone, timedelta
        is_new = (datetime.now(timezone.utc) - p.created_at.replace(tzinfo=timezone.utc)).days < 14

        return ProductCardResponse(
            id            = p.id,
            seller_id     = p.seller_id,
            brand_name    = p.seller.brand_name if p.seller else "",
            brand_color   = p.seller.brand_color if p.seller else "#DFFF00",
            name          = p.name,
            slug          = p.slug,
            price         = int(p.price),
            sale_price    = int(p.sale_price) if p.sale_price else None,
            primary_image = primary_image,
            colours       = colours,
            alpha_sizes   = alpha,
            numeric_sizes = numeric,
            avg_rating    = float(p.avg_rating),
            review_count  = p.review_count,
            is_new        = is_new,
            has_stock     = p.has_stock,
        )

    @staticmethod
    def _to_variant(v) -> VariantWithStockResponse:
        inv = v.inventory
        return VariantWithStockResponse(
            id              = v.id,
            sku             = v.sku,
            size_type       = v.size_type.value,
            size_value      = v.size_value,
            colour          = v.colour,
            price           = int(v.price_override if v.price_override else v.product.price),
            stock           = inv.stock if inv else 0,
            available_stock = inv.available_stock if inv else 0,
            is_active       = v.is_active,
        )

    def _to_detail(self, p: Product) -> ProductDetailResponse:
        card = self._to_card(p)
        return ProductDetailResponse(
            **card.model_dump(),
            description      = p.description,
            meta_title       = p.meta_title,
            meta_description = p.meta_description,
            images           = [ProductImageResponse.model_validate(i) for i in p.images],
            variants         = [self._to_variant(v) for v in p.variants],
            seller           = SellerSummaryResponse(
                id              = p.seller.id,
                brand_name      = p.seller.brand_name,
                slug            = p.seller.slug,
                logo_url        = p.seller.logo_url,
                brand_color     = p.seller.brand_color,
                return_policy   = p.seller.return_policy,
                whatsapp_number = p.seller.whatsapp_number,
            ),
            category         = CategoryResponse.model_validate(p.category) if p.category else None,
            created_at       = p.created_at,
        )