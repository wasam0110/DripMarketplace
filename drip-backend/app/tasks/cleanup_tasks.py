"""
app/tasks/cleanup_tasks.py — ARQ background cleanup tasks.

Tasks:
  - cleanup_abandoned_carts       : remove Redis cart keys inactive for 30 days
  - cleanup_expired_sessions      : purge expired UserSession rows
  - cleanup_soft_deleted_users    : hard-delete accounts soft-deleted > 90 days ago
  - cleanup_orphaned_images       : remove Supabase images with no DB reference
  - cleanup_expired_reset_tokens  : purge stale password-reset tokens from Redis
  - archive_old_notifications     : move read notifications > 90 days to archive
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# CART CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

async def cleanup_abandoned_carts(ctx: dict) -> None:
    """
    Delete Redis cart keys that have had no activity for 30 days.
    Keys follow the pattern  cart:{user_id}  or  cart:guest:{session_id}.
    Redis TTL handles most expiry automatically; this task catches any
    keys where TTL was not set correctly.
    """
    from app.core.redis import get_redis

    redis   = await get_redis()
    pattern = "cart:*"
    deleted = 0

    async for key in redis.scan_iter(pattern):
        ttl = await redis.ttl(key)
        if ttl == -1:
            # No expiry set — set a 30-day window and re-check next run
            await redis.expire(key, 60 * 60 * 24 * 30)
        elif ttl == -2:
            # Already expired/gone — nothing to do
            deleted += 1

    logger.info("cleanup_abandoned_carts", keys_processed=deleted)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

async def cleanup_expired_sessions(ctx: dict) -> None:
    """
    Hard-delete UserSession rows whose expires_at is in the past.
    Runs nightly; keeps the sessions table from growing unbounded.
    """
    from sqlalchemy import delete
    from app.core.database import AsyncSessionLocal
    from app.models.user import UserSession

    cutoff = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(UserSession).where(UserSession.expires_at < cutoff)
        )
        await db.commit()
        logger.info("cleanup_expired_sessions", deleted=result.rowcount)


# ══════════════════════════════════════════════════════════════════════════════
# SOFT-DELETED USER CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

async def cleanup_soft_deleted_users(ctx: dict) -> None:
    """
    Hard-delete User rows that were soft-deleted more than 90 days ago.
    Cascade deletes will remove addresses, sessions, and other child records.
    Reviews and orders are preserved (user_id set to NULL via FK behaviour).
    """
    from sqlalchemy import delete
    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    cutoff = datetime.now(UTC) - timedelta(days=90)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(User).where(
                User.deleted_at.isnot(None),
                User.deleted_at < cutoff,
            )
        )
        await db.commit()
        logger.info("cleanup_soft_deleted_users", deleted=result.rowcount)


# ══════════════════════════════════════════════════════════════════════════════
# EXPIRED RESET-TOKEN CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

async def cleanup_expired_reset_tokens(ctx: dict) -> None:
    """
    Password-reset tokens are stored in Redis with a 1-hour TTL.
    Redis expiry handles them automatically, but we also maintain a
    set  reset_tokens:all  for auditing. This task prunes that set of
    any token keys that no longer exist in Redis.
    """
    from app.core.redis import get_redis

    redis   = await get_redis()
    members = await redis.smembers("reset_tokens:all")
    pruned  = 0

    for token_key in members:
        exists = await redis.exists(token_key)
        if not exists:
            await redis.srem("reset_tokens:all", token_key)
            pruned += 1

    logger.info("cleanup_expired_reset_tokens", pruned=pruned)


# ══════════════════════════════════════════════════════════════════════════════
# OLD NOTIFICATION ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════

async def archive_old_notifications(ctx: dict) -> None:
    """
    Mark notifications as archived if they are:
      - already read, AND
      - older than 90 days

    This keeps the active notifications table lean while preserving history.
    """
    from sqlalchemy import update
    from app.core.database import AsyncSessionLocal
    from app.models.notification import Notification

    cutoff = datetime.now(UTC) - timedelta(days=90)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Notification)
            .where(
                Notification.read_at.isnot(None),
                Notification.created_at < cutoff,
                Notification.is_archived.is_(False),
            )
            .values(is_archived=True)
        )
        await db.commit()
        logger.info("archive_old_notifications", archived=result.rowcount)


# ══════════════════════════════════════════════════════════════════════════════
# ORPHANED IMAGE CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

async def cleanup_orphaned_images(ctx: dict) -> None:
    """
    Scan Supabase storage for product/avatar images that have no matching
    DB record. This can happen when an upload succeeds but the DB write
    fails, or when a product is hard-deleted without removing its images.

    Safety: only deletes files older than 24 hours to avoid racing with
    in-progress uploads.
    """
    from app.core.database import AsyncSessionLocal
    from app.integrations.supabase_storage import SupabaseStorage
    from app.models.product import ProductImage
    from sqlalchemy import select

    storage = SupabaseStorage()
    cutoff  = datetime.now(UTC) - timedelta(hours=24)
    deleted = 0
    skipped = 0

    try:
        files = await storage.list_all_files(bucket="products")
    except Exception as exc:
        logger.error("cleanup_orphaned_images_list_error", error=str(exc))
        return

    async with AsyncSessionLocal() as db:
        for file_info in files:
            url       = file_info.get("url", "")
            updated   = file_info.get("updated_at")

            if updated and updated > cutoff.isoformat():
                skipped += 1
                continue

            stmt = select(ProductImage.id).where(ProductImage.url == url).limit(1)
            exists = (await db.execute(stmt)).scalar_one_or_none()

            if exists is None:
                try:
                    await storage.delete(url)
                    deleted += 1
                except Exception as exc:
                    logger.warning("cleanup_orphaned_image_delete_error", url=url, error=str(exc))

    logger.info("cleanup_orphaned_images", deleted=deleted, skipped=skipped)
