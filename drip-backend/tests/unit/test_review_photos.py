"""Review-media ownership, bounded upload, moderation and durable cleanup without live storage."""

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from PIL import Image

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.review import ReviewImage, ReviewStatus
from app.services import review_photo_service as media

pytestmark = pytest.mark.unit


def png():
    output = io.BytesIO()
    Image.new("RGB", (2, 2)).save(output, "PNG")
    return output.getvalue()


@pytest.fixture
def setup(monkeypatch):
    db = MagicMock()
    for name in (
        "scalar",
        "scalars",
        "flush",
        "commit",
        "refresh",
        "rollback",
        "delete",
        "execute",
    ):
        setattr(db, name, AsyncMock())
    db.scalars.return_value = []
    review = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), product_id=uuid4(), status=ReviewStatus.approved
    )
    db.scalar.return_value = review
    monkeypatch.setattr(media, "lock_active_user", AsyncMock())
    storage = media.SupabaseStorage()
    storage.upload = AsyncMock()
    storage.delete = AsyncMock()
    processor = media.ImageService()
    processor.storage = storage
    monkeypatch.setattr(media, "ImageService", lambda: processor)
    queue = AsyncMock()
    monkeypatch.setattr(media, "queue_photo_cleanup", queue)
    return db, review, media.ReviewPhotoService(db), storage, queue


@pytest.mark.parametrize("status", [ReviewStatus.rejected, ReviewStatus.hidden])
async def test_restricted_review_does_not_upload(setup, status):
    db, review, service, storage, _ = setup
    review.status = status
    with pytest.raises(BusinessRuleError):
        await service.upload(review.user_id, review.id, png())
    storage.upload.assert_not_awaited()


async def test_owner_scope_and_row_lock_precede_storage(setup):
    db, review, service, storage, _ = setup
    db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        await service.upload(review.user_id, review.id, png())
    statement = db.scalar.call_args.args[0]
    assert "FOR UPDATE" in str(statement)
    assert set(statement.compile().params.values()) == {review.id, review.user_id}
    storage.upload.assert_not_awaited()


@pytest.mark.parametrize(
    "data",
    [b"", b"invalid", b"x" * (5 * 1024 * 1024 + 1), b"\x89PNGbroken"],
    ids=["empty", "invalid", "oversize", "corrupt"],
)
async def test_bad_images_never_reach_storage(setup, data):
    _, review, service, storage, _ = setup
    with pytest.raises(BusinessRuleError):
        await service.upload(review.user_id, review.id, data)
    storage.upload.assert_not_awaited()


async def test_photo_limit_and_generated_path(setup):
    db, review, service, storage, _ = setup
    db.scalars.return_value = [SimpleNamespace(sort_order=i) for i in range(5)]
    with pytest.raises(BusinessRuleError):
        await service.upload(review.user_id, review.id, png())
    storage.upload.assert_not_awaited()
    db.scalars.return_value = [SimpleNamespace(sort_order=3)]
    service.finish = AsyncMock(return_value="saved")
    assert await service.upload(review.user_id, review.id, png()) == "saved"
    image = db.add.call_args.args[0]
    assert image.sort_order == 4 and image.review_id == review.id
    assert storage.upload.call_args.args[1] == f"products/{review.id}/{image.id}.webp"
    assert storage.upload.call_args.args[3] == "image/webp"


async def test_ambiguous_upload_queues_reference_checked_cleanup(setup):
    db, review, service, storage, queue = setup
    service.finish = AsyncMock(side_effect=RuntimeError("commit outcome unknown"))
    with pytest.raises(RuntimeError):
        await service.upload(review.user_id, review.id, png())
    db.rollback.assert_awaited_once()
    queue.assert_awaited_once()
    storage.delete.assert_not_awaited()


async def test_delete_scopes_image_and_queues_before_commit(setup):
    db, review, service, storage, queue = setup
    image = ReviewImage(id=uuid4(), review_id=review.id, url="https://example.test/photo.webp")
    db.scalar.side_effect = [review, image]
    service.finish = AsyncMock(return_value="saved")
    await service.delete(review.user_id, review.id, image.id)
    assert set(db.scalar.call_args.args[0].compile().params.values()) == {review.id, image.id}
    queue.assert_awaited_once_with(db, review.id, image)
    db.delete.assert_awaited_once_with(image)
    storage.delete.assert_not_awaited()


async def test_unrelated_image_cannot_be_deleted(setup):
    db, review, service, _, queue = setup
    db.scalar.side_effect = [review, None]
    with pytest.raises(NotFoundError):
        await service.delete(review.user_id, review.id, uuid4())
    queue.assert_not_awaited()


