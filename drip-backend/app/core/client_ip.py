"""Resolve client addresses without trusting caller-supplied forwarding headers."""

import ipaddress

from starlette.requests import Request


def matches_ip(value: str, allowed: list[str]) -> bool:
    """Invalid addresses/configuration never grant trust."""
    try:
        address = ipaddress.ip_address(value)
        return any(address in ipaddress.ip_network(item, strict=False) for item in allowed)
    except ValueError:
        return False


def client_ip(request: Request, trusted_proxies: list[str]) -> str:
    """Walk from the socket peer towards the first untrusted hop, never past it.

    The ASGI server must preserve the socket peer (disable proxy-header
    rewriting when this resolver is used). Proxies must append/replace XFF.
    """
    peer = request.client.host if request.client else ""
    if not matches_ip(peer, trusted_proxies):
        return peer
    forwarded = ",".join(request.headers.getlist("x-forwarded-for"))
    if not forwarded or len(forwarded) > 4096:
        return peer
    candidate = peer
    for hop in reversed(forwarded.split(",")):
        if not matches_ip(candidate, trusted_proxies):
            break
        try:
            candidate = str(ipaddress.ip_address(hop.strip()))
        except ValueError:
            return peer
    return candidate
