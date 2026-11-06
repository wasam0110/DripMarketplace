"""Admin review metadata stays private and version checks remain backward compatible."""

import pytest
from main import create_application
from pydantic import ValidationError

from app.api.v1.admin.reviews import ModerateReviewRequest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "note,expected", [("  Checked  ", "Checked"), (" \n ", None), (None, None)]
)
def test_notes_are_normalized(note, expected):
    payload = ModerateReviewRequest(status="approved", admin_note=note)
    assert payload.admin_note == expected
    assert payload.expected_updated_at is None


def test_version_must_be_timezone_aware_when_supplied():
    assert (
        ModerateReviewRequest(
            status="hidden", expected_updated_at="2026-10-28T00:00:00Z"
        ).expected_updated_at.tzinfo
        is not None
    )
    with pytest.raises(ValidationError):
        ModerateReviewRequest(status="hidden", expected_updated_at="2026-10-28T00:00:00")


def test_openapi_separates_public_and_private_review_contracts():
    schema = create_application().openapi()
    definitions = schema["components"]["schemas"]
    assert {"admin_note", "moderated_at"} <= set(definitions["AdminReviewResponse"]["required"])
    assert not {"admin_note", "moderated_at"} & set(definitions["ReviewResponse"]["properties"])
    for operation in ("get", "patch"):
        response = schema["paths"]["/api/v1/admin/reviews/{review_id}"][operation]["responses"][
            "200"
        ]
        assert response["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/AdminReviewResponse"
        }
