# Backend pre-ship checkpoint 18: trustworthy product HTTP tests

19 October 2026. Backend only; the 162-item audit remains **IN PROGRESS**.
No application code, frontend, production configuration, secrets, migration or live
provider changes. Earlier dirty work is preserved. Nothing staged, committed or pushed.

## Bounded repair

`tests/integration/test_product_api.py` previously built a separate router-only app
with a mocked database and suppressed server exceptions. Several assertions accepted
500, and validation tests made unauthenticated requests while accepting either 401
or 422. Its 18-test baseline passed; that did not establish the named behaviors.
This is a test-quality finding, not evidence that all allowed errors actually occurred.

The file now uses the shared application client, disposable native PostgreSQL rows,
real signed identities and application error handlers. Its 29 cases replace the 18
old cases (11 net additional cases, not 29 new independent scenarios):

- Empty/seeded catalogue payloads, exact price filtering and search suggestions.
- Missing product/variant 404 responses and seeded variant price/stock values.
- Eight protected route cases require exactly 401 and leave product, image, variant
  and inventory snapshots unchanged. Valid request bodies separate auth rejection
  from payload-validation failures.
- An active seller authenticates invalid-price/missing-field/status-filter requests;
  assertions require 422, VALIDATION_ERROR and the relevant error field names.
  Rejected requests leave the same table snapshots unchanged.
- Positive controls verify seller reads, successful persisted creation, valid status
  filters, and admin list/hide behavior with persisted visibility changes.

No broad acceptable-status lists, fake database fixture or module-level skip remain
in this product file. Without TEST_DATABASE_URL, its shared fixture skips explicitly;
that is not native verification. The separate obsolete security module remains
unconditionally skipped and was not modified in this checkpoint.

## Verification

| Run | Result | Evidence file under docs/audit |
|---|---|---|
| Historical mocked baseline | 18 passed; 25 warnings; 3.59s | preship-checkpoint-18-legacy-baseline-2026-10-19.xml |
| Rewritten product tests, native PostgreSQL | 29 passed; 24 warnings; 50.49s | preship-checkpoint-18-product-tests-2026-10-19.xml |
| All unit tests | 671 passed; 244 warnings; 70.94s | preship-checkpoint-18-unit-tests-2026-10-19.xml |
| Combined native regressions | 90 passed; 53 warnings; 186.61s | preship-checkpoint-18-native-tests-2026-10-19.xml |

The 29 rewritten cases are included in the 90-case run, not additional unique tests.
The combined run also covers catalogue money, image/price limits, admin product
reads, cross-account ownership and the protected-route permission matrix. All saved
XML files have zero failures/errors/skips. That does not imply the separately
skipped security module was run. No source edits occurred during final validation.

Configured Ruff passes for the rewritten file; backend `git diff --check` passes.
Offline export retains 190 operations. SHA-256 before/after comparisons confirm
OpenAPI and endpoint inventory are unchanged. No migration check was rerun; head
remains 020. No repository-wide lint/type or mutation-testing sign-off is claimed.

Native checks used only disposable loopback PostgreSQL 16 with synthetic fixtures;
Redis was fakeredis. No fresh native worker/Redis or external-provider validation.
The full suite was not rerun. Its latest historical baseline remains checkpoint 14:
**1,104 passed, 1 skipped, 87.96% coverage**. These scoped runs use --no-cov; the
configured 85% coverage gate is unchanged, with no new coverage measurement.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_product_api.py --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-18-product-tests-2026-10-19.xml
.\.venv\Scripts\python.exe -m pytest tests/unit --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-18-unit-tests-2026-10-19.xml
.\.venv\Scripts\python.exe -m pytest tests/integration/test_product_api.py tests/integration/test_catalogue_money.py tests/integration/test_catalogue_policy_flows.py tests/integration/test_admin_product_reads.py tests/integration/test_resource_ownership.py tests/integration/test_permission_matrix.py --no-cov --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-18-native-tests-2026-10-19.xml
```

Set TEST_DATABASE_URL only to a dedicated disposable database ending in `_test`.
The legacy-baseline artifact describes the old test version and is not recreated
by running the repaired file. After the session resumed, all saved result totals
were rechecked. The checkpoint container and anonymous volume are absent; only
reproducible synthetic data was removed. Development `drip_redis` is healthy and
was not modified by this checkpoint.

## Next and remaining boundaries

Next: repair `tests/security/test_auth.py` using explicit environment prerequisites
and real fixture-based checks instead of its unconditional skip and permissive
legacy assertions. Other API smoke files, seeded load journeys, dependency/static/
type work and broader F16/F17 review remain open. This product test repair does not
close exhaustive security coverage, final retention/offboarding, historical
reconciliation or external release acceptance. No backend-complete sign-off.
