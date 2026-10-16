"""Security regressions for forwarding headers and shared IP resolution."""

import pytest
from starlette.requests import Request

from app.api.v1.payments import _client_ip
from app.core.client_ip import client_ip, matches_ip
from app.core.config import settings
from app.core.middleware import LoggingMiddleware, RateLimitMiddleware


def request(peer="203.0.113.8", forwarded=()):
    return Request({
        "type": "http", "method": "GET", "path": "/api/v1/products",
        "headers": [(b"x-forwarded-for", value.encode()) for value in forwarded],
        "client": (peer, 1234) if peer else None,
    })


@pytest.mark.parametrize(("peer", "headers", "trusted", "expected"), [
    ("203.0.113.8", ["1.2.3.4"], [], "203.0.113.8"),
    ("203.0.113.8", ["1.2.3.4"], ["10.0.0.0/8"], "203.0.113.8"),
    ("10.0.0.2", ["1.2.3.4, 203.0.113.8"], ["10.0.0.0/8"], "203.0.113.8"),
    ("10.0.0.2", ["203.0.113.8, 10.0.0.1"], ["10.0.0.0/8"], "203.0.113.8"),
    ("10.0.0.2", ["1.2.3.4", "203.0.113.8"], ["10.0.0.0/8"], "203.0.113.8"),
    ("10.0.0.2", ["1.2.3.4, bad"], ["10.0.0.0/8"], "10.0.0.2"),
    ("10.0.0.2", [], ["10.0.0.0/8"], "10.0.0.2"),
    ("10.0.0.2", ["x" * 4097], ["10.0.0.0/8"], "10.0.0.2"),
    ("::1", ["2001:db8::8"], ["::1/128"], "2001:db8::8"),
    (None, ["1.2.3.4"], ["10.0.0.0/8"], ""),
])
def test_resolves_only_verified_proxy_chain(peer, headers, trusted, expected):
    assert client_ip(request(peer, headers), trusted) == expected


def test_middleware_and_payment_share_safe_resolution(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", ["10.0.0.0/8"])
    monkeypatch.setattr(settings, "PAYFAST_TRUSTED_PROXY_IPS", [])
    incoming = request("10.0.0.2", ["1.2.3.4, 203.0.113.8"])
    assert _client_ip(incoming) == "203.0.113.8"
    assert LoggingMiddleware._get_client_ip(incoming) == "203.0.113.8"
    assert RateLimitMiddleware._get_identifier(incoming) == "ip:203.0.113.8"


def test_payment_proxy_override_stays_separate(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", ["10.0.0.0/8"])
    monkeypatch.setattr(settings, "PAYFAST_TRUSTED_PROXY_IPS", ["192.168.0.0/16"])
    assert _client_ip(request("10.0.0.2", ["1.2.3.4"])) == "10.0.0.2"


@pytest.mark.parametrize(("value", "allowed"), [
    ("bad", ["10.0.0.0/8"]), ("10.0.0.1", ["bad"]), ("10.0.0.1", []),
])
def test_invalid_allowlists_do_not_grant_trust(value, allowed):
    assert not matches_ip(value, allowed)


def test_rate_limit_scope_cannot_be_reset_by_changing_resource_id():
    first = RateLimitMiddleware._get_rule("GET", "/api/v1/products/one")
    second = RateLimitMiddleware._get_rule("GET", "/api/v1/products/two")
    assert first == second
    assert RateLimitMiddleware._get_limit("POST", "/api/v1/auth/login") == (5, 300)
    assert RateLimitMiddleware._get_limit("POST", "/api/v1/auth/login-fake") == (200, 60)


@pytest.mark.asyncio
async def test_counter_expires_and_does_not_extend_window(isolated_redis):
    key = "drip:rl:test-window"
    assert await RateLimitMiddleware._check(key, 2, 300) == (True, 1)
    assert 0 < await isolated_redis.ttl(key) <= 300
    await isolated_redis.expire(key, 50)
    assert await RateLimitMiddleware._check(key, 2, 300) == (True, 0)
    assert 0 < await isolated_redis.ttl(key) <= 50
    assert await RateLimitMiddleware._check(key, 2, 300) == (False, -1)


@pytest.mark.asyncio
async def test_counter_missing_expiry_is_repaired(isolated_redis):
    await isolated_redis.set("drip:rl:legacy", 1)
    assert await RateLimitMiddleware._check("drip:rl:legacy", 2, 60) == (True, 0)
    assert 0 < await isolated_redis.ttl("drip:rl:legacy") <= 60
