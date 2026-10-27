"""Independent route policy plus real HTTP denial checks for every protected operation.

Shared customer features intentionally accept all verified account roles. Onboarding
requires a seller identity but not an active brand. Guest resources require capabilities
inside services; listing them here does not assert that they are anonymously readable.
"""

import re
from datetime import UTC, datetime

import pytest
from fastapi.routing import APIRoute, iter_route_contexts
from main import app
from test_marketplace_regressions import market as marketplace_fixture

from app.core.security import create_access_token
from app.models.seller import SellerStatus

pytestmark = pytest.mark.integration
market = marketplace_fixture

PUBLIC = (
    {
        ("POST", "/auth/" + suffix)
        for suffix in (
            "forgot-password",
            "login",
            "refresh",
            "register",
            "resend-verification",
            "reset-password",
        )
    }
    | {
        ("GET", path)
        for path in (
            "/auth/google",
            "/auth/google/callback",
            "/auth/verify-email",
            "/brands",
            "/brands/{slug}",
            "/brands/{slug}/products",
            "/categories",
            "/content/banners",
            "/customers/reviews/product/{product_id}",
            "/health",
            "/products",
            "/products/search/suggestions",
            "/products/slug/{slug}",
            "/products/{product_id}",
            "/products/{product_id}/reviews",
            "/products/{product_id}/variants",
            "/seller/register/slot-price",
        )
    }
    | {("POST", path) for path in ("/orders/guest", "/orders/guest/quote", "/seller/register")}
)
PUBLIC |= {("GET", "/payments/callback/payfast"), ("POST", "/payments/callback/payfast")}
CAPABILITY = {
    # Guest checkout recovery is authorized by its private checkout key in the body.
    ("POST", "/orders/guest/recover"),
    ("GET", "/orders/number/{order_number}"),
    ("GET", "/orders/{order_id}"),
    ("POST", "/orders/{order_id}/cancel"),
    ("POST", "/payments/initiate"),
    ("POST", "/payments/{order_id}/retry"),
    ("GET", "/payments/{order_id}/status"),
    ("POST", "/returns/guest"),
    ("GET", "/returns/guest/{return_id}"),
}
ACCOUNT_CHECKOUT = {("POST", "/orders/quote"), ("POST", "/orders/recover")}
REVIEW_PHOTOS = {
    ("GET", "/me/reviews/{review_id}/images"),
    ("POST", "/me/reviews/{review_id}/images"),
    ("DELETE", "/me/reviews/{review_id}/images/{image_id}"),
}
ONBOARDING = {
    "/seller/me",
    "/seller/logo",
    "/seller/dashboard",
    "/seller/slots/purchase",
    "/seller/bank-accounts",
    "/seller/bank-accounts/{account_id}",
}


def policy(method, path):
    path = path.removeprefix("/api/v1")
    if (method, path) in PUBLIC:
        return "public"
    if (method, path) in CAPABILITY:
        return "capability"
    if (method, path) in ACCOUNT_CHECKOUT | REVIEW_PHOTOS:
        return "authenticated"
    if path.startswith(("/admin/", "/payments")) or path in (
        "/auth/setup-2fa",
        "/auth/setup-2fa/verify",
    ):
        return "admin"
    if path in ONBOARDING:
        return "seller_account"
    if path.startswith("/seller/"):
        return "seller"
    if path.startswith(("/customers/", "/cart", "/notifications", "/returns")) or path in (
        "/orders",
        "/coupons/validate",
        "/products/{product_id}/reviews",
        "/auth/me",
        "/auth/logout",
        "/auth/change-password",
    ):
        return "authenticated"
    raise AssertionError(f"Unreviewed route policy: {method} {path}")


def routes():
    return [
        (method, context.path, context)
        for context in iter_route_contexts(app.routes)
        if isinstance(context.original_route, APIRoute)
        for method in context.methods
    ]


def dependencies(node):
    return {getattr(child.call, "__name__", "") for child in node.dependencies} | set().union(
        *(dependencies(child) for child in node.dependencies)
    )


def test_every_operation_has_the_reviewed_guard():
    guards = {
        "admin": "require_admin",
        "seller": "require_seller",
        "seller_account": "require_seller_account",
        "authenticated": "get_current_user_payload",
    }
    seen = set()
    for method, path, context in routes():
        required = policy(method, path)
        seen.add((method, path.removeprefix("/api/v1")))
        if required in guards:
            assert guards[required] in dependencies(context.dependant), (method, path, required)
    assert seen >= PUBLIC | CAPABILITY | ACCOUNT_CHECKOUT | REVIEW_PHOTOS


@pytest.mark.parametrize("path,required", [
    ("/orders/quote", "authenticated"),
    ("/orders/recover", "authenticated"),
    ("/orders/guest/recover", "capability"),
])
def test_checkout_policy_is_explicit_and_method_scoped(path, required):
    assert policy("POST", "/api/v1" + path) == required
    with pytest.raises(AssertionError, match="Unreviewed route policy"):
        policy("DELETE", "/api/v1" + path)


@pytest.mark.parametrize("method,path", sorted(REVIEW_PHOTOS))
def test_review_photo_policy_is_authenticated_and_method_scoped(method, path):
    assert policy(method, "/api/v1" + path) == "authenticated"
    with pytest.raises(AssertionError, match="Unreviewed route policy"):
        policy("PUT", "/api/v1" + path)


@pytest.mark.parametrize(
    "actor",
    [
        "anonymous",
        "customer",
        "seller",
        "admin",
        "inactive_seller",
        "deleted",
        "unverified",
        "forged_role",
    ],
)
async def test_all_protected_operations_reject_invalid_identity_or_role(
    client,
    db,
    market,
    isolated_redis,
    actor,
):
    account = (
        market.seller_user
        if actor in {"seller", "inactive_seller"}
        else (market.admin if actor == "admin" else market.buyer)
    )
    if actor == "inactive_seller":
        market.seller.status = SellerStatus.suspended
    if actor == "deleted":
        account.deleted_at = datetime.now(UTC)
    if actor == "unverified":
        account.has_verified_email = False
    await db.commit()
    token, _ = create_access_token(
        subject=str(account.id), role="admin" if actor == "forged_role" else account.role.value
    )
    headers = {} if actor == "anonymous" else {"Authorization": f"Bearer {token}"}
    checked = 0
    for method, path, _ in routes():
        required = policy(method, path)
        if required in {"public", "capability"}:
            continue
        denied = (
            actor in {"anonymous", "deleted", "unverified", "forged_role"}
            or (required == "admin" and actor != "admin")
            or (required == "seller" and actor != "seller")
            or (required == "seller_account" and actor not in {"seller", "inactive_seller"})
        )
        if not denied:
            continue
        # Prevent rate limiting from masking a missing authorization check.
        await isolated_redis.flushdb()
        url = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000123", path)
        response = await client.request(method, url, headers=headers, json={})
        assert response.status_code in {401, 403}, (
            actor,
            method,
            path,
            response.status_code,
            response.text,
        )
        checked += 1
    assert checked > 0
