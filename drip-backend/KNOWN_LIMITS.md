# Backend release limitations

Reviewed 8 October 2026. Passing coverage is not production approval.

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
- **Live provider acceptance remains gated:** PayFast now follows the published hosted
  checkout/token/callback protocol and has safe status reconciliation; Google, Supabase,
  Resend and worker flows have local signed/mocked coverage. These checks do not prove
  merchant-specific endpoints, source IPs, real Google consent, Supabase permissions or
  Resend delivery. Keep PayFast and Supabase orphan deletion disabled until the staging
  checklists pass. No real charge, email or upload was performed in this review.

## Verification boundaries and technical debt

- Native PostgreSQL tests exercise competing reservations, withdrawal requests,
  settlement/release, refund confirmation, signed payment callbacks and expiry
  sweeps. They are controlled two-contender regressions, not a load test or proof of
  every interleaving, crash/restart or distributed failure mode.
- Real Redis tests prove explicit email-task retry and exhaustion with provider
  transports mocked. Notification jobs now retry database failures and broadcast
  inserts are deterministic, but a durable outbox and provider delivery reconciliation
  are not established by these tests. No exactly-once email claim.
- The inherited `tests/security/test_auth.py` is module-skipped and obsolete.
  Other active tests cover authorization and callback protections, but this is not
  a comprehensive penetration test. The skipped module is reported, not counted
  as passing security coverage.
- PayFast forwarding headers are accepted only from configured trusted proxies. The
  actual proxy and PayFast callback IP/CIDR lists remain deployment-specific and must be
  confirmed before enabling the gateway.
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

This review covers backend Tasks 3, 4 and 6. No Task 7-12 frontend work or publishing was performed.
