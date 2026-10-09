from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.order import Order, OrderItem, OrderStatus, SellerOrder
from app.models.payment import Payment, PaymentStatus, Refund
from app.models.return_ import Dispute, DisputeStatus, Return, ReturnStatus
from app.models.user import User
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.return_repo import DisputeRepository, ReturnRepository
from app.schemas.return_ import (
    AddDisputeMessageRequest,
    AdminReturnActionRequest,
    AdminReturnCustomerResponse,
    AdminReturnDetailResponse,
    AdminReturnDisputeResponse,
    AdminReturnItemResponse,
    AdminReturnOrderResponse,
    AdminReturnRefundResponse,
    AdminReturnSellerResponse,
    CreateReturnRequest,
    DisputeDetailResponse,
    DisputeMessageResponse,
    OpenDisputeRequest,
    PaginatedReturns,
    ResolveDisputeRequest,
    ReturnDetailResponse,
    ReturnItemResponse,
    ReturnRowResponse,
    SellerReturnDetailResponse,
)
from app.services.order_access import authorized_order, guest_token_matches

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
            select(SellerOrder).where(SellerOrder.id == payload.seller_order_id).with_for_update()
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
        return await self._create_return(order, seller_order, user_id, payload)

    async def request_guest_return(
        self, guest_token: str | None, payload: CreateReturnRequest
    ) -> ReturnDetailResponse:
        if not guest_token:
            raise AuthenticationError("Provide a guest order token")
        seller_order = await self.db.scalar(
            select(SellerOrder)
            .where(SellerOrder.id == payload.seller_order_id)
            .with_for_update()
        )
        if not seller_order:
            raise NotFoundError("Seller order not found")
        try:
            order = await authorized_order(
                self.db,
                seller_order.order_id,
                guest_token=guest_token,
                lock=True,
            )
        except NotFoundError as exc:
            raise NotFoundError("Seller order not found") from exc
        return await self._create_return(order, seller_order, None, payload)

    async def _create_return(
        self,
        order: Order,
        seller_order: SellerOrder,
        user_id: UUID | None,
        payload: CreateReturnRequest,
    ) -> ReturnDetailResponse:
        if order.status not in RETURNABLE_STATUSES:
            raise BusinessRuleError(
                f"Returns are only accepted for delivered orders. Current status: {order.status.value}"
            )

        if len({i.order_item_id for i in payload.items}) != len(payload.items):
            raise BusinessRuleError("Each order item may appear only once")
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
            from sqlalchemy import func

            from app.models.return_ import ReturnItem
            already_requested = await self.db.scalar(select(func.coalesce(func.sum(ReturnItem.quantity), 0)).join(Return).where(ReturnItem.order_item_id == order_item.id, Return.status != ReturnStatus.rejected))
            if req_item.quantity + already_requested > order_item.quantity:
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
        return_ = await self.return_repo.get_by_id(return_.id)
        return self._to_detail(return_)  # type: ignore[arg-type]

    async def get_return(self, return_id: UUID, user_id: UUID) -> ReturnDetailResponse:
        return_ = await self.return_repo.get_by_id(return_id, user_id)
        if not return_:
            raise NotFoundError("Return not found")
        return self._to_detail(return_)

    async def get_guest_return(
        self, return_id: UUID, guest_token: str | None
    ) -> ReturnDetailResponse:
        if not guest_token:
            raise AuthenticationError("Provide a guest order token")
        return_ = await self.return_repo.get_by_id(return_id)
        if (
            not return_
            or return_.user_id is not None
            or not guest_token_matches(guest_token, return_.order_id)
        ):
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
        # Match the owner-only policy of get_dispute/open_dispute. Check before
        # looking up the dispute so other users cannot probe its existence/state.
        return_ = await self.return_repo.get_by_id(return_id, sender_id)
        if not return_:
            raise NotFoundError("Return")

        dispute = await self.dispute_repo.get_by_return_id(return_id, for_update=True)
        if not dispute:
            raise NotFoundError("Dispute")
        if dispute.status in (DisputeStatus.resolved_customer, DisputeStatus.resolved_seller, DisputeStatus.closed):
            raise BusinessRuleError("Cannot add messages to a resolved dispute")

        msg = await self.dispute_repo.add_message(
            dispute_id=dispute.id, sender_id=sender_id, body=payload.body
        )
        await self.db.commit()
        return DisputeMessageResponse(
            id=msg.id, sender_id=msg.sender_id, body=msg.body, created_at=msg.created_at
        )

    # â”€â”€ Seller: owned return management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def seller_list_returns(
        self, seller_id: UUID, status: Optional[str] = None, page: int = 1
    ) -> PaginatedReturns:
        rows, total = await self.return_repo.list_seller(seller_id, status, page)
        return PaginatedReturns(
            data=[self._to_row(row) for row in rows],
            total=total,
            page=page,
            total_pages=max(1, (total + 24) // 25),
        )

    async def get_seller_return(
        self, return_id: UUID, seller_id: UUID
    ) -> SellerReturnDetailResponse:
        return_ = await self._get_return_seller(return_id, seller_id)
        order = await self.db.get(Order, return_.order_id)
        if not order:
            raise BusinessRuleError("Return order is missing")
        order_items = await self._load_order_items(return_)
        payment = await self.db.scalar(
            select(Payment).where(Payment.order_id == return_.order_id)
        )
        refund = await self.db.scalar(
            select(Refund)
            .where(Refund.return_id == return_.id)
            .order_by(Refund.created_at.desc())
            .limit(1)
        )
        return SellerReturnDetailResponse(
            **self._to_row(return_).model_dump(),
            notes=return_.notes,
            order_number=order.order_number,
            items=self._to_admin_items(return_, order_items),
            estimated_refund_amount=self._calculate_refund_amount(
                return_, order, order_items
            ),
            available_actions=self._available_seller_actions(return_.status),
            refund_status=(
                "completed" if refund and refund.processed_at else "pending" if refund else None
            ),
            dispute_status=return_.dispute.status.value if return_.dispute else None,
        )

    async def seller_approve_return(
        self, return_id: UUID, seller_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_seller(return_id, seller_id, lock=True)
        if return_.status != ReturnStatus.requested:
            raise BusinessRuleError("Can only approve requested returns")
        await self.return_repo.update_status(
            return_id, ReturnStatus.approved, notes=payload.admin_note
        )
        await self.db.commit()
        return {"message": "Return approved. Awaiting item receipt."}

    async def seller_reject_return(
        self, return_id: UUID, seller_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_seller(return_id, seller_id, lock=True)
        if return_.status != ReturnStatus.requested:
            raise BusinessRuleError("Can only reject requested returns")
        await self.return_repo.update_status(
            return_id, ReturnStatus.rejected, notes=payload.admin_note
        )
        await self.db.commit()
        return {"message": "Return rejected"}

    async def seller_mark_received(
        self, return_id: UUID, seller_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_seller(return_id, seller_id, lock=True)
        if return_.status != ReturnStatus.approved:
            raise BusinessRuleError("Can only mark approved returns as received")
        await self.return_repo.update_status(
            return_id, ReturnStatus.received, notes=payload.admin_note
        )
        await self.db.commit()
        return {"message": "Return marked as received. Awaiting administrator refund."}

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

    async def get_admin_return(self, return_id: UUID) -> AdminReturnDetailResponse:
        return_ = await self._get_return_admin(return_id)
        order = await self.db.get(Order, return_.order_id)
        customer = await self.db.get(User, return_.user_id) if return_.user_id else None
        seller_order = await self.db.scalar(
            select(SellerOrder)
            .options(selectinload(SellerOrder.seller))
            .where(SellerOrder.id == return_.seller_order_id)
        )
        if not order or not seller_order:
            raise BusinessRuleError("Return data is incomplete")

        order_items = await self._load_order_items(return_)
        payment = await self.db.scalar(
            select(Payment).where(Payment.order_id == return_.order_id)
        )
        refund = await self.db.scalar(
            select(Refund)
            .where(Refund.return_id == return_.id)
            .order_by(Refund.created_at.desc())
            .limit(1)
        )
        actions = self._available_admin_actions(return_.status, payment, refund)

        return AdminReturnDetailResponse(
            **self._to_row(return_).model_dump(),
            notes=return_.notes,
            customer=AdminReturnCustomerResponse(
                user_id=customer.id if customer else None,
                is_guest=customer is None,
                email=customer.email if customer else order.guest_email or "",
                first_name=customer.first_name if customer else order.guest_name,
                last_name=customer.last_name if customer else None,
                phone=customer.phone if customer else order.guest_phone,
            ),
            seller=AdminReturnSellerResponse(
                seller_id=seller_order.seller.id,
                brand_name=seller_order.seller.brand_name,
            ),
            order=AdminReturnOrderResponse(
                order_id=order.id,
                order_number=order.order_number,
                status=order.status.value,
                payment_method=order.payment_method.value,
                subtotal=order.subtotal,
                discount_amount=order.discount_amount,
                shipping_fee=order.shipping_fee,
                total=order.total,
                payment_id=payment.id if payment else None,
                payment_status=payment.status.value if payment else None,
            ),
            items=self._to_admin_items(return_, order_items),
            estimated_refund_amount=self._calculate_refund_amount(
                return_, order, order_items
            ),
            available_actions=actions,
            refund=(
                AdminReturnRefundResponse(
                    refund_id=refund.id,
                    status="completed" if refund.processed_at else "pending",
                    amount=refund.amount,
                    transfer_reference=refund.gateway_ref,
                    requested_at=refund.created_at,
                    processed_at=refund.processed_at,
                )
                if refund else None
            ),
            dispute=(
                AdminReturnDisputeResponse(
                    dispute_id=return_.dispute.id,
                    status=return_.dispute.status.value,
                )
                if return_.dispute else None
            ),
        )

    async def approve_return(
        self, return_id: UUID, admin_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_admin(return_id, lock=True)
        if return_.status != ReturnStatus.requested:
            raise BusinessRuleError("Can only approve requested returns")
        await self.return_repo.update_status(return_id, ReturnStatus.approved, notes=payload.admin_note)
        await self.db.commit()
        return {"message": "Return approved. Awaiting item receipt."}

    async def reject_return(
        self, return_id: UUID, admin_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_admin(return_id, lock=True)
        if return_.status != ReturnStatus.requested:
            raise BusinessRuleError("Can only reject requested returns")
        await self.return_repo.update_status(return_id, ReturnStatus.rejected, notes=payload.admin_note)
        await self.db.commit()
        return {"message": "Return rejected"}

    async def mark_received(
        self, return_id: UUID, admin_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_admin(return_id, lock=True)
        if return_.status != ReturnStatus.approved:
            raise BusinessRuleError("Can only mark approved returns as received")
        await self.return_repo.update_status(return_id, ReturnStatus.received, notes=payload.admin_note)
        await self.db.commit()
        return {"message": "Return marked as received. Ready to process refund."}

    async def process_refund(
        self, return_id: UUID, admin_id: UUID, payload: AdminReturnActionRequest
    ) -> dict:
        return_ = await self._get_return_admin(return_id, lock=True)
        if return_.status != ReturnStatus.received:
            raise BusinessRuleError("Can only refund received returns")

        from app.schemas.payment import RefundRequest
        from app.services.payment_service import PaymentService
        payment = await self.db.scalar(select(Payment).where(Payment.order_id == return_.order_id))
        if not payment:
            raise BusinessRuleError("A collected payment is required before a refund")
        # A request remains pending until the external transfer is recorded.
        order = await self.db.get(Order, return_.order_id)
        if not order:
            raise BusinessRuleError("Return order is missing")
        order_items = await self._load_order_items(return_)
        total = self._calculate_refund_amount(return_, order, order_items)
        response = await PaymentService(self.db).refund(payment.id, admin_id,
            RefundRequest(amount=total, reason=payload.admin_note or "Received product return",
                          idempotency_key=f"return:{return_id}"))
        refund = await self.db.get(Refund, response.refund_id)
        refund.return_id = return_.id
        await self.db.commit()
        return {"message": "Refund requested; awaiting recorded transfer", "refund_id": str(refund.id), "status": response.status}

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

    async def get_admin_dispute(self, dispute_id: UUID) -> DisputeDetailResponse:
        dispute = await self.dispute_repo.get_by_id(dispute_id)
        if not dispute:
            raise NotFoundError("Dispute not found")
        return self._to_dispute(dispute)

    async def add_admin_message(
        self, dispute_id: UUID, admin_id: UUID, payload: AddDisputeMessageRequest
    ) -> DisputeMessageResponse:
        dispute = await self.dispute_repo.get_by_id(dispute_id, for_update=True)
        if not dispute:
            raise NotFoundError("Dispute not found")
        if dispute.status in (
            DisputeStatus.resolved_customer,
            DisputeStatus.resolved_seller,
            DisputeStatus.closed,
        ):
            raise BusinessRuleError("Cannot add messages to a resolved dispute")
        if dispute.status == DisputeStatus.open:
            dispute.status = DisputeStatus.under_review
        message = await self.dispute_repo.add_message(
            dispute_id=dispute.id,
            sender_id=admin_id,
            body=payload.body,
        )
        await self.db.commit()
        return DisputeMessageResponse(
            id=message.id,
            sender_id=message.sender_id,
            body=message.body,
            created_at=message.created_at,
        )

    async def resolve_dispute(
        self, dispute_id: UUID, admin_id: UUID, payload: ResolveDisputeRequest
    ) -> DisputeDetailResponse:
        dispute = await self.dispute_repo.get_by_id(dispute_id, for_update=True)
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

    async def _get_return_admin(self, return_id: UUID, *, lock: bool = False) -> Return:
        return_ = await self.return_repo.get_by_id(return_id, for_update=lock)
        if not return_:
            raise NotFoundError("Return not found")
        return return_

    async def _get_return_seller(
        self, return_id: UUID, seller_id: UUID, *, lock: bool = False
    ) -> Return:
        return_ = await self.return_repo.get_by_seller(
            return_id, seller_id, for_update=lock
        )
        if not return_:
            raise NotFoundError("Return not found")
        return return_

    async def _load_order_items(self, return_: Return) -> dict[UUID, OrderItem]:
        ids = [item.order_item_id for item in return_.items]
        rows = (
            (await self.db.execute(select(OrderItem).where(OrderItem.id.in_(ids))))
            .scalars()
            .all()
        )
        by_id = {item.id: item for item in rows}
        if len(by_id) != len(ids):
            raise BusinessRuleError("Return item data is incomplete")
        return by_id

    @staticmethod
    def _calculate_refund_amount(
        return_: Return, order: Order, order_items: dict[UUID, OrderItem]
    ) -> Decimal:
        if order.subtotal <= 0:
            raise BusinessRuleError("Order subtotal must be positive")
        item_total = sum(
            (order_items[item.order_item_id].unit_price * item.quantity for item in return_.items),
            Decimal("0"),
        )
        return (
            item_total * (order.subtotal - order.discount_amount) / order.subtotal
        ).quantize(Decimal("0.01"))

    @staticmethod
    def _available_admin_actions(
        status: ReturnStatus, payment: Optional[Payment], refund: Optional[Refund]
    ) -> list[str]:
        if status == ReturnStatus.requested:
            return ["approve", "reject"]
        if status == ReturnStatus.approved:
            return ["mark_received"]
        if (
            status == ReturnStatus.received
            and refund is None
            and payment is not None
            and payment.status == PaymentStatus.completed
        ):
            return ["request_refund"]
        return []

    @staticmethod
    def _available_seller_actions(status: ReturnStatus) -> list[str]:
        if status == ReturnStatus.requested:
            return ["approve", "reject"]
        if status == ReturnStatus.approved:
            return ["mark_received"]
        return []

    @staticmethod
    def _to_admin_items(
        return_: Return, order_items: dict[UUID, OrderItem]
    ) -> list[AdminReturnItemResponse]:
        return [
            AdminReturnItemResponse(
                id=item.id,
                order_item_id=item.order_item_id,
                product_id=order_items[item.order_item_id].product_id,
                variant_id=order_items[item.order_item_id].variant_id,
                product_name=order_items[item.order_item_id].product_name,
                variant_label=order_items[item.order_item_id].variant_label,
                unit_price=order_items[item.order_item_id].unit_price,
                purchased_quantity=order_items[item.order_item_id].quantity,
                requested_quantity=item.quantity,
                line_subtotal=order_items[item.order_item_id].unit_price * item.quantity,
                reason=item.reason,
            )
            for item in return_.items
        ]

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
