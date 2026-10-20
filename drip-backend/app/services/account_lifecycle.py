"""Serialize account-owned writes with customer deletion."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User


async def lock_active_user(db: AsyncSession, user_id: UUID) -> User:
    """Lock an undeleted account so profile writes serialize with customer deletion."""
    # Acquire this lock before child rows. Recheck after waiting, including when
    # an earlier auth dependency populated the session identity map.
    user = await db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None or user.deleted_at is not None:
        raise NotFoundError("User not found")
    return user
