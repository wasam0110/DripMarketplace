"""Public input boundary checks through Pydantic, not direct validator calls."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import auth, user

REGISTRATION = {
    "first_name": "Ali",
    "last_name": "Khan",
    "email": "ali@example.com",
    "password": "ValidPass123",
}


@pytest.mark.parametrize(
    "model,base,field",
    [
        (auth.RegisterRequest, REGISTRATION, "password"),
        (auth.ResetPasswordRequest, {"token": "test-token"}, "new_password"),
        (auth.ChangePasswordRequest, {"current_password": "OldPass123"}, "new_password"),
        (
            user.ChangePasswordRequest,
            {"current_password": "OldPass123", "confirm_password": "ValidPass123"},
            "new_password",
        ),
    ],
)
@pytest.mark.parametrize(
    "password",
    ["Short1", "A" * 129, "lowercase123", "UPPERCASE123", "NoDigitsHere", "ValidPass123"],
)
def test_password_policy(model, base, field, password):
    payload = {**base, field: password}
    if password == "ValidPass123":
        assert getattr(model(**payload), field) == password
    else:
        with pytest.raises(ValidationError):
            model(**payload)


@pytest.mark.parametrize(
    "email",
    [
        "broken",
        "a@mailinator.com",
        "a@guerrillamail.com",
        "a@tempmail.com",
        "a@" + "b" * 250 + ".com",
    ],
)
def test_registration_rejects_invalid_email(email):
    with pytest.raises(ValidationError):
        auth.RegisterRequest(**{**REGISTRATION, "email": email})


@pytest.mark.parametrize(
    "phone,expected",
    [
        (None, None),
        ("+92 300-1234567", "923001234567"),
        ("00923001234567", "923001234567"),
        ("03001234567", "923001234567"),
        ("3001234567", "3001234567"),
    ],
)
def test_registration_normalization(phone, expected):
    value = auth.RegisterRequest(
        **{**REGISTRATION, "first_name": " Ali ", "email": " ALI@EXAMPLE.COM ", "phone": phone}
    )
    assert (value.first_name, value.email, value.phone) == ("Ali", "ali@example.com", expected)


@pytest.mark.parametrize(
    "field,value", [("first_name", "A"), ("last_name", "A" * 101), ("phone", "123")]
)
def test_registration_invalid_fields(field, value):
    with pytest.raises(ValidationError):
        auth.RegisterRequest(**{**REGISTRATION, field: value})


@pytest.mark.parametrize(
    "code,valid", [(" 123456 ", True), ("12345", False), ("1234567", False), ("abcdef", False)]
)
def test_totp_format(code, valid):
    if valid:
        assert auth.VerifyTOTPRequest(code=code).code == "123456"
    else:
        with pytest.raises(ValidationError):
            auth.VerifyTOTPRequest(code=code)


def test_password_confirmation_and_email_normalization():
    with pytest.raises(ValidationError):
        auth.ChangePasswordRequest(current_password="ValidPass123", new_password="ValidPass123")
    with pytest.raises(ValidationError):
        user.ChangePasswordRequest(
            current_password="OldPass123", new_password="ValidPass123", confirm_password="different"
        )
    assert auth.LoginRequest(email=" ALI@EXAMPLE.COM ", password="x").email == "ali@example.com"
    assert auth.ForgotPasswordRequest(email=" ALI@EXAMPLE.COM ").email == "ali@example.com"


@pytest.mark.parametrize(
    "payload",
    [{"first_name": ""}, {"last_name": "A" * 101}, {"first_name": "Ali123"}, {"phone": "123"}],
)
def test_profile_invalid_fields(payload):
    with pytest.raises(ValidationError):
        user.UpdateProfileRequest(**payload)


def test_profile_optional_and_valid_fields():
    assert user.UpdateProfileRequest(first_name=None, phone=None).first_name is None
    value = user.UpdateProfileRequest(first_name=" Ali ", last_name="O'Brien", phone="03001234567")
    assert value.first_name == "Ali" and value.phone == "03001234567"


@pytest.mark.parametrize(
    "field,value",
    [
        ("street", "short"),
        ("street", "x" * 501),
        ("city", "x"),
        ("province", "x" * 101),
        ("label", "x" * 51),
    ],
)
def test_address_limits(field, value):
    with pytest.raises(ValidationError):
        user.CreateAddressRequest(
            **{**{"street": "12 Test Street", "city": "Lahore", "province": "Punjab"}, field: value}
        )


def test_address_normalization_and_optional_label():
    value = user.CreateAddressRequest(
        street=" 12 Test Street ", city=" Lahore ", province=" Punjab ", label=None
    )
    assert (value.street, value.city, value.province) == ("12 Test Street", "Lahore", "Punjab")
    assert user.CreateAddressRequest(**{**value.model_dump(), "label": " Home "}).label == "Home"


@pytest.mark.parametrize(
    "field,value", [("rating", 0), ("rating", 6), ("title", "x" * 201), ("body", "x" * 2001)]
)
def test_review_limits(field, value):
    with pytest.raises(ValidationError):
        user.CreateReviewRequest(**{**{"product_id": uuid4(), "rating": 5}, field: value})


def test_review_normalization_and_deletion_confirmation():
    value = user.CreateReviewRequest(product_id=uuid4(), rating=5, title=" Good ", body=" Fits ")
    assert (value.title, value.body) == ("Good", "Fits")
    value = user.CreateReviewRequest(product_id=uuid4(), rating=1, title=None, body=None)
    assert value.title is None and value.body is None
    assert user.UpdateReviewRequest(rating=None).rating is None
    assert user.UpdateReviewRequest(rating=3).rating == 3
    with pytest.raises(ValidationError):
        user.UpdateReviewRequest(rating=0)
    with pytest.raises(ValidationError):
        user.DeleteAccountRequest(password="x", confirm_phrase="delete")
    assert (
        user.DeleteAccountRequest(password="x", confirm_phrase=" DELETE MY ACCOUNT ").confirm_phrase
        == "DELETE MY ACCOUNT"
    )
