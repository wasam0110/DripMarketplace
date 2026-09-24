"""Runtime business settings shared by checkout, sellers and workers."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.admin import SystemSetting
from app.schemas.admin import PlatformSettingsResponse


async def get_platform_settings(db: AsyncSession) -> PlatformSettingsResponse:
    values = {key: getattr(settings, key.upper()) for key in PlatformSettingsResponse.model_fields}
    result = await db.execute(select(SystemSetting).execution_options(populate_existing=True))
    values.update({row.key: row.value for row in result.scalars().all() if row.key in values})
    return PlatformSettingsResponse.model_validate(values)
