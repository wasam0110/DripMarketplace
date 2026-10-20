"""repositories / seller repo.

Database operations used by services within their transaction boundaries.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.seller import Seller, SellerStatus, SellerWallet, SellerBankAccount


class SellerRepository:
    def __init__(self, db: AsyncSession) -> None:
        """Bind SellerRepository to its injected dependencies for subsequent operations."""
        self.db = db

    async def create(self, **kwargs) -> Seller:
        """Insert a seller and return it within the caller's transaction."""
        seller = Seller(**kwargs)
        self.db.add(seller)
        await self.db.flush()
        await self.db.refresh(seller)
        return seller

    async def get_by_id(self, seller_id: UUID) -> Optional[Seller]:
        """Look up a seller by id; return None when absent."""
        result = await self.db.execute(
            select(Seller)
            .options(selectinload(Seller.wallet), selectinload(Seller.bank_accounts))
            .where(Seller.id == seller_id, Seller.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Optional[Seller]:
        """Look up a seller by user id; return None when absent."""
        result = await self.db.execute(
            select(Seller)
            .options(selectinload(Seller.wallet), selectinload(Seller.bank_accounts))
            .where(Seller.user_id == user_id, Seller.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Seller]:
        """Look up a seller by slug; return None when absent."""
        result = await self.db.execute(
            select(Seller).where(Seller.slug == slug, Seller.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_brand_name(self, brand_name: str) -> Optional[Seller]:
        """Look up a seller by brand name; return None when absent."""
        result = await self.db.execute(
            select(Seller).where(
                func.lower(Seller.brand_name) == brand_name.lower(),
                Seller.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def exists_for_user(self, user_id: UUID) -> bool:
        """Check for an existing seller for this user."""
        result = await self.db.execute(
            select(Seller.id).where(
                Seller.user_id == user_id, Seller.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none() is not None

    async def update_status(
        self,
        seller_id: UUID,
        status: SellerStatus,
        *,
        approved_by: Optional[UUID] = None,
        rejected_reason: Optional[str] = None,
    ) -> None:
        """Apply the seller status change within the caller's transaction."""
        values: dict = {"status": status, "updated_at": datetime.utcnow()}
        if approved_by:
            values["approved_by"] = approved_by
            values["approved_at"] = datetime.utcnow()
        if rejected_reason:
            values["rejected_reason"] = rejected_reason
        await self.db.execute(update(Seller).where(Seller.id == seller_id).values(**values))

    async def update_profile(self, seller_id: UUID, **kwargs) -> Seller:
        """Apply seller profile fields and reload the seller record."""
        kwargs["updated_at"] = datetime.utcnow()
        await self.db.execute(update(Seller).where(Seller.id == seller_id).values(**kwargs))
        await self.db.flush()
        return await self.get_by_id(seller_id)  # type: ignore[return-value]

    async def update_logo(self, seller_id: UUID, logo_url: str) -> None:
        """Store the uploaded brand logo URL on the seller record."""
        await self.db.execute(
            update(Seller)
            .where(Seller.id == seller_id)
            .values(logo_url=logo_url, updated_at=datetime.utcnow())
        )

    async def add_slots(self, seller_id: UUID, quantity: int) -> Seller:
        """Increase purchased listing capacity and return the updated seller."""
        await self.db.execute(
            update(Seller)
            .where(Seller.id == seller_id)
            .values(total_slots=Seller.total_slots + quantity, updated_at=datetime.utcnow())
        )
        await self.db.flush()
        return await self.get_by_id(seller_id)  # type: ignore[return-value]

    async def increment_slots_used(self, seller_id: UUID) -> None:
        """Increment occupied listing slots when a product is published."""
        await self.db.execute(
            update(Seller)
            .where(Seller.id == seller_id)
            .values(slots_used=Seller.slots_used + 1, updated_at=datetime.utcnow())
        )

    async def decrement_slots_used(self, seller_id: UUID) -> None:
        """Release an occupied listing slot when a product is unpublished or deleted."""
        await self.db.execute(
            update(Seller)
            .where(Seller.id == seller_id, Seller.slots_used > 0)
            .values(slots_used=Seller.slots_used - 1, updated_at=datetime.utcnow())
        )

    async def count_published_products(self, seller_id: UUID) -> int:
        """Requires Block 4 (Products). Returns 0 until then."""
        try:
            from app.models.product import Product
            result = await self.db.execute(
                select(func.count(Product.id)).where(
                    Product.seller_id == seller_id,
                    Product.is_published.is_(True),
                )
            )
            return result.scalar_one() or 0
        except ImportError:
            return 0


class WalletRepository:
    def __init__(self, db: AsyncSession) -> None:
        """Bind WalletRepository to its injected dependencies for subsequent operations."""
        self.db = db

    async def create_for_seller(self, seller_id: UUID) -> SellerWallet:
        """Initialize the seller's wallet within the registration transaction."""
        wallet = SellerWallet(seller_id=seller_id)
        self.db.add(wallet)
        await self.db.flush()
        return wallet

    async def get_by_seller_id(self, seller_id: UUID, *, for_update: bool = False) -> Optional[SellerWallet]:
        """Look up a seller wallet by seller id; return None when absent."""
        query = select(SellerWallet).where(SellerWallet.seller_id == seller_id)
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        result = await self.db.execute(
            query
        )
        return result.scalar_one_or_none()

    async def credit_pending(self, seller_id: UUID, amount: Decimal) -> None:
        """Credit sale proceeds into the wallet's held balance."""
        await self.db.execute(
            update(SellerWallet)
            .where(SellerWallet.seller_id == seller_id)
            .values(
                pending_balance=SellerWallet.pending_balance + amount,
                total_earned=SellerWallet.total_earned + amount,
                updated_at=datetime.utcnow(),
            )
        )

    async def release_pending_to_available(self, seller_id: UUID, amount: Decimal) -> None:
        """Move eligible held proceeds into the withdrawable balance."""
        await self.db.execute(
            update(SellerWallet)
            .where(SellerWallet.seller_id == seller_id)
            .values(
                available_balance=SellerWallet.available_balance + amount,
                pending_balance=SellerWallet.pending_balance - amount,
                updated_at=datetime.utcnow(),
            )
        )

    async def charge_commission(self, seller_id: UUID, commission: Decimal) -> None:
        """Record the wallet's accumulated platform commission charge."""
        await self.db.execute(
            update(SellerWallet)
            .where(SellerWallet.seller_id == seller_id)
            .values(
                total_commission=SellerWallet.total_commission + commission,
                updated_at=datetime.utcnow(),
            )
        )

    async def debit_available(self, seller_id: UUID, amount: Decimal) -> None:
        """Debit withdrawable funds only when the current balance covers the amount."""
        result = await self.db.execute(
            update(SellerWallet)
            .where(
                SellerWallet.seller_id == seller_id,
                SellerWallet.available_balance >= amount,
            )
            .values(
                available_balance=SellerWallet.available_balance - amount,
                updated_at=datetime.utcnow(),
            )
        )
        if result.rowcount != 1:
            from app.core.exceptions import InsufficientBalanceError
            raise InsufficientBalanceError("Available balance changed; reload your wallet")

    async def credit_available(self, seller_id: UUID, amount: Decimal) -> None:
        """Credit withdrawable funds within the caller's transaction."""
        await self.db.execute(update(SellerWallet).where(SellerWallet.seller_id == seller_id).values(
            available_balance=SellerWallet.available_balance + amount,
            updated_at=datetime.utcnow(),
        ))


class BankAccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        """Bind BankAccountRepository to its injected dependencies for subsequent
        operations.
        """
        self.db = db

    async def list_by_seller(self, seller_id: UUID) -> Sequence[SellerBankAccount]:
        """Query payout bank account records for by seller reads using the caller's
        session.
        """
        result = await self.db.execute(
            select(SellerBankAccount)
            .where(SellerBankAccount.seller_id == seller_id)
            .order_by(SellerBankAccount.created_at)
        )
        return result.scalars().all()

    async def create(self, seller_id: UUID, **kwargs) -> SellerBankAccount:
        """Insert a payout bank account and return it within the caller's transaction."""
        account = SellerBankAccount(seller_id=seller_id, **kwargs)
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def clear_default(self, seller_id: UUID) -> None:
        """Clear the seller's existing default payout account before selecting another."""
        await self.db.execute(
            update(SellerBankAccount)
            .where(SellerBankAccount.seller_id == seller_id)
            .values(is_default=False)
        )

    async def delete(self, account_id: UUID, seller_id: UUID) -> bool:
        """Delete the bank account only when it belongs to the supplied seller."""
        result = await self.db.execute(
            select(SellerBankAccount).where(
                SellerBankAccount.id == account_id,
                SellerBankAccount.seller_id == seller_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            return False
        await self.db.delete(account)
        return True
