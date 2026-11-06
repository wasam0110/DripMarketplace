"""Banner CRUD validates before uploads and protects concurrent admin changes."""

import asyncio
import io
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_resource_ownership import headers

from app.api.v1.admin.content import update_banner
from app.core.exceptions import ConflictError
from app.integrations.supabase_storage import SupabaseStorage
from app.models.admin import Banner
from app.models.user import User, UserRole
from app.schemas.admin import UpdateBannerRequest
from app.services.admin_service import AdminService

pytestmark = pytest.mark.integration
WHEN = datetime(2026, 10, 28, tzinfo=UTC)
PATH = "/api/v1/admin/content/banners"


@pytest.fixture
async def client(client):
    """Let HTTPX generate multipart boundaries rather than the shared JSON default."""
    client.headers.pop("Content-Type", None)
    return client


@pytest.fixture
async def actors(db):
    people = {}
    for role in UserRole.admin, UserRole.customer, UserRole.seller:
        user = User(
            email=f"banner-{role.value}@example.test",
            password_hash="synthetic-only",
            role=role,
            has_verified_email=True,
        )
        db.add(user)
        people[role.value] = user
    await db.commit()
    return SimpleNamespace(**people)


@pytest.fixture
async def banner(db):
    row = Banner(
        title="Existing banner",
        image_url="https://example.test/banner.webp",
        position="homepage_hero",
        sort_order=0,
        is_active=False,
        created_at=WHEN,
        updated_at=WHEN,
    )
    db.add(row)
    await db.commit()
    return row


@pytest.fixture
def upload(monkeypatch):
    mock = AsyncMock(return_value="https://example.test/new-banner.webp")
    monkeypatch.setattr(SupabaseStorage, "upload", mock)
    return mock


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize("role", ["guest", "customer", "seller", "unverified"])
@pytest.mark.parametrize("action", ["list", "create", "update", "delete"])
async def test_permissions(client, db, actors, banner, upload, role, action):
    if role == "unverified":
        actors.admin.has_verified_email = False
        await db.commit()
    auth = (
        {}
        if role == "guest"
        else headers(actors.admin if role == "unverified" else getattr(actors, role))
    )
    if action == "create":
        result = await client.post(
            PATH,
            headers=auth,
            data={"title": "Banner", "position": "homepage_hero"},
            files={"image": ("test.png", image_bytes(), "image/png")},
        )
    elif action == "update":
        result = await client.patch(
            f"{PATH}/{banner.id}", headers=auth, json={"title": "Not allowed"}
        )
    elif action == "delete":
        result = await client.delete(f"{PATH}/{banner.id}", headers=auth)
    else:
        result = await client.get(PATH, headers=auth)
    assert result.status_code in (401, 403), result.text
    upload.assert_not_awaited()
    await db.refresh(banner)
    assert banner.title == "Existing banner"


async def test_create_update_schedule_clear_delete(client, db, actors, upload):
    auth = headers(actors.admin)
    result = await client.post(
        PATH,
        headers=auth,
        data={
            "title": "  Summer linen  ",
            "position": "homepage_secondary",
            "is_active": "false",
            "sort_order": "7",
            "link_url": "/clothing",
        },
        files={"image": ("banner.png", image_bytes(), "image/png")},
    )
    assert result.status_code == 201, result.text
    saved = result.json()
    assert saved["title"] == "Summer linen" and saved["is_active"] is False
    assert saved["image_url"] == "https://example.test/new-banner.webp"
    assert saved["valid_from"] is None and saved["valid_until"] is None
    upload.assert_awaited_once()
    assert upload.await_args.kwargs["content_type"] == "image/webp"
    path = f"{PATH}/{saved['id']}"
    result = await client.patch(
        path,
        headers=auth,
        json={
            "title": "Autumn linen",
            "is_active": True,
            "position": "category_top",
            "sort_order": 3,
            "valid_from": "2026-10-29T10:00:00+05:00",
            "valid_until": "2026-10-30T10:00:00+05:00",
            "expected_updated_at": saved["updated_at"],
        },
    )
    assert result.status_code == 200, result.text
    updated = result.json()
    assert updated["title"] == "Autumn linen" and updated["is_active"] is True
    assert (
        updated["image_url"] == saved["image_url"] and updated["updated_at"] != saved["updated_at"]
    )
    assert (await client.get(PATH, headers=auth)).json() == [updated]
    cleared = await client.patch(
        path,
        headers=auth,
        json={
            "valid_from": None,
            "valid_until": None,
            "link_url": " ",
            "expected_updated_at": updated["updated_at"],
        },
    )
    assert cleared.status_code == 200, cleared.text
    final = cleared.json()
    assert final["valid_from"] is final["valid_until"] is final["link_url"] is None
    deleted = await client.delete(
        path, headers=auth, params={"expected_updated_at": final["updated_at"]}
    )
    assert deleted.status_code == 204 and not deleted.content
    assert (await client.get(PATH, headers=auth)).json() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"title": " "},
        {"title": "x" * 201},
        {"position": "other"},
        {"sort_order": "-1"},
        {"sort_order": "2147483648"},
        {"link_url": "javascript:alert(1)"},
        {"link_url": "/\\example.test"},
        {"link_url": "https://user:pass@example.test"},
    ],
)
async def test_create_metadata_rejected_before_upload(client, actors, upload, changes):
    data = {"title": "Banner", "position": "homepage_hero", **changes}
    result = await client.post(
        PATH,
        headers=headers(actors.admin),
        data=data,
        files={"image": ("banner.png", image_bytes(), "image/png")},
    )
    assert result.status_code == 422, result.text
    upload.assert_not_awaited()


