"""Opt-in smoke checks for configured Google, Supabase and Resend services.

This script never prints credentials. Storage writes and email delivery happen only
when their explicit command-line flags are supplied.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage-write",
        action="store_true",
        help="Upload, find and delete a marker in each configured image bucket.",
    )
    parser.add_argument(
        "--email-to",
        metavar="ADDRESS",
        help="Send one real Resend verification message to this address.",
    )
    return parser.parse_args()


async def verify_storage() -> None:
    from app.core.config import settings
    from app.integrations.supabase_storage import SupabaseStorage

    storage = SupabaseStorage()
    buckets = {
        settings.SUPABASE_STORAGE_BUCKET_PRODUCTS,
        settings.SUPABASE_STORAGE_BUCKET_AVATARS,
        settings.SUPABASE_STORAGE_BUCKET_BRANDS,
    }
    for bucket in sorted(buckets):
        path = f"wearhowz-verification/{uuid4()}.txt"
        url = await storage.upload(bucket, path, b"WearHowZ storage check", "text/plain")
        try:
            files = await storage.list_all_files(bucket, prefix="wearhowz-verification")
            if not any(item.get("url") == url for item in files):
                raise RuntimeError(f"Uploaded marker was not listed in bucket {bucket!r}")
        finally:
            await storage.delete(bucket, path)
        print(f"Supabase bucket {bucket}: upload/list/delete passed")


async def verify_email(address: str) -> None:
    from app.integrations.resend_client import ResendClient

    receipt = await ResendClient().send(
        to=address,
        subject="WearHowZ connected-service verification",
        html="<p>WearHowZ Resend delivery is configured.</p>",
    )
    print(f"Resend accepted the message; receipt: {receipt}")


async def main() -> int:
    from app.core.config import settings

    args = parse_args()
    callback = settings.API_BASE_URL.rstrip("/") + "/api/v1/auth/google/callback"
    google_ready = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    print(f"Google credentials configured: {'yes' if google_ready else 'no'}")
    print(f"Google authorized redirect URI: {callback}")
    if args.storage_write:
        await verify_storage()
    else:
        print("Supabase write check skipped (pass --storage-write to run it)")
    if args.email_to:
        await verify_email(args.email_to)
    else:
        print("Resend delivery check skipped (pass --email-to ADDRESS to run it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
