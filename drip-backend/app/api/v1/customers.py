"""
app/api/v1/customers.py
────────────────────────
Customer-facing endpoints for:
  - Profile read / update / avatar upload / password change
  - Address CRUD
  - Reviews (create, update, delete, mark helpful)
  - Wishlist (add, remove, list)
  - Account deletion

All routes require authentication (CurrentUser dependency).
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentUser
from app.schemas.user import (
    UserProfileResponse,
    UpdateProfileRequest,
    ChangePasswordRequest,
    AvatarUploadResponse,
    AddressResponse,
    CreateAddressRequest,
    UpdateAddressRequest,
    ReviewResponse,
    CreateReviewRequest,
    UpdateReviewRequest,
    ReviewHelpfulRequest,
    PaginatedReviews,
    WishlistResponse,
    AddToWishlistRequest,
    NotificationPreferencesResponse,
    UpdateNotificationPreferencesRequest,
    DeleteAccountRequest,
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/me", response_model=UserProfileResponse)
async def get_profile(db: DB, current_user: CurrentUser) -> UserProfileResponse:
    """Return the authenticated customer's profile."""
    return await CustomerService(db).get_profile(user_id=UUID(current_user["sub"]))


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(
    payload:      UpdateProfileRequest,
    db:           DB,
    current_user: CurrentUser,
) -> UserProfileResponse:
    """Update first_name, last_name, and/or phone."""
    return await CustomerService(db).update_profile(
        user_id=UUID(current_user["sub"]), payload=payload
    )


@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    db:           DB,
    current_user: CurrentUser,
    avatar:       UploadFile = File(...),
) -> AvatarUploadResponse:
    """Upload a new profile avatar (JPEG/PNG/WebP, max 2 MB)."""
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if avatar.content_type not in allowed:
        raise HTTPException(status_code=422, detail="Allowed types: jpeg, png, webp")
    contents = await avatar.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Avatar must be under 2 MB")
    return await CustomerService(db).upload_avatar(
        user_id=UUID(current_user["sub"]),
        file_bytes=contents,
        content_type=avatar.content_type,
    )


@router.post("/me/change-password", status_code=204)
async def change_password(
    payload:      ChangePasswordRequest,
    db:           DB,
    current_user: CurrentUser,
) -> Response:
    """Change account password. Invalidates all existing sessions."""
    await CustomerService(db).change_password(
        user_id=UUID(current_user["sub"]), payload=payload
    )
    return Response(status_code=204)


# ══════════════════════════════════════════════════════════════════════════════
# ADDRESSES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/me/addresses", response_model=list[AddressResponse])
async def list_addresses(db: DB, current_user: CurrentUser) -> list[AddressResponse]:
    """List all saved delivery addresses for the current user."""
    return await CustomerService(db).list_addresses(user_id=UUID(current_user["sub"]))


@router.post("/me/addresses", response_model=AddressResponse, status_code=201)
async def create_address(
    payload:      CreateAddressRequest,
    db:           DB,
    current_user: CurrentUser,
) -> AddressResponse:
    """Add a new delivery address. Maximum 10 per account."""
    return await CustomerService(db).create_address(
        user_id=UUID(current_user["sub"]), payload=payload
    )


@router.patch("/me/addresses/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id:   UUID,
    payload:      UpdateAddressRequest,
    db:           DB,
    current_user: CurrentUser,
) -> AddressResponse:
    """Update an existing address."""
    return await CustomerService(db).update_address(
        user_id=UUID(current_user["sub"]), address_id=address_id, payload=payload
    )


@router.delete("/me/addresses/{address_id}", status_code=204)
async def delete_address(
    address_id:   UUID,
    db:           DB,
    current_user: CurrentUser,
) -> Response:
    """Remove a saved address."""
    await CustomerService(db).delete_address(
        user_id=UUID(current_user["sub"]), address_id=address_id
    )
    return Response(status_code=204)


@router.post("/me/addresses/{address_id}/set-default", response_model=AddressResponse)
async def set_default_address(
    address_id:   UUID,
    db:           DB,
    current_user: CurrentUser,
) -> AddressResponse:
    """Mark an address as the default shipping address."""
    return await CustomerService(db).set_default_address(
        user_id=UUID(current_user["sub"]), address_id=address_id
    )


# ══════════════════════════════════════════════════════════════════════════════
# REVIEWS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/me/reviews", response_model=list[ReviewResponse])
async def list_my_reviews(
    db:           DB,
    current_user: CurrentUser,
    page:         int = Query(default=1, ge=1),
    per_page:     int = Query(default=20, ge=1, le=50),
) -> list[ReviewResponse]:
    """List reviews written by the current user."""
    return await CustomerService(db).list_user_reviews(
        user_id=UUID(current_user["sub"]), page=page, per_page=per_page
    )


