# Backend pre-ship checklist audit

Source: user-supplied `pre-ship-backend.html`; audit started 2026-10-13.

Inventory: **162 items across 18 sections**. No checklist requirement is silently omitted.

## Status and scope

**IN PROGRESS — not a production-readiness sign-off.** Backend only. The original HTML and frontend are unchanged. Its browser checkboxes are not evidence of backend verification.

Every source item is retained below with a stable identifier. `Unverified` means no complete evidence has been established in this audit; it does not by itself mean the implementation is broken. Prior B1–B4 reports remain historical evidence, not a substitute for rerunning checks after changes. `External` requires deployment/provider access or an owner decision, not merely source changes.

## Execution order

1. Request/security boundaries: proxy trust, rate limits, validation, authorization and lifecycle deletion.
2. Data/money: authoritative payment verification, retention, stock/moderation behavior, migrated-schema parity and native races.
3. Worker/integration reliability: retries, delivery recovery, suppression, startup/shutdown and monitoring.
4. Release checks: dependency/static/type analysis, full native PostgreSQL/Redis tests, unchanged 85% coverage gate, API/schema checks and contract export.
5. Handoff: current architecture/configuration/operations documentation, reproducible packaging and explicit external sign-off checklist.

No live charges, real customer emails, production deletion, deployment, secret rotation or acceptance of launch blockers is authorized by this audit. These need a separate approved scope.

## Verified change notes

Latest: [checkpoint 11](PRE_SHIP_CHECKPOINT_11.md), 17 October 2026 — **977 passed,
1 skipped; 87.55% coverage** with native PostgreSQL/Redis enabled. Catalogue/wishlist
responses preserve paisa as two-decimal strings; whole-PKR entry/filter policy is
unchanged. 35 new native/unit cases cover response types, variant/checkout agreement,
cursor precision, seller edits and wishlist isolation. Checkpoint 10's slot/notification
presentation and checkpoints 8/9's analytics/coupon precision remain passing.
Bulk-stock transaction, seller isolation and inventory-health repairs remain in place.
Earlier email privacy, durable cleanup and notification recovery remain in place.
Migration head remains 020; contract remains 190 operations.
Final retention/offboarding, exhaustive ownership/input coverage and other unverified
checklist items remain open. [Checkpoint 10](PRE_SHIP_CHECKPOINT_10.md) and earlier
reports remain historical evidence, not the latest verification.

These are repair checkpoints, **not a completed A–Z review**. New code fixes
have focused evidence; untouched checklist rows intentionally remain unverified.

- Shared client-IP resolver ignores forwarding headers from untrusted socket peers and walks trusted proxy chains right-to-left. Docker disables Uvicorn proxy rewriting. `TRUSTED_PROXY_IPS` defaults to no trust; the existing PayFast-specific override remains supported.
- Rate-limit buckets use rule scope rather than resource IDs; counter increments and initial expiration run in one Redis transaction. Remaining-count header corrected. Redis outage policy is still fail-open and needs risk review.
- Catalogue cursors reject invalid JSON shape/types, invalid decimals/non-finite values, oversized data and timezone-less timestamps before executing SQL.
- Seller suspension now relies on seller visibility checks instead of overwriting product moderation. Reinstatement preserves independently hidden products. Legacy product flags remain conservative: prior suspension-hidden products cannot safely be distinguished from independently moderated products and require manual review.
- Lifespan uses an exit stack so both pools are closed after partial startup, shutdown errors or application exceptions. Sentry is now a declared/pinned runtime dependency; its configuration disables local-variable and request-body capture. Real alert delivery and complete PII redaction are not verified.
- Verification: **662 passed, 1 skipped; 85.78% coverage**, native PostgreSQL 16 and Redis 7. The 85% gate is unchanged. See [checkpoint report](PRE_SHIP_CHECKPOINT_1.md). Passing tests do not establish the whole checklist.

Proxy trust reference: [MDN X-Forwarded-For security guidance](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For). Production ingress must preserve the socket peer and append/replace forwarding headers; never configure arbitrary internet CIDRs as trusted.

## 1. Authentication and sessions

