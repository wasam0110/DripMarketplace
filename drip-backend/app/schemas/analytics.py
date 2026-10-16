from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Optional
from pydantic import BaseModel, Field


# Pydantic serializes Decimal as a JSON string, matching dashboard/wallet APIs.
AnalyticsMoney = Annotated[
    Decimal,
    Field(decimal_places=2, allow_inf_nan=False,
          description="PKR major units as a decimal string, not integer paisa. "
                      "Analytics emits two decimal places; averages use ROUND_HALF_UP."),
]


# ── Seller ─────────────────────────────────────────────────────────────────────

class SellerAnalyticsOverview(BaseModel):
    period:          str
    gross_revenue:   AnalyticsMoney
    commission_paid: AnalyticsMoney
    net_earnings:    AnalyticsMoney
    order_count:     int
    units_sold:      int
    avg_order_value: AnalyticsMoney
    total_views:     int
    conversion_rate: float


class RevenueDayRow(BaseModel):
    date:       str
    gross:      AnalyticsMoney
    commission: AnalyticsMoney
    net:        AnalyticsMoney
    orders:     int


class RevenueSeriesResponse(BaseModel):
    period:      str
    granularity: str
    data:        list[RevenueDayRow]


class TopProductRow(BaseModel):
    product_id:   str
    product_name: str
    image_url:    Optional[str]
    revenue:      AnalyticsMoney
    units_sold:   int
    views:        int
    avg_rating:   float


class TopProductsResponse(BaseModel):
    period:   str
    sort_by:  str
    data:     list[TopProductRow]


class InventoryHealthResponse(BaseModel):
    """Active variants on non-deleted seller products.

    In-stock includes low-stock variants. Low stock means positive available
    units at or below that variant's reorder point; zero availability is counted
    separately as out of stock. Available units exclude reservations.
    """

    total_variants: int
    in_stock:       int
    low_stock:      int
    out_of_stock:   int
    total_units:    int


# ── Admin ──────────────────────────────────────────────────────────────────────

class PlatformAnalytics(BaseModel):
    period:             str
    total_gmv:          AnalyticsMoney
    commission_revenue: AnalyticsMoney
    slot_revenue:       AnalyticsMoney
    total_orders:       int
    new_customers:      int
    active_sellers:     int
    avg_order_value:    AnalyticsMoney
    cod_rate:           float
    cancellation_rate:  float


class TopSellerRow(BaseModel):
    seller_id:   str
    brand_name:  str
    logo_url:    Optional[str]
    gmv:         AnalyticsMoney
    commission:  AnalyticsMoney
    order_count: int


class TopSellersResponse(BaseModel):
    period: str
    data:   list[TopSellerRow]


class CohortRow(BaseModel):
    cohort_month: str
    cohort_size:  int
    retention:    list[Optional[float]]


class CohortResponse(BaseModel):
    months: int
    data:   list[CohortRow]


class PaymentMethodStat(BaseModel):
    count:             int
    total:             AnalyticsMoney
    share:             float
    verified_rate:     Optional[float] = None
    cancellation_rate: Optional[float] = None


class PaymentMethodsResponse(BaseModel):
    period:    str
    payfast:   PaymentMethodStat
    cod:       PaymentMethodStat


class CityRow(BaseModel):
    city:        str
    order_count: int
    total_gmv:   AnalyticsMoney
    share:       float


class CitiesResponse(BaseModel):
    period: str
    data:   list[CityRow]


class ConversionResponse(BaseModel):
    measurement: str = "server_event_counts"
    tracked_since: str | None = None
    period:             str
    product_views:      int
    add_to_cart:        int
    orders_completed:   int
    view_to_cart_rate:  float
    cart_to_order_rate: float
    overall_cvr:        float


class SearchQueryRow(BaseModel):
    query:          str
    count:          int
    no_result_rate: float


class SearchQueriesResponse(BaseModel):
    tracked_since: str | None = None
    period: str
    data:   list[SearchQueryRow]
