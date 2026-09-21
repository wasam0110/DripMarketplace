from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.models.return_ import Return, ReturnStatus, Dispute, DisputeStatus
from app.models.order import Order, OrderStatus, OrderItem, SellerOrder
from app.repositories.return_repo import ReturnRepository, DisputeRepository
from app.repositories.inventory_repo import InventoryRepository
from app.schemas.return_ import (
    CreateReturnRequest, ReturnDetailResponse, ReturnRowResponse,
    PaginatedReturns, ReturnItemResponse,
    OpenDisputeRequest, AddDisputeMessageRequest,
    DisputeDetailResponse, DisputeMessageResponse,
    AdminReturnActionRequest, ResolveDisputeRequest,
)

RETURNABLE_STATUSES = {OrderStatus.delivered, OrderStatus.completed}


class ReturnService:
    def __init__(self, db: AsyncSession) -> None:
        self.db          = db
        self.return_repo = ReturnRepository(db)
        self.dispute_repo= DisputeRepository(db)
        self.inv_repo    = InventoryRepository(db)

    # ── Customer: request return ───────────────────────────────────────────────

    async def request_return(
        self, user_id: UUID, payload: CreateReturnRequest
    ) -> ReturnDetailResponse:
        # Verify seller_order belongs to user
        so_result = await self.db.execute(
            select(SellerOrder).where(SellerOrder.id == payload.seller_order_id)
        )
        seller_order = so_result.scalar_one_or_none()
        if not seller_order:
            raise NotFoundError("Seller order not found")

        order_result = await self.db.execute(
            select(Order).where(Order.id == seller_order.order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order or order.user_id != user_id:
            raise PermissionDeniedError("You can only return your own orders")
        if order.status not in RETURNABLE_STATUSES:
            raise BusinessRuleError(
                f"Returns are only accepted for delivered orders. Current status: {order.status.value}"
            )

        # Validate order items belong to this seller_order
        for req_item in payload.items:
            item_result = await self.db.execute(
                select(OrderItem).where(
                    OrderItem.id == req_item.order_item_id,
                    OrderItem.order_id == order.id,
                    OrderItem.seller_id == seller_order.seller_id,
                )
            )
            order_item = item_result.scalar_one_or_none()
            if not order_item:
                raise BusinessRuleError(f"Order item {req_item.order_item_id} not found in this seller order")
            if req_item.quantity > order_item.quantity:
                raise BusinessRuleError(
                    f"Cannot return more than purchased quantity for {order_item.product_name}"
                )

        return_ = await self.return_repo.create(
            order_id        = order.id,
            seller_order_id = payload.seller_order_id,
            user_id         = user_id,
            reason          = payload.reason,
            notes           = payload.notes,
        )
        for req_item in payload.items:
            await self.return_repo.add_item(
                return_id     = return_.id,
                order_item_id = req_item.order_item_id,
                quantity      = req_item.quantity,
                reason        = req_item.reason,
            )

        await self.db.commit()
        return_ = await self.return_repo.get_by_id(return_.id, user_id)
        return self._to_detail(return_)  # type: ignore[arg-type]

    async def get_return(self, return_id: UUID, user_id: UUID) -> ReturnDetailResponse:
        return_ = await self.return_repo.get_by_id(return_id, user_id)
        if not return_:
            raise NotFoundError("Return not found")
        return self._to_detail(return_)

    async def list_returns(self, user_id: UUID, page: int = 1) -> PaginatedReturns:
        rows, total = await self.return_repo.list_by_user(user_id, page)
        total_pages = max(1, (total + 9) // 10)
        return PaginatedReturns(
            data=[self._to_row(r) for r in rows],
            total=total, page=page, total_pages=total_pages,
        )

    # ── Customer: disputes ─────────────────────────────────────────────────────

    async def open_dispute(
        self, return_id: UUID, user_id: UUID, payload: OpenDisputeRequest
    ) -> DisputeDetailResponse:
        return_ = await self.return_repo.get_by_id(return_id, user_id)
        if not return_:
            raise NotFoundError("Return not found")
        if return_.status not in (ReturnStatus.rejected,):
            raise BusinessRuleError("Disputes can only be opened on rejected returns")
        if return_.dispute:
            raise BusinessRuleError("A dispute is already open for this return")

        so_result = await self.db.execute(
            select(SellerOrder).where(SellerOrder.id == return_.seller_order_id)
        )
        seller_order = so_result.scalar_one_or_none()

        dispute = await self.dispute_repo.create(
            return_id = return_id,
            seller_id = seller_order.seller_id if seller_order else user_id,
            user_id   = user_id,
        )
        await self.dispute_repo.add_message(
            dispute_id = dispute.id,
            sender_id  = user_id,
            body       = payload.message,
        )
        await self.db.commit()
        dispute = await self.dispute_repo.get_by_id(dispute.id)
        return self._to_dispute(dispute)  # type: ignore[arg-type]

    async def get_dispute(self, return_id: UUID, user_id: UUID) -> DisputeDetailResponse:
        return_ = await self.return_repo.get_by_id(return_id, user_id)
        if not return_:
            raise NotFoundError("Return not found")
        if not return_.dispute:
            raise NotFoundError("No dispute found for this return")
        return self._to_dispute(return_.dispute)

    async def add_message(
        self, return_id: UUID, sender_id: UUID, payload: AddDisputeMessageRequest
    ) -> DisputeMessageResponse:
        dispute = await self.dispute_repo.get_by_return_id(return_id)
        if not dispute:
            raise NotFoundError("Dispute not found")
        if dispute.status in (DisputeStatus.resolved_customer, DisputeStatus.resolved_seller, DisputeStatus.closed):
            raise BusinessRuleError("Cannot add messages to a resolved dispute")

        msg = await self.dispute_repo.add_message(
            dispute_id=dispute.id, sender_id=sender_id, body=payload.body
        )
        await self.db.commit()
        return DisputeMessageResponse(
            id=msg.id, sender_id=msg.sender_id, body=msg.body, created_at=msg.created_at
        )

    # ── Admin: return management ───────────────────────────────────────────────

    async def admin_list_returns(
        self, status: Optional[str] = None, page: int = 1
    ) -> PaginatedReturns:
        rows, total = await self.return_repo.list_admin(status, page)
        total_pages = max(1, (total + 24) // 25)
        return PaginatedReturns(
            data=[self._to_row(r) for r in rows],
            total=total, page=page, total_pages=total_pages,
        )

    async def approve_return(
        self, return_id: UUID, admin_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_admin(return_id)
        if return_.status != ReturnStatus.requested:
            raise BusinessRuleError("Can only approve requested returns")
        await self.return_repo.update_status(return_id, ReturnStatus.approved, notes=payload.admin_note)
        await self.db.commit()
        return {"message": "Return approved. Awaiting item receipt."}

    async def reject_return(
        self, return_id: UUID, admin_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_admin(return_id)
        if return_.status != ReturnStatus.requested:
            raise BusinessRuleError("Can only reject requested returns")
        await self.return_repo.update_status(return_id, ReturnStatus.rejected, notes=payload.admin_note)
        await self.db.commit()
        return {"message": "Return rejected"}

    async def mark_received(
        self, return_id: UUID, admin_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_admin(return_id)
        if return_.status != ReturnStatus.approved:
            raise BusinessRuleError("Can only mark approved returns as received")
        await self.return_repo.update_status(return_id, ReturnStatus.received, notes=payload.admin_note)
        await self.db.commit()
        return {"message": "Return marked as received. Ready to process refund."}

    async def process_refund(
        self, return_id: UUID, admin_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_admin(return_id)
        if return_.status != ReturnStatus.received:
            raise BusinessRuleError("Can only refund received returns")

        # Restock inventory
        for item in return_.items:
            order_item_result = await self.db.execute(
                select(OrderItem).where(OrderItem.id == item.order_item_id)
            )
            order_item = order_item_result.scalar_one_or_none()
            if order_item:
                await self.inv_repo.release(order_item.variant_id, item.quantity)

        await self.return_repo.update_status(
            return_id, ReturnStatus.refunded,
            notes=payload.admin_note,
            resolved_at=datetime.utcnow(),
        )
        await self.db.commit()
        return {"message": "Return refunded. Inventory restocked."}

    # ── Admin: dispute management ──────────────────────────────────────────────

    async def admin_list_disputes(
        self, status: Optional[str] = None, page: int = 1
    ) -> dict:
        rows, total = await self.dispute_repo.list_admin(status, page)
        return {
            "data":  [self._to_dispute(d) for d in rows],
            "total": total,
            "page":  page,
        }

    async def resolve_dispute(
        self, dispute_id: UUID, admin_id: UUID, payload: ResolveDisputeRequest
    ) -> DisputeDetailResponse:
        dispute = await self.dispute_repo.get_by_id(dispute_id)
        if not dispute:
            raise NotFoundError("Dispute not found")
        if dispute.status in (DisputeStatus.resolved_customer, DisputeStatus.resolved_seller, DisputeStatus.closed):
            raise BusinessRuleError("Dispute is already resolved")

        status = (
            DisputeStatus.resolved_customer
            if payload.in_favor_of == "customer"
            else DisputeStatus.resolved_seller
        )
        await self.dispute_repo.resolve(
            dispute_id      = dispute_id,
            status          = status,
            resolution_note = payload.resolution_note,
            resolved_by     = admin_id,
        )
        await self.db.commit()
        dispute = await self.dispute_repo.get_by_id(dispute_id)
        return self._to_dispute(dispute)  # type: ignore[arg-type]

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_return_admin(self, return_id: UUID) -> Return:
        return_ = await self.return_repo.get_by_id(return_id)
        if not return_:
            raise NotFoundError("Return not found")
        return return_

    @staticmethod
    def _to_row(r: Return) -> ReturnRowResponse:
        return ReturnRowResponse(
            id              = r.id,
            order_id        = r.order_id,
            seller_order_id = r.seller_order_id,
            status          = r.status.value,
            reason          = r.reason,
            item_count      = len(r.items),
            requested_at    = r.requested_at,
            resolved_at     = r.resolved_at,
        )

    @staticmethod
    def _to_detail(r: Return) -> ReturnDetailResponse:
        return ReturnDetailResponse(
            id              = r.id,
            order_id        = r.order_id,
            seller_order_id = r.seller_order_id,
            status          = r.status.value,
            reason          = r.reason,
            notes           = r.notes,
            item_count      = len(r.items),
            requested_at    = r.requested_at,
            resolved_at     = r.resolved_at,
            items           = [
                ReturnItemResponse(
                    id=i.id, order_item_id=i.order_item_id,
                    quantity=i.quantity, reason=i.reason
                ) for i in r.items
            ],
        )

    @staticmethod
    def _to_dispute(d: Dispute) -> DisputeDetailResponse:
        return DisputeDetailResponse(
            id              = d.id,
            return_id       = d.return_id,
            seller_id       = d.seller_id,
            status          = d.status.value,
            resolution_note = d.resolution_note,
            created_at      = d.created_at,
            resolved_at     = d.resolved_at,
            messages        = [
                DisputeMessageResponse(
                    id=m.id, sender_id=m.sender_id,
                    body=m.body, created_at=m.created_at
                ) for m in d.messages
            ],
        )