@pytest.mark.parametrize(
    "data,expected", [(b"bad image", 422), (b"x" * (5 * 1024 * 1024 + 1), 413)],
    ids=["corrupt-image", "oversized-image"],
)
async def test_bad_image_never_reaches_storage(client, actors, upload, data, expected):
    result = await client.post(
        PATH,
        headers=headers(actors.admin),
        data={"title": "Banner", "position": "homepage_hero"},
        files={"image": ("bad.png", data, "image/png")},
    )
    assert result.status_code == expected, result.text
    upload.assert_not_awaited()


async def test_stale_update_and_delete_are_rejected(client, actors, banner):
    auth, path = headers(actors.admin), f"{PATH}/{banner.id}"
    first = await client.patch(
        path, headers=auth, json={"title": "First change", "expected_updated_at": WHEN.isoformat()}
    )
    assert first.status_code == 200, first.text
    assert (
        await client.patch(
            path,
            headers=auth,
            json={"title": "Stale change", "expected_updated_at": WHEN.isoformat()},
        )
    ).status_code == 409
    assert (
        await client.delete(path, headers=auth, params={"expected_updated_at": WHEN.isoformat()})
    ).status_code == 409
    assert (await client.get(PATH, headers=auth)).json() == [first.json()]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": None},
        {"sort_order": None},
        {"valid_from": "2026-10-30T00:00:00Z", "valid_until": "2026-10-29T00:00:00Z"},
    ],
)
async def test_invalid_patch_does_not_mutate(client, db, actors, banner, payload):
    result = await client.patch(f"{PATH}/{banner.id}", headers=headers(actors.admin), json=payload)
    assert result.status_code == 422
    await db.refresh(banner)
    assert banner.title == "Existing banner" and banner.valid_from is None


async def test_missing_and_stable_order(client, db, actors, banner):
    other = Banner(
        title="Same order",
        image_url="https://example.test/other.webp",
        position="homepage_hero",
        sort_order=0,
        created_at=WHEN,
        updated_at=WHEN,
    )
    db.add(other)
    await db.commit()
    rows = (await client.get(PATH, headers=headers(actors.admin))).json()
    assert [row["id"] for row in rows] == sorted([str(banner.id), str(other.id)])
    missing = f"{PATH}/{uuid4()}"
    assert (
        await client.patch(missing, headers=headers(actors.admin), json={"title": "Missing"})
    ).status_code == 404
    assert (await client.delete(missing, headers=headers(actors.admin))).status_code == 404


@pytest.mark.parametrize("first_action", ["update", "delete"])
async def test_stale_preloaded_sessions_cannot_overwrite_or_delete(test_engine, first_action):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sessions() as setup:
        banner = Banner(
            title="Race",
            image_url="https://example.test/race.webp",
            position="homepage_hero",
            sort_order=0,
            updated_at=WHEN,
        )
        setup.add(banner)
        await setup.commit()
        banner_id = banner.id
    async with sessions() as first, sessions() as second:
        loaded = await second.get(Banner, banner_id)
        if first_action == "update":
            await update_banner(
                banner_id, UpdateBannerRequest(title="Winner", expected_updated_at=WHEN), first, {}
            )
            with pytest.raises(ConflictError):
                await AdminService(second).delete_banner(
                    banner_id, expected_updated_at=loaded.updated_at
                )
        else:
            await AdminService(first).delete_banner(banner_id, expected_updated_at=WHEN)
            from app.core.exceptions import NotFoundError

            with pytest.raises(NotFoundError):
                await update_banner(
                    banner_id,
                    UpdateBannerRequest(title="Stale", expected_updated_at=WHEN),
                    second,
                    {},
                )
        await second.rollback()


async def test_concurrent_updates_have_one_winner(test_engine):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sessions() as setup:
        banner = Banner(
            title="Race",
            image_url="https://example.test/race.webp",
            position="homepage_hero",
            sort_order=0,
            updated_at=WHEN,
        )
        setup.add(banner)
        await setup.commit()
        banner_id = banner.id
    ready, loaded_count = asyncio.Event(), 0

    async def update(title):
        nonlocal loaded_count
        async with sessions() as db:
            loaded = await db.scalar(select(Banner).where(Banner.id == banner_id))
            assert loaded.updated_at == WHEN
            loaded_count += 1
            if loaded_count == 2:
                ready.set()
            await ready.wait()
            try:
                return await update_banner(
                    banner_id, UpdateBannerRequest(title=title, expected_updated_at=WHEN), db, {}
                )
            except ConflictError:
                await db.rollback()
                return None

    results = await asyncio.wait_for(asyncio.gather(update("First"), update("Second")), timeout=20)
    assert len([result for result in results if result is not None]) == 1