| ID | Requirement | Status / evidence |
|---|---|---|
| 1.1 | **BLOCKER:** Passwords hashed with a vetted algorithm (argon2, bcrypt, scrypt); no home-rolled crypto | Static evidence — `app/core/security.py` uses argon2-cffi PasswordHasher (time 3, memory 65536 KiB, parallelism 4). Final independent security sign-off is still required. |
| 1.2 | **BLOCKER:** Tokens signed with a strong key; algorithm pinned on decode | Partial — decode pins the configured server-side algorithm and validates issuer/audience/expiry. Production key strength/provisioning and boot-time algorithm/key validation still require evidence. No real key was read. |
| 1.3 | Access tokens short-lived; refresh tokens rotate and can be revoked | Unverified — review and evidence pending. |
| 1.4 | **BLOCKER:** Logout and password change invalidate existing sessions or refresh tokens | Unverified — review and evidence pending. |
| 1.5 | Token storage is safe: httpOnly secure cookies or equivalent, not long-lived secrets in localStorage | Backend evidence — refresh cookie is HttpOnly, SameSite strict, Secure in production and auth-path scoped. Frontend token storage is deliberately outside this backend-only audit. |
| 1.6 | Login, signup, password reset and OTP endpoints rate-limited | Unverified — review and evidence pending. |
| 1.7 | Brute-force and credential-stuffing protection (lockout or backoff) | Unverified — review and evidence pending. |
| 1.8 | No account enumeration: same response for unknown user and wrong password | Unverified — review and evidence pending. |
| 1.9 | Password reset tokens are single-use, expiring and unguessable | Unverified — review and evidence pending. |
| 1.10 | Email verification and change-email flows require re-authentication | Unverified — review and evidence pending. |
| 1.11 | MFA available for admin accounts | Unverified — review and evidence pending. |
| 1.12 | Default, demo and test accounts removed in production | External — configuration, runtime evidence or owner sign-off required. |

## 2. Authorization and access control

| ID | Requirement | Status / evidence |
|---|---|---|
| 2.1 | **BLOCKER:** Every route has an explicit auth dependency; intentionally public routes are listed and commented | Locally verified — independent policy classifies all 190 operations; 28 public and 8 capability-checked exceptions are explicitly enumerated. All 154 protected operations have the expected dependency, including onboarding seller identity and admin-only 2FA. |
| 2.2 | **BLOCKER:** Ownership checks on every resource read, update and delete (IDOR tested) | Partial — checkpoint 4 adds 43 cross-resource requests and owner/list/account-isolation scenarios. Checkpoint 6 adds real two-seller aggregate/low-stock tests, including forged seller-ID claims and foreign filters. Exhaustive per-operation/input and bulk-mutation coverage remains open. |
| 2.3 | **BLOCKER:** Role and permission checks run on the server; role comes from the database, not the token body | Shared dependency evidence — `get_current_user_payload` loads User and rejects deleted/unverified users, role mismatch and auth-version mismatch before role dependencies authorize. Per-route wiring/matrix coverage remains separate (2.1/11.1). |
| 2.4 | **BLOCKER:** Multi-tenant or multi-vendor queries scoped by the authenticated identity, never by request body or path alone | Partial — cross-seller product/inventory/order/return/bank/wallet tests and forged seller-ID claim tests pass. Remaining aggregate/bulk combinations still need independent review. |
| 2.5 | Admin routes require admin and are tested with a non-admin | Locally verified — HTTP matrix rejects customer/seller access to all 67 admin operations, including payment/admin routes outside the admin URL prefix. |
| 2.6 | Mass assignment blocked: clients cannot set role, price, owner or balance fields | Partial — checkpoint 7 proves admin bulk stock rejects reserved, reorder_point, seller_id and unknown batch fields before writes. Other request models and privileged fields still need exhaustive review. |
| 2.7 | List and bulk endpoints filter by ownership, not just single-record endpoints | Partial — checkpoint 4 covers private lists, mark-all and account-scoped cart operations. Checkpoint 6 covers all four seller analytics routes, low-stock lists, foreign product/SKU/name filters and inventory pagination with distinct two-seller records. Checkpoint 7 proves admin-only bulk-stock corrections may span two sellers while non-admin requests cannot mutate stock. Other bulk mutations/input combinations are not signed off. |
| 2.8 | Object IDs are unguessable or every access is authorization-checked | Unverified — review and evidence pending. |
| 2.9 | Privileged actions (refunds, payouts, role changes) have extra checks and are audit-logged | Unverified — review and evidence pending. |
| 2.10 | Internal and service-to-service endpoints are not publicly exposed | Unverified — review and evidence pending. |

