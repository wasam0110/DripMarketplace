# Backend pre-ship checkpoint 6: seller aggregates and low-stock thresholds

16 October 2026. Backend only. The wider 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, external provider call, deployment, commit or push.

## Result and scope

Added real two-seller HTTP/DB evidence for all four seller analytics routes and
seller low-stock/inventory filters. No cross-seller disclosure was found in these
tested paths. The tests do not mock authorization or analytics/inventory services.

Fixed a reproduced dashboard inconsistency: inventory-health used a constant 5,
ignoring persisted per-variant reorder points already used by inventory alerts.
It now compares available units against ProductInventory.reorder_point. Removed
the obsolete constant; there is no migration or new setting.

Preserved and documented the existing response semantics:

- Available units = stock minus reserved units.
- In-stock counts all positive available variants, including low-stock variants.
- Low-stock counts positive available variants at/below their own reorder point.
- Out-of-stock counts zero available variants separately.
- Health includes active variants on non-deleted products. Management inventory
  lists can include inactive variants; that existing population rule was not changed.
  Inventory alerts also include zero-availability variants, unlike health.low_stock.

OpenAPI now describes these semantics. Response field names/types, 190 HTTP
operations and migration head 020 are unchanged.

## Evidence

New module: tests/integration/test_seller_analytics_ownership.py, **20 cases**.
Fixtures have distinct seller sales, views, private products and stock, plus a shared
multi-brand order and a synthetic partial-refund ledger. Assertions cover:

- Exact owned overview totals, units, views and refund-adjusted net ledger amounts
  for each supported period (7d, 30d, 90d, 1y).
- Revenue isolation across day/week/month groupings and every supported period.
- Owned top-products for revenue/units/views sorts with limit=1, including a private
  unpublished product that must not leak into another seller's results.
- Health/low-stock isolation; foreign product, SKU and name filters; combined filters;
  page boundaries; unchanged stored inventory after read requests.
- Signed stale seller-ID claims and caller-supplied seller_id query parameters cannot
  redirect any of the four aggregate routes or low-stock listing.
- Moving both sellers' records to 45 days ago exercises included/excluded periods.
- Reorder points above 5, zero, exact boundary, reserved units and out-of-stock cases;
  inactive/deleted-product health exclusions and deleted-product alert exclusion.

Before the fix, the six threshold cases produced **3 failed / 3 passed**; failures
were the expected low_stock mismatch. After the fix, the combined new/existing
analytics, inventory and ownership suite passed **65 tests**.

Full suite: **795 passed, 1 skipped, zero failures/errors; 86.85% coverage**
(8,293/9,549 statements), exit 0 in 872.81 seconds. The unchanged 85% gate passes.
The inherited obsolete security module remains skipped; active native ownership
and permission tests ran. Runtime/test file fingerprints are unchanged since the run.

Saved evidence: [JUnit XML](audit/preship-checkpoint-6-tests-2026-10-16.xml) and
[coverage JSON](audit/preship-checkpoint-6-coverage-2026-10-16.json).

New test-module Ruff checks and syntax-critical checks on the two touched runtime
modules pass. This is not a repository-wide lint/type-clean claim. API export
succeeds offline with synthetic settings; no application .env was read or changed.

Full-run command (only against disposable local test services):

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://audit:local-audit-only@127.0.0.1:15432/wearhowz_preship_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-6-tests-2026-10-16.xml --cov-report=json:docs/audit/preship-checkpoint-6-coverage-2026-10-16.json
```

The synthetic test services are independent of development Redis and production.
Recreate disposable services before rerunning after cleanup.
Both labeled preship6 containers and their anonymous test-data volumes were removed
after verification; development drip_redis was preserved. Removed synthetic test data
is reproducible from fixtures, not retained as a backup.

## Still open

- Exhaustive per-operation/input ownership, remaining bulk mutation combinations,
  mass-assignment review and mixed-operation races across the wider backend.
  Recommended next: admin bulk-stock valid/missing/reserved/duplicate/oversized
  inputs and actual rollback/result consistency. Source catches per-item database
  exceptions without savepoints before a shared commit; its partial-success behavior
  needs a native failure test, not an assumption that counts equal persisted updates.
- F16 money presentation/configuration/error-contract consistency. This checkpoint
  intentionally preserves existing analytics integer-PKR schemas and differing
  reporting bases: ledger aggregates are refund-adjusted; top-product revenue uses
  qualifying order-item snapshots. It does not certify fractional-money presentation
  or make every metric a reconciled net-revenue report.
- Versioned consent, final retention/legal-hold policy, managed seller/admin closure,
  historical cleanup and pending/provider/backup retention acceptance.
- Static/type debt, reproducible dependency locking, remaining checklist evidence
  and provider/staging/deployment gates. Passing tests are not release approval.