@router.post("/me/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    payload:      CreateReviewRequest,
    db:           DB,
    current_user: CurrentUser,
) -> ReviewResponse:
    """Submit a product review. One review per product per customer."""
    return await CustomerService(db).create_review(
        user_id=UUID(current_user["sub"]), payload=payload
    )


@router.patch("/me/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id:    UUID,
    payload:      UpdateReviewRequest,
    db:           DB,
    current_user: CurrentUser,
) -> ReviewResponse:
    """Update an existing review (only pending or approved reviews)."""
    return await CustomerService(db).update_review(
        user_id=UUID(current_user["sub"]), review_id=review_id, payload=payload
    )


@router.delete("/me/reviews/{review_id}", status_code=204)
async def delete_review(
    review_id:    UUID,
    db:           DB,
    current_user: CurrentUser,
) -> Response:
    """Delete a review authored by the current user."""
    await CustomerService(db).delete_review(
        user_id=UUID(current_user["sub"]), review_id=review_id
    )
    return Response(status_code=204)


# ── Public review endpoints (no auth required) ─────────────────────────────

@router.get("/reviews/product/{product_id}", response_model=PaginatedReviews)
async def list_product_reviews(
    product_id: UUID,
    db:         DB,
    rating:     Optional[int] = Query(default=None, ge=1, le=5),
    sort:       str           = Query(default="newest", pattern="^(newest|oldest|helpful|rating_asc|rating_desc)$"),
    page:       int           = Query(default=1, ge=1),
    per_page:   int           = Query(default=20, ge=1, le=50),
) -> PaginatedReviews:
    """Fetch approved reviews for a product (public)."""
    return await CustomerService(db).list_product_reviews(
        product_id=product_id, rating=rating, sort=sort, page=page, per_page=per_page
    )


@router.post("/reviews/{review_id}/helpful", status_code=204)
async def mark_review_helpful(
    review_id:    UUID,
    payload:      ReviewHelpfulRequest,
    db:           DB,
    current_user: CurrentUser,
) -> Response:
    """Vote a review as helpful or unhelpful. One vote per user per review."""
    await CustomerService(db).vote_review(
        user_id=UUID(current_user["sub"]),
        review_id=review_id,
        helpful=payload.helpful,
    )
    return Response(status_code=204)


# ══════════════════════════════════════════════════════════════════════════════
# WISHLIST
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/me/wishlist", response_model=WishlistResponse)
async def get_wishlist(db: DB, current_user: CurrentUser) -> WishlistResponse:
    """Retrieve the current user's wishlist."""
    return await CustomerService(db).get_wishlist(user_id=UUID(current_user["sub"]))


@router.post("/me/wishlist", response_model=WishlistResponse, status_code=201)
async def add_to_wishlist(
    payload:      AddToWishlistRequest,
    db:           DB,
    current_user: CurrentUser,
) -> WishlistResponse:
    """Add a product to the wishlist. Idempotent — duplicate adds are ignored."""
    return await CustomerService(db).add_to_wishlist(
        user_id=UUID(current_user["sub"]), product_id=payload.product_id
    )


@router.delete("/me/wishlist/{product_id}", status_code=204)
async def remove_from_wishlist(
    product_id:   UUID,
    db:           DB,
    current_user: CurrentUser,
) -> Response:
    """Remove a product from the wishlist."""
    await CustomerService(db).remove_from_wishlist(
        user_id=UUID(current_user["sub"]), product_id=product_id
    )
    return Response(status_code=204)


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION PREFERENCES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/me/notification-preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    db: DB, current_user: CurrentUser
) -> NotificationPreferencesResponse:
    """Return current notification preference settings."""
    return await CustomerService(db).get_notification_prefs(user_id=UUID(current_user["sub"]))


@router.patch("/me/notification-preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    payload:      UpdateNotificationPreferencesRequest,
    db:           DB,
    current_user: CurrentUser,
) -> NotificationPreferencesResponse:
    """Update notification preferences (partial update)."""
    return await CustomerService(db).update_notification_prefs(
        user_id=UUID(current_user["sub"]), payload=payload
    )


# ══════════════════════════════════════════════════════════════════════════════
# ACCOUNT DELETION
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/me", status_code=204)
async def delete_account(
    payload:      DeleteAccountRequest,
    db:           DB,
    current_user: CurrentUser,
) -> Response:
    """
    Permanently delete the account. Requires password confirmation and the
    phrase 'DELETE MY ACCOUNT'. Active orders block deletion.
    """
    await CustomerService(db).delete_account(
        user_id=UUID(current_user["sub"]), payload=payload
    )
    return Response(status_code=204)
