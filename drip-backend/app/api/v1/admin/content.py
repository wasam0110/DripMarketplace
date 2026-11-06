"""api / v1 / admin / content.

HTTP handlers connect validated requests and access dependencies to backend services.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import AwareDatetime, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, get_db
from app.core.catalogue_policy import MAX_IMAGE_BYTES
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.admin import Banner
from app.schemas.admin import BannerResponse, UpdateBannerRequest
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/content", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/banners", response_model=list[BannerResponse])
async def list_banners(db: DB, current_admin: CurrentAdmin) -> list[BannerResponse]:
    # Handle GET /banners at this router boundary. Delegates to AdminService.list_banners.
    # Access dependency: CurrentAdmin.
    return await AdminService(db).list_banners()


@router.post("/banners", response_model=BannerResponse, status_code=201)
async def create_banner(
    db: DB,
    current_admin: CurrentAdmin,
    title: str = Form(..., min_length=1, max_length=200),
    position: Literal["homepage_hero", "homepage_secondary", "category_top"] = Form(...),
    link_url: str | None = Form(default=None, max_length=500),
    sort_order: int = Form(default=0, ge=0, le=2_147_483_647),
    is_active: bool = Form(default=True),
    image: UploadFile = File(...),
) -> BannerResponse:
    # Handle POST /banners at this router boundary. Delegates to
    # ImageService.process_and_upload, AdminService.create_banner. Access dependency:
    # CurrentAdmin.
    # Validate all metadata before uploading anything to external storage.
    try:
        metadata = UpdateBannerRequest(
            title=title,
            position=position,
            link_url=link_url,
            sort_order=sort_order,
            is_active=is_active,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail="Invalid banner title or destination link"
        ) from exc

    contents = await image.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Banner image must be under 5 MB")

    # Upload to Supabase (reuse image service)
    from app.services.image_service import ImageService

    image_url = await ImageService().process_and_upload(contents, f"banner_{sort_order}")

    return await AdminService(db).create_banner(
        title=metadata.title,
        image_url=image_url,
        link_url=metadata.link_url,
        position=position,
        sort_order=sort_order,
        is_active=is_active,
    )


@router.delete("/banners/{banner_id}")
async def delete_banner(
    banner_id: UUID,
    db: DB,
    current_admin: CurrentAdmin,
    expected_updated_at: AwareDatetime | None = Query(default=None),
) -> Response:
    # Handle DELETE /banners/{banner_id} at this router boundary. Delegates to
    # AdminService.delete_banner. Access dependency: CurrentAdmin.
    await AdminService(db).delete_banner(banner_id, expected_updated_at=expected_updated_at)
    return Response(status_code=204)


@router.patch("/banners/{banner_id}", response_model=BannerResponse)
async def update_banner(
    banner_id: UUID, payload: UpdateBannerRequest, db: DB, current_admin: CurrentAdmin
) -> BannerResponse:
    # Handle PATCH /banners/{banner_id} at this router boundary. Access dependency:
    # CurrentAdmin.
    banner = await db.scalar(
        select(Banner)
        .where(Banner.id == banner_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if banner is None:
        raise NotFoundError("Banner not found")
    if payload.expected_updated_at is not None and payload.expected_updated_at != banner.updated_at:
        raise ConflictError("The banner changed. Refresh and review it again.")
    changes = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
    if not changes:
        raise BusinessRuleError("Provide a banner field to update")
    for key, value in changes.items():
        if key in ("title", "position", "sort_order", "is_active") and value is None:
            raise BusinessRuleError(f"{key} cannot be null")
    start = changes.get("valid_from", banner.valid_from)
    end = changes.get("valid_until", banner.valid_until)
    if start and end and end <= start:
        raise BusinessRuleError("Banner end must follow its start")
    for key, value in changes.items():
        setattr(banner, key, value)
    banner.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(banner)
    return BannerResponse.model_validate(banner)
