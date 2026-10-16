"""Defensive redaction for structured logs and outbound error events.

Keep stable event names and stack locations; never stringify arbitrary objects or
capture exception locals/messages. Application code must still avoid logging PII.
"""

import re
import sys
import traceback
from pathlib import PurePath
from typing import Any

REDACTED = "[REDACTED]"
_EVENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.:-]{0,159}\Z")
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_BEARER = re.compile(r"(?i)\bBearer\s+\S+")
_URL_CREDENTIALS = re.compile(r"(\w+://)[^\s/@:]+:[^\s/@]+@")
_SENSITIVE = {
    "password", "passwordhash", "token", "accesstoken", "refreshtoken", "guesttoken",
    "jwt", "secret", "apikey", "authorization", "cardnumber", "cvv", "cvc",
    "integritysalt", "hashkey", "privatekey", "servicerolekey", "totpsecret",
    "email", "recipientemail", "phone", "address", "street", "firstname", "lastname",
    "recipientname", "guestname", "guestemail", "guestphone", "clientip", "ipaddress",
    "useragent", "cookie", "cookies", "headers", "body", "payload", "rawpayload",
    "querystring", "query", "url", "databaseurl", "redisurl", "locals", "vars",
    "error", "errormessage", "detail", "reason", "subject", "excvalue", "message",
    "params", "parameters", "statement", "sql", "identifier",
}


def redact(value: Any, depth: int = 0) -> Any:  # noqa: ANN401 - accepts heterogeneous log metadata
    if depth > 12:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            name = key if isinstance(key, str) else "[non-string-key]"
            normalized = re.sub(r"[^a-z0-9]", "", name.lower())
            sensitive = normalized in _SENSITIVE or normalized.endswith(
                ("password", "secret", "token", "privatekey", "apikey")
            )
            if sensitive:
                result[name] = REDACTED
            elif name == "event" and (not isinstance(item, str) or not _EVENT.fullmatch(item)):
                result[name] = "redacted.freeform_event"
            else:
                result[name] = redact(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [redact(item, depth + 1) for item in value]
    if isinstance(value, str):
        value = _URL_CREDENTIALS.sub(r"\1[REDACTED]@", value)
        return _BEARER.sub(REDACTED, _JWT.sub(REDACTED, _EMAIL.sub(REDACTED, value)))
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return f"<{type(value).__name__}>"


def safe_exception(logger: object, method: str, event: dict) -> dict:
    """Replace exc_info with stack coordinates, never message text or locals."""
    info = event.pop("exc_info", None)
    if not info:
        return event
    if isinstance(info, BaseException):
        info = (type(info), info, info.__traceback__)
    elif not isinstance(info, tuple):
        info = sys.exc_info()
    kind, _, tb = info
    event["exception"] = {
        "type": kind.__name__ if kind else "UnknownError",
        "frames": [{"filename": PurePath(frame.filename).name, "line": frame.lineno,
                    "function": frame.name} for frame in traceback.extract_tb(tb)],
    }
    return event


def scrub_sentry_event(event: dict, hint: dict | None = None) -> dict:
    """Strip request/user/free-form context before an error leaves the process."""
    result = {key: value for key, value in event.items() if key in {
        "event_id", "timestamp", "platform", "level", "release", "environment", "logger",
        "exception", "sdk", "type", "start_timestamp",
    }}
    exceptions = result.get("exception", {}).get("values", [])
    result["exception"] = {"values": [
        {"type": item.get("type", "Error"), "value": REDACTED,
         "stacktrace": {"frames": [
             {"filename": PurePath(frame.get("filename", "unknown")).name,
              "lineno": frame.get("lineno"), "function": frame.get("function")}
             for frame in item.get("stacktrace", {}).get("frames", [])
         ]}} for item in exceptions
    ]}
    return redact(result)
