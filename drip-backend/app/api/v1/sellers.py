"""api / v1 / sellers.

HTTP handlers connect validated requests and access dependencies to backend services.
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, CurrentSellerAccount
from app.schemas.seller import (
    SellerRegistrationRequest,
    SellerRegistrationResponse,
    SlotPricingResponse,
    SlotPurchaseRequest,
    SlotPurchaseResponse,
    SellerProfileResponse,
    SellerProfileUpdateRequest,
    LogoUploadResponse,
    SellerDashboardResponse,
    BankAccountResponse,
    CreateBankAccountRequest,
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
    db: DB,
    extra_slots: int = Query(default=0, ge=0, le=10_000),
) -> SlotPricingResponse:
    # Handle GET /register/slot-price at this router boundary. Delegates to
    # SlotService.get_pricing.
    return await SlotService(db).get_pricing(extra_slots)


# ── PROFILE ────────────────────────────────────────────────────────────────────


@router.get("/me", response_model=SellerProfileResponse)
async def get_seller_profile(db: DB, current_user: CurrentSellerAccount) -> SellerProfileResponse:
    # Handle GET /me at this router boundary. Delegates to SellerService.get_profile. Access
    # dependency: CurrentSellerAccount.
    return await SellerService(db).get_profile(user_id=UUID(current_user["sub"]))


@router.patch("/me", response_model=SellerProfileResponse)
async def update_seller_profile(
    payload: SellerProfileUpdateRequest, db: DB, current_user: CurrentSellerAccount
) -> SellerProfileResponse:
    # Handle PATCH /me at this router boundary. Delegates to SellerService.update_profile.
    # Access dependency: CurrentSellerAccount.
    return await SellerService(db).update_profile(
        user_id=UUID(current_user["sub"]), payload=payload
    )


@router.post("/logo", response_model=LogoUploadResponse)
async def upload_logo(
    db: DB,
    current_user: CurrentSellerAccount,
    logo: UploadFile = File(...),
) -> LogoUploadResponse:
    # Handle POST /logo at this router boundary. Delegates to ImageService.process_and_upload,
    # SellerService.update_logo. Access dependency: CurrentSellerAccount.
    from app.repositories.seller_repo import SellerRepository
    from app.services.image_service import ImageService
    from app.core.config import settings
    from app.core.exceptions import NotFoundError

    user_id = UUID(current_user["sub"])
    seller = await SellerRepository(db).get_by_user_id(user_id)
    if not seller:
        raise NotFoundError("Seller account not found")
    contents = await logo.read(2 * 1024 * 1024 + 1)
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Logo must be under 2 MB")
    logo_url = await ImageService().process_and_upload(
        contents, str(seller.id), bucket=settings.SUPABASE_STORAGE_BUCKET_BRANDS
    )
    return await SellerService(db).update_logo(user_id=user_id, logo_url=logo_url)


# ── SLOTS ──────────────────────────────────────────────────────────────────────


@router.post("/slots/purchase", response_model=SlotPurchaseResponse)
async def purchase_slots(
    payload: SlotPurchaseRequest, db: DB, current_user: CurrentSellerAccount
) -> SlotPurchaseResponse:
    # Handle POST /slots/purchase at this router boundary. Delegates to
    # SlotService.purchase_slots. Access dependency: CurrentSellerAccount.
    return await SlotService(db).purchase_slots(user_id=UUID(current_user["sub"]), payload=payload)


# ── DASHBOARD ──────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=SellerDashboardResponse)
async def get_dashboard(
    db: DB,
    current_user: CurrentSellerAccount,
    period: str = Query(default="month", pattern="^(today|week|month|quarter|year)$"),
) -> SellerDashboardResponse:
    # Handle GET /dashboard at this router boundary. Delegates to SellerService.get_dashboard.
    # Access dependency: CurrentSellerAccount.
    return await SellerService(db).get_dashboard(user_id=UUID(current_user["sub"]), period=period)


# ── ORDERS (stubs — Block 5) ───────────────────────────────────────────────────


# ── BANK ACCOUNTS ──────────────────────────────────────────────────────────────


@router.get("/bank-accounts", response_model=list[BankAccountResponse])
async def list_bank_accounts(db: DB, current_user: CurrentSellerAccount) -> list[BankAccountResponse]:
    # Handle GET /bank-accounts at this router boundary. Delegates to
    # SellerService.list_bank_accounts. Access dependency: CurrentSellerAccount.
    return await SellerService(db).list_bank_accounts(user_id=UUID(current_user["sub"]))


@router.post("/bank-accounts", response_model=BankAccountResponse, status_code=201)
async def add_bank_account(
    payload: CreateBankAccountRequest, db: DB, current_user: CurrentSellerAccount
) -> BankAccountResponse:
    # Handle POST /bank-accounts at this router boundary. Delegates to
    # SellerService.add_bank_account. Access dependency: CurrentSellerAccount.
    return await SellerService(db).add_bank_account(
        user_id=UUID(current_user["sub"]), payload=payload
    )


@router.delete("/bank-accounts/{account_id}")
async def delete_bank_account(account_id: UUID, db: DB, current_user: CurrentSellerAccount) -> Response:
    # Handle DELETE /bank-accounts/{account_id} at this router boundary. Delegates to
    # SellerService.delete_bank_account. Access dependency: CurrentSellerAccount.
    await SellerService(db).delete_bank_account(
        user_id=UUID(current_user["sub"]), account_id=account_id
    )
    return Response(status_code=204)
