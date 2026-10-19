# Backend pre-ship checkpoint 14: seller-order read contracts

Started 18 October 2026; results reviewed and handoff completed 19 October 2026.
Backend only. The 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, live provider calls, production changes, deployment,
commit or push. Local secrets and deployment configuration were not read or changed.

## Bounded repair

The live seller-order list/detail endpoints returned dictionaries, with only an
untyped object in OpenAPI. The old seller schemas were unused by these routes and
did not match the emitted payload: they required phantom fields such as net_amount,
payment_method and cod_verified and used integer-only money fields. Wiring those
old schemas directly would reject valid fractional order data or change the payload.

The existing schema names now describe the actual response, and both read routes
declare them as response models. The service still builds the same dictionaries;
there is no ledger, checkout, refund, fulfilment-transition or authorization change.
Unused placeholder imports were removed from the separate seller-profile router.

| Route | Response model | Exact PKR fields |
|---|---|---|
| GET /api/v1/seller/orders | PaginatedSellerOrders | data[].subtotal |
| GET /api/v1/seller/orders/{seller_order_id} | SellerOrderDetailResponse | subtotal, items[].unit_price, items[].subtotal |

The three underlying money fields use the existing `PKRResponseAmount` type:
non-negative finite Decimal values, at most two fractional places, serialized as
two-decimal JSON strings in PKR major units, not integer paisa. Invalid values are
rejected rather than silently truncated or rounded. Clients must consume the
documented strings; counts and quantities stay integers. This addresses an untyped
contract and stale schemas; it is not evidence that live seller-order amounts were
previously truncated to whole rupees by the service.

List rows retain id, order_id, order_number, status, subtotal, tracking_number,
courier_name, shipped_at, delivered_at and created_at. Details additionally retain
shipping_address and seller-scoped items. No new financial totals, commission,
customer-name or payment-status fields are inferred from the old placeholders.
Shipping address keys, nullable values and the existing missing-address fallback
are preserved. ISO datetime serialization preserves the service's offset spelling
(including +00:00 rather than Z). Pagination retains page/per_page/total/total_pages
and a page size of 25. Route paths, status filters and access dependencies are unchanged.

## Verification status

Before repair, eight of 17 new unit cases failed: existing live rows/details could
not validate against the old shapes, and OpenAPI had no usable response schema.
The final focused run passed **37 tests** (126 warnings, 95.74 seconds): 17 new
schema/contract unit cases, 12 new native seller-read cases and eight existing
cross-account ownership cases. The new cases cover two-brand fractional checkout
values, unchanged database snapshots, forbidden/missing IDs, anonymous/customer/admin
role rejection, empty/filter/invalid pages, 26-row pagination, tracking timestamps
and the missing-address fallback. No live provider is involved.

Configured Ruff passes for both new test files; syntax-critical checks pass for the
three modified runtime files. This is not repository-wide lint/type sign-off.
Offline contract export succeeds with 190 inventory operations (187 documented;
the existing hidden health/callback operations are unchanged). Migration head is
still 020; there are no migration changes.

The full suite passed **1,104 tests, 1 skipped, 87.96% coverage** on disposable
loopback-only PostgreSQL 16 and Redis 7. The unchanged **85% coverage gate passes**.
Saved XML records 1,105 cases, zero failures/errors and 1,801.408 seconds. The single
skip is the inherited `tests.security.test_auth` legacy module. All 29 new cases
and all four real Redis-worker cases ran. Exact coverage is 8,508/9,673 statements,
87.95616664943658%.

Evidence retains the run's original 18 October filenames:

- `docs/audit/preship-checkpoint-14-tests-2026-10-18.xml`
- `docs/audit/preship-checkpoint-14-coverage-2026-10-18.json`

```powershell
.\.venv\Scripts\python.exe -m pytest --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-14-tests-2026-10-18.xml --cov-report=json:docs/audit/preship-checkpoint-14-coverage-2026-10-18.json
```

TEST_DATABASE_URL and TEST_REDIS_URL targeted only isolated synthetic services.
The process finished before the session resumed on 19 October; the final totals
were checked directly in the saved XML and coverage JSON. No runtime/test source
edits were made during the full run. The in-memory pre-run fingerprint snapshot did
not survive the session restart, so an independent before/after hash match is not
claimed for this checkpoint.

After resuming on 19 October, all 17 seller-order contract unit cases passed again
(68 warnings, 12.44 seconds), and the targeted Ruff checks passed again. The current
three-file runtime diff was reviewed against this report. Both checkpoint 14
containers and their anonymous synthetic-data volumes were removed; absence was
verified. Development `drip_redis` remains healthy and was not modified. Deleted
test data is reproducible from fixtures, not retained as a backup. Earlier checkpoint
12/13 changes remain in the working tree; nothing was staged, committed or pushed.

## Remaining boundaries

This checkpoint does not add fields promised only by obsolete placeholder classes,
change the reporting basis of seller subtotals, expand seller access to another
brand's items or redefine customer/guest information needed for fulfilment.
Static follow-up classification: `/admin/products` still returns an untyped dict
containing product price; it is the next concrete response-contract target. Current
wallet/payout and admin seller-money schemas already use Decimal, not integer casts;
they are not newly certified here. The old `seller.RevenueDayRow` and
`RevenueAnalyticsResponse` integer shapes have no runtime callers in the inspected
backend; live analytics use the separate repaired analytics schemas. Dormant classes
should not be reported as proven active money truncation. Duplicated policy limits
also remain under F16. Wider ownership/input/race checks, dependency
reproducibility, static/type debt, final retention/offboarding, historical financial
reconciliation and staging/production acceptance remain open. No backend-complete
or defect-free guarantee follows from this repair.
