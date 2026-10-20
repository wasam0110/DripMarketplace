"""api / v1 / cart.

HTTP handlers connect validated requests and access dependencies to backend services.
"""

from __future__ import annotations

from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentUser
from app.schemas.order import CartResponse, AddToCartRequest, UpdateCartItemRequest, SyncCartRequest
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["cart"])

DB = Annotated[AsyncSession, Depends(get_db)]


async def _get_redis():
    """Provide the initialized Redis client through FastAPI dependency injection."""
    from app.core.redis import get_redis
    return get_redis()


@router.get("", response_model=CartResponse)
async def get_cart(db: DB, current_user: CurrentUser) -> CartResponse:
    # Handle GET / at this router boundary. Delegates to CartService.get_cart. Access
    # dependency: CurrentUser.
    redis = await _get_redis()
    return await CartService(db, redis).get_cart(UUID(current_user["sub"]))


@router.post("", response_model=CartResponse)
async def add_to_cart(
    payload:      AddToCartRequest,
    db:           DB,
    current_user: CurrentUser,
) -> CartResponse:
    # Handle POST / at this router boundary. Delegates to CartService.add_item. Access
    # dependency: CurrentUser.
    redis = await _get_redis()
    return await CartService(db, redis).add_item(UUID(current_user["sub"]), payload)


@router.patch("/{variant_id}", response_model=CartResponse)
async def update_cart_item(
    variant_id:   UUID,
    payload:      UpdateCartItemRequest,
    db:           DB,
    current_user: CurrentUser,
) -> CartResponse:
    # Handle PATCH /{variant_id} at this router boundary. Delegates to CartService.update_item.
    # Access dependency: CurrentUser.
    redis = await _get_redis()
    return await CartService(db, redis).update_item(
        UUID(current_user["sub"]), variant_id, payload.quantity
    )


@router.delete("/{variant_id}")
async def remove_cart_item(
    variant_id:   UUID,
    db:           DB,
    current_user: CurrentUser,
) -> Response:
    # Handle DELETE /{variant_id} at this router boundary. Delegates to CartService.remove_item.
    # Access dependency: CurrentUser.
    redis = await _get_redis()
    await CartService(db, redis).remove_item(UUID(current_user["sub"]), variant_id)
    return Response(status_code=204)


@router.post("/clear")
async def clear_cart(db: DB, current_user: CurrentUser) -> Response:
    # Handle POST /clear at this router boundary. Delegates to CartService.clear. Access
    # dependency: CurrentUser.
    redis = await _get_redis()
    await CartService(db, redis).clear(UUID(current_user["sub"]))
    return Response(status_code=204)


@router.post("/sync", response_model=CartResponse)
async def sync_cart(
    payload:      SyncCartRequest,
    db:           DB,
    current_user: CurrentUser,
) -> CartResponse:
    """Merge guest (localStorage) cart into server cart after login."""
    redis  = await _get_redis()
    items  = [{"variant_id": i.variant_id, "quantity": i.quantity} for i in payload.items]
    return await CartService(db, redis).sync(UUID(current_user["sub"]), items)
