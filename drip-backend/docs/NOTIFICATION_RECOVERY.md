# Durable notification recovery and legacy preferences

Updated 15 October 2026. Local implementation and synthetic tests, not live-provider acceptance.

The same durable dispatcher now also handles `cleanup_deleted_customer`. Its bounded
failure/replay behavior is shared, but it performs privacy cache/image cleanup rather
than sending a notification. See [customer privacy](CUSTOMER_PRIVACY.md). Deploy API and
workers together after draining old workers; old task allowlists do not recognize it.

## Delivery lifecycle

Business transactions persist an event in `notification_outbox`. The minute dispatcher
publishes `deliver_notification_outbox`, using an ID containing the event UUID, replay
generation and publication attempt. A successful enqueue is **not** delivery completion.

The delivery wrapper locks the event row, runs an allowlisted task, and records
`completed_at` only after that task commits its keyed delivery records. Concurrent
workers and delayed job generations serialize on that row. Completed/dead-lettered
events are no-ops. A crash after local delivery but before acknowledgement reuses the
existing notification/email delivery keys on replay.

Unfinished published events become eligible again after **15 minutes**, longer than
the worker's 300-second timeout. This also recovers a job deleted/lost in Redis or
an ARQ job whose attempts were exhausted. Limits per recovery cycle:

- 10 publication attempts (including enqueue failures).
- 5 completed delivery attempts that fail.
- Unknown task names immediately enter the failed queue.

Exhausted events are retained with `dead_lettered_at` and a sanitized error class/code.
`notification.outbox_dead_letter` emits the event ID, not recipient data. Configure
staging/production alerts for that event and monitor the failed queue. The outbox
state is authoritative: the wrapper can finish its ARQ invocation successfully after
durably recording a delivery failure for the next recovery cycle.

External email is **at least once**, not exactly once. If Resend accepts a message
but its response/local receipt is lost, a later retry can send another message.
Review provider evidence before replaying uncertain deliveries.

## Worker result privacy and legacy email compatibility

Checkpoint 5 sets WorkerSettings.keep_result to 0 and keep_result_forever to false.
ARQ results serialize the original args, including email addresses and reset tokens.
ARQ 0.26.1 uses the worker default on exhausted retries/pre-execution failures even
when a function has its own retention setting, so the default applies to all jobs.
Do not use ARQ result polling as delivery evidence; use the durable outbox/EmailLog
for their supported flows, sanitized failure events and worker counters. This does
not add durable dead letters for authentication or other legacy tasks. Auth resend
remains the recovery path after their three attempts are exhausted.

Completed Redis job IDs no longer have a result-key deduplication window. Business
idempotency must come from database transaction/state checks and durable delivery
keys, not retained ARQ results. The outbox still uses generation-specific job IDs.

Legacy task names/signatures remain compatible with already-enqueued jobs. They
recheck signed auth-token identity, current registered-order ownership or exact guest
recipient, and seller/brand eligibility. Deleted/reassigned/unverifiable recipients
are skipped. Shipping/COD notices honor current and legacy opt-outs. Database/Redis/
provider failures retry without treating infrastructure failure as recipient consent.
See [customer privacy](CUSTOMER_PRIVACY.md) for locking and provider-cancellation limits.

Deploy/restart all workers together. Existing result keys are not retroactively
removed; their original TTLs still apply. Pending/deferred jobs remain sensitive
until processed/expired. Redis persistence, backups and provider retention require
separate operational acceptance; do not bulk-clear a shared queue to implement erasure.

## Admin recovery endpoints

- `GET /api/v1/admin/notifications/failed?page=1&per_page=25` lists retained failures
  without raw task arguments. Maximum page size is 100.
- `POST /api/v1/admin/notifications/failed/{event_id}/replay` accepts
  `{"reason":"Provider configuration repaired"}` (10–500 characters).

Replay requires an authenticated admin and an unresolved failed event. It records
the actor, timestamp, reason, prior error and attempt totals in `replay_history`, then
starts a fresh bounded cycle. Replaying an already pending/completed event is rejected.
The next minute dispatcher performs the enqueue; this endpoint does not send mail.
Replay-generation job IDs avoid collisions with retained Redis result keys.

The wrapper and task use separate DB sessions: provision pool capacity for both per
active delivery, plus API traffic. Do not increase worker concurrency without checking
connection capacity. Stop/drain old workers before deploying migration 019 and the new
worker together. Older published rows are eligible for keyed recovery, not assumed sent.

## One-time Redis preference import

On first preference read/update or preference-sensitive delivery, migrate
`notif_prefs:{user_id}` into `notification_preferences` under a row lock:

| Legacy field | Database field |
|---|---|
| `email_order_updates` | `order_updates_email` |
| `email_promotions` | `promotions_email` |
| `email_new_arrivals` | `email_new_arrivals` |
| `sms_order_updates` | `sms_order_updates` |
| `whatsapp_order_updates` | `whatsapp_order_updates` |

New records inherit explicit legacy values. If both stores already contain a record,
false wins on the initial merge; a legacy value cannot silently re-enable a database
opt-out, nor can a database default erase a legacy opt-out. `legacy_imported` prevents
old Redis data from overriding subsequent explicit edits.

Redis data is not deleted or assigned a new expiry. Unavailable Redis, malformed known
values or an import timeout fail closed; optional delivery retries rather than assuming
consent. Already-imported preferences no longer need Redis for consent reads. Missing or
previously expired legacy keys cannot be reconstructed; review backups if those records
are required. This preserves the existing mandatory transactional-notice policy and does
not add marketing, SMS or WhatsApp senders.

## Migration precautions

Revision 019 adds delivery/import bookkeeping; downgrade discards that bookkeeping and
replay history. Export it first and stop workers before a rollback. Revision 020 adds
missing review/seller indexes and nonnegative review-count/image-order checks. Existing
invalid values cause upgrade to fail rather than being rewritten. Inspect and resolve
such rows explicitly on a backed-up copy; no production data cleanup was performed.
