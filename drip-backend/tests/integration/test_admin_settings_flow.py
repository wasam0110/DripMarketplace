"""Runtime settings authorization, reviewed updates and native writer races."""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.exceptions import ConflictError
from app.core.security import create_access_token
from app.models.admin import SystemSetting
from app.models.user import User, UserRole
from app.services.admin_service import AdminService

pytestmark = pytest.mark.integration


def headers(user):
    token, _ = create_access_token(
        subject=str(user.id), role=user.role.value, extra_claims={"ver": user.auth_version}
    )
    return {"Authorization": f"Bearer {token}"}


async def make_admin(db):
    user = User(
        email="settings-admin@example.test",
        password_hash="synthetic-only",
        role=UserRole.admin,
        has_verified_email=True,
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def admin(db):
    return await make_admin(db)


async def test_effective_settings_partial_update_and_actor(client, db, admin):
    path = "/api/v1/admin/settings"
    before = (await client.get(path, headers=headers(admin))).json()
    response = await client.patch(
        path,
        headers=headers(admin),
        json={
            "registration_fee": 0,
            "commission_rate": 0.125,
            "expected_settings": before,
        },
    )
    assert response.status_code == 200, response.text
    expected = {**before, "registration_fee": 0, "commission_rate": 0.125}
    assert response.json() == expected
    assert (await client.get(path, headers=headers(admin))).json() == expected
    rows = (await db.scalars(select(SystemSetting))).all()
    assert {row.key for row in rows} == {"registration_fee", "commission_rate"}
    assert all(row.updated_by == admin.id for row in rows)
    second = await client.patch(
        path,
        headers=headers(admin),
        json={"registration_fee": 123, "expected_settings": expected},
    )
    assert second.status_code == 200, second.text
    assert second.json() == {**expected, "registration_fee": 123}


async def test_stale_review_writes_nothing(client, db, admin):
    path = "/api/v1/admin/settings"
    before = (await client.get(path, headers=headers(admin))).json()
    assert (
        await client.patch(path, headers=headers(admin), json={"wallet_hold_days": 30})
    ).status_code == 200
    stale = {**before, "wallet_hold_days": 0}
    response = await client.patch(
        path,
        headers=headers(admin),
        json={
            "registration_fee": 0,
            "expected_settings": stale,
        },
    )
    assert response.status_code == 409, response.text
    rows = (await db.scalars(select(SystemSetting))).all()
    assert [(row.key, row.value) for row in rows] == [("wallet_hold_days", "30")]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"unknown_setting": 1},
        {"commission_rate": 1.01},
        {"registration_fee": -1},
        {"extra_slot_price": 1.5},
        {"cod_timeout_minutes": 4},
        {"cod_timeout_minutes": 1441},
        {"wallet_hold_days": 31},
        {"standard_shipping_fee": -1},
        {"free_shipping_threshold": -1},
        {"registration_fee": 0, "expected_settings": {}},
    ],
)
async def test_invalid_changes_do_not_write(client, db, admin, payload):
    response = await client.patch("/api/v1/admin/settings", headers=headers(admin), json=payload)
    assert response.status_code == 422, response.text
    assert (await db.scalars(select(SystemSetting))).all() == []


@pytest.mark.parametrize(
    "role,verified",
    [
        (UserRole.customer, True),
        (UserRole.seller, True),
        (UserRole.admin, False),
    ],
)
async def test_only_verified_admin_can_read_or_write(client, db, role, verified):
    user = User(
        email="settings-denied@example.test",
        password_hash="synthetic-only",
        role=role,
        has_verified_email=verified,
    )
    db.add(user)
    await db.commit()
    for method in ("GET", "PATCH"):
        response = await client.request(
            method,
            "/api/v1/admin/settings",
            headers=headers(user),
            **({"json": {"registration_fee": 0}} if method == "PATCH" else {}),
        )
        assert response.status_code == (403 if verified else 401), response.text
        if not verified:
            assert response.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
    assert (await db.scalars(select(SystemSetting))).all() == []


@pytest.mark.parametrize("existing", [False, True])
async def test_concurrent_overrides_do_not_overwrite_review(test_engine, existing):
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sessions() as db:
        admin_id = (await make_admin(db)).id
        if existing:
            await AdminService(db).update_settings({"registration_fee": 789}, admin_id)
    ready, count = asyncio.Event(), 0

    async def change(amount):
        nonlocal count
        async with sessions() as db:
            service = AdminService(db)
            before = await service.get_settings()
            count += 1
            if count == 2:
                ready.set()
            await ready.wait()
            try:
                return await service.update_settings(
                    {"registration_fee": amount, "expected_settings": before.model_dump()}, admin_id
                )
            except ConflictError:
                await db.rollback()
                return None

    results = await asyncio.wait_for(asyncio.gather(change(123), change(456)), 20)
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    async with sessions() as db:
        saved = await AdminService(db).get_settings()
        assert saved == winners[0]
        assert len((await db.scalars(select(SystemSetting))).all()) == 1
