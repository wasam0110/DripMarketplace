"""Server-recorded, timestamped events; no account IDs or IP addresses retained."""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (Index("ix_analytics_events_kind_time", "kind", "created_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(30))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    query: Mapped[str | None] = mapped_column(String(200))
    result_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
