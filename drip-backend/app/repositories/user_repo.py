"""
app/repositories/user_repo.py
──────────────────────────────
Database access for User, UserSession, UserAddress.
Zero business logic — pure DB queries.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
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
        """Look up a user by email; return None when absent."""
        stmt = select(User).where(User.email == email.lower().strip())
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def get_by_google_id(cls, db: AsyncSession, google_id: str) -> User | None:
        """Look up a user by google id; return None when absent."""
        stmt = select(User).where(User.google_id == google_id, User.deleted_at.is_(None))
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def email_exists(cls, db: AsyncSession, email: str) -> bool:
        """Check whether the email already identifies a user."""
        stmt = select(User.id).where(
            User.email == email.lower().strip(),
            User.deleted_at.is_(None),
        )
        return (await db.execute(stmt)).scalar_one_or_none() is not None

    # ── Update helpers ────────────────────────────────────────────────────────

    @classmethod
    async def verify_email(cls, db: AsyncSession, user_id: uuid.UUID) -> None:
        """Mark the user's email as verified within the caller's session."""
        await db.execute(
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(has_verified_email=True)
        )
        await db.flush()

    @classmethod
    async def update_password(cls, db: AsyncSession, user_id: uuid.UUID, password_hash: str) -> None:
        """Replace the stored password hash without handling session revocation here."""
        await db.execute(
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(password_hash=password_hash)
        )
        await db.flush()

    @classmethod
    async def update_last_login(cls, db: AsyncSession, user_id: uuid.UUID) -> None:
        """Record the latest successful login timestamp."""
        await db.execute(
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .values(last_login_at=datetime.now(UTC))
        )
        await db.flush()

    @classmethod
    async def set_totp(cls, db: AsyncSession, user_id: uuid.UUID, secret: str | None, enabled: bool) -> None:
        """Persist the admin TOTP secret and enablement state."""
        await db.execute(
            update(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
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
        """Insert a refresh session and return it within the caller's transaction."""
        from app.services.account_lifecycle import lock_active_user
        await lock_active_user(db, user_id)
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
        """Lock an unexpired refresh session after checking its associated user remains
        active.
        """
        # Match deletion's user -> session lock order. Recheck the session after
        # waiting so simultaneous refreshes cannot reuse the same old token.
        user_id = await db.scalar(select(UserSession.user_id).where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.now(UTC),
        ))
        if user_id is None:
            return None
        user = await db.scalar(select(User).where(User.id == user_id).with_for_update()
                               .execution_options(populate_existing=True))
        if user is None or user.deleted_at is not None:
            return None
        stmt = select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.now(UTC),
        )
        return (await db.execute(stmt.with_for_update())).scalar_one_or_none()

    @classmethod
    async def delete_by_token_hash(cls, db: AsyncSession, token_hash: str) -> None:
        """Revoke the refresh session identified by its stored token hash."""
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
        """Query saved address records for for user reads using the caller's session."""
        stmt = (
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def clear_default(cls, db: AsyncSession, user_id: uuid.UUID) -> None:
        """Clear the user's default address flag before choosing another address."""
        await db.execute(
            update(UserAddress)
            .where(UserAddress.user_id == user_id)
            .values(is_default=False)
        )
        await db.flush()
