# Backend pre-ship checkpoint 4: ownership and limited customer privacy

15 October 2026. Backend only. No frontend changes, real provider calls, production
cleanup, commit or push. The broader pre-ship review remains **IN PROGRESS**.

## Approved scope and implementation

The owner approved safe customer cleanup, with final financial/dispute retention
periods and new seller/admin offboarding workflows deferred. See the exact behavior,
proposed policy and operating limits in [CUSTOMER_PRIVACY.md](CUSTOMER_PRIVACY.md).

- Added cross-account HTTP tests with actual PostgreSQL records and signed tokens:
  two customers and two sellers. No authorization/service mocks; the upload test
  mocks only the external provider and asserts unauthorized calls never reach it.
- Added `lock_active_user` and applied it to customer profile/address/review/cache
  writes, preferences, return/dispute creation and new refresh sessions. Queries
  refresh cached identities after acquiring the lock and reject deleted accounts.
- Refresh lookup now takes the user lock before the session lock, rechecking the
  session afterwards. Authentication updates exclude deleted users, preventing late
  password/email-verification/TOTP/login-timestamp writes from restoring profile data.
- Default-address selection checks ownership before clearing the caller's defaults.
- Deletion transaction removes notifications/preferences/review free text/image
  references and records external cleanup durably. Financial/dispute history remains.
- Redis cleanup runs after commit and retries through the outbox on failure. Storage
  cleanup is restricted to attributable generated object paths, checks shared
  references, retains uncertain targets for manual review and clears completed manifests.
- Registered-order notifications and broadcasts skip deleted users under the account
  lock; delayed jobs cannot repopulate those in-app notifications after deletion.
- Corrected the deletion API description and updated policy/runbooks/audit documentation.
  No new API route or migration: **190 operations; migration head 020**.

## Ownership evidence and limits

`tests/integration/test_resource_ownership.py` contains eight grouped scenarios:

| Area | Evidence |
|---|---|
| Customer-owned IDs | Addresses/defaults, reviews, notifications, order UUID/number/cancellation, payment initiation/retry/status, returns/disputes/messages |
| Seller-owned IDs | Product read/write/delete/publish, variants, image ordering/primary/delete/upload, inventory read/set/adjust, bank deletion, fulfilment, return decisions, withdrawal account |
| Nested IDs | A valid owned product cannot be combined with another product's variant/image identifiers |
| Lists and bulk state | Customer address/review/notification/order/return lists; seller product/inventory/bank/order/return lists; foreign product filters; notification mark-all |
| Account-derived resources | Profile, both preference APIs, cart sync/update/delete/clear and wishlist changes remain scoped to the token subject |
| Money/private history | Wallet balances, payouts, transaction lists and bank details remain seller-scoped; stale seller-ID token claims do not override database ownership |

The customer/seller ID tables, nested-ID cases and upload scenario exercise **43
cross-resource requests**. Denied DB mutations compare stored target-table values
before and after. Valid owner reads/writes and existing end-to-end journeys ensure
the tests are not merely probing nonexistent records. Another user's notification
read correctly preserves the existing `200 {"marked": false}` no-op contract.

These supplement checkpoint 3's all-route role-denial matrix. They do **not** claim
exhaustive owner-success/other-user/input coverage for all 190 operations; aggregate
analytics, every bulk combination and remaining checklist review still need evidence.

## Privacy verification

`test_customer_privacy.py` and `test_privacy_auth_races.py` cover:

- Retained financial records, scrubbed profile-adjacent data and removed cache keys.
- Failed DB commit rolls back cleanup/event creation and leaves caches untouched.
- Redis outage preserves a durable cleanup request; subsequent delivery clears it.
- Storage failure retains the manifest, retry completes, duplicate completion does
  not call storage again; unrelated/shared/external/folder URLs are not deleted.
- Stale access tokens and late account/authentication writes cannot restore deleted
  data; registered-order/broadcast delivery does not recreate customer notifications.
- Six native two-session interleavings: deletion first and return/dispute/refresh
  first. New active cases block deletion; deletion blocks new cases/refresh; completed
  deletion leaves no refresh sessions. These are controlled races, not a load test.

The existing broadcast failure unit test now supplies an explicitly active mock user
so it still reaches and verifies database failure rollback/retry.

## Verification results

- Full native PostgreSQL 16 / Redis 7 suite: **753 passed, 1 skipped, 636 warnings**
  in **822.042 seconds**. Zero failures/errors. All 20 new ownership/privacy cases pass.
- **86.65890816758358%** reported line coverage: **8,191 / 9,452 statements**.
  The unchanged **85% gate passes**. Coverage is not proof of complete security testing.
- Includes existing native races, fresh/round-trip migrations, 42-table schema parity,
  durable worker recovery, all-route permission tests and the new ownership/privacy cases.
- The obsolete inherited security module remains skipped and is not counted as passing.
- Focused Ruff checks pass on the two new services and three new test modules;
  `git diff --check` passes. No repository-wide lint/type-clean claim is made.
- Offline contract export succeeds: **190 operations**. No additional migration;
  head remains **020**. All external provider deletion/delivery calls in these tests
  were mocked; no production or user data was deleted.

Saved evidence: [JUnit XML](audit/preship-checkpoint-4-tests-2026-10-15.xml) and
[coverage JSON](audit/preship-checkpoint-4-coverage-2026-10-15.json).

Reproduce from `drip-backend` with disposable local services:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://audit:local-audit-only@127.0.0.1:15432/wearhowz_preship_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-4-tests-2026-10-15.xml --cov-report=json:docs/audit/preship-checkpoint-4-coverage-2026-10-15.json
```

These are synthetic audit credentials, not application configuration. Tests use
isolated schemas; never point them at production. Temporary audit services are removed
after verification and must be recreated to rerun this exact local setup.

## Remaining boundaries

No timer-based financial/dispute/log deletion, versioned consent acceptance, new
seller/admin closure workflow or retrospective bulk privacy cleanup was enabled.
Provider acceptance, backups, raw-address legacy email tasks/queue payload retention,
uncertain historical assets and final retention/legal-hold policy remain open.
The complete 162-item audit, money presentation/configuration issues, static/type
backlog, reproducible dependency locking and broader deployment gates are not closed.
