from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError, PermissionDeniedError, InsufficientBalanceError
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

    # ── Purchase ───────────────────────────────────────────────────────────────

    async def purchase_slots(
        self, user_id: UUID, payload: SlotPurchaseRequest
    ) -> SlotPurchaseResponse:
        seller = await self.seller_repo.get_by_user_id(user_id)
        if not seller:
            raise NotFoundError("Seller profile not found")

        if seller.status != SellerStatus.active:
            raise PermissionDeniedError(
                f"Only active sellers can purchase slots. Status: {seller.status.value}"
            )

        amount = Decimal(payload.quantity * EXTRA_SLOT_PRICE)

        if payload.payment_method == "wallet":
            await self._charge_wallet(seller.id, amount)
        # jazzcash / easypaisa payment intent wired in Block 7

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
        wallet = await self.wallet_repo.get_by_seller_id(seller_id)
        if not wallet:
            raise NotFoundError("Seller wallet not found")
        if wallet.available_balance < amount:
            raise InsufficientBalanceError(
                f"Need PKR {int(amount):,}, have PKR {int(wallet.available_balance):,}"
            )
        await self.wallet_repo.debit_available(seller_id, amount)