"""
app/services/customer_service.py
──────────────────────────────────
Business logic for customer-facing operations:
  - Profile management
  - Address CRUD
  - Product reviews
  - Wishlist
  - Notification preferences
  - Account deletion
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.user import User, UserAddress
from app.models.review import Review, ReviewImage, ReviewStatus
from app.models.product import Product
from app.repositories.user_repo import UserRepository
from app.schemas.user import (
    UserProfileResponse,
    UpdateProfileRequest,
    ChangePasswordRequest,
    AvatarUploadResponse,
    AddressResponse,
    CreateAddressRequest,
    UpdateAddressRequest,
    ReviewResponse,
    ReviewAuthorResponse,
    ReviewImageResponse,
    CreateReviewRequest,
    UpdateReviewRequest,
    PaginatedReviews,
    WishlistResponse,
    WishlistItemResponse,
    NotificationPreferencesResponse,
    UpdateNotificationPreferencesRequest,
    DeleteAccountRequest,
)

logger = get_logger(__name__)

MAX_ADDRESSES = 10


class CustomerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _get_user(self, user_id: uuid.UUID) -> User:
        user = await UserRepository.get(self.db, user_id)
        if user is None:
            raise NotFoundError("User")
        return user

    @staticmethod
    def _review_to_schema(r: Review) -> ReviewResponse:
        return ReviewResponse(
            id=r.id,
            user=ReviewAuthorResponse(
                id=r.user.id,
                first_name=r.user.first_name,
                last_name=r.user.last_name,
                avatar_url=r.user.avatar_url,
            ),
            product_id=r.product_id,
            rating=r.rating,
            title=r.title,
            body=r.body,
            status=r.status.value if hasattr(r.status, "value") else r.status,
            is_verified_purchase=r.is_verified_purchase,
            helpful_count=r.helpful_count,
            unhelpful_count=r.unhelpful_count,
            images=[
                ReviewImageResponse(id=img.id, url=img.url, sort_order=img.sort_order)
                for img in (r.images or [])
            ],
            created_at=r.created_at,
            updated_at=r.updated_at,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # PROFILE
    # ══════════════════════════════════════════════════════════════════════════

    async def get_profile(self, user_id: uuid.UUID) -> UserProfileResponse:
        user = await self._get_user(user_id)
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            avatar_url=user.avatar_url,
            has_verified_email=user.has_verified_email,
            is_2fa_enabled=user.is_2fa_enabled,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )

    async def update_profile(
        self, user_id: uuid.UUID, payload: UpdateProfileRequest
    ) -> UserProfileResponse:
        user = await self._get_user(user_id)
        updates: dict = {}
        if payload.first_name is not None:
            updates["first_name"] = payload.first_name
        if payload.last_name is not None:
            updates["last_name"] = payload.last_name
        if payload.phone is not None:
            updates["phone"] = payload.phone
        if updates:
            await self.db.execute(
                update(User).where(User.id == user_id).values(**updates)
            )
            await self.db.commit()
            await self.db.refresh(user)
        return await self.get_profile(user_id)

    async def upload_avatar(
        self,
        user_id: uuid.UUID,
        file_bytes: bytes,
        content_type: str,
    ) -> AvatarUploadResponse:
        from app.services.image_service import ImageService
        avatar_url = await ImageService().upload(
            data=file_bytes,
            content_type=content_type,
            folder=f"avatars/{user_id}",
        )
        await self.db.execute(
            update(User).where(User.id == user_id).values(avatar_url=avatar_url)
        )
        await self.db.commit()
        return AvatarUploadResponse(avatar_url=avatar_url)

    async def change_password(
        self, user_id: uuid.UUID, payload: ChangePasswordRequest
    ) -> None:
        user = await self._get_user(user_id)
        if user.password_hash is None:
            raise BusinessRuleError("Cannot change password for OAuth-linked accounts.")
        if not verify_password(payload.current_password, user.password_hash):
            raise BusinessRuleError("Current password is incorrect.")
        new_hash = hash_password(payload.new_password)
        await self.db.execute(
            update(User).where(User.id == user_id).values(password_hash=new_hash)
        )
        # Invalidate all active sessions
        from app.models.user import UserSession
        await self.db.execute(
            delete(UserSession).where(UserSession.user_id == user_id)
        )
        await self.db.commit()
        logger.info("password_changed", user_id=str(user_id))

    # ══════════════════════════════════════════════════════════════════════════
    # ADDRESSES
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _addr_to_schema(a: UserAddress) -> AddressResponse:
        return AddressResponse(
            id=a.id,
            label=a.label,
            street=a.street,
            city=a.city,
            province=a.province,
            is_default=a.is_default,
            created_at=a.created_at,
        )

    async def list_addresses(self, user_id: uuid.UUID) -> list[AddressResponse]:
        stmt = (
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .order_by(UserAddress.is_default.desc(), UserAddress.created_at)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [self._addr_to_schema(r) for r in rows]

    async def create_address(
        self, user_id: uuid.UUID, payload: CreateAddressRequest
    ) -> AddressResponse:
        count_stmt = select(func.count()).where(UserAddress.user_id == user_id)
        count = (await self.db.execute(count_stmt)).scalar_one()
        if count >= MAX_ADDRESSES:
            raise BusinessRuleError(f"Maximum {MAX_ADDRESSES} addresses allowed.")

        if payload.is_default:
            await self.db.execute(
                update(UserAddress)
                .where(UserAddress.user_id == user_id)
                .values(is_default=False)
            )

        addr = UserAddress(
            user_id=user_id,
            label=payload.label,
            street=payload.street,
            city=payload.city,
            province=payload.province,
            is_default=payload.is_default,
        )
        self.db.add(addr)
        await self.db.commit()
        await self.db.refresh(addr)
        return self._addr_to_schema(addr)

    async def update_address(
        self,
        user_id: uuid.UUID,
        address_id: uuid.UUID,
        payload: UpdateAddressRequest,
    ) -> AddressResponse:
        stmt = select(UserAddress).where(
            UserAddress.id == address_id, UserAddress.user_id == user_id
        )
        addr = (await self.db.execute(stmt)).scalar_one_or_none()
        if addr is None:
            raise NotFoundError("Address")

        updates: dict = {}
        if payload.label     is not None: updates["label"]      = payload.label
        if payload.street    is not None: updates["street"]     = payload.street
        if payload.city      is not None: updates["city"]       = payload.city
        if payload.province  is not None: updates["province"]   = payload.province
        if payload.is_default is not None:
            if payload.is_default:
                await self.db.execute(
                    update(UserAddress)
                    .where(UserAddress.user_id == user_id)
                    .values(is_default=False)
                )
            updates["is_default"] = payload.is_default

        if updates:
            await self.db.execute(
                update(UserAddress).where(UserAddress.id == address_id).values(**updates)
            )
            await self.db.commit()
            await self.db.refresh(addr)
        return self._addr_to_schema(addr)

    async def delete_address(self, user_id: uuid.UUID, address_id: uuid.UUID) -> None:
        result = await self.db.execute(
            delete(UserAddress).where(
                UserAddress.id == address_id, UserAddress.user_id == user_id
            )
        )
        if result.rowcount == 0:
            raise NotFoundError("Address")
        await self.db.commit()

    async def set_default_address(
        self, user_id: uuid.UUID, address_id: uuid.UUID
    ) -> AddressResponse:
        await self.db.execute(
            update(UserAddress)
            .where(UserAddress.user_id == user_id)
            .values(is_default=False)
        )
        result = await self.db.execute(
            update(UserAddress)
            .where(UserAddress.id == address_id, UserAddress.user_id == user_id)
            .values(is_default=True)
            .returning(UserAddress)
        )
        addr = result.scalar_one_or_none()
        if addr is None:
            raise NotFoundError("Address")
        await self.db.commit()
        return self._addr_to_schema(addr)

    # ══════════════════════════════════════════════════════════════════════════
    # REVIEWS
    # ══════════════════════════════════════════════════════════════════════════

    async def list_user_reviews(
        self, user_id: uuid.UUID, page: int, per_page: int
    ) -> list[ReviewResponse]:
        offset = (page - 1) * per_page
        stmt = (
            select(Review)
            .where(Review.user_id == user_id)
            .order_by(Review.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [self._review_to_schema(r) for r in rows]

    async def create_review(
        self, user_id: uuid.UUID, payload: CreateReviewRequest
    ) -> ReviewResponse:
        # Check product exists
        product = await self.db.get(Product, payload.product_id)
        if product is None:
            raise NotFoundError("Product")

        # One review per user per product
        existing = await self.db.execute(
            select(Review).where(
                Review.user_id == user_id,
                Review.product_id == payload.product_id,
            )
        )
        if existing.scalar_one_or_none():
            raise BusinessRuleError("You have already reviewed this product.")

        # Check if this is a verified purchase
        is_verified = False
        if payload.order_id:
            from app.models.order import Order, OrderItem
            order = await self.db.get(Order, payload.order_id)
            if not order or order.user_id != user_id:
                raise BusinessRuleError("Order does not belong to this account")
            item = await self.db.scalar(select(OrderItem.id).where(OrderItem.order_id == order.id, OrderItem.product_id == payload.product_id))
            if not item:
                raise BusinessRuleError("Product is not part of this order")
            is_verified = order.status.value in ("delivered", "completed")

        review = Review(
            user_id=user_id,
            product_id=payload.product_id,
            order_id=payload.order_id,
            rating=payload.rating,
            title=payload.title,
            body=payload.body,
            status=ReviewStatus.pending,
            is_verified_purchase=is_verified,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review, ["user", "images"])
        logger.info("review_created", review_id=str(review.id), product_id=str(payload.product_id))
        return self._review_to_schema(review)

    async def update_review(
        self,
        user_id: uuid.UUID,
        review_id: uuid.UUID,
        payload: UpdateReviewRequest,
    ) -> ReviewResponse:
        stmt = select(Review).where(Review.id == review_id, Review.user_id == user_id)
        review = (await self.db.execute(stmt)).scalar_one_or_none()
        if review is None:
            raise NotFoundError("Review")
        if review.status == ReviewStatus.rejected:
            raise BusinessRuleError("Rejected reviews cannot be edited.")

        updates: dict = {}
        if payload.rating is not None: updates["rating"] = payload.rating
        if payload.title  is not None: updates["title"]  = payload.title
        if payload.body   is not None: updates["body"]   = payload.body
        if updates:
            updates["status"] = ReviewStatus.pending   # re-enter moderation queue
            await self.db.execute(
                update(Review).where(Review.id == review_id).values(**updates)
            )
            await self.refresh_product_rating(review.product_id)
            await self.db.commit()
            await self.db.refresh(review)
        return self._review_to_schema(review)

    async def delete_review(self, user_id: uuid.UUID, review_id: uuid.UUID) -> None:
        review = await self.db.scalar(select(Review).where(Review.id == review_id, Review.user_id == user_id))
        if not review:
            raise NotFoundError("Review not found")
        product_id = review.product_id
        await self.db.delete(review)
        await self.db.flush()
        await self.refresh_product_rating(product_id)
        await self.db.commit()

    async def refresh_product_rating(self, product_id):
        await self.db.execute(select(Product.id).where(Product.id == product_id).with_for_update())
        average, count = (await self.db.execute(select(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id))
            .where(Review.product_id == product_id, Review.status == ReviewStatus.approved))).one()
        await self.db.execute(update(Product).where(Product.id == product_id).values(avg_rating=average, review_count=count))

    async def list_product_reviews(
        self,
        product_id: uuid.UUID,
        rating: Optional[int],
        sort: str,
        page: int,
        per_page: int,
    ) -> PaginatedReviews:
        base = select(Review).where(
            Review.product_id == product_id,
            Review.status == ReviewStatus.approved,
        )
        if rating is not None:
            base = base.where(Review.rating == rating)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        order_col = {
            "newest":      Review.created_at.desc(),
            "oldest":      Review.created_at.asc(),
            "helpful":     Review.helpful_count.desc(),
            "rating_asc":  Review.rating.asc(),
            "rating_desc": Review.rating.desc(),
        }[sort]

        offset = (page - 1) * per_page
        stmt = base.order_by(order_col).offset(offset).limit(per_page)
        rows = (await self.db.execute(stmt)).scalars().all()

        # Rating breakdown
        breakdown_stmt = (
            select(Review.rating, func.count().label("cnt"))
            .where(Review.product_id == product_id, Review.status == ReviewStatus.approved)
            .group_by(Review.rating)
        )
        breakdown_rows = (await self.db.execute(breakdown_stmt)).all()
        breakdown = {row.rating: row.cnt for row in breakdown_rows}

        avg_stmt = select(func.avg(Review.rating)).where(
            Review.product_id == product_id, Review.status == ReviewStatus.approved
        )
        avg = (await self.db.execute(avg_stmt)).scalar_one()

        return PaginatedReviews(
            data=[self._review_to_schema(r) for r in rows],
            total=total,
            page=page,
            per_page=per_page,
            pages=-(-total // per_page),   # ceiling division
            avg_rating=round(float(avg), 2) if avg else None,
            rating_breakdown=breakdown,
        )

    async def vote_review(
        self, user_id: uuid.UUID, review_id: uuid.UUID, helpful: bool
    ) -> None:
        review = await self.db.get(Review, review_id)
        if review is None:
            raise NotFoundError("Review")
        if review.status != ReviewStatus.approved:
            raise BusinessRuleError("You can only vote on approved reviews.")
        if str(review.user_id) == str(user_id):
            raise BusinessRuleError("You cannot vote on your own review.")

        from sqlalchemy.dialects.postgresql import insert
        from app.models.review import ReviewVote
        inserted = await self.db.execute(insert(ReviewVote).values(review_id=review_id, user_id=user_id, helpful=helpful)
            .on_conflict_do_nothing().returning(ReviewVote.review_id))
        if inserted.scalar_one_or_none() is None:
            return
        col = Review.helpful_count if helpful else Review.unhelpful_count
        await self.db.execute(
            update(Review).where(Review.id == review_id).values({col: col + 1})
        )
        await self.db.commit()

    # ══════════════════════════════════════════════════════════════════════════
    # WISHLIST
    # ══════════════════════════════════════════════════════════════════════════

    async def get_wishlist(self, user_id: uuid.UUID) -> WishlistResponse:
        # Wishlist stored in Redis for speed; fallback to user metadata
        from app.core.redis import get_redis
        redis = get_redis()
        key = f"wishlist:{user_id}"
        raw = await redis.smembers(key)
        product_ids = [uuid.UUID(pid) for pid in raw if pid]

        if not product_ids:
            return WishlistResponse(items=[], total=0)

        from sqlalchemy.orm import selectinload
        from app.models.product import ProductVariant
        from app.models.seller import Seller, SellerStatus
        stmt = select(Product).options(selectinload(Product.variants).selectinload(ProductVariant.inventory)).where(
            Product.is_published.is_(True), Product.admin_hidden.is_(False),
            Product.seller.has(Seller.status == SellerStatus.active),
            Product.id.in_(product_ids),
            Product.deleted_at.is_(None),
        )
        products = (await self.db.execute(stmt)).scalars().all()
        product_map = {p.id: p for p in products}

        items = []
        for pid in product_ids:
            p = product_map.get(pid)
            if p is None:
                continue
            from app.models.product import ProductImage
            image_stmt = (
                select(ProductImage.url)
                .where(ProductImage.product_id == pid, ProductImage.sort_order == 0)
                .limit(1)
            )
            primary_image = (await self.db.execute(image_stmt)).scalar_one_or_none()
            items.append(
                WishlistItemResponse(
                    id=p.id,
                    product_id=p.id,
                    product_name=p.name,
                    product_slug=p.slug,
                    product_image=primary_image,
                    price=int(p.price),
                    sale_price=int(p.sale_price) if p.sale_price else None,
                    is_in_stock=p.has_stock,
                    added_at=p.created_at,
                )
            )
        return WishlistResponse(items=items, total=len(items))

    async def add_to_wishlist(
        self, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> WishlistResponse:
        product = await self.db.get(Product, product_id)
        if product is None or product.deleted_at is not None:
            raise NotFoundError("Product")
        from app.core.redis import get_redis
        redis = get_redis()
        key = f"wishlist:{user_id}"
        await redis.sadd(key, str(product_id))
        await redis.expire(key, 60 * 60 * 24 * 90)   # 90-day TTL
        return await self.get_wishlist(user_id)

    async def remove_from_wishlist(
        self, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> None:
        from app.core.redis import get_redis
        redis = get_redis()
        await redis.srem(f"wishlist:{user_id}", str(product_id))

    # ══════════════════════════════════════════════════════════════════════════
    # NOTIFICATION PREFERENCES
    # ══════════════════════════════════════════════════════════════════════════

    async def get_notification_prefs(
        self, user_id: uuid.UUID
    ) -> NotificationPreferencesResponse:
        # Defaults — stored in Redis hash for now
        from app.core.redis import get_redis
        redis = get_redis()
        key = f"notif_prefs:{user_id}"
        raw = await redis.hgetall(key)
        def _bool(v: Optional[bytes], default: bool = True) -> bool:
            if v is None:
                return default
            return v in (b"1", b"true", "1", "true")
        return NotificationPreferencesResponse(
            email_order_updates    = _bool(raw.get(b"email_order_updates"),  True),
            email_promotions       = _bool(raw.get(b"email_promotions"),     True),
            email_new_arrivals     = _bool(raw.get(b"email_new_arrivals"),   False),
            sms_order_updates      = _bool(raw.get(b"sms_order_updates"),    False),
            whatsapp_order_updates = _bool(raw.get(b"whatsapp_order_updates"), True),
        )

    async def update_notification_prefs(
        self,
        user_id: uuid.UUID,
        payload: UpdateNotificationPreferencesRequest,
    ) -> NotificationPreferencesResponse:
        from app.core.redis import get_redis
        redis = get_redis()
        key = f"notif_prefs:{user_id}"
        updates: dict = {}
        for field, val in payload.model_dump(exclude_none=True).items():
            updates[field] = "1" if val else "0"
        if updates:
            await redis.hset(key, mapping=updates)
            await redis.expire(key, 60 * 60 * 24 * 365)
        return await self.get_notification_prefs(user_id)

    # ══════════════════════════════════════════════════════════════════════════
    # ACCOUNT DELETION
    # ══════════════════════════════════════════════════════════════════════════

    async def delete_account(
        self, user_id: uuid.UUID, payload: DeleteAccountRequest
    ) -> None:
        user = await self._get_user(user_id)

        if user.password_hash and not verify_password(payload.password, user.password_hash):
            raise BusinessRuleError("Incorrect password.")

        # Block if active orders exist
        from app.models.order import Order, OrderStatus
        active_statuses = [
            OrderStatus.pending_cod_verification,
            OrderStatus.processing,
            OrderStatus.shipped,
        ]
        active_stmt = select(func.count()).where(
            Order.user_id == user_id,
            Order.status.in_(active_statuses),
        )
        active_count = (await self.db.execute(active_stmt)).scalar_one()
        if active_count > 0:
            raise BusinessRuleError(
                f"Cannot delete account with {active_count} active order(s). "
                "Please wait for them to be delivered or cancelled."
            )

        # Soft-delete
        from datetime import datetime, timezone
        await self.db.execute(
            update(User).where(User.id == user_id).values(
                deleted_at=datetime.now(timezone.utc),
                email=f"deleted_{user_id}@drip.deleted",
            )
        )
        # Invalidate sessions
        from app.models.user import UserSession
        await self.db.execute(delete(UserSession).where(UserSession.user_id == user_id))
        await self.db.commit()
        logger.info("account_deleted", user_id=str(user_id))
