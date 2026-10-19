# Backend pre-ship checkpoint 13: error-response contracts

18 October 2026. Backend only. The 162-item audit remains **IN PROGRESS**.
No frontend inspection/change, real provider call, production mutation, deployment,
commit or push. Local secrets and deployment configuration were not read or changed.

## Repairs and client compatibility

Direct FastAPI/Starlette HTTP exceptions, including router 404/405 errors, now use
the existing application error envelope instead of a top-level `detail` property:

```json
{"error":{"code":"NOT_FOUND","message":"Not Found","request_id":"example-id"}}
```

Clients consuming `detail` for these responses must switch to `error.message` and
`error.code`. Validation retains `error.fields` (field-location to message mapping).
Existing domain-specific error codes, messages, fields and HTTP statuses remain.
Optional fields are omitted when absent; normal application requests carry the
request ID in both the JSON and `X-Request-ID`. Success bodies are unchanged.

| HTTP status | Direct HTTP exception code |
|---|---|
| 400 / 401 / 403 | BAD_REQUEST / UNAUTHORIZED / FORBIDDEN |
| 404 / 405 / 409 | NOT_FOUND / METHOD_NOT_ALLOWED / CONFLICT |
| 413 / 415 / 422 | PAYLOAD_TOO_LARGE / UNSUPPORTED_MEDIA_TYPE / VALIDATION_ERROR |
| 429 / 500 | RATE_LIMITED / INTERNAL_ERROR |
| 502 / 503 / 504 | EXTERNAL_SERVICE_ERROR / SERVICE_UNAVAILABLE / GATEWAY_TIMEOUT |

Other explicit HTTP statuses use `HTTP_<status>`. Domain exceptions keep their
existing more-specific codes, rather than being remapped solely by HTTP status.
String 4xx explanations remain public; arbitrary structured exception details are
not serialized. Direct HTTP 5xx and unexpected failures use generic messages,
never internal exception text. Validation does not serialize raw input or context.
This is not an exhaustive audit of every existing domain-message call site.

All shared application error responses now use `Cache-Control: no-store`.
`Allow`, `WWW-Authenticate`, `Retry-After` and rate-limit metadata are preserved
when supplied; no auth policy, rate-limit thresholds or Redis outage policy changed.
Application errors do not become successful responses and callbacks still reject
the same unauthorized/malformed/oversized input before payment handling.

An inner ASGI error boundary converts unexpected route/inner-middleware failures
before request-ID, security-header and CORS wrappers finish. Allowed browser origins
therefore receive the normal headers on these 500 responses. Disallowed origins
remain disallowed. The existing privacy-aware structured exception event is retained.
Cancellation and non-HTTP scopes propagate normally. After response headers have
been sent, streaming/background failures propagate instead of sending a second body.

OpenAPI uses the existing `ErrorResponse` schema for common error statuses,
including 422 instead of FastAPI's default validation-error shape. The degraded
health response explicitly retains `HealthResponse` for 503. No migration, endpoint
rename or permission change is introduced.

## Deliberate boundaries

- Health readiness returns its dependency-status body, not the generic error body.
- CORS preflight retains Starlette's protocol responses, including plain-text 400
  rejection. It is outside the application JSON-error contract.
- Bodyless HTTP statuses stay bodyless. Proxy/server-generated failures and errors
  in the outer request-ID/security/CORS wrappers are not guaranteed this full header
  contract. The global generic exception handler remains as a fallback.
- Post-start streaming errors, background-task failures, worker errors, transport
  disconnects and startup failures cannot be converted into a replacement HTTP body.
- No new live monitoring/alert delivery, provider acceptance or universal input/log
  privacy certification is claimed. API responses never prove provider readiness.

## Verification

Initial regression run: all 20 new cases failed against the old implementation.
Those cases passed after the repair. The final expanded unit run passed 38 cases
(68 warnings, 29.17 seconds); the native error-flow and existing log-privacy run
passed 13 cases (24 warnings, 24.64 seconds). Together these are **51 focused checks**,
including **46 new cases** (38 unit and eight native).

Configured Ruff passes for the new helper and both new test modules. Syntax-critical
checks pass for main, middleware and health. This is not a whole-repository lint or
type-cleanliness claim. Offline export regenerated OpenAPI with the new error schemas;
the endpoint inventory remains unchanged at 190 operations. The test-mode export
documents 187 operations: health and the two PayFast callback methods remain hidden
from the public schema. `HTTPValidationError` is no longer generated. Migration head
remains 020.

Full-suite verification passed **1,075 tests, 1 skipped, 87.96% coverage** against
disposable loopback-only PostgreSQL 16 and Redis 7 with synthetic credentials
(750 warnings, 1,908.70 seconds). The unchanged **85% coverage gate passes**.
Exact coverage is 8,506/9,670 statements, 87.96277145811789%. Saved XML contains
1,076 cases, zero failures/errors and the inherited skipped legacy security module
`tests.security.test_auth`. All 46 new cases and all four real Redis-worker tests ran.
SHA-256 fingerprints for all
17 changed runtime/test files across checkpoints 12–13 matched before/after the run.

Evidence:

- `docs/audit/preship-checkpoint-13-tests-2026-10-18.xml`
- `docs/audit/preship-checkpoint-13-coverage-2026-10-18.json`

Full-suite command, with TEST_DATABASE_URL and TEST_REDIS_URL pointing only to the
isolated synthetic services:

```powershell
.\.venv\Scripts\python.exe -m pytest --disable-warnings --show-capture=no --junitxml=docs/audit/preship-checkpoint-13-tests-2026-10-18.xml --cov-report=json:docs/audit/preship-checkpoint-13-coverage-2026-10-18.json
```

New tests cover explicit HTTP and domain errors, router errors, validation,
unexpected/response-validation failures, request IDs, CORS, success/bodyless
responses, streaming/cancellation/scope handling and OpenAPI schemas. Native tests
exercise real authorization/resource dependencies and reject four callback variants
without calling payment handling or creating payment rows. Provider calls are mocked.

Both labeled checkpoint 13 containers and their anonymous synthetic-data volumes
were removed after verification; absence was checked. Development `drip_redis`
remains healthy and unchanged. Deleted test data can be regenerated from fixtures;
it was not retained as a backup. No provider was contacted or enabled, and no code
was staged, committed or pushed. Existing checkpoint 12 changes were preserved.

## Remaining work

F16 remains partially repaired: remaining legacy/untyped money shapes and duplicated
policy limits need review. Wider ownership/input coverage, mixed-operation races,
dependency reproducibility, static/type debt, final retention and managed offboarding,
historical reconciliation and live acceptance/deployment gates remain open. Prior
zero-total/free-shipping and historical-allocation limits are unchanged. Passing
local tests is not production approval or a defect-free guarantee.
