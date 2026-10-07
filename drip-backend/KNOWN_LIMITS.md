# Release limitations — Task 6 review

Reviewed 7 October 2026. Passing coverage is not production approval.

## Release blockers

- **Dependency security:** the saved local pip-audit report identifies 45 advisory
  entries across nine installed packages. This includes development tools; it is not
  a claim that all 45 affect production or are exploitable here. Runtime dependencies
  include cryptography, ecdsa, orjson, Pillow, python-jose, python-multipart and Starlette.
  Some entries have no listed fix. See `docs/dependency-audit.json`. Upgrades and, where
  needed, dependency replacement require compatibility/security review and a new test
  run; dependencies were not silently upgraded in this task.
- **Historical money:** no real historical settlement records or transfer receipts
  were supplied. Legacy release protection remains unchanged. Follow SETUP.md before
  reopening any historical pending balance. Local synthetic races do not reconcile
  a merchant's real books or approve platform absorption of refund shortfalls.
- **Provider verification remains gated:** local signatures, HTTP mocks and worker
  tests do not prove real PayFast endpoints, merchant callbacks, reconciliation,
  Google sign-in, Supabase permissions or Resend delivery. Keep PayFast disabled.
  The earlier Task 3/4 completion descriptions must not be read as live-provider
  certification. No real charges or external emails/uploads were performed.
- **Scheduled image cleanup needs review before real storage use:** it scans the
  hard-coded `products` bucket and checks only ProductImage references. Other image
  owners and missing/invalid timestamps are not safely covered. Do not enable the
  scheduled worker against valuable storage until this is corrected and tested.

## Verification boundaries and technical debt

- Native PostgreSQL tests exercise competing reservations, withdrawal requests,
  settlement/release, refund confirmation, signed payment callbacks and expiry
  sweeps. They are controlled two-contender regressions, not a load test or proof of
  every interleaving, crash/restart or distributed failure mode.
- Real Redis tests prove explicit email-task retry and exhaustion with provider
  transports mocked. Other notification paths catch/log some exceptions and can
  acknowledge a failed delivery; durable outbox/deduplication and provider delivery
  reconciliation are not established by these tests. No exactly-once email claim.
- The inherited `tests/security/test_auth.py` is module-skipped and obsolete.
  Other active tests cover authorization and callback protections, but this is not
  a comprehensive penetration test. The skipped module is reported, not counted
  as passing security coverage.
- PayFast callback IP filtering currently reads `X-Forwarded-For`; deployment must
  not trust client-supplied forwarding headers. Trusted-proxy handling and provider
  ranges need validation before enabling the gateway.
- Health returns HTTP 200 with `status=degraded` when a dependency is unavailable.
  The Docker curl health check tests HTTP status only. Readiness monitoring must
  inspect the body or be corrected before relying on it for routing.
- Repository-wide Ruff has a substantial inherited backlog. Targeted formatting
  does not establish a clean lint gate. Strict typing is configured but mypy is not
  part of the checked-in development requirements; a clean type-check result has
  not been established.
- The migration test uses a fresh isolated schema and a 013 → 012 → 013 round trip,
  not a populated production backup. Rollback drops notification archive/read data.
- API/worker image build success alone does not prove deployment, health, secrets,
  network policy, scheduled delivery, backup/restore or operational monitoring.

Only Task 6 is in scope. No Task 7–12 work or publishing is authorized by this review.
