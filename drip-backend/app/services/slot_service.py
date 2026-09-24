from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError, PermissionDeniedError, InsufficientBalanceError, BusinessRuleError
)
from app.models.seller import SellerStatus
from app.repositories.seller_repo import SellerRepository, WalletRepository
from app.schemas.seller import SlotPricingResponse, SlotPurchaseRequest, SlotPurchaseResponse

REGISTRATION_FEE = 5000
BASE_SLOTS       = 50
EXTRA_SLOT_PRICE = 50


class SlotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db          = db
        self.seller_repo = SellerRepository(db)
        self.wallet_repo = WalletRepository(db)

    async def get_pricing(self, extra_slots: int) -> SlotPricingResponse:
        from app.services.platform_settings import get_platform_settings
        policy = await get_platform_settings(self.db)
        return SlotPricingResponse(
            registration_fee=policy.registration_fee, base_slots=BASE_SLOTS,
            extra_slots=extra_slots, extra_slot_price=policy.extra_slot_price,
            extra_cost=extra_slots * policy.extra_slot_price,
            total_cost=policy.registration_fee + extra_slots * policy.extra_slot_price,
            total_slots=BASE_SLOTS + extra_slots,
        )

    # ── Public pricing calculator (no DB) ─────────────────────────────────────

    @staticmethod
    def calculate_pricing(extra_slots: int) -> SlotPricingResponse:
        extra_cost = extra_slots * EXTRA_SLOT_PRICE
        return SlotPricingResponse(
            registration_fee = REGISTRATION_FEE,
            base_slots       = BASE_SLOTS,
            extra_slots      = extra_slots,
            extra_slot_price = EXTRA_SLOT_PRICE,
            extra_cost       = extra_cost,
            total_cost       = REGISTRATION_FEE + extra_cost,
            total_slots      = BASE_SLOTS + extra_slots,
        )

    async def purchase_slots(
        self, user_id: UUID, payload: SlotPurchaseRequest
    ) -> SlotPurchaseResponse:
        seller = await self.seller_repo.get_by_user_id(user_id)
        if not seller:
            raise NotFoundError("Seller profile not found")

        seller_status = seller.status.value if hasattr(seller.status, 'value') else seller.status
        if seller_status != SellerStatus.active.value:
            raise PermissionDeniedError(
                f"Only active sellers can purchase slots. Status: {seller_status}"
            )

        if payload.payment_method != "wallet":
            raise BusinessRuleError("Extra slots currently require wallet payment")
        from sqlalchemy import select
        from app.models.seller import Seller, SellerWallet
        await self.db.execute(select(Seller.id).where(Seller.id == seller.id).with_for_update())
        await self.db.execute(select(SellerWallet.id).where(SellerWallet.seller_id == seller.id).with_for_update())
        from app.services.platform_settings import get_platform_settings
        policy = await get_platform_settings(self.db)
        amount = Decimal(payload.quantity * policy.extra_slot_price)

        if payload.payment_method == "wallet":
            await self._charge_wallet(seller.id, amount)

        updated = await self.seller_repo.add_slots(seller.id, payload.quantity)
        await self.db.commit()

        return SlotPurchaseResponse(
            slots_purchased     = payload.quantity,
            new_total_slots     = updated.total_slots,
            new_slots_available = updated.slots_available,
            amount_charged      = int(amount),
        )
    # ── Guard used by Product service (Block 4) ────────────────────────────────

    async def assert_slot_available(self, seller_id: UUID) -> None:
        seller = await self.seller_repo.get_by_id(seller_id)
        if not seller:
            raise NotFoundError("Seller not found")
        if seller.slots_used >= seller.total_slots:
            raise PermissionDeniedError(
                f"No slots available ({seller.slots_used}/{seller.total_slots}). "
                "Purchase extra slots at PKR 50 each."
            )

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _charge_wallet(self, seller_id: UUID, amount: Decimal) -> None:
        wallet = await self.wallet_repo.get_by_seller_id(seller_id, for_update=True)
        if not wallet:
            raise NotFoundError("Seller wallet not found")
        if wallet.available_balance < amount:
            raise InsufficientBalanceError(
                f"Need PKR {int(amount):,}, have PKR {int(wallet.available_balance):,}"
            )
        await self.wallet_repo.debit_available(seller_id, amount)
        from uuid import uuid4
        from app.models.wallet import WalletTxType
        from app.repositories.wallet_repo import WalletTransactionRepository
        await self.db.refresh(wallet)
        await WalletTransactionRepository(self.db).create(
            seller_id=seller_id, type=WalletTxType.debit_adjustment, amount=amount,
            balance_after=wallet.available_balance, reference=f"slot-purchase:{uuid4()}",
            note="Additional product slots purchased",
        )
