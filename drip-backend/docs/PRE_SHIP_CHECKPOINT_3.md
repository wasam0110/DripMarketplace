# Backend pre-ship checkpoint 3

15 October 2026. **The broader audit remains IN PROGRESS.** Backend-only implementation
of notification recovery, legacy preferences, permission coverage and schema checks.
No frontend changes, production migrations, real provider messages, commit or push.

## Implemented and verified

- Durable outbox delivery acknowledgement, stale-job recovery, bounded publication
  and delivery attempts, retained dead letters and admin-only audited replay.
  Concurrent generations serialize on the event; keyed local deliveries survive a
  crash between delivery and acknowledgement. Replay has a distinct ARQ job generation.
- One-time import of the five legacy Redis preference fields under a database row
  lock. Initial conflicting opt-outs win; later explicit user edits are preserved.
  Redis failure/malformed data fails closed. Existing mandatory-notice policy remains.
- Independent policy inventory for all **190 HTTP operations**: 28 public,
  8 capability-checked, 44 verified-account, 67 admin, 8 seller-account/onboarding and
  35 active-seller operations. All **154 protected operations** have expected guards.
  Real HTTP rejection tests exercise **938 actor/operation combinations**, including
  anonymous, wrong-role, suspended seller, deleted, unverified and forged-role actors.
  Seller onboarding routes now require an actual seller account; 2FA routes require admin.
- Native PostgreSQL parity for **42 model tables**: columns/types/nullability/defaults,
  indexes, unique/foreign keys, primary keys, check constraints and enum labels/order.
  Models now match existing migrated constraints/defaults rather than weakening them.
  Historical JazzCash/Easypaisa/card order rows remain readable; new checkout and
  payment initiation still reject those legacy methods.
- Migration **019** adds recovery/import bookkeeping. **020** adds missing indexes
  and nonnegative review-count/image-order checks. Current migration head: **020**.
- Regenerated OpenAPI and endpoint inventory; updated setup, limits and the
  [notification recovery runbook](NOTIFICATION_RECOVERY.md).

## Verification

Full suite on local **native PostgreSQL 16 and Redis 7**, with synthetic data:

- **733 passed, 1 skipped, 590 warnings**, in 717.374 seconds.
- **86.04825737265415%** reported line coverage: 8,024 / 9,325 statements.
  The unchanged **85%** gate passes. Coverage is not proof of branch completeness.
- Includes fresh migrations, migration round trip, full schema comparison, actual
  ARQ lost-job recovery, concurrent notification generations, replay audit history,
  preference import, historical payment reads and route permission checks.
- Focused Ruff checks pass for the newly added recovery/preference services and
  five new integration-test modules. No repository-wide lint/type pass is claimed.
- The one skipped legacy security module is not counted as passing. New permission
  tests run actively with native PostgreSQL and authenticated HTTP requests.

From the backend directory, with disposable test services configured:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://audit:local-audit-only@127.0.0.1:15432/wearhowz_preship_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-3-tests-2026-10-15.xml --cov-report=json:docs/audit/preship-checkpoint-3-coverage-2026-10-15.json
```

The displayed credentials are synthetic disposable audit credentials, not application
configuration. Tests isolate database schemas; do not use a production database.
Saved evidence: [JUnit XML](audit/preship-checkpoint-3-tests-2026-10-15.xml) and
[coverage JSON](audit/preship-checkpoint-3-coverage-2026-10-15.json).

## Deployment precautions and remaining limits

- Back up and preflight existing data before migration 020: negative review counts
  or image ordering values cause failure, not silent cleanup. Stop/drain old workers
  before migration 019 and the new worker are deployed together. Downgrading 019
  discards recovery/import history; export it first.
- Email delivery is at least once, not exactly once across a lost provider receipt.
  Delivery holds an event-row lock and uses two database sessions; provision pool
  capacity and verify production concurrency/alerting. No live provider was exercised.
- Missing/expired legacy Redis preferences cannot be reconstructed from absent data.
  Redis hashes are not deleted by the import; review backups if historical consent is needed.
- Route-role denial coverage is complete for the inventoried protected operations;
  **exhaustive same-role owner-versus-other-user testing is not complete**. Existing
  targeted ownership tests pass, but the broader IDOR/tenant-isolation audit remains open.
- Remaining work also includes unverified items in the [162-item audit](PRE_SHIP_AUDIT.md),
  retention/erasure policy, static/type debt, dependency reproducibility, F16 contract
  details, and deployment/provider acceptance. This checkpoint does not establish a
  foolproof backend or close the full A–Z review.
