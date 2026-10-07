"""Export the API contract offline with test settings and no local credentials."""

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.dependencies.models import Dependant

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    os.environ.update(
        {
            "ENVIRONMENT": "test",
            "DEBUG": "false",
            "APP_NAME": "WearHowZ API",
            "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:55432/wearhowz_test",
            "REDIS_URL": "redis://127.0.0.1:56379/15",
            "JWT_PRIVATE_KEY": "",
            "JWT_PUBLIC_KEY": "",
            "SUPABASE_URL": "https://storage.example.invalid",
            "SUPABASE_SERVICE_ROLE_KEY": "",
            "RESEND_API_KEY": "",
            "PAYFAST_ENABLED": "false",
        }
    )
    from fastapi.routing import APIRoute
    from main import app

    target = ROOT / "docs"
    target.mkdir(exist_ok=True)
    schema = app.openapi()
    (target / "openapi.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    def dependencies(node: "Dependant") -> set[str]:
        names = set()
        for child in node.dependencies:
            names.add(getattr(child.call, "__name__", type(child.call).__name__))
            names.update(dependencies(child))
        return names

    rows = []
    seen = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        deps = dependencies(route.dependant)
        access = (
            ", ".join(
                sorted(
                    deps
                    & {
                        "require_admin",
                        "require_seller",
                        "require_customer",
                        "get_current_user_payload",
                        "get_optional_user_payload",
                    }
                )
            )
            or "Public / handler checks"
        )
        for method in sorted(route.methods):
            key = (route.path, method)
            if key in seen:
                raise RuntimeError(f"Duplicate route: {key}")
            seen.add(key)
            rows.append(
                (
                    route.path,
                    method,
                    access,
                    route.endpoint.__module__ + "." + route.endpoint.__name__,
                )
            )
    lines = [
        "# WearHowZ endpoint inventory",
        "",
        f"Generated from the application: {len(rows)} HTTP operations.",
        "",
        "Dependency names show route-level access checks. Guest capability tokens, "
        "resource ownership, payment verification and business-state checks also run "
        "inside handlers/services; consult the OpenAPI schema and implementation.",
        "",
        "| Method | Path | Access dependencies | Handler |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {method} | `{path}` | {access} | `{handler}` |"
        for path, method, access, handler in sorted(rows)
    )
    (target / "ENDPOINTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Exported {len(rows)} operations to docs/openapi.json and docs/ENDPOINTS.md")


if __name__ == "__main__":
    main()
