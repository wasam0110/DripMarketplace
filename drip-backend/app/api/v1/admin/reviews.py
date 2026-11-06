"""Review moderation and product rating refresh."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.models.review import Review, ReviewStatus
from app.schemas.user import ReviewResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/admin/reviews", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


class ModerateReviewRequest(BaseModel):
    status: Literal["approved", "rejected", "hidden"]
    admin_note: str | None = Field(default=None, max_length=1000)
    expected_updated_at: AwareDatetime | None = None

    @field_validator("admin_note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        """Store a trimmed private note, or clear it explicitly."""
        return value.strip() or None if value is not None else None


class AdminReviewResponse(ReviewResponse):
    admin_note: str | None
    moderated_at: datetime | None


class AdminReviewsPage(BaseModel):
    data: list[AdminReviewResponse]
    total: int
    page: int
    per_page: int


def admin_response(review: Review) -> AdminReviewResponse:
    """Extend the public serializer only at this protected admin boundary."""
    return AdminReviewResponse(
        **CustomerService._review_to_schema(review).model_dump(),
        admin_note=review.admin_note,
        moderated_at=review.moderated_at,
    )


@router.get("", response_model=AdminReviewsPage)
async def list_reviews(
    db: DB,
    current_admin: CurrentAdmin,
    status: ReviewStatus | None = None,
    page: int = Query(1, ge=1),
) -> AdminReviewsPage:
    # Handle GET / at this router boundary. Access dependency: CurrentAdmin.
    query = select(Review)
    if status:
        query = query.where(Review.status == status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (
        await db.scalars(
            query.order_by(Review.created_at.desc(), Review.id).offset((page - 1) * 25).limit(25)
        )
    ).all()
    return AdminReviewsPage(
        data=[admin_response(r) for r in rows], total=total or 0, page=page, per_page=25
    )


@router.get("/{review_id}", response_model=AdminReviewResponse)
async def review_detail(
    review_id: UUID, db: DB, current_admin: CurrentAdmin
) -> AdminReviewResponse:
    """Read pending and non-public review content without changing it."""
    review = await db.scalar(select(Review).where(Review.id == review_id))
    if not review:
        raise NotFoundError("Review not found")
    return admin_response(review)


@router.patch("/{review_id}", response_model=AdminReviewResponse)
async def moderate_review(
    review_id: UUID, payload: ModerateReviewRequest, db: DB, current_admin: CurrentAdmin
) -> AdminReviewResponse:
    # Handle PATCH /{review_id} at this router boundary. Delegates to
    # CustomerService.refresh_product_rating. Access dependency: CurrentAdmin.
    review = await db.scalar(
        select(Review)
        .where(Review.id == review_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not review:
        raise NotFoundError("Review not found")
    if payload.expected_updated_at is not None and payload.expected_updated_at != review.updated_at:
        raise ConflictError("The review changed. Refresh and review it again before moderating.")
    review.status = ReviewStatus(payload.status)
    review.admin_note = payload.admin_note
    review.moderated_at = datetime.now(UTC)
    review.updated_at = review.moderated_at
    await db.flush()
    await CustomerService(db).refresh_product_rating(review.product_id)
    await db.commit()
    await db.refresh(review)
    return admin_response(review)
