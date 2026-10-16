# Pre-ship audit — checkpoint 1

13 October 2026. **Partial completion, not release approval.** Backend only.

## Scope

The original HTML contains 162 checklist entries in 18 sections. All are retained
in [PRE_SHIP_AUDIT.md](PRE_SHIP_AUDIT.md), with evidence, open findings and external
gates. The HTML SHA-256 is
`4e5c0922ecf82851f4947b0b7b4a106899cb4f64b1cc4921691868281aaa86ff`.
This checkpoint does not claim every backend file or checklist item was freshly
reviewed. Earlier B1–B4 changes were preserved; no commit or push was made.

## Repairs

- Shared trusted-proxy resolver for rate limiting, request logs and payment ingress.
  It rejects direct spoofing and walks proxy chains right-to-left, including repeated
  XFF headers and IPv6. Docker disables upstream Uvicorn rewriting. Global proxy
  trust defaults to none, with a supported PayFast-specific override.
- Rate-limit buckets group resource paths by configured rule. Redis MULTI/EXEC
  atomically increments and establishes expiry without extending active windows.
  Remaining-request headers no longer subtract twice. The policy remains fixed-window
  and per-IP before route authentication, not a sliding/user limiter. Scope changes
  start new bounded counters; old expiring counters expire naturally.
- Invalid catalogue cursor shape/types, decimals, encodings, size and timestamps
  are rejected as client errors before SQL execution.
- Seller suspension no longer overwrites independent product moderation. Public
  product access is denied while suspended, and reinstatement keeps hidden products
  hidden. Existing ambiguous hidden flags are not automatically cleared.
- API lifespan cleans both resource pools on partial startup, application exceptions
  and cleanup failures. Missing Sentry runtime dependency added (`2.72.0`); local
  configuration validation sends no events and disables local-variable/body capture.

## Verification

- Initial proxy/payment run: 27 passed.
- Expanded proxy/cursor/product/payment run: 65 passed.
- Native boundary/moderation, startup, auth and customer journeys: 72 passed.
- **Full suite: 662 passed, 1 skipped, 695 warnings; 85.78% coverage.** The unchanged
  85% requirement passed. Forty-one regression cases were added in this checkpoint.
- The skipped item is the inherited module-level skipped security suite; it is not
  successful security coverage. Warnings include inherited deprecated APIs.
- New source/test files pass configured Ruff; repository-wide lint/type cleanliness
  is not established. `git diff --check` and `pip check` pass.
- Native Redis test sends 30 concurrent counter operations and admits exactly five,
  proving atomic count/expiry and no sliding extension. PostgreSQL tests prove seller
  visibility and moderation preservation against persisted data.
- Tests use isolated PostgreSQL schemas and dedicated Redis database 15. No external
  provider acceptance, live transfer, real notification or production data was used.
- No new migration was introduced here. The full suite includes existing migration
  checks, but it does not close the independently identified model/migration drift.

Full command, with dedicated `TEST_DATABASE_URL` and `TEST_REDIS_URL` configured:

```powershell
.venv/Scripts/python.exe -m pytest --junitxml=docs/audit/preship-tests-2026-10-13.xml --cov-report=json:docs/audit/preship-coverage-2026-10-13.json --disable-warnings
```

Machine evidence: [test results](audit/preship-tests-2026-10-13.xml),
[coverage](audit/preship-coverage-2026-10-13.json),
[dependency audit](audit/preship-dependency-audit-2026-10-13.json).

## Remaining blockers and next decision

The fresh installed-dependency scan still reports **45 advisory entries in nine
packages**, including development tools. This is not a claim that every advisory is
exploitable in production. Security upgrades/replacement and compatibility validation
remain necessary; a successful `pip check` does not establish vulnerability safety.

Other open code work includes authoritative PayFast verification, account deletion,
inventory reorder thresholds, model/migration alignment, outbox failure recovery,
log redaction, readiness status, legacy preferences, full route authorization coverage,
and money/configuration consistency. The exhaustive tracker remains in progress.

**Owner decision requested:** should customer deletion anonymize the account while
retaining necessary financial history, with seller/admin offboarding handled separately?
The current 90-day bulk hard-delete is not a safe complete retention policy. No
destructive cleanup or new retention policy was applied during this checkpoint.

Provider credentials, staging delivery checks, production backup/restore, alert
recipients, retention periods and final independent sign-off remain separate gates.
No real payment or deployment is authorized by these tests.

## Workspace cleanup

Removed only `wearhowz_preship_postgres` and `wearhowz_preship_redis`, including their
disposable synthetic-test volumes. These temporary test data are not recoverable;
the tests recreate them. The existing `drip_redis`, frontend, local configuration,
Git history and original HTML were left untouched. Downloaded images remain cached.
