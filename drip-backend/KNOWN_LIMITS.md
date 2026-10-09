# Backend release limitations

Updated 10 October 2026. Passing coverage is not production approval.

## Release blockers

- **Dependency security:** the saved local pip-audit report identifies 45 advisory
  entries across nine installed packages. This includes development tools; it is not
  a claim that all 45 affect production or are exploitable here. Runtime dependencies
  include cryptography, ecdsa, orjson, Pillow, python-jose, python-multipart and Starlette.
  Some entries have no listed fix. See `docs/dependency-audit.json`. Upgrades and, where
  needed, dependency replacement require compatibility/security review and a new test
  run; dependencies were not silently upgraded in this task.
- **Historical money:** no real historical settlement records or transfer receipts
  were supplied. Legacy release protection remains unchanged. Follow SETUP.md before
  reopening any historical pending balance. Local synthetic races do not reconcile
  a merchant's real books or approve platform absorption of refund shortfalls.
- **Live provider acceptance remains gated:** PayFast now follows the published hosted
  checkout/token/callback protocol and has safe status reconciliation; Google, Supabase,
  Resend and worker flows have local signed/mocked coverage. These checks do not prove
  merchant-specific endpoints, source IPs, real Google consent, Supabase permissions or
  Resend delivery. Keep PayFast and Supabase orphan deletion disabled until the staging
  checklists pass. No real charge, email or upload was performed in this review.

## Verification boundaries and technical debt

- The Task 7 dispute-message ownership finding is fixed in this working tree.
  Only the return owner can use the customer reply route; non-owner sellers and
  admins have no bypass. Eighteen new API/PostgreSQL regression cases are part of
  the passing focused suite. B4 later adds a separate admin-only detail/reply path
  with dispute-row locking against resolution races. Seller dispute replies remain
  unsupported. See [the Task 7 review](docs/TASK_7_DESIGN_REVIEW.md).
- Guest checkout now has a public, read-only quote contract for current item prices,
  stock, runtime shipping, totals and payment availability. It intentionally creates
  no reservation and is not a guaranteed future price; order creation revalidates all
  values. Guest coupons still require authentication.
- Admin refund queue/detail/payment-history reads now expose pending, completed,
  reserved and remaining amounts. Revision 014 separates requester from confirmer for
  new records. Older completed rows are backfilled from the prior single actor field,
  so their `requested_by` value is best-effort and may identify the confirmer.
- Admin return detail exposes authorized item/order/customer/seller context,
  discount-prorated estimated refund value, linked refund/dispute state and allowed
  lifecycle actions. Sellers can list, inspect, approve, reject and acknowledge receipt
  only for their own brand returns; refund request/confirmation remains admin-only.
- Admin dispute detail and replies are available without weakening the owner-only
  customer route. Guest cancellation and return creation/detail require the signed
  capability token for the exact order; matching an email never grants access. Guest
  disputes remain unsupported because the dispute model requires an account owner.
- Native PostgreSQL tests exercise competing reservations, withdrawal requests,
  settlement/release, refund confirmation, signed payment callbacks and expiry
  sweeps. They are controlled two-contender regressions, not a load test or proof of
  every interleaving, crash/restart or distributed failure mode.
- Real Redis tests prove explicit email-task retry and exhaustion with provider
  transports mocked. Notification jobs now retry database failures and broadcast
  inserts are deterministic, but a durable outbox and provider delivery reconciliation
  are not established by these tests. No exactly-once email claim.
- The inherited `tests/security/test_auth.py` is module-skipped and obsolete.
  Other active tests cover authorization and callback protections, but this is not
  a comprehensive penetration test. The skipped module is reported, not counted
  as passing security coverage.
- PayFast forwarding headers are accepted only from configured trusted proxies. The
  actual proxy and PayFast callback IP/CIDR lists remain deployment-specific and must be
  confirmed before enabling the gateway.
- Health returns HTTP 200 with `status=degraded` when a dependency is unavailable.
  The Docker curl health check tests HTTP status only. Readiness monitoring must
  inspect the body or be corrected before relying on it for routing.
- Repository-wide Ruff has a substantial inherited backlog. Targeted formatting
  does not establish a clean lint gate. Strict typing is configured but mypy is not
  part of the checked-in development requirements; a clean type-check result has
  not been established.
- The migration test uses a fresh isolated schema and a 015 → 012 → 015 round trip,
  not a populated production backup. Rollback drops notification archive/read data and
  the refund requester audit field. Revision 015 cannot downgrade while guest-return
  rows with null user ownership remain; reconcile them explicitly rather than deleting
  them silently.
- API/worker image build success alone does not prove deployment, health, secrets,
  network policy, scheduled delivery, backup/restore or operational monitoring.

The release evidence above covers backend Tasks 3, 4 and 6. Task 7 has begun
as a Canva/API review with user-approved B1–B4 backend fixes. Asset extraction and
full visual/interaction design review remain outstanding.
No frontend application implementation, Canva edits or publishing was performed.
