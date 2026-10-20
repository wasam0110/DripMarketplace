"""api / v1 / analytics / seller.

HTTP handlers connect validated requests and access dependencies to backend services.
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentSeller
from app.schemas.analytics import (
    SellerAnalyticsOverview, RevenueSeriesResponse,
    TopProductsResponse, InventoryHealthResponse,
)
from app.services.analytics_service import SellerAnalyticsService

router = APIRouter(prefix="/seller/analytics", tags=["analytics"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/overview", response_model=SellerAnalyticsOverview)
async def seller_overview(
    db:             DB,
    current_seller: CurrentSeller,
    period:         str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
) -> SellerAnalyticsOverview:
    # Handle GET /overview at this router boundary. Delegates to
    # SellerAnalyticsService.get_overview. Access dependency: CurrentSeller.
    return await SellerAnalyticsService(db).get_overview(
        seller_id=UUID(current_seller["seller_id"]), period=period
    )


@router.get("/revenue", response_model=RevenueSeriesResponse)
async def seller_revenue_series(
    db:             DB,
    current_seller: CurrentSeller,
    period:         str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
    granularity:    str = Query(default="day",  pattern="^(day|week|month)$"),
) -> RevenueSeriesResponse:
    # Handle GET /revenue at this router boundary. Delegates to
    # SellerAnalyticsService.get_revenue_series. Access dependency: CurrentSeller.
    return await SellerAnalyticsService(db).get_revenue_series(
        seller_id=UUID(current_seller["seller_id"]),
        period=period, granularity=granularity,
    )


@router.get("/top-products", response_model=TopProductsResponse)
async def seller_top_products(
    db:             DB,
    current_seller: CurrentSeller,
    period:         str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
    sort_by:        str = Query(default="revenue", pattern="^(revenue|units|views)$"),
    limit:          int = Query(default=10, ge=1, le=50),
) -> TopProductsResponse:
    # Handle GET /top-products at this router boundary. Delegates to
    # SellerAnalyticsService.get_top_products. Access dependency: CurrentSeller.
    return await SellerAnalyticsService(db).get_top_products(
        seller_id=UUID(current_seller["seller_id"]),
        period=period, sort_by=sort_by, limit=limit,
    )


@router.get("/inventory-health", response_model=InventoryHealthResponse)
async def seller_inventory_health(
    db:             DB,
    current_seller: CurrentSeller,
) -> InventoryHealthResponse:
    # Handle GET /inventory-health at this router boundary. Delegates to
    # SellerAnalyticsService.get_inventory_health. Access dependency: CurrentSeller.
    return await SellerAnalyticsService(db).get_inventory_health(
        seller_id=UUID(current_seller["seller_id"])
    )
