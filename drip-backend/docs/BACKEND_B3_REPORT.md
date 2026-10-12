# Backend repair batch 3 report

Completed 13 October 2026. Scope: post-review finding F07. This batch is separate from the earlier Canva/API task labels. No frontend source, provider configuration, live data, deployment, commit or push was included.

## Result

### Customer-won dispute continuation

Resolving a dispute for the customer now reconnects the existing return workflow. In the same transaction, the service locks the dispute and rejected return, acquires the seller-order aggregate lock, revalidates every requested item against other non-rejected returns, resolves the dispute and changes the return to `approved`.

The aggregate lock is the same lock used when account and guest returns are created. Consequently, a new claim and a customer-win cannot both activate quantities beyond what was purchased. If another return already consumed the available quantity, the customer-win is rejected and the dispute remains unresolved for manual review.

A seller-won dispute still leaves the return `rejected`.

### Manual receipt and transfer boundary

A favourable decision records only the adjudication and approval. It does not mark the parcel received, create a refund request, restock inventory or claim that money moved. The existing explicit transitions remain:

1. admin or owning seller records receipt;
2. admin requests the return-linked refund;
3. admin confirms the external transfer with its receipt/reference;
4. confirmation restocks inventory, marks the return refunded and applies revision-016 accounting.

This preserves the manual-transfer audit boundary while making the customer-won path usable.

## Files

Application:

- `app/services/return_service.py`

Regression and audit material:

- `tests/integration/test_b3_dispute_resolution.py`
- `tests/integration/test_release_native.py`
- [batch-3 source supplement](audit/b3-changes.md)
- [batch-3 verification record](audit/b3-verification-2026-10-13.json)

No model, schema, route or Alembic change was required. The existing API contract remains at 188 documented operations.

## Verification

- 3/3 new B3 cases pass: complete customer-win/manual-refund journey, seller-win terminal behavior and native competing-quantity ownership.
- 47/47 focused dispute, return, refund, B1/B4 and native concurrency regressions pass.
- The native race permits exactly one winner between customer-win activation and a new claim for all remaining purchased quantity.
- Fatal-error Ruff selection passes for the changed application and tests. Full configured Ruff still has an inherited backlog, so this is not a clean repository-wide lint claim.
- Final full suite: **617 passed, 1 skipped, 669 warnings in 521.24 seconds**.
- Coverage: **85.77%** (7,586/8,845 statements), so the unchanged 85% gate passes.
- The existing native migration regression remains passing through revision 016; B3 adds no migration.

All database and Redis checks used disposable local services and synthetic data. No provider API, development/production data or frontend code was used.

## Remaining backend work

F08-F17 remain open. The next code work is either PayFast reconciliation evidence (F08, partly dependent on the merchant/provider contract) or notification delivery/preferences (F09). Separate pre-production gates remain unchanged. This batch does not make the backend complete or production-ready.