## 3. API design and input handling

| ID | Requirement | Status / evidence |
|---|---|---|
| 3.1 | **BLOCKER:** All input validated on the server with schemas: types, ranges, lengths, enums | Partial — checkpoint 7 adds native bulk-stock evidence for unique IDs, 1-500 rows, stock 0-999999, malformed/fractional input and forbidden fields. Invalid HTTP/service batches perform no writes. This does not certify all input schemas. |
| 3.2 | Consistent error format; no stack traces or internals in responses | Unverified — review and evidence pending. |
| 3.3 | Correct status codes (401, 403, 404); no 500s on bad input | Partial — Cursor error handling repaired; other routes still need negative-input coverage. |
| 3.4 | Pagination, filtering and sorting limits enforced server-side | Partial — Cursor size/type validation repaired; review all endpoint bounds. |
| 3.5 | Request body size limits and timeouts set | Unverified — review and evidence pending. |
| 3.6 | Idempotency keys on create and payment endpoints that clients may retry | Unverified — review and evidence pending. |
| 3.7 | API versioned, with a deprecation approach | Unverified — review and evidence pending. |
| 3.8 | OpenAPI or equivalent docs generated and accurate | Unverified — review and evidence pending. |
| 3.9 | API fuzzed or schema-tested against the spec | Unverified — review and evidence pending. |
| 3.10 | File uploads: type, size and content checks, private storage, random names | Unverified — review and evidence pending. |
| 3.11 | Open redirect and SSRF checked on any endpoint that takes a URL | Unverified — review and evidence pending. |
| 3.12 | User input is never returned as unescaped HTML | Unverified — review and evidence pending. |

## 4. Database and migrations

| ID | Requirement | Status / evidence |
|---|---|---|
| 4.1 | **BLOCKER:** Migrations run from an empty database to the current schema without errors | Unverified — review and evidence pending. |
| 4.2 | **BLOCKER:** Models and migrations agree (schema drift check passes) | Locally verified — full 42-table comparison covers columns/types/nullability/defaults, indexes, unique/FK constraints plus explicit PostgreSQL checks, enum labels/order and primary keys. Models preserve existing legacy columns/defaults; revisions 019–020 add reviewed recovery fields and missing indexes/checks. |
| 4.3 | Rollback or forward-fix plan for each risky migration | Unverified — review and evidence pending. |
| 4.4 | Constraints in the database: foreign keys, unique, not null, checks | Unverified — review and evidence pending. |
| 4.5 | Indexes on foreign keys and frequently filtered columns | Unverified — review and evidence pending. |
| 4.6 | No N+1 queries on list endpoints | Unverified — review and evidence pending. |
| 4.7 | Multi-step writes wrapped in transactions; isolation level considered | Partial — checkpoint 7 reproduces and repairs false bulk-stock success after PostgreSQL transaction abortion. Row savepoints retain valid updates; fatal errors roll back the batch. Native reservation and overlapping-batch races pass; broader mixed-operation transaction review remains open. |
| 4.8 | Row-level security enabled wherever the database is reachable from clients (for example Supabase REST) | External — configuration, runtime evidence or owner sign-off required. |
| 4.9 | Connection pooling configured; pool size matches host limits | External — configuration, runtime evidence or owner sign-off required. |
| 4.10 | App uses a least-privilege database user; no superuser in production | External — configuration, runtime evidence or owner sign-off required. |
| 4.11 | Sensitive columns (tokens, IDs, personal data) encrypted or hashed where appropriate | Unverified — review and evidence pending. |
| 4.12 | Seed and test data absent from production | External — configuration, runtime evidence or owner sign-off required. |
| 4.13 | Soft-delete versus hard-delete behavior defined and consistent | Unverified — review and evidence pending. |

## 5. Data privacy and compliance

