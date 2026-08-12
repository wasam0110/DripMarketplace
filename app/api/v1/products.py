from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentUser, CurrentSeller, CurrentAdmin
from app.schemas.product import (
    CreateProductRequest, UpdateProductRequest,
    ProductDetailResponse, CataloguePage,
    SellerProductsPage, UploadImagesResponse,
    VariantWithStockResponse, SearchSuggestionsResponse,
)
from app.services.product_service import ProductService
from app.services.image_service import ImageService

router = APIRouter(tags=["products"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/products", response_model=CataloguePage)
async def list_products(
    db: DB,
    category_id:  Optional[UUID]       = Query(default=None),
    seller_id:    Optional[UUID]       = Query(default=None),
    size_alpha:   Optional[List[str]]  = Query(default=None),
    size_numeric: Optional[List[str]]  = Query(default=None),
    colour:       Optional[List[str]]  = Query(default=None),
    min_price:    Optional[int]        = Query(default=None, ge=0),
    max_price:    Optional[int]        = Query(default=None, le=500_000),
    on_sale:      Optional[bool]       = Query(default=None),
    is_new:       Optional[bool]       = Query(default=None),
    q:            Optional[str]        = Query(default=None, max_length=200),
    sort:         str                  = Query(default="newest", pattern="^(newest|price_asc|price_desc|rating|trending)$"),
    limit:        int                  = Query(default=20, ge=1, le=100),
    cursor:       Optional[str]        = Query(default=None),
) -> CataloguePage:
    return await ProductService(db).get_catalogue(
        category_id  = category_id,
        seller_id    = seller_id,
        size_alpha   = size_alpha,
        size_numeric = size_numeric,
        colours      = colour,
        min_price    = min_price,
        max_price    = max_price,
        on_sale      = on_sale,
        is_new       = is_new,
        q            = q,
        sort         = sort,
        limit        = limit,
        cursor       = cursor,
    )


@router.get("/products/search/suggestions", response_model=SearchSuggestionsResponse)
async def search_suggestions(
    db: DB,
    q: str = Query(min_length=2, max_length=100),
) -> SearchSuggestionsResponse:
    return await ProductService(db).search_suggestions(q)


@router.get("/products/slug/{slug}", response_model=ProductDetailResponse)
async def get_product_by_slug(slug: str, db: DB) -> ProductDetailResponse:
    return await ProductService(db).get_product_by_slug(slug)


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def get_product(product_id: UUID, db: DB) -> ProductDetailResponse:
    return await ProductService(db).get_product_detail(product_id)


@router.get("/products/{product_id}/variants", response_model=list[VariantWithStockResponse])
async def get_product_variants(product_id: UUID, db: DB) -> list[VariantWithStockResponse]:
    return await ProductService(db).get_variants(product_id)


@router.get("/products/{product_id}/reviews")
async def get_product_reviews(
    product_id: UUID,
    db: DB,
    page:     int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
) -> dict:
    """Reviews implemented in Block 9 (Notifications/Reviews)."""
    raise HTTPException(status_code=501, detail="Implemented in Block 9")


@router.post("/products/{product_id}/reviews", status_code=201)
async def submit_review(
    product_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> dict:
    """Reviews implemented in Block 9."""
    raise HTTPException(status_code=501, detail="Implemented in Block 9")


# ══════════════════════════════════════════════════════════════════════════════
# SELLER
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/seller/products", response_model=SellerProductsPage)
async def list_seller_products(
    db: DB,
    current_seller: CurrentSeller,
    status: str = Query(default="all", pattern="^(all|published|draft)$"),
    page:   int = Query(default=1, ge=1),
) -> SellerProductsPage:
    from uuid import UUID
    seller_id = UUID(current_seller["seller_id"])
    return await ProductService(db).get_seller_products(seller_id, status, page)


@router.post("/seller/products", response_model=ProductDetailResponse, status_code=201)
async def create_product(
    payload:        CreateProductRequest,
    db:             DB,
    current_seller: CurrentSeller,
) -> ProductDetailResponse:
    seller_id = UUID(current_seller["seller_id"])
    return await ProductService(db).create_product(seller_id, payload)


@router.put("/seller/products/{product_id}", response_model=ProductDetailResponse)
async def update_product(
    product_id:     UUID,
    payload:        UpdateProductRequest,
    db:             DB,
    current_seller: CurrentSeller,
) -> ProductDetailResponse:
    seller_id = UUID(current_seller["seller_id"])
    return await ProductService(db).update_product(seller_id, product_id, payload)


@router.delete("/seller/products/{product_id}")
async def delete_product(
    product_id:     UUID,
    db:             DB,
    current_seller: CurrentSeller,
) -> Response:
    seller_id = UUID(current_seller["seller_id"])
    await ProductService(db).delete_product(seller_id, product_id)
    return Response(status_code=204)


@router.post("/seller/products/{product_id}/publish")
async def publish_product(
    product_id:     UUID,
    db:             DB,
    current_seller: CurrentSeller,
) -> dict:
    seller_id = UUID(current_seller["seller_id"])
    return await ProductService(db).publish_product(seller_id, product_id)


@router.post("/seller/products/{product_id}/unpublish")
async def unpublish_product(
    product_id:     UUID,
    db:             DB,
    current_seller: CurrentSeller,
) -> dict:
    seller_id = UUID(current_seller["seller_id"])
    return await ProductService(db).unpublish_product(seller_id, product_id)


@router.post("/seller/products/{product_id}/images", response_model=UploadImagesResponse, status_code=201)
async def upload_product_images(
    product_id:     UUID,
    db:             DB,
    current_seller: CurrentSeller,
    images:         List[UploadFile] = File(...),
) -> UploadImagesResponse:
    if len(images) > 6:
        raise HTTPException(status_code=422, detail="Maximum 6 images per upload")

    image_svc = ImageService()
    urls: list[str] = []

    for upload in images:
        data = await upload.read()
        url  = await image_svc.process_and_upload(data, str(product_id))
        urls.append(url)

    seller_id = UUID(current_seller["seller_id"])
    uploaded  = await ProductService(db).add_images(seller_id, product_id, urls)
    return UploadImagesResponse(images=uploaded)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/products")
async def admin_list_products(
    db:            DB,
    current_admin: CurrentAdmin,
    seller_id:     Optional[UUID] = Query(default=None),
    admin_hidden:  Optional[bool] = Query(default=None),
    page:          int            = Query(default=1, ge=1),
) -> dict:
    """Admin product list — implemented in Block 8 (Admin)."""
    raise HTTPException(status_code=501, detail="Implemented in Block 8")


@router.post("/admin/products/{product_id}/hide")
async def admin_hide_product(
    product_id:    UUID,
    db:            DB,
    current_admin: CurrentAdmin,
) -> dict:
    """Admin hide product — implemented in Block 8 (Admin)."""
    raise HTTPException(status_code=501, detail="Implemented in Block 8")