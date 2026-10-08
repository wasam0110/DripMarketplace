# Task 6 — backend release-check report

Refreshed 8 October 2026 after backend Task 3/4 hardening. **Coverage/check deliverables achieved; production release blocked.**
No work on the frontend queue, deployment, push, real
charges or historical wallet corrections was performed.

## Verified results

| Check | Result |
|---|---|
| Full suite, Python 3.13.14 | 570 passed, 1 skipped; 85.62% line coverage |
| Coverage gate | Original 85% requirement unchanged; passed |
| Database | Native PostgreSQL 15, isolated random schemas in `wearhowz_test` |
| Migration | Fresh base → 013, 013 → 012_marketplace_gaps → 013; all 39 model tables readable |
| Concurrency | Independent committed transactions test competing stock reservations, withdrawals, settlement/release, refund confirmation, signed callbacks and expiry sweeps |
| Worker/Redis | Redis 7 DB 15; actual ARQ retry scheduling, recovery and max-tries exhaustion; provider sends mocked |
| Lifecycle | Native DB/Redis worker startup, healthy dependency checks and shutdown |
| API image | Local `wearhowz-task6-api:review` Docker build passed; shell-CMD signal warning remains |
| Worker image | Local `wearhowz-task6-worker:review` Docker build passed; scheduled jobs not started against live providers |
| Contract | OpenAPI 3.1: 171 schema operations, 181 schemas; inventory includes 174 operations including hidden routes |
| Compilation | `compileall` on app, scripts and tests passed |
| Lint | Changed files were formatted; the inherited repository-wide Ruff backlog remains and no clean lint claim is made |
| Dependency consistency | `pip check` passed; this does not clear security advisories |
| Typing | mypy unavailable in checked-in dev environment; no clean type-check claim |
| Dependency audit | 45 advisory entries across 9 installed packages; unresolved |

The full suite command and environment are in [SETUP.md](../SETUP.md). Its result is
also recorded in `test-results.xml`. The single skip is the inherited module-level
skip in `tests/security/test_auth.py`, not a skipped native infrastructure check.
Coverage is line coverage, not branch coverage, and excludes the existing configured
paths/lines without widening exclusions or reducing the threshold.

## Repairs made while validating

- Restored the background-task session factory interface; shutdown now clears it.
- Added notification `read_at`/`is_archived` fields and migration 013; read operations
  preserve the original read timestamp and active queries omit archived entries.
- Made the migration environment accept Alembic's supplied connection for isolated
  migration checks without nesting event loops.
- Fixed email verification's repository call and customer account lookup/avatar
  upload calls. Added an explicit avatars bucket setting.
- Customer password changes now increment the authentication version so old access
  tokens are revoked. Notification preferences now handle decoded Redis keys.
- Added the missing asynchronous ResendClient interface used by notification
  delivery; its synchronous SDK send runs in a thread.
- Email task failures now raise ARQ Retry, including previously silent failures.
  Retry delay follows attempt count; the configured worker maximum remains three.
- Fixed cleanup structured logging and admin dispute eager-loading to prevent an
  async database-loading error during serialization.
- Isolated tests from local `.env` and host DEBUG values. Repaired obsolete test
  mocks/fixtures without relaxing production validation or financial assertions.

Added meaningful tests for schema validation, task dispatch, cache and DB lifecycle,
native accounting/inventory races, customer/auth/storefront/seller/admin/return
journeys, local signed Google ID-token flow, repository behavior and real Redis retries.
These do not certify external providers or replace a security assessment.

## Handoff and blockers

Deliverables: [setup](../SETUP.md), [known limits](../KNOWN_LIMITS.md),
[endpoint inventory](ENDPOINTS.md), [OpenAPI](openapi.json),
[dependency audit](dependency-audit.json), and `scripts/package_review.py`.
The source ZIP is `dist/WearHowZ_Task_6_Review.zip`, with per-file hashes inside
`MANIFEST.json` and a sibling ZIP SHA-256 file. It is a review snapshot, not an
in-place updater or production-approved release. Packaging excludes local settings,
keys, Git metadata, virtual environments and caches; archive integrity and source
hashes are checked by the packaging script.

Task 6 cannot be signed off as a backend release while dependency security findings
and historical ledger reconciliation remain unresolved. Full-repository lint/type
validation also remains open. Storage cleanup is now opt-in and reference-aware, but
live provider acceptance for Tasks 3/4 stays gated. See KNOWN_LIMITS.md for
the exact distinctions and SETUP.md for the accounting-owner reconciliation procedure.
No legacy `released_at` marker was cleared and no real balances were reopened.

The next decision is the scope of dependency/security remediation and provision of
historical accounting evidence, not automatic advancement to Task 7.
