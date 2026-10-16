# Backend repair batch 4 report

Completed 13 October 2026. Scope: post-review finding F09. Backend only; no frontend source, real message, provider configuration, live data, deployment, commit or push was included.

## Result

### Transactional dispatch

Revision 017 adds a notification outbox. Order placement and lifecycle changes, PayFast confirmation/reconciliation, COD verification/cancellation/expiry, payout approval/rejection/completion and seller approval/rejection now insert a deterministic event in the same database transaction as the business change. A registered once-per-minute ARQ job publishes committed rows with deterministic job IDs, records attempts/errors and retries Redis failures. Admin broadcasts use the same path.

The outbox removes the former database-commit/queue-publish gap. Published rows are retained as an audit trail. Replaying an event cannot create a second outbox row.

### Retry and local deduplication

Email-provider exceptions are no longer swallowed. A failed attempt updates one keyed `email_log` row, commits the failure evidence and raises into ARQ retry. Successful retries update that same row, and later replays return the saved receipt without calling the provider again. In-app rows use deterministic UUIDs, so task replay cannot create duplicate notifications.

This is local idempotency rather than a provider-level exactly-once claim. The installed Resend SDK exposes no idempotency-key option. A connection failure after provider acceptance but before the receipt is stored can still cause an external duplicate; staging delivery/reconciliation remains a pre-production gate.

### Canonical preferences and policy

The customer settings endpoints no longer store a second Redis hash. Both API surfaces read and update the same `notification_preferences` row, including new-arrival, SMS and WhatsApp channel fields.

- Order placement confirmation is required transactional delivery.
- Registered routine order email and in-app delivery honor `order_updates_email` and `order_updates_push`.
- Guest lifecycle email is required because the guest has no preference account.
- Seller payout in-app delivery honors `payout_notifications`.
- Seller application decisions are required transactional delivery.
- Promotion/new-arrival email, SMS and WhatsApp preferences are persisted, but this batch adds no such sender. Admin broadcasts remain in-app announcements.

### Safe email content and guest access

Product, variant, status and URL values interpolated into order email HTML are escaped. Guest order links include a fresh signed capability scoped to the exact order. The existing backend contract still expects that capability in `X-Guest-Token`; frontend work must capture it safely, avoid logging/referrer leakage and remove it from the visible URL.

## Files

Core implementation:

- `alembic/versions/017_notification_delivery.py`
- `app/models/notification.py`
- `app/repositories/notification_repo.py`
- `app/schemas/notification.py`
- `app/services/notification_outbox.py`
- `app/services/notification_service.py`
- `app/services/customer_service.py`
- `app/services/order_service.py`
- `app/services/payment_service.py`
- `app/services/admin_service.py`
- `app/services/wallet_service.py`
- `app/tasks/notification_tasks.py`
- `app/tasks/order_tasks.py`
- `app/tasks/worker.py`

Regression and handoff material:

- `tests/integration/test_b4_notifications.py`
- `tests/integration/test_release_journeys.py`
- `docs/BACKEND_REPAIR_QUEUE.md`
- `docs/audit/b4-verification-2026-10-13.json`
- `KNOWN_LIMITS.md`
- `README.md`

## Verification

- 4/4 new native B4 acceptance cases pass.
- The focused B4/notification regression set passes (75 tests).
- The complete marketplace regression module passes after the migration-verification database was reset to remove public-schema test contamination.
- Fresh migrations through revision 017 and a 017 → 016 → 017 round trip pass on disposable PostgreSQL.
- Final full suite: **621 passed, 1 skipped**.
- Coverage: **85.88%** (8,946 statements, 1,263 missed), so the unchanged 85% gate passes.
- Backend compile and patch-integrity checks pass. Full configured Ruff still has a large inherited backlog; this batch does not claim a clean repository-wide lint gate.

All PostgreSQL/Redis checks used named disposable local containers and synthetic data. Resend was mocked; no external message was sent. No frontend file was viewed or changed.

## Remaining backend work

F08 and F10-F17 remain open, along with the separate pre-production gates. The next code batch in the queue is security and account lifecycle (F10/F11), unless the user selects the PayFast code gap (F08) first.