| ID | Requirement | Status / evidence |
|---|---|---|
| 5.1 | **BLOCKER:** Deletion requests delete or anonymize across all tables, third parties and backup policy | Partial — approved cleanup preserves financial/dispute records and durably retries cache/safe-image deletion. Checkpoint 5 adds send-time suppression for legacy email jobs, deletion/delivery races and zero new ARQ result retention. See CUSTOMER_PRIVACY.md. Pending/old queue payloads, backup/provider retention, final expiry rules, consent versions and managed offboarding remain open. |
| 5.2 | Data export process exists if your markets require it | External — configuration, runtime evidence or owner sign-off required. |
| 5.3 | Retention periods enforced by jobs; old logs and data expire | Unverified — review and evidence pending. |
| 5.4 | Consent records stored: what, when, policy version | Gap — no consent/policy-version persistence found in models/schemas/services. Define applicable consent and policy versions with the owner; notification toggles alone are not versioned consent. |
| 5.5 | Only necessary personal data is collected and stored | Unverified — review and evidence pending. |
| 5.6 | No tokens, passwords, card or personal data in logs or error reports | Partial — recursive metadata redaction, safe traceback coordinates and outbound Sentry scrubbing implemented with regression tests. Complete call-site review and real monitoring acceptance remain. |
| 5.7 | Sensitive documents in private storage with signed, expiring URLs | Unverified — review and evidence pending. |
| 5.8 | Data processors listed (hosting, email, payments, analytics) and their terms checked | External — configuration, runtime evidence or owner sign-off required. |
| 5.9 | Access to production data is restricted and audited | External — configuration, runtime evidence or owner sign-off required. |

## 6. Payments and money logic

| ID | Requirement | Status / evidence |
|---|---|---|
| 6.1 | **BLOCKER:** Prices, discounts and totals computed server-side only | Unverified — review and evidence pending. |
| 6.2 | Money stored as integers in minor units with defined rounding | Project uses exact Decimal/PostgreSQL NUMERIC in PKR major units, not integer storage. Checkpoints 8/9 repair analytics and coupon precision. Checkpoint 10 repairs slot response types and notification/email presentation. Checkpoint 11 repairs catalogue/wishlist price responses. Whole-PKR entry/settings and accounting are unchanged. Remaining legacy/untyped money contracts and wider F16 remain open; no financial-schema conversion was made to match generic checklist wording. |
| 6.3 | **BLOCKER:** Webhooks verify the signature or hash and process each event exactly once | Unverified — review and evidence pending. |
| 6.4 | Callback amount, currency and status checked against your own records | Locally verified — success callback requires authenticated status lookup; reconciliation requires explicit consistent amount/currency plus matching basket/transaction/order total. Native tests cover rejection, retry, replay and concurrency. Keep PayFast disabled pending merchant UAT/response mapping. |
| 6.5 | Order and payment state machine defined; invalid transitions rejected | Unverified — review and evidence pending. |
| 6.6 | Wallet, balance and payout changes use a transaction with row locking; balance never negative | Unverified — review and evidence pending. |
| 6.7 | Concurrent requests cannot double-spend, double-credit or oversell stock | Unverified — review and evidence pending. |
| 6.8 | Commission and fee calculations tested with edge cases and rounding | Unverified — review and evidence pending. |
| 6.9 | Refund total cannot exceed amount paid; partial refunds handled | Unverified — review and evidence pending. |
| 6.10 | Failed, pending and timed-out payments reconciled by a job | Unverified — review and evidence pending. |
| 6.11 | Test and live keys separated per environment; live keys never in dev | Unverified — review and evidence pending. |
| 6.12 | Payment provider onboarding requirements met | External — configuration, runtime evidence or owner sign-off required. |
| 6.13 | Receipts, invoices and financial records retained as required | External — configuration, runtime evidence or owner sign-off required. |

## 7. Webhooks and integrations

