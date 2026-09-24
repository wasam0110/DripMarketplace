from __future__ import annotations
from decimal import Decimal

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
        self.user_repo = UserRepository

    # ── Registration (public — creates User + Seller in one call) ──────────────

    async def register(self, payload: SellerRegistrationRequest) -> SellerRegistrationResponse:
        # 1. Email must not already exist
        if await self.user_repo.get_by_email(self.db, payload.email):
            raise ConflictError("An account with this email already exists")

        # 2. Brand name must be globally unique
        if await self.seller_repo.get_by_brand_name(payload.brand_name):
            raise ConflictError(f"Brand name '{payload.brand_name}' is already taken")

        # 3. Find a unique slug
        slug = await self._unique_slug(payload.brand_name)

        # 4. Create User with role=seller
        user = await self.user_repo.create(
            self.db,
            email         = payload.email,
            password_hash = hash_password(payload.password),
            first_name    = payload.first_name,
            last_name     = payload.last_name,
            role          = UserRole.seller,
        )

        # 5. Create Seller linked to that user
        from app.services.slot_service import SlotService
        pricing = await SlotService(self.db).get_pricing(payload.extra_slots)
        total_slots = pricing.total_slots
        seller = await self.seller_repo.create(
            user_id          = user.id,
            brand_name       = payload.brand_name,
            slug             = slug,
            description      = payload.description,
            return_policy    = payload.return_policy,
            whatsapp_number  = payload.whatsapp_number,
            instagram_handle = payload.instagram_handle,
            total_slots      = total_slots,
            registration_fee = Decimal(pricing.total_cost),
            status           = SellerStatus.pending_payment if pricing.total_cost else SellerStatus.pending_approval,
        )

        # 6. Create zero-balance wallet
        await self.wallet_repo.create_for_seller(seller.id)

        await self.db.commit()

        from app.core.config import settings
        if settings.ENVIRONMENT != "test":
            from app.core.security import create_email_verify_token
            from arq import create_pool
            from arq.connections import RedisSettings
            try:
                pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
                try:
                    await pool.enqueue_job("task_send_verification_email", user.email, user.first_name or "there", create_email_verify_token(str(user.id)))
                finally:
                    await pool.aclose()
            except Exception:
                from app.core.logging import get_logger
                get_logger(__name__).warning("seller.verification_enqueue_failed", seller_id=str(seller.id))
        return SellerRegistrationResponse(
            seller_id = seller.id,
            amount_due = seller.registration_fee,
            message   = (
                f"Application submitted. Complete payment of PKR {seller.registration_fee:,.2f} "
                "before your application can be approved."
                if seller.registration_fee else
                "Application submitted for approval. No registration payment is due."
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

        from sqlalchemy import select, func
        from datetime import datetime, UTC, timedelta
        from app.models.wallet import CommissionLedger
        from app.models.order import SellerOrder
        now = datetime.now(UTC)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) if period == "today" else now - timedelta(days={"week": 7, "month": 30, "quarter": 90, "year": 365}.get(period, 30))
        gross, commission, net = (await self.db.execute(select(
            func.coalesce(func.sum(CommissionLedger.gross_amount), 0),
            func.coalesce(func.sum(CommissionLedger.commission_amount), 0),
            func.coalesce(func.sum(CommissionLedger.seller_amount), 0))
            .where(CommissionLedger.seller_id == seller.id, CommissionLedger.settled_at >= start))).one()
        rows = (await self.db.execute(select(SellerOrder.status, func.count()).where(SellerOrder.seller_id == seller.id, SellerOrder.created_at >= start).group_by(SellerOrder.status))).all()
        counts = {status.value: count for status, count in rows}
        return SellerDashboardResponse(
            period            = period,
            gross_revenue     = gross,
            commission_paid   = commission,
            net_earnings      = net,
            order_count       = sum(counts.values()),
            product_count     = product_count,
            slots_used        = seller.slots_used,
            slots_available   = seller.slots_available,
            pending_balance   = wallet.pending_balance if wallet else 0,
            available_balance = wallet.available_balance if wallet else 0,
            status_breakdown  = OrderStatusBreakdown(**counts),
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
            registration_amount_due = Decimal("0") if seller.registration_paid_at else seller.registration_fee,
            registration_paid_at = seller.registration_paid_at,
        )
