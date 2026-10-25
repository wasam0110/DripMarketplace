"""Authenticated, bounded multipart review-photo operations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.review import Review
from app.schemas.user import ReviewResponse
from app.services.customer_service import CustomerService
from app.services.image_service import MAX_FILE_SIZE
from app.services.review_photo_service import ReviewPhotoService

router = APIRouter(prefix="/me/reviews", tags=["customers"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{review_id}/images", response_model=ReviewResponse)
async def get_review_photos(review_id: UUID, db: DB, current_user: CurrentUser) -> ReviewResponse:
    """Read photo metadata only through the owning account, including locked reviews."""
    review = await db.scalar(
        select(Review).where(Review.id == review_id, Review.user_id == UUID(current_user["sub"]))
    )
    if review is None:
        raise NotFoundError("Review")
    return CustomerService._review_to_schema(review)


@router.post("/{review_id}/images", response_model=ReviewResponse, status_code=201)
async def upload_review_photo(
    review_id: UUID, db: DB, current_user: CurrentUser, image: UploadFile = File(...)
) -> ReviewResponse:
    """Accept one bounded file; the service validates actual bytes and decoded dimensions."""
    try:
        data = await image.read(MAX_FILE_SIZE + 1)
    finally:
        await image.close()
    if len(data) > MAX_FILE_SIZE:
        raise BusinessRuleError("Image must be no larger than 5 MB")
    return await ReviewPhotoService(db).upload(UUID(current_user["sub"]), review_id, data)


@router.delete("/{review_id}/images/{image_id}", response_model=ReviewResponse)
async def delete_review_photo(
    review_id: UUID, image_id: UUID, db: DB, current_user: CurrentUser
) -> ReviewResponse:
    """Remove only a photo belonging to the authenticated customer's review."""
    return await ReviewPhotoService(db).delete(UUID(current_user["sub"]), review_id, image_id)
