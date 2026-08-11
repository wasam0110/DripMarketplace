from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, CurrentUser
from app.schemas.seller import (
    SellerRegistrationRequest, SellerRegistrationResponse,
    SlotPricingResponse, SlotPurchaseRequest, SlotPurchaseResponse,
    SellerProfileResponse, SellerProfileUpdateRequest, LogoUploadResponse,
    SellerDashboardResponse, PaginatedSellerOrders, PagePagination,
    SellerOrderDetailResponse, UpdateOrderStatusRequest,
    BankAccountResponse, CreateBankAccountRequest,
    RevenueAnalyticsResponse,
)
from app.services.seller_service import SellerService
from app.services.slot_service import SlotService

router = APIRouter(prefix="/seller", tags=["seller"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ── PUBLIC ─────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=SellerRegistrationResponse, status_code=201)
async def register_seller(payload: SellerRegistrationRequest, db: DB) -> SellerRegistrationResponse:
    """Creates a new User (role=seller) and Seller profile in one step. No auth required."""
    return await SellerService(db).register(payload)


@router.get("/register/slot-price", response_model=SlotPricingResponse)
async def get_slot_pricing(
    extra_slots: int = Query(default=0, ge=0, le=10_000)
) -> SlotPricingResponse:
    return SlotService.calculate_pricing(extra_slots)


# ── PROFILE ────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=SellerProfileResponse)
async def get_seller_profile(db: DB, current_user: CurrentUser) -> SellerProfileResponse:
    return await SellerService(db).get_profile(user_id=UUID(current_user["sub"]))


@router.patch("/me", response_model=SellerProfileResponse)
async def update_seller_profile(
    payload: SellerProfileUpdateRequest, db: DB, current_user: CurrentUser
) -> SellerProfileResponse:
    return await SellerService(db).update_profile(
        user_id=UUID(current_user["sub"]), payload=payload
    )


@router.post("/logo", response_model=LogoUploadResponse)
async def upload_logo(
    db: DB,
    current_user: CurrentUser,
    logo: UploadFile = File(...),
) -> LogoUploadResponse:
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if logo.content_type not in allowed:
        raise HTTPException(status_code=422, detail="Allowed types: jpeg, png, webp")

    contents = await logo.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Logo must be under 2 MB")

    user_id  = UUID(current_user["sub"])
    logo_url = f"https://cdn.drip.pk/logos/{user_id}/{logo.filename}"
    return await SellerService(db).update_logo(user_id=user_id, logo_url=logo_url)


# ── SLOTS ──────────────────────────────────────────────────────────────────────

@router.post("/slots/purchase", response_model=SlotPurchaseResponse)
async def purchase_slots(
    payload: SlotPurchaseRequest, db: DB, current_user: CurrentUser
) -> SlotPurchaseResponse:
    return await SlotService(db).purchase_slots(
        user_id=UUID(current_user["sub"]), payload=payload
    )


# ── DASHBOARD ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=SellerDashboardResponse)
async def get_dashboard(
    db: DB,
    current_user: CurrentUser,
    period: str = Query(default="month", pattern="^(today|week|month|quarter|year)$"),
) -> SellerDashboardResponse:
    return await SellerService(db).get_dashboard(
        user_id=UUID(current_user["sub"]), period=period
    )


# ── ORDERS (stubs — Block 5) ───────────────────────────────────────────────────

@router.get("/orders", response_model=PaginatedSellerOrders)
async def list_seller_orders(
    db: DB,
    current_user: CurrentUser,
    order_status: str = Query(default="all", alias="status",
                              pattern="^(all|pending|processing|shipped|delivered|cancelled)$"),
    page:     int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
) -> PaginatedSellerOrders:
    return PaginatedSellerOrders(
        data=[],
        pagination=PagePagination(page=page, per_page=per_page, total=0, total_pages=0),
    )


@router.get("/orders/{seller_order_id}", response_model=SellerOrderDetailResponse)
async def get_seller_order(
    seller_order_id: UUID, db: DB, current_user: CurrentUser
) -> SellerOrderDetailResponse:
    raise HTTPException(status_code=501, detail="Implemented in Block 5")


@router.put("/orders/{seller_order_id}/status", status_code=200)
async def update_order_status(
    seller_order_id: UUID,
    payload: UpdateOrderStatusRequest,
    db: DB,
    current_user: CurrentUser,
) -> dict:
    raise HTTPException(status_code=501, detail="Implemented in Block 5")


# ── BANK ACCOUNTS ──────────────────────────────────────────────────────────────

@router.get("/bank-accounts", response_model=list[BankAccountResponse])
async def list_bank_accounts(db: DB, current_user: CurrentUser) -> list[BankAccountResponse]:
    return await SellerService(db).list_bank_accounts(user_id=UUID(current_user["sub"]))


@router.post("/bank-accounts", response_model=BankAccountResponse, status_code=201)
async def add_bank_account(
    payload: CreateBankAccountRequest, db: DB, current_user: CurrentUser
) -> BankAccountResponse:
    return await SellerService(db).add_bank_account(
        user_id=UUID(current_user["sub"]), payload=payload
    )


@router.delete("/bank-accounts/{account_id}")
async def delete_bank_account(
    account_id: UUID, db: DB, current_user: CurrentUser
) -> Response:
    await SellerService(db).delete_bank_account(
        user_id=UUID(current_user["sub"]), account_id=account_id
    )
    return Response(status_code=204)

# ── ANALYTICS (stub — Block 10) ────────────────────────────────────────────────

@router.get("/analytics/revenue", response_model=RevenueAnalyticsResponse)
async def get_revenue_analytics(
    db: DB,
    current_user: CurrentUser,
    period:      str = Query(default="30d", pattern="^(7d|30d|90d|1y)$"),
    granularity: str = Query(default="day", pattern="^(day|week|month)$"),
) -> RevenueAnalyticsResponse:
    return RevenueAnalyticsResponse(period=period, granularity=granularity, data=[])