| ID | Requirement | Status / evidence |
|---|---|---|
| 7.1 | Timeouts, retries with backoff and circuit breaking on every outbound call | Unverified — review and evidence pending. |
| 7.2 | Outbound calls never block request threads indefinitely | Unverified — review and evidence pending. |
| 7.3 | Inbound webhooks acknowledge fast and process asynchronously | Unverified — review and evidence pending. |
| 7.4 | Replay protection: timestamp tolerance and event ID dedupe | Unverified — review and evidence pending. |
| 7.5 | Behavior defined when a third party is down (payment, email, storage, SMS) | Unverified — review and evidence pending. |
| 7.6 | Integration API keys scoped to least privilege and rotatable | External — configuration, runtime evidence or owner sign-off required. |
| 7.7 | Sandbox and production endpoints configured per environment | Unverified — review and evidence pending. |

## 8. Background jobs and email

| ID | Requirement | Status / evidence |
|---|---|---|
| 8.1 | Jobs are idempotent and safe to retry | Unverified — review and evidence pending. |
| 8.2 | Failed jobs go to a dead-letter queue and raise an alert | Partial — checkpoint 3 implements stale/lost-job recovery, retained bounded dead letters, audited admin replay and structured error events; checkpoint 4 reuses it for privacy cleanup. Actual alert delivery and unrelated legacy job paths still need staging/review evidence. |
| 8.3 | Scheduled jobs run exactly once across multiple instances | Unverified — review and evidence pending. |
| 8.4 | Long tasks moved off the request path | Unverified — review and evidence pending. |
| 8.5 | **BLOCKER:** Unsubscribes and suppression lists are honored by the sender | Partial — current/legacy order-update email preferences and deleted-account suppression have native DB tests, including legacy shipping/COD jobs in checkpoint 5. Mandatory auth/order-confirmation policy is unchanged. Provider bounce/complaint suppression and complete sender/consent acceptance remain external/open. |
| 8.6 | SPF, DKIM and DMARC set; bounces and complaints handled | External — configuration, runtime evidence or owner sign-off required. |
| 8.7 | Transactional emails (signup, reset, receipt) tested end to end | External — configuration, runtime evidence or owner sign-off required. |

## 9. Security hardening

| ID | Requirement | Status / evidence |
|---|---|---|
| 9.1 | **BLOCKER:** No secrets in git history, images, logs or client responses | Unverified — review and evidence pending. |
| 9.2 | CORS limited to real origins; no wildcard with credentials | Unverified — review and evidence pending. |
| 9.3 | HTTPS enforced; security headers set on responses | Unverified — review and evidence pending. |
| 9.4 | Rate limiting on expensive or sensitive endpoints | Partial — Proxy spoofing and per-resource bucket bypass repaired; expensive endpoint limits and outage behavior remain. |
| 9.5 | Dependencies scanned for known vulnerabilities; lockfile committed | Partial — upgraded installed environment reports zero known vulnerabilities in `audit/preship2-dependency-audit-2026-10-14.json`; python-jose/ecdsa replaced by PyJWT. Complete transitive lock and clean Linux build verification remain. |
| 9.6 | Static analysis (SAST) has no high findings | Unverified — review and evidence pending. |
| 9.7 | Container runs as non-root on a minimal base image | Unverified — review and evidence pending. |
| 9.8 | Debug mode, interactive docs and admin tools disabled or protected in production | Unverified — review and evidence pending. |
| 9.9 | Dev-only routes, test endpoints and verbose errors removed | Unverified — review and evidence pending. |
| 9.10 | Secrets rotation plan exists; leaked-key response documented | External — configuration, runtime evidence or owner sign-off required. |
| 9.11 | CSRF handled if cookie-based auth is used | Unverified — review and evidence pending. |
| 9.12 | Vulnerability-report contact published | External — configuration, runtime evidence or owner sign-off required. |

## 10. Vibe-code failure modes

| ID | Requirement | Status / evidence |
|---|---|---|
| 10.1 | Every dependency exists on the registry and is the intended package | Unverified — review and evidence pending. |
| 10.2 | No stubs: mock data, fake delays, hardcoded users, TODO endpoints | Unverified — review and evidence pending. |
| 10.3 | No empty except or catch blocks swallowing errors | Unverified — review and evidence pending. |
| 10.4 | No duplicate or conflicting helpers such as two auth utilities or two money helpers | Unverified — review and evidence pending. |
| 10.5 | No auth or validation that exists only in the frontend | Unverified — review and evidence pending. |
| 10.6 | Dead code, unused routes and unused dependencies removed | Unverified — review and evidence pending. |
| 10.7 | Hardcoded URLs, keys and localhost references removed | Unverified — review and evidence pending. |
| 10.8 | You can explain what each critical file does | External — configuration, runtime evidence or owner sign-off required. |

