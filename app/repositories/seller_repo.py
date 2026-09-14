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
        self.db = db

    async def create(self, **kwargs) -> Seller:
        seller = Seller(**kwargs)
        self.db.add(seller)
        await self.db.flush()
        await self.db.refresh(seller)
        return seller

    async def get_by_id(self, seller_id: UUID) -> Optional[Seller]:
        result = await self.db.execute(
            select(Seller)
            .options(selectinload(Seller.wallet), selectinload(Seller.bank_accounts))
            .where(Seller.id == seller_id, Seller.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Optional[Seller]:
        result = await self.db.execute(
            select(Seller)
            .options(selectinload(Seller.wallet), selectinload(Seller.bank_accounts))
            .where(Seller.user_id == user_id, Seller.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Seller]:
        result = await self.db.execute(
            select(Seller).where(Seller.slug == slug, Seller.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_brand_name(self, brand_name: str) -> Optional[Seller]:
        result = await self.db.execute(
            select(Seller).where(
                func.lower(Seller.brand_name) == brand_name.lower(),
                Seller.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def exists_for_user(self, user_id: UUID) -> bool:
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
        values: dict = {"status": status, "updated_at": datetime.utcnow()}
        if approved_by:
            values["approved_by"] = approved_by
            values["approved_at"] = datetime.utcnow()
        if rejected_reason:
            values["rejected_reason"] = rejected_reason
        await self.db.execute(update(Seller).where(Seller.id == seller_id).values(**values))

    async def update_profile(self, seller_id: UUID, **kwargs) -> Seller:
        kwargs["updated_at"] = datetime.utcnow()
        await self.db.execute(update(Seller).where(Seller.id == seller_id).values(**kwargs))
        await self.db.flush()
        return await self.get_by_id(seller_id)  # type: ignore[return-value]

    async def update_logo(self, seller_id: UUID, logo_url: str) -> None:
        await self.db.execute(
            update(Seller)
            .where(Seller.id == seller_id)
            .values(logo_url=logo_url, updated_at=datetime.utcnow())
        )

    async def add_slots(self, seller_id: UUID, quantity: int) -> Seller:
        await self.db.execute(
            update(Seller)
            .where(Seller.id == seller_id)
            .values(total_slots=Seller.total_slots + quantity, updated_at=datetime.utcnow())
        )
        await self.db.flush()
        return await self.get_by_id(seller_id)  # type: ignore[return-value]

    async def increment_slots_used(self, seller_id: UUID) -> None:
        await self.db.execute(
            update(Seller)
            .where(Seller.id == seller_id)
            .values(slots_used=Seller.slots_used + 1, updated_at=datetime.utcnow())
        )

    async def decrement_slots_used(self, seller_id: UUID) -> None:
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
        self.db = db

    async def create_for_seller(self, seller_id: UUID) -> SellerWallet:
        wallet = SellerWallet(seller_id=seller_id)
        self.db.add(wallet)
        await self.db.flush()
        return wallet

    async def get_by_seller_id(self, seller_id: UUID) -> Optional[SellerWallet]:
        result = await self.db.execute(
            select(SellerWallet).where(SellerWallet.seller_id == seller_id)
        )
        return result.scalar_one_or_none()

    async def credit_pending(self, seller_id: UUID, amount: Decimal) -> None:
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
        await self.db.execute(
            update(SellerWallet)
            .where(SellerWallet.seller_id == seller_id)
            .values(
                total_commission=SellerWallet.total_commission + commission,
                updated_at=datetime.utcnow(),
            )
        )

    async def debit_available(self, seller_id: UUID, amount: Decimal) -> None:
        await self.db.execute(
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


class BankAccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_seller(self, seller_id: UUID) -> Sequence[SellerBankAccount]:
        result = await self.db.execute(
            select(SellerBankAccount)
            .where(SellerBankAccount.seller_id == seller_id)
            .order_by(SellerBankAccount.created_at)
        )
        return result.scalars().all()

    async def create(self, seller_id: UUID, **kwargs) -> SellerBankAccount:
        account = SellerBankAccount(seller_id=seller_id, **kwargs)
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def clear_default(self, seller_id: UUID) -> None:
        await self.db.execute(
            update(SellerBankAccount)
            .where(SellerBankAccount.seller_id == seller_id)
            .values(is_default=False)
        )

    async def delete(self, account_id: UUID, seller_id: UUID) -> bool:
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