from __future__ import annotations

from uuid import UUID
from typing import Annotated, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, CurrentAdmin
from app.schemas.admin import BannerResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/content", tags=["admin"])
DB = Annotated[AsyncSession, Depends(get_db)]

VALID_POSITIONS = {"homepage_hero", "homepage_secondary", "category_top"}


@router.get("/banners", response_model=list[BannerResponse])
async def list_banners(db: DB, current_admin: CurrentAdmin) -> list[BannerResponse]:
    return await AdminService(db).list_banners()


@router.post("/banners", response_model=BannerResponse, status_code=201)
async def create_banner(
    db: DB,
    current_admin: CurrentAdmin,
    title: str = Form(...),
    position: str = Form(...),
    link_url: Optional[str] = Form(default=None),
    sort_order: int = Form(default=0),
    is_active: bool = Form(default=True),
    image: UploadFile = File(...),
) -> BannerResponse:
    if position not in VALID_POSITIONS:
        raise HTTPException(
            status_code=422, detail=f"position must be one of: {', '.join(VALID_POSITIONS)}"
        )

    contents = await image.read(5 * 1024 * 1024 + 1)
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Banner image must be under 5 MB")

    # Upload to Supabase (reuse image service)
    from app.services.image_service import ImageService

    image_url = await ImageService().process_and_upload(contents, f"banner_{sort_order}")

    return await AdminService(db).create_banner(
        title=title,
        image_url=image_url,
        link_url=link_url,
        position=position,
        sort_order=sort_order,
        is_active=is_active,
    )


@router.delete("/banners/{banner_id}")
async def delete_banner(
    banner_id: UUID,
    db: DB,
    current_admin: CurrentAdmin,
) -> Response:
    await AdminService(db).delete_banner(banner_id)
    return Response(status_code=204)


from app.schemas.admin import UpdateBannerRequest


@router.patch("/banners/{banner_id}", response_model=BannerResponse)
async def update_banner(
    banner_id: UUID, payload: UpdateBannerRequest, db: DB, current_admin: CurrentAdmin
):
    from app.models.admin import Banner
    from app.core.exceptions import NotFoundError, BusinessRuleError

    banner = await db.get(Banner, banner_id)
    if banner is None:
        raise NotFoundError("Banner not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise BusinessRuleError("Provide a banner field to update")
    for key, value in changes.items():
        if key in ("title", "position", "sort_order", "is_active") and value is None:
            raise BusinessRuleError(f"{key} cannot be null")
        if key in ("valid_from", "valid_until") and value and value.tzinfo is None:
            raise BusinessRuleError("Banner schedule must include a timezone")
        if (
            key == "link_url"
            and value
            and not (
                value.startswith("https://")
                or (value.startswith("/") and not value.startswith("//"))
            )
        ):
            raise BusinessRuleError("Use an HTTPS or relative banner link")
        setattr(banner, key, value)
    if banner.valid_from and banner.valid_until and banner.valid_until <= banner.valid_from:
        raise BusinessRuleError("Banner end must follow its start")
    await db.commit()
    return banner