## 11. Testing

| ID | Requirement | Status / evidence |
|---|---|---|
| 11.1 | **BLOCKER:** Auth matrix tests per protected route: anonymous, other user, owner, admin | Partial — all protected operations have identity/role-denial tests. Checkpoints 4 and 6 add real cross-account resource/nested-ID/list/wallet/aggregate/filter cases and owner success checks. Exhaustive per-operation/input coverage remains open. The obsolete security module remains skipped; active native permission/ownership tests are not. |
| 11.2 | Integration tests run against a real database, not mocks | Unverified — review and evidence pending. |
| 11.3 | Tests assert intended behavior, not just current output | Unverified — review and evidence pending. |
| 11.4 | Property or invariant tests on money, balances and permissions | Unverified — review and evidence pending. |
| 11.5 | Concurrency tests: double submit, races, duplicate webhooks | Unverified — review and evidence pending. |
| 11.6 | Webhook tests: valid, tampered, replayed and out-of-order events | Unverified — review and evidence pending. |
| 11.7 | Migration tests from an empty database and from the previous release | Unverified — review and evidence pending. |
| 11.8 | Failure-injection tests: timeouts, database drop, provider errors | Unverified — review and evidence pending. |
| 11.9 | Mutation testing or bug seeding shows the tests catch real faults | Unverified — review and evidence pending. |
| 11.10 | Every fixed bug got a regression test | Unverified — review and evidence pending. |
| 11.11 | Coverage measured on critical modules, not just overall | Unverified — review and evidence pending. |

## 12. Performance and scalability

| ID | Requirement | Status / evidence |
|---|---|---|
| 12.1 | Load test of main endpoints at expected traffic | External — configuration, runtime evidence or owner sign-off required. |
| 12.2 | p95 latency and error-rate targets defined | External — configuration, runtime evidence or owner sign-off required. |
| 12.3 | Slow query log reviewed; heavy queries explained and indexed | External — configuration, runtime evidence or owner sign-off required. |
| 12.4 | Caching strategy defined (HTTP, Redis, CDN) with invalidation rules | Unverified — review and evidence pending. |
| 12.5 | Memory and connection leaks checked under sustained load | External — configuration, runtime evidence or owner sign-off required. |
| 12.6 | Large responses paginated or streamed | Unverified — review and evidence pending. |
| 12.7 | Safe to scale horizontally: no local state, sticky sessions or local file storage | Unverified — review and evidence pending. |

## 13. Reliability and error handling

| ID | Requirement | Status / evidence |
|---|---|---|
| 13.1 | Health and readiness endpoints reflect app and dependency state | Locally verified — `/health` returns 503 on either bounded DB/Redis probe failure, 200 when healthy; HTTP regression tests cover all four combinations and close the DB generator. Separate process-only liveness is not provided. |
| 13.2 | Global error handler returns safe errors and logs the details | Unverified — review and evidence pending. |
| 13.3 | Graceful shutdown finishes in-flight requests and jobs | Partial — connection cleanup tested on startup/application/shutdown failures; real in-flight request/job draining and deployment behavior remain unverified. |
| 13.4 | Timeouts on every external call and database query | Unverified — review and evidence pending. |
| 13.5 | **BLOCKER:** Backups enabled and a restore actually tested | External — configuration, runtime evidence or owner sign-off required. |
| 13.6 | Recovery targets (RPO and RTO) written down | External — configuration, runtime evidence or owner sign-off required. |
| 13.7 | Retries are bounded; no retry storms | Unverified — review and evidence pending. |
| 13.8 | Feature flags or kill switches for risky features | Static evidence — PayFast and destructive Supabase orphan cleanup default to disabled. Verify operational toggling and any other necessary kill switches in staging. |

## 14. Configuration and secrets

