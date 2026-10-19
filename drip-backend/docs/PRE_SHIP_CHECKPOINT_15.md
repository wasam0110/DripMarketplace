# Backend pre-ship checkpoint 15: admin product read contract

19 October 2026. Backend only; the 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, live provider calls, production changes, secret reads,
commit, staging, push or deployment. Earlier uncommitted repairs are preserved.

## Bounded change

`GET /api/v1/admin/products` now declares `AdminProductsPage`. Its seven row fields
remain id, seller_id, name, price, slug, is_published and admin_hidden. Pagination
remains page/per_page/total, with page size 25; no total_pages field is invented.

Price uses the existing `PKRResponseAmount`: finite non-negative Decimal with at most
two fractional places, serialized as a two-decimal JSON string in PKR major units,
not integer paisa. Clients must consume this documented string representation.
It is the base product price, not sale price or variant/checkout effective pricing.
The service already returned Decimal; this repairs an untyped API contract, not a
proven service truncation bug. Invalid amounts are rejected, not silently rounded.

Only `app/schemas/product.py` and `app/api/v1/products.py` change runtime source.
Service queries, admin-only access, optional seller/hidden filters, inclusion of
drafts and hidden products, soft-delete exclusion and descending created_at/id
ordering are unchanged. Admin access intentionally spans sellers. No accounting,
price-entry policy, database or migration change; migration head remains 020.

## Verification

The new OpenAPI regression failed before implementation because the endpoint exposed
only an untyped object. After repair:

- **614 unit tests passed** (200 warnings, 43.19 seconds).
- **50 targeted tests passed** with disposable native PostgreSQL 16
  (67 warnings, 149.86 seconds): admin product reads, catalogue money, the route
  permission matrix and seller-order reads. Redis dependencies use test fakeredis;
  no fresh native Redis-worker validation is claimed.
- All **25 new cases** ran: 11 schema/contract cases and 14 native admin-read cases.
  They cover exact fractional prices, invalid money, empty results, field parity,
  seller/hidden filters, draft/hidden visibility, deleted-row exclusion, role denial,
  invalid query inputs and equal-timestamp 27-row pagination. Product snapshots
  remain unchanged across successful/denied reads.
- Configured Ruff passes on both new test files; syntax-critical checks pass on
  both runtime files. Backend `git diff --check` passes. Not repository-wide
  lint/type sign-off; existing warnings remain.
- Offline export succeeds: 190 inventory operations, unchanged endpoint inventory.
  OpenAPI now references the admin page/row/pagination schemas.

Evidence:

- `docs/audit/preship-checkpoint-15-unit-tests-2026-10-19.xml`
- `docs/audit/preship-checkpoint-15-native-tests-2026-10-19.xml`

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-15-unit-tests-2026-10-19.xml
.\.venv\Scripts\python.exe -m pytest tests/integration/test_admin_product_reads.py tests/integration/test_catalogue_money.py tests/integration/test_permission_matrix.py tests/integration/test_seller_order_reads.py --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-15-native-tests-2026-10-19.xml
.\.venv\Scripts\python.exe scripts/export_contract.py
```

The native command used TEST_DATABASE_URL targeting only the disposable loopback
PostgreSQL database with synthetic fixtures. No runtime/test source edits were made
during these runs. The full suite was not rerun for this two-file schema repair;
the latest full-suite baseline remains [checkpoint 14](PRE_SHIP_CHECKPOINT_14.md):
**1,104 passed, 1 skipped, 87.96% coverage**. That is historical evidence, not a fresh
checkpoint-15 coverage result. The configured 85% coverage gate is unchanged.

The checkpoint's PostgreSQL container and anonymous volume were removed; their
absence was verified. Only disposable synthetic data was deleted and can be
recreated from fixtures. Development `drip_redis` remains healthy and untouched.

## Remaining work

Next bounded review: duplicated policy limits under F16. Broader contract/input/
ownership/race checks, dependency reproducibility, static/type debt, final retention
and managed offboarding, historical financial reconciliation and external release
acceptance remain open. This checkpoint is not backend-complete or production-ready
sign-off, nor an assurance that no defects remain.
