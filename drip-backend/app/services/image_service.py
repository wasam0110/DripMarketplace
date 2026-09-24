from __future__ import annotations

import io
import uuid
from typing import Optional

from PIL import Image, ImageOps, UnidentifiedImageError
from app.core.config import settings

from app.core.exceptions import BusinessRuleError
from app.integrations.supabase_storage import SupabaseStorage

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
}
PRODUCT_IMAGES_BUCKET = settings.SUPABASE_STORAGE_BUCKET_PRODUCTS


class ImageService:
    def __init__(self) -> None:
        self.storage = SupabaseStorage()

    # ── Validation ─────────────────────────────────────────────────────────────

    def validate(self, data: bytes) -> str:
        """Returns detected MIME type or raises BusinessRuleError."""
        if len(data) > MAX_FILE_SIZE:
            raise BusinessRuleError("Image must be under 5 MB")

        if data[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if data[:4] == b"\x89PNG":
            return "image/png"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"

        raise BusinessRuleError("Invalid image. Allowed formats: JPEG, PNG, WebP")

    # ── Conversion ─────────────────────────────────────────────────────────────

    def to_webp(self, data: bytes, quality: int = 85) -> bytes:
        try:
            with Image.open(io.BytesIO(data)) as source:
                if source.width * source.height > 25_000_000:
                    raise BusinessRuleError("Image exceeds 25 megapixels")
                source.load()
                img = ImageOps.exif_transpose(source)
                img.thumbnail((2400, 2400))
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                buf = io.BytesIO()
                img.save(buf, format="WEBP", quality=quality)
                return buf.getvalue()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise BusinessRuleError("Image is corrupt or unsupported") from exc

    # ── Upload ─────────────────────────────────────────────────────────────────

    async def process_and_upload(
        self, data: bytes, product_id: str, *, bucket: str | None = None
    ) -> str:
        """Validate → convert to WebP → upload to Supabase → return public URL."""
        self.validate(data)
        webp_data = self.to_webp(data)
        path = f"products/{product_id}/{uuid.uuid4()}.webp"
        url = await self.storage.upload(
            bucket=bucket or PRODUCT_IMAGES_BUCKET,
            path=path,
            data=webp_data,
            content_type="image/webp",
        )
        return url

    async def delete(self, url: str) -> None:
        """Delete an image from Supabase Storage given its public URL."""
        prefix = self.storage.get_public_url(PRODUCT_IMAGES_BUCKET, "")
        if url.startswith(prefix):
            await self.storage.delete(PRODUCT_IMAGES_BUCKET, url[len(prefix) :])