async def test_finish_reenters_moderation_and_refreshes_rating(setup, monkeypatch):
    from app.services.customer_service import CustomerService

    db, review, service, _, _ = setup
    rating = AsyncMock()
    monkeypatch.setattr(CustomerService, "refresh_product_rating", rating)
    monkeypatch.setattr(CustomerService, "_review_to_schema", lambda value: value)
    await service.finish(review)
    assert review.status == ReviewStatus.pending
    assert review.admin_note is None and review.moderated_at is None
    rating.assert_awaited_once_with(review.product_id)
    db.commit.assert_awaited_once()


@pytest.mark.parametrize("suffix", ["../x.webp", "wrong.webp", "", "x.webp?query=1"])
def test_cleanup_rejects_unsafe_paths(suffix):
    storage = media.SupabaseStorage()
    owner = str(uuid4())
    prefix = storage.get_public_url(
        media.settings.SUPABASE_STORAGE_BUCKET_PRODUCTS, f"products/{owner}/"
    )
    with pytest.raises(ValueError):
        media.review_photo_path(storage, owner, prefix + suffix)


@pytest.mark.parametrize("referenced", [True, False])
async def test_cleanup_preserves_references_and_retries_exact_object(monkeypatch, referenced):
    import app.core.database as database

    storage = media.SupabaseStorage()
    storage.delete = AsyncMock()
    monkeypatch.setattr(media, "SupabaseStorage", lambda: storage)
    db = MagicMock()
    db.scalar = AsyncMock(return_value="still-used" if referenced else None)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)
    owner, image_id = uuid4(), uuid4()
    path = f"products/{owner}/{image_id}.webp"
    url = storage.get_public_url(media.settings.SUPABASE_STORAGE_BUCKET_PRODUCTS, path)
    await media.cleanup_review_photo({}, str(owner), url)
    if referenced:
        storage.delete.assert_not_awaited()
    else:
        storage.delete.assert_awaited_once_with(
            media.settings.SUPABASE_STORAGE_BUCKET_PRODUCTS, path
        )


async def test_route_reads_only_limit_plus_one_and_closes_file(monkeypatch):
    from app.api.v1.review_photos import upload_review_photo

    file = SimpleNamespace(
        read=AsyncMock(return_value=b"x" * (media.MAX_FILE_SIZE + 1)), close=AsyncMock()
    )
    with pytest.raises(BusinessRuleError):
        await upload_review_photo(uuid4(), MagicMock(), {"sub": str(uuid4())}, file)
    file.read.assert_awaited_once_with(media.MAX_FILE_SIZE + 1)
    file.close.assert_awaited_once()


def test_routes_are_registered():
    from main import create_application

    paths = create_application().openapi()["paths"]
    assert "post" in paths["/api/v1/me/reviews/{review_id}/images"]
    assert "delete" in paths["/api/v1/me/reviews/{review_id}/images/{image_id}"]
    assert "get" in paths["/api/v1/me/reviews/{review_id}/images"]


async def test_photo_read_scopes_owner_and_rejects_missing_review():
    from app.api.v1.review_photos import get_review_photos

    db = SimpleNamespace(scalar=AsyncMock(return_value=None))
    owner, review_id = uuid4(), uuid4()
    with pytest.raises(NotFoundError):
        await get_review_photos(review_id, db, {"sub": str(owner)})
    assert set(db.scalar.call_args.args[0].compile().params.values()) == {owner, review_id}


async def test_whole_review_delete_queues_each_photo(setup, monkeypatch):
    from app.services import customer_service

    db, review, _, _, queue = setup
    review.images = [
        ReviewImage(id=uuid4(), review_id=review.id, url="https://example.test/p.webp")
    ]
    monkeypatch.setattr(customer_service, "lock_active_user", AsyncMock())
    monkeypatch.setattr(customer_service.CustomerService, "refresh_product_rating", AsyncMock())
    await customer_service.CustomerService(db).delete_review(review.user_id, review.id)
    queue.assert_awaited_once_with(db, review.id, review.images[0])
    db.commit.assert_awaited_once()


@pytest.mark.parametrize("fails", [False, True])
async def test_cleanup_is_delivered_through_durable_outbox(monkeypatch, fails):
    import app.core.database as database
    from app.tasks.notification_tasks import deliver_notification_outbox

    event = SimpleNamespace(
        completed_at=None,
        dead_lettered_at=None,
        delivery_attempts=0,
        task_name="cleanup_review_photo",
        args=[str(uuid4()), "fixture-url", "event-key"],
        id=uuid4(),
        event_key="event-key",
    )
    db = SimpleNamespace(scalar=AsyncMock(return_value=event), commit=AsyncMock())
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)
    cleanup = AsyncMock(side_effect=RuntimeError("retry") if fails else None)
    monkeypatch.setattr(media, "cleanup_review_photo", cleanup)
    await deliver_notification_outbox({}, str(event.id))
    cleanup.assert_awaited_once_with({}, *event.args)
    assert event.delivery_attempts == 1
    assert (event.completed_at is None) == fails
    assert event.dead_lettered_at is None
    db.commit.assert_awaited_once()
