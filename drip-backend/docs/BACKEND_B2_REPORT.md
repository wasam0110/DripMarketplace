# Backend repair batch 2 report

Completed 13 October 2026. Scope: post-review findings F04-F06. This batch is separate from the earlier Canva/API task labels. No frontend source, provider configuration, live data, deployment, commit or push was included.

## Result

### F04 - finite release and real return/dispute holds

The mature-release worker now delegates to one service implementation. Each eligible ledger releases only its refund-adjusted seller entitlement and is held only by an active return or dispute for that seller order. Open, under-review and customer-resolved disputes stay held; a seller-resolved dispute no longer creates a permanent hold. One seller's return or refund cannot freeze another seller's ledger in the same customer order.

Historical processed refunds without revision-016 accounting remain quarantined. This is deliberate protection against releasing money whose seller allocation is unknown.

### F05 - persisted seller-specific allocation

Revision 016 adds one `refund_accounting` row per refund and one `refund_allocations` row per affected seller order. Return-linked refunds target that seller order. Direct payment refunds consume the remaining merchandise capacity across seller orders deterministically, with cent-safe proportional allocation; only an amount beyond remaining merchandise is classified as shipping.

Allocations are persisted before application and uniquely constrained by refund and seller order. A confirmed refund before settlement remains pending against that seller order, then becomes an explicit settlement offset when delivery is settled. Replay sees the existing allocation and does not debit the wallet or credit stock twice.

### F06 - complete net accounting

Commission ledgers retain their original gross, commission and seller amounts while accumulating refunded gross, reversed commission, reversed seller entitlement, actual seller recovery, settlement offset and platform shortfall. Hybrid net values supply refund-adjusted reporting without erasing the original audit basis.

The retained accounting policy is explicit:

- the seller bears only the reversed seller entitlement;
- the platform bears refunded shipping and reversed platform commission;
- if seller funds cannot be recovered, the platform records and bears that shortfall;
- no recoverable seller debt is created.

Database constraints enforce the important conservation equations. At refund level, seller reversal equals recovered funds plus settlement offset plus platform shortfall; platform funding equals shipping plus reversed commission plus shortfall. Applied seller allocations also require reversed commission plus reversed seller entitlement to equal allocated merchandise.

Admin refund responses expose the accounting summary and seller allocations. Seller commission history exposes original, reversal and net values. Wallet totals, seller summaries and analytics now aggregate net ledger values where the business question is post-refund revenue.

## Files

Core accounting and release behavior:

- `app/models/wallet.py`
- `app/models/payment.py`
- `app/services/commission_service.py`
- `app/tasks/wallet_tasks.py`
- `alembic/versions/016_refund_accounting.py`

API, repositories and reporting:

- `app/repositories/payment_repo.py`
- `app/repositories/wallet_repo.py`
- `app/schemas/payment.py`
- `app/schemas/wallet.py`
- `app/services/payment_service.py`
- `app/services/admin_service.py`
- `app/services/wallet_service.py`
- `app/services/seller_service.py`
- `app/services/analytics_service.py`

Regression and audit material:

- `tests/integration/test_marketplace_regressions.py`
- `tests/unit/test_commission_service.py`
- `docs/openapi.json`
- `docs/ENDPOINTS.md`
- [batch-2 source supplement](audit/b2-changes.md)
- [batch-2 verification record](audit/b2-verification-2026-10-13.json)

`app/services/customer_service.py` already had an unrelated local change and was neither edited nor claimed by this batch.

## Verification

- 9/9 focused B2 accounting/release regressions pass.
- The targeted multi-brand allocation and admin accounting-contract cases pass.
- 20/20 commission-service unit cases pass.
- All 11 native release/concurrency cases pass with dedicated PostgreSQL 15 and Redis 7 services.
- Fresh migration through revision 016, downgrade to 012, re-upgrade to 016 and reads of every model table pass.
- Fatal-error Ruff selection passes for the changed application, migration and test files. Full configured Ruff still has an inherited backlog, so this is not a clean repository-wide lint claim.
- Final full suite: **614 passed, 1 skipped, 637 warnings in 440.28 seconds**.
- Coverage: **85.70%** (7,568/8,831 statements), so the unchanged 85% gate passes.

All database tests used disposable local services and synthetic data. No provider API, development/production data or frontend code was used.

## Remaining backend work

F07 is next: reconnect a customer-won dispute to a usable return, receipt and refund workflow without inventing a transfer receipt. F08-F17, inherited quality work and the separately listed pre-production gates remain open. This batch does not make the backend complete or production-ready.
