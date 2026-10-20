"""models / admin.

SQLAlchemy persistence definitions shared by repositories and services.
"""

from __future__ import annotations

from sqlalchemy import Index as SchemaIndex

from sqlalchemy import text as sql_text

from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemSetting(Base):
    """Key-value store for platform-wide configuration."""
    __tablename__ = "system_settings"

    key:        Mapped[str]      = mapped_column(String(100), primary_key=True)
    value:      Mapped[str]      = mapped_column(Text, nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), server_default="now()"
                )


class Banner(Base, TimestampMixin):
    """Promotional banners displayed on the storefront."""
    __tablename__ = "banners"
    __table_args__ = (
        SchemaIndex("ix_banners_is_active", "is_active"),
        SchemaIndex("ix_banners_position", "position"),
    )

    id:          Mapped[UUID]          = mapped_column(primary_key=True, default=uuid4, server_default=sql_text("gen_random_uuid()"))
    title:       Mapped[str]           = mapped_column(String(200))
    image_url:   Mapped[str]           = mapped_column(String(500))
    link_url:    Mapped[str | None]    = mapped_column(String(500))
    position:    Mapped[str]           = mapped_column(String(50))
    sort_order:  Mapped[int]           = mapped_column(Integer, default=0, server_default="0")
    is_active:   Mapped[bool]          = mapped_column(Boolean, default=True, server_default="true")
    valid_from:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
