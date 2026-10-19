"""Configured public origins, never request Host headers or the CORS allowlist."""

from urllib.parse import urlencode, urlsplit

from pydantic import AnyHttpUrl


def normalize_origin(value: str) -> str:
    """Accept an HTTP(S) origin with an optional single trailing slash."""
    if any(char.isspace() or ord(char) < 32 or char in "\\<>\"'" for char in value):
        raise ValueError("Public origins must not contain whitespace or unsafe characters")
    if not urlsplit(value).netloc:
        raise ValueError("Public origins must be absolute HTTP(S) URLs")
    parsed = AnyHttpUrl(value)
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.path not in (None, "/")
        or parsed.query is not None
        or parsed.fragment is not None
    ):
        raise ValueError("Use an HTTP(S) origin without credentials, path, query or fragment")
    return str(parsed).removesuffix("/")


def _build_url(origin: str, path: str, query: dict[str, str]) -> str:
    if (
        (path and (not path.startswith("/") or path.startswith("//")))
        or any(char.isspace() or ord(char) < 32 or char in "\\?#" for char in path)
        or any(segment in {".", ".."} for segment in path.split("/"))
    ):
        raise ValueError("Public link paths must be root-relative without a query or fragment")
    url = normalize_origin(origin) + path
    return url + "?" + urlencode(query) if query else url


def frontend_url(path: str = "", **query: str) -> str:
    from app.core.config import settings

    return _build_url(settings.FRONTEND_URL, path, query)


def api_url(path: str, **query: str) -> str:
    from app.core.config import settings

    return _build_url(settings.API_BASE_URL, path, query)
