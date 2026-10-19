# Backend pre-ship checkpoint 17: shared catalogue/media limits

19 October 2026. Backend only. The 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, local secret reads, live provider calls, production
configuration changes, staging, commit, push or deployment. Earlier dirty work is preserved.

## Bounded consolidation

The inspected price, image-count and upload-byte values agreed, but were repeated
across request schemas, routes and services. This is drift prevention, not a claim
that those boundaries previously enforced different values.

`app/core/catalogue_policy.py` now defines four fixed constants:

- MIN_PRODUCT_PRICE = 100 and MAX_PRODUCT_PRICE = 500000, in PKR major units.
- MAX_IMAGES_PER_PRODUCT = 6.
- MAX_IMAGE_BYTES = 5 * 1024 * 1024 (5 MiB; existing messages retain "5 MB").

The product schema, product routes and product service share price/count constants.
ImageService and the admin banner route share the byte cap. The old
`image_service.MAX_FILE_SIZE` alias remains available; the product-service image-cap
name remains available through its import. Six runtime files are added/modified.

No new setting or policy is introduced. Whole-PKR price entry, optional fields,
sale-price relationship checks, zero catalogue minimum-price filter, six-image
reorder maximum, upload errors and HTTP statuses remain unchanged. Oversized product
images return 422; oversized banners return 413. Existing locks, ownership checks,
image conversion, primary-image handling and storage paths are untouched.

Model SQL constraints and historical migration 003 retain literal price bounds.
These persist independently in the database and must not silently follow a changed
Python constant. New tests assert parity with model constraints and exercise native
accept/reject boundaries. A future price-policy change needs migration review.
No migration was changed or rerun here; head remains 020.

## Verification

All 39 focused unit cases passed before the broader runs. Final results:

- **671 unit tests passed**, 244 warnings, 74.23 seconds.
- **53 targeted native tests passed**, 59 warnings, 120.55 seconds.
- **54 new cases**: 39 unit and 15 native. Unit checks cover six price fields,
  whole-PKR boundaries, sale/base relationship preservation, reorder sizes, the
  header/byte validation gate just below/at/above 5 MiB, compatibility aliases,
  SQL constraint values and OpenAPI bounds. The byte-gate tests alone do not claim
  that synthetic header-only data is a fully decodable image.
- Native checks cover upload batch/total caps before storage calls, five new images
  reaching six total, seventh-image rejection, reorder behavior, direct service
  enforcement, roles, oversized product/banner uploads, persisted price constraints
  and catalogue filters. Other selected tests cover catalogue money, admin reads,
  cross-account ownership (including foreign-image upload denial before storage)
  and the seller-product lifecycle.
- External storage upload/delete calls are mocked. Native checks use disposable
  loopback PostgreSQL 16 and synthetic rows; Redis uses fakeredis. No live storage
  or fresh native Redis-worker acceptance is claimed.
- Configured Ruff passes for the policy module and both new test files;
  syntax-critical checks pass for the five modified legacy runtime files.
  Backend `git diff --check` passes. Not repository-wide lint/type sign-off.
- Offline export succeeds with 190 operations. SHA-256 comparisons before/after
  export confirm **both OpenAPI and endpoint inventory are unchanged**.

Evidence:

- `docs/audit/preship-checkpoint-17-unit-tests-2026-10-19.xml`
- `docs/audit/preship-checkpoint-17-native-tests-2026-10-19.xml`

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-17-unit-tests-2026-10-19.xml
.\.venv\Scripts\python.exe -m pytest tests/integration/test_catalogue_policy_flows.py tests/integration/test_catalogue_money.py tests/integration/test_admin_product_reads.py tests/integration/test_resource_ownership.py tests/integration/test_release_journeys.py::test_seller_product_lifecycle_and_public_visibility --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-17-native-tests-2026-10-19.xml
.\.venv\Scripts\python.exe scripts/export_contract.py
```

The native command used TEST_DATABASE_URL pointing only to the disposable `_test`
database. Runtime/test source was not edited during the final runs. The full suite
was not rerun; its latest baseline remains checkpoint 14: **1,104 passed, 1 skipped,
87.96% coverage**. That is historical evidence, not a fresh coverage result.
The configured 85% gate is unchanged; the scoped runs explicitly use --no-cov.

## Remaining boundaries

The checkpoint PostgreSQL container and its anonymous volume were removed; absence
was verified. Only disposable synthetic data was deleted and can be recreated from
fixtures. Development `drip_redis` remains healthy and untouched.

Next: legacy smoke/security test-quality gaps under F17, especially tests that can
pass on 500 responses or authentication rejection without exercising the named rule.
F16 still requires broader helper/contract parity review. Upload concurrency,
decoder resource safety, partial-upload cleanup and external storage lifecycle were
not changed or newly certified. Dependency/static/type work, final retention and
managed offboarding, historical reconciliation and external release acceptance
remain open. This is not backend-complete or production-ready sign-off.
