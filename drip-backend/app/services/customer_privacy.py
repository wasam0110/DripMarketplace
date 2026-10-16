"""Approved limited cleanup, not automatic financial/dispute retention expiry."""

import asyncio
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.models.notification import Notification, NotificationPreference
from app.models.review import Review, ReviewImage
from app.models.user import User
from app.services.notification_outbox import queue_notification


async def clear_customer_cache(user_id: UUID) -> None:
    async with asyncio.timeout(3):
        await get_redis().delete(f"cart:{user_id}", f"wishlist:{user_id}", f"notif_prefs:{user_id}")


class AssetCleanupReviewRequiredError(ValueError):
    """An asset cannot be safely attributed; an operator must inspect it."""


async def prepare_customer_cleanup(db: AsyncSession, user: User) -> None:
    """Caller holds user lock and owns commit. Do not touch financial evidence."""
    assets = []
    if user.avatar_url:
        assets.append(
            {
                "url": user.avatar_url,
                "owner": str(user.id),
                "bucket": settings.SUPABASE_STORAGE_BUCKET_AVATARS,
            }
        )
    reviews = select(Review.id).where(Review.user_id == user.id)
    for image in await db.scalars(select(ReviewImage).where(ReviewImage.review_id.in_(reviews))):
        assets.append(
            {
                "url": image.url,
                "owner": str(image.review_id),
                "bucket": settings.SUPABASE_STORAGE_BUCKET_PRODUCTS,
            }
        )
    await db.execute(delete(ReviewImage).where(ReviewImage.review_id.in_(reviews)))
    # Free text can identify a person. Keep rating/status for aggregate integrity,
    # but do not claim that retaining an internal identity key is full anonymization.
    await db.execute(
        update(Review)
        .where(Review.user_id == user.id)
        .values(
            title=None,
            body=None,
            admin_note=None,
        )
    )
    await db.execute(delete(Notification).where(Notification.user_id == user.id))
    await db.execute(
        delete(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    await queue_notification(
        db, f"privacy:{user.id}:cleanup", "cleanup_deleted_customer", str(user.id), assets
    )


async def cleanup_deleted_customer(
    ctx: dict, user_id: str, assets: list[dict], event_key: str | None = None
) -> None:
    """Retry safely through the existing bounded durable outbox/admin replay path."""
    from app.core.database import AsyncSessionLocal
    from app.integrations.supabase_storage import SupabaseStorage
    from app.models.admin import Banner
    from app.models.product import Category, ProductImage
    from app.models.seller import Seller

    uid = UUID(user_id)
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.id == uid).with_for_update())
        if user is None or user.deleted_at is None:
            raise ValueError("Cleanup requires a deleted account")
        await clear_customer_cache(uid)
        storage = SupabaseStorage()
        needs_review = False
        for asset in assets:
            bucket, url = asset["bucket"], asset["url"]
            owner = str(UUID(asset["owner"]))
            if bucket not in {
                settings.SUPABASE_STORAGE_BUCKET_AVATARS,
                settings.SUPABASE_STORAGE_BUCKET_PRODUCTS,
            }:
                needs_review = True
                continue
            prefix = storage.get_public_url(bucket, f"products/{owner}/")
            filename = url.removeprefix(prefix)
            # Only our generated UUID.webp objects are safe automatic targets.
            # No arbitrary external URLs, traversal, shared assets or bucket scans.
            try:
                safe_name = str(UUID(filename.removesuffix(".webp"))) + ".webp"
            except ValueError:
                safe_name = ""
            if not safe_name or not url.startswith(prefix) or filename != safe_name:
                needs_review = True
                continue
            shared = False
            for column in (
                User.avatar_url,
                ReviewImage.url,
                ProductImage.url,
                Category.image_url,
                Banner.image_url,
                Seller.logo_url,
            ):
                if await db.scalar(select(column).where(column == url).limit(1)):
                    shared = True
                    break
            if shared:
                needs_review = True
                continue
            await storage.delete(bucket, f"products/{owner}/{filename}")
        if needs_review:
            # Retain the manifest for explicit operator inspection; never guess.
            raise AssetCleanupReviewRequiredError("Asset ownership needs manual review")
