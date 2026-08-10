"""
app/repositories/user_repo.py
──────────────────────────────
Database access for User, UserSession, UserAddress.
Zero business logic — pure DB queries.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserAddress, UserSession
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    # ── Lookup ────────────────────────────────────────────────────────────────

    @classmethod
    async def get_by_email(
        cls, db: AsyncSession, email: str, include_deleted: bool = False
    ) -> User | None:
        stmt = select(User).where(User.email == email.lower().strip())
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def get_by_google_id(cls, db: AsyncSession, google_id: str) -> User | None:
        stmt = select(User).where(User.google_id == google_id, User.deleted_at.is_(None))
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def email_exists(cls, db: AsyncSession, email: str) -> bool:
        stmt = select(User.id).where(
            User.email == email.lower().strip(),
            User.deleted_at.is_(None),
        )
        return (await db.execute(stmt)).scalar_one_or_none() is not None

    # ── Update helpers ────────────────────────────────────────────────────────

    @classmethod
    async def verify_email(cls, db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(has_verified_email=True)
        )
        await db.flush()

    @classmethod
    async def update_password(cls, db: AsyncSession, user_id: uuid.UUID, password_hash: str) -> None:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(password_hash=password_hash)
        )
        await db.flush()

    @classmethod
    async def update_last_login(cls, db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(UTC))
        )
        await db.flush()

    @classmethod
    async def set_totp(cls, db: AsyncSession, user_id: uuid.UUID, secret: str | None, enabled: bool) -> None:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(totp_secret=secret, is_2fa_enabled=enabled)
        )
        await db.flush()


class SessionRepository:
    """Manages refresh token sessions (UserSession table)."""

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession:
        session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(session)
        await db.flush()
        return session

    @classmethod
    async def get_by_token_hash(cls, db: AsyncSession, token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.now(UTC),
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def delete_by_token_hash(cls, db: AsyncSession, token_hash: str) -> None:
        await db.execute(delete(UserSession).where(UserSession.token_hash == token_hash))
        await db.flush()

    @classmethod
    async def delete_all_for_user(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        """Invalidate all sessions for a user (password change / account deletion)."""
        result = await db.execute(
            delete(UserSession).where(UserSession.user_id == user_id)
        )
        await db.flush()
        return result.rowcount

    @classmethod
    async def cleanup_expired(cls, db: AsyncSession) -> int:
        """Delete all expired sessions. Called by maintenance task."""
        result = await db.execute(
            delete(UserSession).where(UserSession.expires_at <= datetime.now(UTC))
        )
        await db.flush()
        return result.rowcount


class AddressRepository(BaseRepository[UserAddress]):
    model = UserAddress

    @classmethod
    async def list_for_user(cls, db: AsyncSession, user_id: uuid.UUID) -> list[UserAddress]:
        stmt = (
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def clear_default(cls, db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(UserAddress)
            .where(UserAddress.user_id == user_id)
            .values(is_default=False)
        )
        await db.flush()