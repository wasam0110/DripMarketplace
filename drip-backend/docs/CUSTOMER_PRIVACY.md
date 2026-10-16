# Customer deletion and draft retention/offboarding policy

15 October 2026. The owner approved **limited customer-data cleanup**. Timed financial/
dispute deletion and new seller/admin offboarding workflows are **not enabled**.
This is implementation guidance, not legal approval or a universal erasure claim.

## Implemented customer flow

The authenticated customer must supply the existing password and confirmation phrase.
Seller/admin self-deletion remains blocked. Active orders, open returns/disputes and
pending refunds block customer deletion; the financial record is not discarded.

Deletion and supported account writes take the user-row lock before child rows.
Return/dispute creation and refresh rotation now follow this order too. A request
that authenticated before deletion must recheck the account after obtaining its lock.
Authentication update helpers cannot restore credentials on a deleted row.

In the deletion database transaction:

- Disable/anonymize the profile, increment the authentication version and remove sessions
  and saved addresses (existing behavior).
- Remove in-app notifications and database notification preferences.
- Remove review-image references and review title/body/moderation-note free text. Keep
  rating, moderation status and internal ownership/order references for consistency.
  This is **pseudonymization**, not irreversible anonymization of every retained row.
- Persist a deterministic `cleanup_deleted_customer` event in the durable outbox.
  Save the removed avatar/review-image URLs only as a pending cleanup manifest.

After commit, attempt immediate removal of exactly `cart:{user_id}`, `wishlist:{user_id}`
and `notif_prefs:{user_id}`. A Redis outage does not undo account disablement: the
committed event retries cache cleanup. No account cache is cleared before DB commit.

The worker uses the existing bounded recovery/dead-letter/admin-replay mechanism.
It verifies the account is deleted, then removes cache keys and safe image objects.
Image deletion is restricted to configured storage buckets and the exact generated
`products/{owner_uuid}/{object_uuid}.webp` namespace. Review-image owner IDs are the
stored review IDs. The worker rejects unexpected/external URLs, folder paths and
objects still referenced by other profiles, reviews, products, categories, banners or
brands. Unverifiable legacy objects are **not deleted**; they fail with
`AssetCleanupReviewRequiredError` and eventually need explicit operator review.

Storage failures retry idempotently. A completed cleanup event removes asset URLs from
its arguments. Failed events retain the manifest so cleanup is not silently forgotten.
There is no bucket scan or bulk historical deletion. No real provider object was
deleted during local verification.

Queued registered-order notifications and broadcasts recheck/lock their recipients;
they cannot recreate notifications for deleted users. This does not recall a message
already accepted by an external provider.

Legacy raw-address email jobs now also recheck recipients at delivery. Verification/
reset jobs validate the signed purpose/expiry and token subject, require the current
matching email and an undeleted user, and suppress already-verified/used-reset links.
Registered-order jobs resolve the order's user rather than a same-email replacement
account. Guest jobs require the order's guest address. Seller approval requires the
matching active, undeleted brand/account; its link uses configured FRONTEND_URL.
Queued names are ignored in favor of current account/guest names. Shipping/COD updates
respect database and legacy email opt-outs; mandatory confirmation/auth notices keep
their existing policy. Preference checks use the legacy bridge inside the delivery
transaction without committing its temporary import; normal preference APIs/durable
notifications remain responsible for persisting the one-time import.

The user-row lock is held through the provider call. If deletion wins, no delivery
starts; if sending wins, deletion waits for that call's transaction to finish. A
provider request already in flight (including a synchronous SDK thread surviving
worker cancellation) cannot be recalled or guaranteed absent after deletion returns.
These tests mock provider handoff, not real delivery or provider erasure.

ARQ result retention is now zero for the worker, including exhausted-retry results:
those results otherwise duplicate original recipient/token arguments. Pending jobs
still contain their original sensitive payload until execution/expiry; Redis access,
TLS, persistence/backup retention and old result-key expiry require operational review.
No historical queue, result, financial or audit records were bulk-purged.

## Operator procedure

1. Deploy API and workers together after draining old workers; migration head remains
   020. Old workers do not know the new allowlisted cleanup task. No new migration is needed.
   This exact-object, customer-requested cleanup is independent of the disabled
   bucket-wide orphan-cleanup flag. Validate storage permissions and failure handling
   in staging before enabling account deletion in a deployed environment.
2. Monitor `GET /api/v1/admin/notifications/failed` and the structured
   `notification.outbox_dead_letter` event. This queue now also contains privacy cleanup.
3. Provider outage: fix configuration, check storage evidence, then use the existing
   admin replay endpoint with a reason. Do not assume a 204 account-deletion response
   proves external-image deletion already completed.
4. `AssetCleanupReviewRequiredError`: an authorized operator must inspect the pending
   manifest in the database and establish ownership/shared references. Raw URLs are not
   exposed by the public failed-job listing. Do not simply increase retry counts, weaken
   the path checks or delete a shared bucket. Manual resolution needs its own approved scope.
5. Restore rehearsal must reapply deletion tombstones and pending cleanup requests
   before reopening traffic. Backup erasure is not performed by the application.

See [notification recovery](NOTIFICATION_RECOVERY.md) for retry limits, replay audit,
two-session worker capacity and rollout/rollback precautions.

## Proposed policy — not an automatic expiry configuration

| Data | Proposal for owner/professional confirmation |
|---|---|
| Orders, payments, refunds, payouts and essential financial evidence | Provisional six years after the relevant tax year; retain longer under an applicable legal hold. Confirm applicability with the accountant before enabling expiry. |
| Return/dispute evidence | Align essential evidence with the linked financial record; an open dispute/legal hold prevents expiry. |
| Ordinary delivery logs | Proposed 90 days from the event, unless linked evidence must be retained. No new expiry job enabled. |
| Security logs | Proposed one year from the event; financial/admin audit evidence follows its applicable longer rule. No new expiry job enabled. |
| Seller closure | Authorized admin approval; stop new sales, resolve existing obligations with restricted access, reconcile balances, then close. Security suspension revokes access immediately. Not implemented as a new workflow. |
| Admin closure | Another authorized admin approves; protect the last usable administrator and transfer responsibilities. Not implemented as a new workflow. |

FBR states a six-year requirement for income-tax return records. That does not establish
the correct retention rule for every WearHowZ record or all legal holds; confirm the
business-specific rules before destructive automation.
[FBR record-keeping guidance](https://fbr.gov.pk/categ/file-income-tax-return/51147/80860/71163).

## Explicit remaining boundaries

- Financial orders/addresses, return/dispute messages, email/audit logs, review votes,
  internal identifiers and required evidence are not globally erased by this flow.
- Previously deleted accounts are not bulk reprocessed. Their missing avatar references
  cannot be reconstructed automatically; historical cleanup needs an approved inventory.
- Legacy email send-time suppression and new ARQ result non-retention are implemented.
  Pending/old queue payloads, Redis backups and provider retention are not globally
  erased. Authentication jobs still use bounded ARQ retries, not the durable outbox;
  manual resend remains necessary after exhausted delivery attempts.
- External storage/CDN caches, provider logs, backups, already-sent messages and live
  account recovery/retention operations require staging verification and owner decisions.
- Versioned consent/policy acceptance storage and full seller/admin offboarding remain
  open; notification preferences are not a substitute for policy-version consent records.
