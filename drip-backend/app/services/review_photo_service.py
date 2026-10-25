"""Owned review media, re-moderation and durable, narrowly scoped storage cleanup."""

import asyncio
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging import get_logger
from app.integrations.supabase_storage import SupabaseStorage
from app.models.review import Review, ReviewImage, ReviewStatus
from app.schemas.user import ReviewResponse
from app.services.account_lifecycle import lock_active_user
from app.services.image_service import MAX_FILE_SIZE, ImageService
from app.services.notification_outbox import queue_notification

MAX_REVIEW_IMAGES = 5


async def queue_photo_cleanup(db: AsyncSession, review_id: UUID, image: ReviewImage) -> None:
    """Commit removal and its retryable cleanup event in the same transaction."""
    await queue_notification(
        db, f"review-photo:{image.id}:cleanup", "cleanup_review_photo", str(review_id), image.url
    )


def review_photo_path(storage: SupabaseStorage, review_id: str, url: str) -> str:
    """Accept only a generated UUID.webp object in this review's exact prefix."""
    owner = str(UUID(review_id))
    prefix = storage.get_public_url(settings.SUPABASE_STORAGE_BUCKET_PRODUCTS, f"products/{owner}/")
    filename = url.removeprefix(prefix)
    try:
        safe = str(UUID(filename.removesuffix(".webp"))) + ".webp"
    except ValueError as exc:
        raise ValueError("Review asset ownership needs manual inspection") from exc
    if not url.startswith(prefix) or filename != safe:
        raise ValueError("Review asset ownership needs manual inspection")
    return f"products/{owner}/{filename}"


async def cleanup_review_photo(
    ctx: dict, review_id: str, url: str, event_key: str | None = None
) -> None:
    """Retry deletion without touching objects still referenced anywhere in the app."""
    from app.core.database import AsyncSessionLocal
    from app.models.admin import Banner
    from app.models.product import Category, ProductImage
    from app.models.seller import Seller
    from app.models.user import User

    storage = SupabaseStorage()
    path = review_photo_path(storage, review_id, url)
    async with AsyncSessionLocal() as db:
        for column in (
            ReviewImage.url,
            ProductImage.url,
            User.avatar_url,
            Category.image_url,
            Banner.image_url,
            Seller.logo_url,
        ):
            if await db.scalar(select(column).where(column == url).limit(1)):
                return  # A commit may have succeeded despite an ambiguous upload response.
        await storage.delete(settings.SUPABASE_STORAGE_BUCKET_PRODUCTS, path)


class ReviewPhotoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def owned(self, user_id: UUID, review_id: UUID) -> Review:
        """Serialize changes with account deletion and review moderation."""
        await lock_active_user(self.db, user_id)
        review = await self.db.scalar(
            select(Review)
            .where(Review.id == review_id, Review.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if review is None:
            raise NotFoundError("Review")
        if review.status not in (ReviewStatus.pending, ReviewStatus.approved):
            raise BusinessRuleError("Photos on rejected or hidden reviews cannot be changed")
        return review

    async def finish(self, review: Review) -> ReviewResponse:
        """Remove public rating eligibility until a moderator approves the changed review."""
        from app.services.customer_service import CustomerService

        review.status = ReviewStatus.pending
        review.admin_note = None
        review.moderated_at = None
        await self.db.flush()
        await CustomerService(self.db).refresh_product_rating(review.product_id)
        await self.db.commit()
        await self.db.refresh(review, ["images", "user", "updated_at"])
        return CustomerService._review_to_schema(review)

    async def upload(self, user_id: UUID, review_id: UUID, data: bytes) -> ReviewResponse:
        review = await self.owned(user_id, review_id)
        images = list(
            await self.db.scalars(select(ReviewImage).where(ReviewImage.review_id == review_id))
        )
        if len(images) >= MAX_REVIEW_IMAGES:
            raise BusinessRuleError("A review can have at most five photos")
        if not data or len(data) > MAX_FILE_SIZE:
            raise BusinessRuleError("Choose a non-empty image no larger than 5 MB")
        processor = ImageService()
        processor.validate(data)
        converted = await asyncio.to_thread(processor.to_webp, data)
        image_id = uuid4()
        path = f"products/{review_id}/{image_id}.webp"
        bucket = settings.SUPABASE_STORAGE_BUCKET_PRODUCTS
        url = processor.storage.get_public_url(bucket, path)
        image = ReviewImage(
            id=image_id,
            review_id=review_id,
            url=url,
            sort_order=max((item.sort_order for item in images), default=-1) + 1,
        )
        try:
            await processor.storage.upload(bucket, path, converted, "image/webp")
            self.db.add(image)
            return await self.finish(review)
        except Exception:
            # Never immediately delete after an ambiguous DB commit. The worker checks references.
            try:
                await self.db.rollback()
                # Rollback can expire attached ORM attributes; use captured immutable identifiers.
                cleanup_image = ReviewImage(id=image_id, review_id=review_id, url=url)
                await queue_photo_cleanup(self.db, review_id, cleanup_image)
                await self.db.commit()
            except Exception:
                get_logger(__name__).error(
                    "review_photo.cleanup_reconciliation_required", image_id=str(image_id)
                )
            raise

    async def delete(self, user_id: UUID, review_id: UUID, image_id: UUID) -> ReviewResponse:
        review = await self.owned(user_id, review_id)
        image = await self.db.scalar(
            select(ReviewImage).where(
                ReviewImage.id == image_id, ReviewImage.review_id == review_id
            )
        )
        if image is None:
            raise NotFoundError("Review photo")
        await queue_photo_cleanup(self.db, review_id, image)
        await self.db.delete(image)
        return await self.finish(review)
