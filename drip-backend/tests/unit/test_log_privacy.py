"""Logging/error events never retain tested credential/PII or traceback values."""

import json

from app.core.log_privacy import redact, safe_exception, scrub_sentry_event


def test_nested_redaction_and_freeform_events():
    event = {"event": "payment.failed", "nested": [
        {"Authorization": "Bearer NEVER_LOG_ME", "X-Guest-Token": "NEVER_LOG_ME",
         "email": "NEVER_LOG_ME@example.com", "phone": "NEVER_LOG_ME"},
    ], "error": "unlabelled NEVER_LOG_ME", "count": 3}
    result = redact(event)
    assert "NEVER_LOG_ME" not in json.dumps(result)
    assert result["count"] == 3 and result["event"] == "payment.failed"
    assert event["error"] == "unlabelled NEVER_LOG_ME"
    assert redact({"event": "Email failed for NEVER_LOG_ME"})["event"] == "redacted.freeform_event"


def test_scrubber_bounds_cycles_and_does_not_stringify_objects():
    class Unsafe:
        def __str__(self):
            raise AssertionError("Objects must not be stringified")
    cyclic = {}
    cyclic["child"] = cyclic
    assert "TRUNCATED" in json.dumps(redact(cyclic))
    assert redact({"object": Unsafe()}) == {"object": "<Unsafe>"}


def test_exceptions_keep_coordinates_not_messages_or_locals():
    private_value = "NEVER_LOG_ME"
    try:
        raise ValueError(private_value)
    except ValueError:
        result = safe_exception(None, "error", {"event": "provider.failed", "exc_info": True})
    assert result["exception"]["type"] == "ValueError"
    assert result["exception"]["frames"]
    assert private_value not in json.dumps(result)
    assert "exc_info" not in result


def test_sentry_removes_user_request_and_stack_context():
    result = scrub_sentry_event({
        "event_id": "abc", "level": "error", "user": {"email": "NEVER_LOG_ME"},
        "request": {"url": "NEVER_LOG_ME"}, "extra": {"anything": "NEVER_LOG_ME"},
        "breadcrumbs": [{"message": "NEVER_LOG_ME"}],
        "exception": {"values": [{"type": "ValueError", "value": "NEVER_LOG_ME",
            "stacktrace": {"frames": [{"filename": "/server/app.py", "lineno": 12,
                "function": "send", "vars": {"credential": "NEVER_LOG_ME"},
                "pre_context": ["NEVER_LOG_ME"]}]}}]},
    })
    assert "NEVER_LOG_ME" not in json.dumps(result)
    assert result["exception"]["values"][0]["stacktrace"]["frames"][0]["lineno"] == 12


def test_embedded_common_credential_forms_are_redacted():
    cleaned = redact({"other": "user@example.com Bearer tokensecret redis://login:pw@host"})
    assert all(
        value not in cleaned["other"] for value in ("user@example.com", "tokensecret", "login:pw")
    )
