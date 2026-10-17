# Backend pre-ship checkpoint 9: coupon money and seller allocation

17 October 2026. Backend only. The broader 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, live provider call, deployment, commit or push.

## Reproduced problems and repairs

- Coupon previews truncated both the coupon value and calculated discount with
  `int()`. A 12.50% coupon on PKR 100.05 reported 12 rather than 12.51; a fixed
  PKR 2.75 coupon reported 2. Values now remain Decimal throughout the response.
- Minimum-spend validation truncated the stored threshold, and the legacy apply
  helper also truncated the supplied subtotal. PKR 100.74 incorrectly qualified
  for a PKR 100.75 minimum. Exact comparisons and full two-place error amounts
  now apply in preview, authoritative checkout and the legacy helper.
- Discount rounding now explicitly uses ROUND_HALF_UP, consistent with the ledger
  money policy: 10% of 100.05 becomes 10.01. Fixed/percentage discounts are capped
  at the merchandise subtotal and quantized once to two decimal places.
- Six sellers, each with PKR 100.05 merchandise, exposed accumulated allocation
  rounding. A 0.04 coupon could increase the final seller subtotal to 100.06;
  a 600.26 coupon could make it -0.01. Each share is now bounded by the remaining
  discount, its seller's value and later sellers' remaining capacity. The exact
  total discount is conserved, with every seller subtotal between zero and its
  original value. Ordinary proportional shares and their existing rounding rule
  remain unchanged; only out-of-bounds residual allocation is corrected.

No migration, existing accounting row, coupon usage policy, shipping rule, product
price minimum or authentication policy changed. Head remains 020. This checkpoint
does not retroactively reconcile historical orders with invalid seller allocations.

## API contract and compatibility

`POST /api/v1/coupons/validate` accepts a finite PKR-major-unit subtotal with at
most two fractional places and at most 12 total digits, matching order storage.
The existing PKR 1 input minimum is retained. Extra nonzero fractional places,
overflow and non-finite values return 422 before coupon use is recorded.

The response already used Decimal strings; this is a value/precision correction,
not a change from JSON numbers to strings. `discount_value` is the percentage rate
for percentage coupons or PKR amount for fixed coupons. `discount_amount` and
`new_subtotal` are two-place PKR strings, not integer paisa. A full merchandise
discount returns `"0.00"` as the new subtotal; shipping remains separate.

Preview is an estimate based on the supplied subtotal, not a quote reservation.
It does not consume a use or reserve inventory. Checkout reads current database
prices, rechecks eligibility under the existing coupon lock, and persists exact
order/seller amounts. A price change can alter or invalidate a prior preview.
Authenticated checkout is still required for coupon use.

## Verification

After correcting test fixture prices to respect the existing PKR 100 product
constraint, the initial native regression selection reproduced seven failures
and three passes. The additional six-brand cases both failed before the allocation
repair; the two-brand controls passed.

New native module: `tests/integration/test_coupon_precision.py`, 23 cases. Covers
exact preview/checkout values, percentage/fixed/full caps, minimum boundaries,
invalid inputs, legacy apply precision, price changes after preview, one-time
usage, unchanged stock/cart on denial and two-/six-brand allocation conservation.
Uses native PostgreSQL and the standard isolated fake Redis cart fixture.

New unit module: `tests/unit/test_coupon_money.py`, 16 cases. Covers half-paisa,
sub-paisa, sub-rupee, large-value and capped discounts under different ambient
Decimal rounding modes. No external provider is involved.

The focused selection passed **61 tests** (62 warnings, 59.69 seconds), including
the two new modules, existing order schema tests and the existing persisted coupon
regression. Configured Ruff checks on both new modules and syntax-critical checks
on the three runtime modules pass; this is not a repository-wide lint/type-clean claim.
The offline exporter succeeds without application .env credentials and still
reports 190 operations. Only coupon field descriptions changed in exported OpenAPI.

Full suite: **893 passed, 1 skipped, zero failures/errors; 87.26% coverage**
(8,338/9,555 statements), exit 0 in 884.63 seconds. The unchanged 85% gate passes.
There were 674 warnings, including existing deprecations; this is not a warning-free
claim. The inherited obsolete security module remains skipped; native financial,
concurrency, migration and Redis-worker tests ran. All five changed runtime/test
file fingerprints match the snapshot captured before the full run.

Saved evidence: [JUnit XML](audit/preship-checkpoint-9-tests-2026-10-17.xml) and
[coverage JSON](audit/preship-checkpoint-9-coverage-2026-10-17.json).

Full-run command, only against disposable local test services:

```powershell
$env:TEST_DATABASE_URL='postgresql+asyncpg://audit:local-audit-only@127.0.0.1:15432/wearhowz_preship_test'
$env:TEST_REDIS_URL='redis://127.0.0.1:16379/15'
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-9-tests-2026-10-17.xml --cov-report=json:docs/audit/preship-checkpoint-9-coverage-2026-10-17.json
```

These loopback-only services contain synthetic data and are separate from the
development Redis. Recreate disposable services before rerunning after cleanup.
Both labeled checkpoint 9 containers and their anonymous synthetic-data volumes
were removed after verification; absence was checked. Development `drip_redis`
remains healthy and unchanged. Removed data is reproducible from the test fixtures,
not retained as a backup.

## Still open / next

F16 is **partially repaired**, not closed. Next: slot response and notification/email
money precision, then canonical public links and error-envelope consistency.

This checkpoint does not certify every coupon/concurrency combination, historical
allocation repair, or zero-total orders with free shipping (the order constraint
still requires total > 0). The unused legacy apply helper's transaction/concurrency
contract is not expanded here. Native full-suite financial/worker checks are not
provider acceptance or evidence that every mixed-operation race is covered.

The wider audit still includes ownership/input coverage, static/type debt,
dependency reproducibility, consent/final retention and managed offboarding,
historical reconciliation, and provider/staging/deployment gates. Local passing
tests do not authorize production or certify a defect-free backend.
