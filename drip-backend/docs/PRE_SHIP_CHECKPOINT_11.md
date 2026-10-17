# Backend pre-ship checkpoint 11: catalogue and wishlist price precision

17 October 2026. Backend only. The broader 162-item audit remains **IN PROGRESS**.
Earlier checkpoint 9/10 working-tree changes are preserved. No frontend inspection
or change, commit, push, provider call, production mutation or deployment.

## Repairs

- Product cards/details retain stored regular and sale prices; absent sale prices
  remain JSON null. Variant responses retain override prices or the existing
  effective-product-price fallback.
- Search suggestions retain the effective product price, seller product lists retain
  the regular price, and wishlist add/read responses retain regular and sale prices.
- Removed integer casts in these response paths. A shared response-only Decimal
  type validates finite, nonnegative, at-most-two-place amounts and serializes them
  as fixed two-decimal strings. It does not silently round invalid precision.
- No checkout, stock, ledger, pricing-precedence, authorization or pagination
  algorithm change. Product/variant price-entry requests still require whole PKR
  between 100 and 500,000; catalogue price filters remain whole-PKR boundaries.
  Fractional persisted prices are exercised using synthetic database fixtures, not
  by widening the seller's price-entry policy.

There is no migration; head remains 020. Existing no-slot message fixes are preserved.

## Intentional API compatibility change

The seven underlying money-field definitions below now serialize as strings in
**PKR major units**, not integer paisa. Whole amounts also return strings, e.g.
`"1500.00"`; fractional examples are `"1500.25"`, `"1200.75"`, `"1100.05"`.
Stock, counts and pagination numbers remain integers. Clients must adapt these
response types; no frontend code was inspected or edited.

| Response model | Changed fields |
|---|---|
| ProductCardResponse / inherited ProductDetailResponse | price, sale_price (nullable) |
| VariantWithStockResponse | price |
| SellerProductRowResponse | price |
| SearchSuggestion | price |
| WishlistItemResponse | price, sale_price (nullable) |

Affected operations (all paths prefixed `/api/v1`):

- GET `/products`, `/products/{product_id}`, `/products/slug/{slug}`,
  `/products/{product_id}/variants`, `/products/search/suggestions`.
- GET/POST `/seller/products`, GET/PUT `/seller/products/{product_id}`,
  POST `/seller/products/{product_id}/variants`,
  PATCH `/seller/products/{product_id}/variants/{variant_id}`.
- GET/POST `/customers/me/wishlist`.

The regenerated OpenAPI documents string/nullable-string response types; the
endpoint inventory remains 190 operations. Search/card prices remain product-level
prices, not a promise that every variant has that price; selected-variant responses,
cart and checkout use the variant override where present. Quotes do not reserve
prices: checkout still revalidates the current price and stock.

## Verification

Before repair, 13 native cases reproduced truncated catalogue/variant/seller values.
Two wishlist cases initially used an incorrect test URL; after correcting it to
the existing `/customers/me/wishlist` route, both reproduced truncation as well.
An initial combined collection found duplicate test module basenames; the new unit
module was renamed before verification. Neither issue required runtime changes.

There are **35 new cases**: 15 native cases in
`tests/integration/test_catalogue_money.py` and 20 unit/schema cases in
`tests/unit/test_catalogue_money_schema.py`. They cover:

- Public/seller response prices, unchanged stored values and nullable sales.
- Wishlist deduplication, cross-account isolation and hidden-product exclusion.
- Regular/sale/override prices matching guest quotes, account carts and persisted
  COD checkout amounts; unit prices and quantity multiplication retain paisa.
- Fractional ascending/descending cursor ordering with equal-price UUID ties,
  whole-rupee filter boundaries, no duplicated/missing rows, and terminal cursors.
- Seller metadata updates preserving prices, whole-rupee override updates and
  clearing overrides back to the existing fractional sale price.
- Decimal Python values, fixed JSON strings, invalid/non-finite/excess-precision
  rejection, response OpenAPI types and unchanged request limits.

The final focused run passed **60 tests** (54 deselected, 38 warnings, 37.42 seconds),
including the new modules and selected existing product/ownership regressions.

The full suite passed **977 tests, 1 skipped, 87.55% coverage** (694 warnings,
780.07 seconds), with the unchanged **85%** gate passing. Exact coverage is
8,391/9,584 statements, 87.55217028380635%. Saved XML has 978 cases, zero failures,
zero errors and one inherited skipped legacy security module (`tests.security.test_auth`).
All four real Redis worker cases ran; the new modules contributed 15 and 20 cases.

Evidence:

- `docs/audit/preship-checkpoint-11-tests-2026-10-17.xml`
- `docs/audit/preship-checkpoint-11-coverage-2026-10-17.json`

Full-suite command (synthetic local service URLs supplied through TEST_DATABASE_URL
and TEST_REDIS_URL, never development credentials):

```powershell
.\.venv\Scripts\python.exe -m pytest --disable-warnings --junitxml=docs/audit/preship-checkpoint-11-tests-2026-10-17.xml --cov-report=json:docs/audit/preship-checkpoint-11-coverage-2026-10-17.json
```

Configured Ruff passed for the new helper/tests; syntax-critical Ruff checks passed
for the four changed existing runtime files. This is not a repository-wide lint/type
cleanliness claim. Offline contract export succeeded with 190 operations; all six
affected response schemas, including the inherited detail schema, expose string
prices and nullable-string sales where applicable. SHA-256 fingerprints for the
five affected runtime files and two new test modules matched before/after the run.

Both labeled checkpoint 11 containers and their two anonymous synthetic-data volumes
were removed after verification; absence was checked. Development `drip_redis`
remains healthy and unchanged. Removed data is reproducible from test fixtures,
not retained as a backup. No production or development database was used.

## Remaining boundaries

F16 is **partially repaired**, not closed. Next: canonical public-link/callback
configuration, then error-envelope consolidation. Remaining legacy/untyped money
contracts and pricing-policy consistency still need review; this checkpoint does
not certify every money-bearing shape. It does not enable fractional price entry,
retroactively reprice orders or repair corrupted/unsupported historical prices.

Broader ownership/input checks, mixed-operation races, dependency reproducibility,
static/type debt, final consent/retention and managed offboarding, historical
reconciliation, provider acceptance and staging/deployment gates remain open.
Checkpoint 9's historical allocation and zero-total/free-shipping boundaries remain.
Passing local tests is not production approval or a defect-free guarantee.