| ID | Requirement | Status / evidence |
|---|---|---|
| 14.1 | **BLOCKER:** Environment variables validated at boot; the app refuses to start if one is missing | Unverified — review and evidence pending. |
| 14.2 | Separate config and credentials for dev, staging and production | External — configuration, runtime evidence or owner sign-off required. |
| 14.3 | Secrets live in the host's secret manager, not in files | External — configuration, runtime evidence or owner sign-off required. |
| 14.4 | .env.example is complete and holds no real values | Unverified — review and evidence pending. |
| 14.5 | Each variable documented: purpose, example, required or optional | Unverified — review and evidence pending. |
| 14.6 | Timezone, locale and currency set explicitly; UTC in storage | Unverified — review and evidence pending. |

## 15. Deployment and CI/CD

| ID | Requirement | Status / evidence |
|---|---|---|
| 15.1 | CI runs lint, types, tests and security scans on every PR | Unverified — review and evidence pending. |
| 15.2 | Build is reproducible from a clean checkout | Unverified — review and evidence pending. |
| 15.3 | Staging environment mirrors production | External — configuration, runtime evidence or owner sign-off required. |
| 15.4 | Migration ordering relative to the code release is defined | Unverified — review and evidence pending. |
| 15.5 | Zero-downtime deploy and a rehearsed rollback | External — configuration, runtime evidence or owner sign-off required. |
| 15.6 | Container image and runtime versions pinned | Unverified — review and evidence pending. |
| 15.7 | Production deploys require review; no direct pushes | External — configuration, runtime evidence or owner sign-off required. |
| 15.8 | Dependency updates automated with Renovate or Dependabot | Unverified — review and evidence pending. |

## 16. Observability and incident readiness

| ID | Requirement | Status / evidence |
|---|---|---|
| 16.1 | Error tracking installed and a deliberate test error arrived | External — configuration, runtime evidence or owner sign-off required. |
| 16.2 | Structured logs with request IDs | Partial — Client-IP trust repaired; request-ID validation and log redaction remain. |
| 16.3 | Metrics: request rate, errors, latency, queue depth, database pool | Unverified — review and evidence pending. |
| 16.4 | **BLOCKER:** Alerts reach a real phone or inbox: downtime, error spikes, failed jobs, failed payments | External — configuration, runtime evidence or owner sign-off required. |
| 16.5 | Audit log for admin, money and permission changes | Unverified — review and evidence pending. |
| 16.6 | Uptime check on the health endpoint from outside | External — configuration, runtime evidence or owner sign-off required. |
| 16.7 | Runbook: outage, bad deploy, leaked key, payment failure | Unverified — review and evidence pending. |
| 16.8 | A named owner watches errors for the first 48 hours after launch | External — configuration, runtime evidence or owner sign-off required. |

## 17. Docs and handover

| ID | Requirement | Status / evidence |
|---|---|---|
| 17.1 | API documentation current and published to the right audience | Unverified — review and evidence pending. |
| 17.2 | Architecture notes: components, data flow, third parties | Unverified — review and evidence pending. |
| 17.3 | README: setup, run, test and deploy in under 15 minutes | Unverified — review and evidence pending. |
| 17.4 | Code map (such as an ATLAS file) generated and current | Unverified — review and evidence pending. |
| 17.5 | Known limitations and unverified areas written down | Unverified — review and evidence pending. |

## 18. Final backend sign-off

| ID | Requirement | Status / evidence |
|---|---|---|
| 18.1 | **BLOCKER:** Auth matrix passes with no unexpected access | Unverified — review and evidence pending. |
| 18.2 | **BLOCKER:** Payment flow tested end to end in the provider sandbox, then once with a real low-value transaction | External — configuration, runtime evidence or owner sign-off required. |
| 18.3 | **BLOCKER:** Restore from backup rehearsed on a clean environment | External — configuration, runtime evidence or owner sign-off required. |
| 18.4 | Production smoke test: signup, login, core action, deletion | External — configuration, runtime evidence or owner sign-off required. |
| 18.5 | Security review of auth, money and admin code by a second person | External — configuration, runtime evidence or owner sign-off required. |
| 18.6 | Every blocker above is done or consciously accepted in writing | External — configuration, runtime evidence or owner sign-off required. |

