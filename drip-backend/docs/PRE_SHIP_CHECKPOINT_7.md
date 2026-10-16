# Backend pre-ship checkpoint 7: admin bulk-stock transaction integrity

16 October 2026. Backend only. The wider 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, external provider call, deployment, commit or push.

## Reproduced defect and repair

A native PostgreSQL constraint failure in the middle of a three-row correction
aborted the shared transaction. The old endpoint returned HTTP 200 with one update
and two failures, but a separate connection showed **all three stocks unchanged**.
The claimed success had rolled back. This was reproduced before the repair, not
inferred from mocks. The rejecting CHECK constraint exists only in a disposable
test schema; no application migration or business constraint was added.

The service now isolates each row with a savepoint. Integrity/data errors roll
back that row and produce a sanitized error while other valid rows can commit.
Unexpected statement errors and commit failures roll back the batch and propagate;
they do not produce a successful bulk response. Counts are returned only after commit.
An uncertain network outcome at commit still requires reading current stock; this
does not add a durable operation ID or an exactly-once request protocol.

Validation accepts 1-500 unique variant IDs and stock from 0 through 999,999, matching
the existing single-stock correction limit. Duplicate IDs and invalid batches are
rejected before writes, including direct service calls. Unknown fields remain forbidden.
Rows lock in UUID order to avoid opposite-order bulk/bulk deadlocks; error entries
remain in request order. This is not proof against every mixed-operation deadlock.

The existing atomic reserved-stock predicate is retained. Corrections cannot lower
stock below reservations. Reserved units and reorder points are not overwritten.
This endpoint remains admin-only and can intentionally correct multiple sellers.
It sets absolute quantities; repeating it does not add stock. `updated` counts matched
rows even when their quantity was already equal, not only changed quantities.
The optional `reason` is still not a durable stock-adjustment audit trail.

OpenAPI describes limits and partial/fatal failure semantics. Migration head 020
and the 190-operation contract remain unchanged.

## Verification

New module: `tests/integration/test_admin_bulk_stock.py`, 25 cases covering:

- Real server-side row failure, continued valid updates, sanitized errors and fresh
  independent reads of persisted stock.
- Valid/missing/below-reservation rows, input-ordered errors, zero/upper stock bounds
  and repeated absolute corrections without double credits.
- Duplicate/empty/oversized batches, negative/oversized/fractional quantities,
  malformed IDs and forbidden reserved/reorder/seller/batch fields, with no writes.
- Real admin/customer/seller/anonymous HTTP authentication/authorization and an
  allowed admin batch spanning two sellers; no authorization or service mocks.
- Injected unexpected statement and commit failures after real database writes,
  followed by whole-batch rollback and independent stored-state checks.
- Native correction-versus-reservation races in both forced lock orderings;
  opposite-order concurrent bulk requests plus observed deterministic lock order.
- Direct service validation and the schema's exact 500-item boundary.

The focused bulk-stock, existing inventory, resource-ownership and permission-matrix
suite passed **45 tests** (48 warnings, 168.32 seconds). It includes all 25 new cases.
The HTTP matrix checks the existing 154 protected operations across identity/role
states.

Full suite: **820 passed, 1 skipped, zero failures/errors; 87.15% coverage**
(8,319/9,546 statements), exit 0 in 1,405.05 seconds. The unchanged 85% gate passes.
The inherited obsolete security module remains skipped; active native ownership,
permission, migration and worker tests ran. The three changed runtime/test file
fingerprints are unchanged since the run. There were 638 warnings, including
existing dependency/datetime deprecations; this is not a warning-free release claim.

Saved evidence: [JUnit XML](audit/preship-checkpoint-7-tests-2026-10-16.xml) and
[coverage JSON](audit/preship-checkpoint-7-coverage-2026-10-16.json).

The new module passes configured Ruff checks; the two runtime modules pass
syntax-critical Ruff checks. This is not a repository-wide lint/type-clean claim.
The offline exporter succeeds with 190 operations; generated schemas expose the
quantity and batch-size bounds. No application .env was read or changed.

Full-run command (only against disposable local test services):

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://audit:local-audit-only@127.0.0.1:15432/wearhowz_preship_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-7-tests-2026-10-16.xml --cov-report=json:docs/audit/preship-checkpoint-7-coverage-2026-10-16.json
```

Both labeled preship7 audit containers and their anonymous test-data volumes were
removed after verification; absence was checked. Development `drip_redis` remains
running and was not modified. Removed synthetic data can be recreated from fixtures;
it was not retained as a backup. Recreate disposable services before rerunning.

## Still open

- Exhaustive operation/input ownership and mass-assignment review, mixed-operation
  races and a durable inventory correction history are not certified by these tests.
- Recommended next: F16 money presentation consistency, starting with analytics
  and report responses that currently use integer-PKR amounts. Existing stored
  Decimal/NUMERIC accounting and refund allocations must be preserved.
- Final retention/legal-hold policy, consent versions, managed seller/admin closure,
  historical cleanup and pending/provider/backup retention acceptance remain open.
- Static/type debt, reproducible dependency locking, remaining checklist evidence
  and provider/staging/deployment gates. Passing tests are not release approval.
