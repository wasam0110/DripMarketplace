from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentAdmin
from app.schemas.analytics import (
    PlatformAnalytics, RevenueSeriesResponse,
    TopSellersResponse, CohortResponse,
    PaymentMethodsResponse, CitiesResponse,
    ConversionResponse, SearchQueriesResponse,
)
from app.services.analytics_service import AdminAnalyticsService

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/platform", response_model=PlatformAnalytics)
async def platform_analytics(
    db:            DB,
    current_admin: CurrentAdmin,
    period:        str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
) -> PlatformAnalytics:
    return await AdminAnalyticsService(db).get_platform_analytics(period)


@router.get("/revenue", response_model=RevenueSeriesResponse)
async def platform_revenue(
    db:            DB,
    current_admin: CurrentAdmin,
    period:        str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
    granularity:   str = Query(default="day",  pattern="^(day|week|month)$"),
) -> RevenueSeriesResponse:
    return await AdminAnalyticsService(db).get_platform_revenue(period, granularity)


@router.get("/top-sellers", response_model=TopSellersResponse)
async def top_sellers(
    db:            DB,
    current_admin: CurrentAdmin,
    period:        str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
    limit:         int = Query(default=10, ge=1, le=50),
) -> TopSellersResponse:
    return await AdminAnalyticsService(db).get_top_sellers(period, limit)


@router.get("/cohort", response_model=CohortResponse)
async def cohort_retention(
    db:            DB,
    current_admin: CurrentAdmin,
    months:        int = Query(default=6, ge=1, le=12),
) -> CohortResponse:
    return await AdminAnalyticsService(db).get_cohort(months)


@router.get("/payment-methods", response_model=PaymentMethodsResponse)
async def payment_methods(
    db:            DB,
    current_admin: CurrentAdmin,
    period:        str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
) -> PaymentMethodsResponse:
    return await AdminAnalyticsService(db).get_payment_methods(period)


@router.get("/cities", response_model=CitiesResponse)
async def orders_by_city(
    db:            DB,
    current_admin: CurrentAdmin,
    period:        str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
    limit:         int = Query(default=20, ge=1, le=100),
) -> CitiesResponse:
    return await AdminAnalyticsService(db).get_cities(period, limit)


@router.get("/conversion", response_model=ConversionResponse)
async def conversion_funnel(
    db:            DB,
    current_admin: CurrentAdmin,
    period:        str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
) -> ConversionResponse:
    return await AdminAnalyticsService(db).get_conversion(period)


@router.get("/search-queries", response_model=SearchQueriesResponse)
async def search_queries(
    db:            DB,
    current_admin: CurrentAdmin,
    period:        str = Query(default="7d",  pattern="^(7d|30d|90d|1y)$"),
    limit:         int = Query(default=50, ge=1, le=200),
) -> SearchQueriesResponse:
    return await AdminAnalyticsService(db).get_search_queries(period, limit)