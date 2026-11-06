"""Offline audit probes: synthetic inputs only; no settings, DB or providers.

Run with Python -B. This intentionally asserts the observed defects, not desired
application behavior, and is not a replacement for application regression tests.
"""

import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "drip-backend"))

from app.schemas.auth import (  # noqa: E402
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.schemas.user import ChangePasswordRequest as CustomerPasswordRequest  # noqa: E402
from app.schemas.user import UpdateAddressRequest, UpdateReviewRequest  # noqa: E402
from app.core.log_privacy import redact  # noqa: E402


def main():
    padded = " SyntheticPassword123 "
    values = {
        "register": RegisterRequest(first_name="Synthetic", last_name="Person",
            email="synthetic@example.com", password=padded).password,
        "login": LoginRequest(email="synthetic@example.com", password=padded).password,
        "reset": ResetPasswordRequest(token="synthetic-token", new_password=padded).new_password,
        "auth_change": ChangePasswordRequest(current_password="OldSynthetic123",
            new_password=padded).new_password,
        "customer_change": CustomerPasswordRequest(current_password="OldSynthetic123",
            new_password=padded, confirm_password=padded.strip()).new_password,
    }
    assert all(value == padded.strip() for value in values.values())
    address = UpdateAddressRequest(street="", city="x" * 101, label="x" * 51)
    review = UpdateReviewRequest(title="x" * 201, body="x" * 2001)
    assert address.street == "" and len(address.city) == 101 and len(review.title) == 201
    # Execute just this pure helper's AST, avoiding route imports and settings.
    path = ROOT / "drip-backend/app/api/v1/auth.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_get_ip")
    namespace = {"Request": object}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), str(path), "exec"), namespace)
    request = SimpleNamespace(headers={"X-Forwarded-For": "192.0.2.99, 10.0.0.2"},
                              client=SimpleNamespace(host="203.0.113.8"))
    spoofed = namespace["_get_ip"](request)
    assert spoofed == "192.0.2.99" and spoofed != request.client.host
    request.headers["X-Forwarded-For"] = "x" * 80
    assert len(namespace["_get_ip"](request)) == 80
    assert redact({"event": "auth.registered", "email": "synthetic@example.com"})["email"] == "[REDACTED]"
    assert "app.core.config" not in sys.modules, "Probe must not load settings"
    print(json.dumps({
        "password_schemas_that_strip_outer_spaces": list(values),
        "customer_confirmation_differing_only_in_spaces_is_accepted": True,
        "login_ip_helper_trusts_unverified_forwarded_value": True,
        "login_ip_helper_accepts_non_ip_beyond_database_field_length": True,
        "structured_email_redaction_control_passed": True,
        "address_update_accepts_empty_street_and_overlong_city_label": True,
        "review_update_accepts_title201_and_body2001": True,
        "settings_imported": False,
        "scope": "isolated schema/helper behavior only; no HTTP, DB, Redis, provider, or concurrency verification",
    }, indent=2))


if __name__ == "__main__":
    main()
