"""Review moderation and product rating refresh."""

from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, CurrentAdmin
from app.core.exceptions import NotFoundError
from app.models.review import Review, ReviewStatus
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/admin/reviews", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


class ModerateReviewRequest(BaseModel):
    status: Literal["approved", "rejected", "hidden"]
    admin_note: str | None = Field(default=None, max_length=1000)


@router.get("")
async def list_reviews(
    db: DB,
    current_admin: CurrentAdmin,
    status: ReviewStatus | None = None,
    page: int = Query(1, ge=1),
):
    query = select(Review)
    if status:
        query = query.where(Review.status == status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (
        await db.scalars(
            query.order_by(Review.created_at.desc(), Review.id).offset((page - 1) * 25).limit(25)
        )
    ).all()
    return {
        "data": [CustomerService._review_to_schema(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": 25,
    }


@router.patch("/{review_id}")
async def moderate_review(
    review_id: UUID, payload: ModerateReviewRequest, db: DB, current_admin: CurrentAdmin
):
    review = await db.scalar(select(Review).where(Review.id == review_id).with_for_update())
    if not review:
        raise NotFoundError("Review not found")
    review.status = ReviewStatus(payload.status)
    review.admin_note = payload.admin_note
    await db.flush()
    await CustomerService(db).refresh_product_rating(review.product_id)
    await db.commit()
    await db.refresh(review)
    return CustomerService._review_to_schema(review)
