from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.exceptions import StorageError


class SupabaseStorage:
    """
    Thin async wrapper around Supabase Storage REST API.
    Buckets must be created in advance via the Supabase dashboard.
    """

    def __init__(self) -> None:
        self.base_url    = str(settings.SUPABASE_URL).rstrip("/")
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY

    def _headers(self, content_type: str | None = None) -> dict:
        h = {
            "Authorization": f"Bearer {self.service_key}",
            "apikey":        self.service_key,
        }
        if content_type:
            h["Content-Type"] = content_type
        return h

    async def upload(
        self,
        bucket:       str,
        path:         str,
        data:         bytes,
        content_type: str,
    ) -> str:
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    url,
                    content=data,
                    headers=self._headers(content_type),
                )
                if r.status_code not in (200, 201):
                    raise StorageError(f"Upload failed: {r.text}")
        except httpx.HTTPError as exc:
            raise StorageError(f"Storage unreachable: {exc}") from exc

        return self.get_public_url(bucket, path)

    def get_public_url(self, bucket: str, path: str) -> str:
        return f"{self.base_url}/storage/v1/object/public/{bucket}/{path}"

    async def delete(self, bucket: str, path: str) -> None:
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.delete(url, headers=self._headers())
        except httpx.HTTPError:
            pass