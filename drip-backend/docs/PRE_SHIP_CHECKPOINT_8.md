# Backend pre-ship checkpoint 8: analytics money precision

16 October 2026. Backend only. The broader 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, provider call, deployment, commit or push.

## Reproduced problem and repair

All eight money-bearing analytics endpoints truncated PostgreSQL NUMERIC values
with `int()`. A native two-seller fixture with a partial-refund ledger reproduced
PKR 18.05 becoming 18, 20.07 becoming 20, 27.08 becoming 27 and recorded seller fees
2.80 becoming 2. Payment/city shares also used truncated amounts: 17.06/27.08 was
reported as 62.96% rather than 63.00%. Sub-rupee totals of 0.01 and 0.03 both became
zero, producing 0% shares instead of 25%/75%. All ten pre-fix regression cases failed.

Money stays Decimal throughout analytics calculations. Response amounts are
quantized to two decimal places using explicit ROUND_HALF_UP, consistent with the
existing accounting rounding convention. Averages divide exact totals before
rounding (for example 18.05 / 2 = 9.025 becomes 9.03, not 9). Shares use exact
decimal totals before converting the rounded percentage to the existing float type.
Count/rating/conversion/inventory fields retain their existing types.

No accounting rows, financial allocations, report filters, period grouping, sorting,
ownership policy or database schema were changed. Head remains 020; the API still
has 190 operations. Existing working-tree repairs were preserved.

## API compatibility and frontend handoff

**Intentional response-type change:** the 16 monetary fields below now serialize as
JSON decimal strings (for example `"18.05"` and `"0.00"`), matching the existing
Decimal dashboard/wallet convention. They are **PKR major units, not integer paisa**.
Clients expecting integers must update their types and use decimal-aware money
handling; JavaScript `parseInt()` would reintroduce the defect. No frontend was edited.

| Response model | Monetary fields |
|---|---|
| SellerAnalyticsOverview | gross_revenue, commission_paid, net_earnings, avg_order_value |
| RevenueDayRow (seller/admin) | gross, commission, net |
| TopProductRow | revenue |
| PlatformAnalytics | total_gmv, commission_revenue, slot_revenue, avg_order_value |
| TopSellerRow | gmv, commission |
| PaymentMethodStat | total |
| CityRow | total_gmv |

The generated OpenAPI describes string amounts, PKR units and rounding. New response
constraints reject non-finite and unrounded fractional values rather than silently
coercing them to integers. There is no single-row maximum imposed on aggregate sums.

Preserved reporting bases, which must not be conflated:

- Seller overview/revenue and admin ledger revenue/top sellers use refund-adjusted
  commission-ledger amounts, filtered by settlement time. Their order counts count
  ledger rows (seller orders), not distinct platform orders.
- Top-product revenue uses qualifying order-item snapshots; it is not a net-refund
  allocation report. Platform GMV and cities use qualifying Order.total snapshots,
  including shipping/discount effects, and are not refund-adjusted ledger totals.
- Platform average retains its existing denominator: all orders in the period,
  not just the orders whose statuses qualify for GMV. This checkpoint does not
  redefine that metric or claim it is the average of paid orders only.
- Payment-method totals retain the existing non-pending-payment population,
  including cancelled/refunded rows; the share denominator can include historical
  payment methods not exposed as separate response fields. City shares use the
  returned top-city subset. These semantics are unchanged, not reconciled revenue.
- `slot_revenue` retains its existing combined recorded registration and slot fees.

## Verification

New native module: `tests/integration/test_analytics_money.py`, 18 cases. Eight
populated-route cases check exact HTTP money strings, partial-refund conservation,
two-seller separation, fractional recorded fees and no financial-row mutation.
Two cases exercise sub-rupee shares; eight cover empty-data response types.

New unit module: `tests/unit/test_analytics_money_contract.py`, 16 cases. Covers
all seven money-bearing schemas/16 fields, serialization beyond JavaScript's exact
integer range, published string schemas, preserved non-money types, rounding
boundaries, and rejection of NaN/infinities/unrounded output.

Existing seller-ownership expected values now assert decimal strings; the actual
ownership, period, grouping, sorting and filter assertions are retained.
The native analytics/ownership and existing analytics unit selection passed **55
tests** (24 warnings, 229.31 seconds); the new money-contract unit module separately
passed **16 tests** (24 warnings, 1.39 seconds).

Full suite: **854 passed, 1 skipped, zero failures/errors; 87.13% coverage**
(8,322/9,551 statements), exit 0 in 1,397.96 seconds. The unchanged 85% gate passes.
The inherited obsolete security module remains skipped; active ownership, native
financial/concurrency, migration and worker checks ran. There were 638 warnings,
including existing deprecations; this is not a warning-free or release-ready claim.
All five changed runtime/test file fingerprints match the tested snapshot.

Saved evidence: [JUnit XML](audit/preship-checkpoint-8-tests-2026-10-16.xml) and
[coverage JSON](audit/preship-checkpoint-8-coverage-2026-10-16.json).

Configured Ruff checks on the new/updated tests and syntax-critical Ruff checks on
the two runtime modules pass. This is not a repository-wide lint/type-clean claim.
The offline contract exporter succeeds without reading the application .env.

Full-run command, only against disposable local test services:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://audit:local-audit-only@127.0.0.1:15432/wearhowz_preship_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-8-tests-2026-10-16.xml --cov-report=json:docs/audit/preship-checkpoint-8-coverage-2026-10-16.json
```

Both labeled preship8 containers and their anonymous synthetic-data volumes were
removed after verification; absence was checked. Development `drip_redis` remains
running and unchanged. Removed test data is reproducible from fixtures, not retained
as a backup. Recreate disposable services before rerunning these commands.

## Still open / recommended next

F16 is **partially repaired**, not closed. Recommended next: coupon validation and
discount precision, including minimum-spend comparisons and consistency with checkout.
Source inspection still finds integer conversions there and in slot responses and
notification/email amounts. Those paths were not repaired or fully verified here.
Canonical public-link configuration and error-envelope consolidation also remain open.

The wider audit still includes exhaustive ownership/input coverage, mixed-operation
races, static/type debt, dependency reproducibility, consent/final retention and
managed offboarding, historical reconciliation, and provider/staging/deployment gates.
Passing local tests does not authorize production or certify a defect-free backend.
