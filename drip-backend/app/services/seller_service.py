from __future__ import annotations

import re
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.security import hash_password
from app.models.seller import Seller, SellerStatus
from app.models.user import UserRole
from app.repositories.seller_repo import SellerRepository, WalletRepository, BankAccountRepository
from app.repositories.user_repo import UserRepository
from app.schemas.seller import (
    SellerRegistrationRequest,
    SellerRegistrationResponse,
    SellerProfileResponse,
    SellerProfileUpdateRequest,
    LogoUploadResponse,
    SellerDashboardResponse,
    OrderStatusBreakdown,
    BankAccountResponse,
    CreateBankAccountRequest,
)

REGISTRATION_FEE = 5000
BASE_SLOTS       = 50


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = text.encode("ascii", errors="ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:120]


class SellerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db          = db
        self.seller_repo = SellerRepository(db)
        self.wallet_repo = WalletRepository(db)
        self.bank_repo   = BankAccountRepository(db)
        self.user_repo   = UserRepository(db)

    # ── Registration (public — creates User + Seller in one call) ──────────────

    async def register(self, payload: SellerRegistrationRequest) -> SellerRegistrationResponse:
        # 1. Email must not already exist
        if await self.user_repo.get_by_email(payload.email):
            raise ConflictError("An account with this email already exists")

        # 2. Brand name must be globally unique
        if await self.seller_repo.get_by_brand_name(payload.brand_name):
            raise ConflictError(f"Brand name '{payload.brand_name}' is already taken")

        # 3. Find a unique slug
        slug = await self._unique_slug(payload.brand_name)

        # 4. Create User with role=seller
        user = await self.user_repo.create(
            email         = payload.email,
            password_hash = hash_password(payload.password),
            first_name    = payload.first_name,
            last_name     = payload.last_name,
            role          = UserRole.seller,
        )

        # 5. Create Seller linked to that user
        total_slots = BASE_SLOTS + payload.extra_slots
        seller = await self.seller_repo.create(
            user_id          = user.id,
            brand_name       = payload.brand_name,
            slug             = slug,
            description      = payload.description,
            return_policy    = payload.return_policy,
            whatsapp_number  = payload.whatsapp_number,
            instagram_handle = payload.instagram_handle,
            total_slots      = total_slots,
            status           = SellerStatus.pending_payment,
        )

        # 6. Create zero-balance wallet
        await self.wallet_repo.create_for_seller(seller.id)

        await self.db.commit()

        return SellerRegistrationResponse(
            seller_id = seller.id,
            message   = (
                f"Application submitted. Complete payment of PKR {REGISTRATION_FEE:,} "
                "to activate your seller account."
            ),
        )

    # ── Profile ────────────────────────────────────────────────────────────────

    async def get_profile(self, user_id: UUID) -> SellerProfileResponse:
        seller = await self._require_seller(user_id)
        return self._to_profile(seller)

    async def update_profile(
        self, user_id: UUID, payload: SellerProfileUpdateRequest
    ) -> SellerProfileResponse:
        seller = await self._require_seller(user_id)
        data   = {k: v for k, v in payload.model_dump().items() if v is not None}
        updated = await self.seller_repo.update_profile(seller.id, **data)
        await self.db.commit()
        return self._to_profile(updated)

    async def update_logo(self, user_id: UUID, logo_url: str) -> LogoUploadResponse:
        seller = await self._require_seller(user_id)
        await self.seller_repo.update_logo(seller.id, logo_url)
        await self.db.commit()
        return LogoUploadResponse(logo_url=logo_url)

    # ── Dashboard ──────────────────────────────────────────────────────────────

    async def get_dashboard(self, user_id: UUID, period: str) -> SellerDashboardResponse:
        seller = await self._require_seller(user_id)
        self._require_active(seller)

        wallet        = await self.wallet_repo.get_by_seller_id(seller.id)
        product_count = await self.seller_repo.count_published_products(seller.id)

        return SellerDashboardResponse(
            period            = period,
            gross_revenue     = 0,
            commission_paid   = 0,
            net_earnings      = 0,
            order_count       = 0,
            product_count     = product_count,
            slots_used        = seller.slots_used,
            slots_available   = seller.slots_available,
            pending_balance   = int(wallet.pending_balance)   if wallet else 0,
            available_balance = int(wallet.available_balance) if wallet else 0,
            status_breakdown  = OrderStatusBreakdown(),
        )

    # ── Bank Accounts ──────────────────────────────────────────────────────────

    async def list_bank_accounts(self, user_id: UUID) -> list[BankAccountResponse]:
        seller   = await self._require_seller(user_id)
        accounts = await self.bank_repo.list_by_seller(seller.id)
        return [BankAccountResponse.model_validate(a) for a in accounts]

    async def add_bank_account(
        self, user_id: UUID, payload: CreateBankAccountRequest
    ) -> BankAccountResponse:
        seller = await self._require_seller(user_id)
        if payload.is_default:
            await self.bank_repo.clear_default(seller.id)
        account = await self.bank_repo.create(seller.id, **payload.model_dump())
        await self.db.commit()
        await self.db.refresh(account)
        return BankAccountResponse.model_validate(account)

    async def delete_bank_account(self, user_id: UUID, account_id: UUID) -> None:
        seller  = await self._require_seller(user_id)
        deleted = await self.bank_repo.delete(account_id, seller.id)
        if not deleted:
            raise NotFoundError("Bank account not found")
        await self.db.commit()

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _require_seller(self, user_id: UUID) -> Seller:
        seller = await self.seller_repo.get_by_user_id(user_id)
        if not seller:
            raise NotFoundError("Seller profile not found")
        return seller

    @staticmethod
    def _require_active(seller: Seller) -> None:
        if seller.status != SellerStatus.active:
            raise PermissionDeniedError(
                f"Account is '{seller.status.value}'. Only active sellers can access this."
            )

    async def _unique_slug(self, brand_name: str) -> str:
        base      = _slugify(brand_name)
        candidate = base
        counter   = 1
        while await self.seller_repo.get_by_slug(candidate):
            candidate = f"{base}-{counter}"
            counter  += 1
        return candidate

    @staticmethod
    def _to_profile(seller: Seller) -> SellerProfileResponse:
        return SellerProfileResponse(
            id               = seller.id,
            brand_name       = seller.brand_name,
            slug             = seller.slug,
            description      = seller.description,
            logo_url         = seller.logo_url,
            brand_color      = seller.brand_color,
            return_policy    = seller.return_policy,
            whatsapp_number  = seller.whatsapp_number,
            instagram_handle = seller.instagram_handle,
            status           = seller.status.value,
            total_slots      = seller.total_slots,
            slots_used       = seller.slots_used,
            slots_available  = seller.slots_available,
            joined_at        = seller.created_at,
        )