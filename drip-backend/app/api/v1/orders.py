from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSeller, CurrentUser, OptionalUser, get_db
from app.schemas.order import (
    CancelOrderRequest,
    CouponValidationResponse,
    CreateGuestOrderRequest,
    CreateOrderRequest,
    CreateOrderResponse,
    GuestCheckoutQuoteRequest,
    GuestCheckoutQuoteResponse,
    OrderDetailResponse,
    PaginatedOrders,
    UpdateSellerOrderRequest,
    ValidateCouponRequest,
)
from app.services.coupon_service import CouponService
from app.services.order_service import OrderService

router = APIRouter(tags=["orders"])

DB = Annotated[AsyncSession, Depends(get_db)]


async def _get_redis():
    from app.core.redis import get_redis

    return get_redis()


# ── Customer Orders ────────────────────────────────────────────────────────────


@router.post("/orders", response_model=CreateOrderResponse, status_code=201)
async def place_order(
    payload: CreateOrderRequest,
    db: DB,
    current_user: CurrentUser,
) -> CreateOrderResponse:
    redis = await _get_redis()
    return await OrderService(db, redis).create_order(
        user_id=UUID(current_user["sub"]), payload=payload
    )


@router.post("/orders/guest", response_model=CreateOrderResponse, status_code=201)
async def place_guest_order(
    payload: CreateGuestOrderRequest,
    db: DB,
) -> CreateOrderResponse:
    return await OrderService(db).create_guest_order(payload)


@router.post("/orders/guest/quote", response_model=GuestCheckoutQuoteResponse)
async def quote_guest_checkout(
    payload: GuestCheckoutQuoteRequest,
    db: DB,
) -> GuestCheckoutQuoteResponse:
    return await OrderService(db).quote_guest_checkout(payload)


@router.get("/orders", response_model=PaginatedOrders)
async def list_orders(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
) -> PaginatedOrders:
    return await OrderService(db).get_customer_orders(user_id=UUID(current_user["sub"]), page=page)


@router.get("/orders/number/{order_number}", response_model=OrderDetailResponse)
async def get_order_by_number(
    order_number: str,
    db: DB,
    current_user: OptionalUser,
    email: str | None = Query(default=None, deprecated=True),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> OrderDetailResponse:
    return await OrderService(db).get_order_by_number(
        order_number, email, UUID(current_user["sub"]) if current_user else None, guest_token
    )


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: UUID,
    db: DB,
    current_user: OptionalUser,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> OrderDetailResponse:
    from app.services.order_access import authorized_order

    order = await authorized_order(
        db, order_id, UUID(current_user["sub"]) if current_user else None, guest_token
    )
    return OrderService._to_detail(order)


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    payload: CancelOrderRequest,
    db: DB,
    current_user: OptionalUser,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
) -> dict:
    return await OrderService(db).cancel_order(
        order_id=order_id,
        user_id=UUID(current_user["sub"]) if current_user else None,
        guest_token=guest_token,
        payload=payload,
    )


# ── Coupons ────────────────────────────────────────────────────────────────────


@router.post("/coupons/validate", response_model=CouponValidationResponse)
async def validate_coupon(
    payload: ValidateCouponRequest,
    db: DB,
    current_user: CurrentUser,
) -> CouponValidationResponse:
    return await CouponService(db).validate(payload=payload, user_id=UUID(current_user["sub"]))


# ── Seller Order Management ────────────────────────────────────────────────────


@router.get("/seller/orders")
async def list_seller_orders(
    db: DB,
    current_seller: CurrentSeller,
    status: str = Query(
        default="all", pattern="^(all|pending|processing|shipped|delivered|cancelled)$"
    ),
    page: int = Query(default=1, ge=1),
) -> dict:
    return await OrderService(db).get_seller_orders(
        seller_id=UUID(current_seller["seller_id"]),
        status=status,
        page=page,
    )


@router.get("/seller/orders/{seller_order_id}")
async def get_seller_order(
    seller_order_id: UUID,
    db: DB,
    current_seller: CurrentSeller,
) -> dict:
    return await OrderService(db).get_seller_order_detail(
        seller_id=UUID(current_seller["seller_id"]),
        seller_order_id=seller_order_id,
    )


@router.put("/seller/orders/{seller_order_id}/status")
async def update_seller_order_status(
    seller_order_id: UUID,
    payload: UpdateSellerOrderRequest,
    db: DB,
    current_seller: CurrentSeller,
) -> dict:
    return await OrderService(db).update_seller_order_status(
        seller_id=UUID(current_seller["seller_id"]),
        seller_order_id=seller_order_id,
        payload=payload,
    )
