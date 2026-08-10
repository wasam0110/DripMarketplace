"""
app/repositories/base.py
─────────────────────────
Generic async CRUD repository that all domain repositories extend.

Design rules:
  • Repositories only touch the database. Zero business logic.
  • All methods are async and accept an AsyncSession.
  • Soft-deleted records are excluded by default (WHERE deleted_at IS NULL).
  • Use SELECT FOR UPDATE for operations that require row-level locking.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base, SoftDeleteMixin

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic repository providing create, read, update, soft-delete, and list.
    Subclasses set `model` to the specific SQLAlchemy model class.

    Usage:
        class UserRepository(BaseRepository[User]):
            model = User
    """

    model: type[ModelT]

    # ── Create ────────────────────────────────────────────────────────────────

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        **kwargs: Any,
    ) -> ModelT:
        """Create and flush a new record. Does NOT commit — caller controls tx."""
        instance = cls.model(**kwargs)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    # ── Read ──────────────────────────────────────────────────────────────────

    @classmethod
    async def get_by_id(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID | str,
        include_deleted: bool = False,
    ) -> ModelT | None:
        """Fetch a single record by primary key. Returns None if not found."""
        stmt = select(cls.model).where(cls.model.id == record_id)  # type: ignore[attr-defined]
        if not include_deleted and issubclass(cls.model, SoftDeleteMixin):
            stmt = stmt.where(cls.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_id_or_raise(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID | str,
        include_deleted: bool = False,
    ) -> ModelT:
        """Fetch by ID or raise NotFoundError."""
        from app.core.exceptions import NotFoundError
        instance = await cls.get_by_id(db, record_id, include_deleted)
        if not instance:
            raise NotFoundError(resource=cls.model.__name__, resource_id=str(record_id))
        return instance

    @classmethod
    async def get_by_field(
        cls,
        db: AsyncSession,
        field: str,
        value: Any,
        include_deleted: bool = False,
    ) -> ModelT | None:
        """Fetch by any column field name. Returns None if not found."""
        column = getattr(cls.model, field, None)
        if column is None:
            raise AttributeError(f"{cls.model.__name__} has no field '{field}'")
        stmt = select(cls.model).where(column == value)
        if not include_deleted and issubclass(cls.model, SoftDeleteMixin):
            stmt = stmt.where(cls.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_for_update(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID | str,
    ) -> ModelT | None:
        """
        Fetch with SELECT FOR UPDATE (row-level lock).
        Use for inventory decrements and wallet operations.
        Must be called within an open transaction.
        """
        stmt = (
            select(cls.model)
            .where(cls.model.id == record_id)  # type: ignore[attr-defined]
            .with_for_update()
        )
        if issubclass(cls.model, SoftDeleteMixin):
            stmt = stmt.where(cls.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── List ──────────────────────────────────────────────────────────────────

    @classmethod
    async def list_all(
        cls,
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        """Return a page of records ordered by created_at DESC."""
        stmt = select(cls.model)
        if not include_deleted and issubclass(cls.model, SoftDeleteMixin):
            stmt = stmt.where(cls.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        if hasattr(cls.model, "created_at"):
            stmt = stmt.order_by(cls.model.created_at.desc())  # type: ignore[attr-defined]
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def count(
        cls,
        db: AsyncSession,
        include_deleted: bool = False,
    ) -> int:
        """Count all records (optionally including soft-deleted)."""
        stmt = select(func.count()).select_from(cls.model)
        if not include_deleted and issubclass(cls.model, SoftDeleteMixin):
            stmt = stmt.where(cls.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await db.execute(stmt)
        return result.scalar_one()

    # ── Update ────────────────────────────────────────────────────────────────

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        instance: ModelT,
        **kwargs: Any,
    ) -> ModelT:
        """Update fields on an existing instance. Flushes but does not commit."""
        for field, value in kwargs.items():
            if not hasattr(instance, field):
                raise AttributeError(f"{cls.model.__name__} has no field '{field}'")
            setattr(instance, field, value)
        await db.flush()
        await db.refresh(instance)
        return instance

    @classmethod
    async def bulk_update(
        cls,
        db: AsyncSession,
        filters: dict[str, Any],
        values: dict[str, Any],
    ) -> int:
        """
        Bulk-update records matching filters.
        Returns the number of rows affected.
        WARNING: bypasses ORM events and refresh — use only for simple bulk ops.
        """
        stmt = update(cls.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(cls.model, field) == value)
        if issubclass(cls.model, SoftDeleteMixin):
            stmt = stmt.where(cls.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await db.execute(stmt.values(**values))
        await db.flush()
        return result.rowcount

    # ── Soft Delete ───────────────────────────────────────────────────────────

    @classmethod
    async def soft_delete(
        cls,
        db: AsyncSession,
        instance: ModelT,
    ) -> ModelT:
        """
        Mark a record as deleted without removing it from the database.
        Requires the model to have SoftDeleteMixin.
        """
        if not isinstance(instance, SoftDeleteMixin):
            raise TypeError(f"{cls.model.__name__} does not support soft delete.")
        instance.soft_delete()  # Sets deleted_at = now()
        await db.flush()
        return instance

    @classmethod
    async def restore(
        cls,
        db: AsyncSession,
        instance: ModelT,
    ) -> ModelT:
        """Restore a soft-deleted record."""
        if not isinstance(instance, SoftDeleteMixin):
            raise TypeError(f"{cls.model.__name__} does not support restore.")
        instance.restore()  # Clears deleted_at
        await db.flush()
        return instance

    # ── Existence check ───────────────────────────────────────────────────────

    @classmethod
    async def exists(
        cls,
        db: AsyncSession,
        **filters: Any,
    ) -> bool:
        """Check if a record exists matching the given field=value pairs."""
        stmt = select(func.count()).select_from(cls.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(cls.model, field) == value)
        if issubclass(cls.model, SoftDeleteMixin):
            stmt = stmt.where(cls.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await db.execute(stmt)
        return (result.scalar_one() or 0) > 0