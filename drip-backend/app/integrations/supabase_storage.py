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
        """Upload bytes to Supabase Storage and return the public URL."""
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    url,
                    content=data,
                    headers=self._headers(content_type),
                )
                if r.status_code not in (200, 201):
                    raise StorageError("Storage upload failed", detail=f"HTTP {r.status_code}")
        except httpx.HTTPError as exc:
            raise StorageError("Storage unreachable") from exc

        return self.get_public_url(bucket, path)

    def get_public_url(self, bucket: str, path: str) -> str:
        return f"{self.base_url}/storage/v1/object/public/{bucket}/{path}"

    async def delete(self, bucket: str, path: str) -> None:
        """
        Delete a file from Supabase Storage.
        A 404 is treated as success — the file is already gone.
        """
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.delete(url, headers=self._headers())
                if response.status_code == 404:
                    return  # Already deleted — idempotent.
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise StorageError("Storage deletion failed") from exc

    async def list_all_files(self, bucket: str, prefix: str = "") -> list[dict]:
        """
        List all files under a bucket (or prefix) using the Supabase Storage
        list endpoint.

        Returns a list of file-info dicts, each augmented with a "url" key
        containing the public URL for that file. Callers use "url" for DB
        lookups and "name" (the path within the bucket) for delete calls.

        POST {base_url}/storage/v1/object/list/{bucket}
        Body: {"prefix": "", "limit": 1000, "offset": 0}
        """
        list_url = f"{self.base_url}/storage/v1/object/list/{bucket}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    list_url,
                    json={"prefix": prefix, "limit": 1000, "offset": 0},
                    headers=self._headers("application/json"),
                )
                r.raise_for_status()
                files: list[dict] = r.json()
        except httpx.HTTPError as exc:
            raise StorageError("Storage listing failed") from exc

        # Attach the public URL so callers can compare against ProductImage.url.
        return [
            {**f, "url": self.get_public_url(bucket, f["name"])}
            for f in files
            if f.get("name")
        ]