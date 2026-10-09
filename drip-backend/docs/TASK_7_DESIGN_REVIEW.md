# WearHowZ Task 7 — design/API alignment, first pass

Design review: 8 October 2026. Backend follow-ups: 9–10 October 2026. **Task 7 remains in progress; not a completed frontend or a release approval.**

## Scope and decisions

- Read the Canva foundations and the named complete Shopper, Seller Studio, Marketplace Admin and Mobile Journeys sets through the connected Canva plugin.
- Reviewed extracted copy across 135 static pages. Visually inspected four thumbnail previews: both foundation pages, Shopper page 1 and Mobile page 3. This is not full-resolution visual QA of every page.
- Compared the screen families below with `openapi.json`, `ENDPOINTS.md` and targeted route/service/schema implementations. No live provider calls or account mutations were made.
- The interactive prototype returned one page with no extractable text; its navigation, animation and embedded code have not been verified.
- The working source selection is the named complete sets plus Identity & UI Foundations. Older alternatives were not merged or treated as additional requirements.
- Per the user's direction, leave `drip-frontend` untouched. The intended replacement location is a separate `wearhowz-frontend` folder; it has not been created. No frontend contents were inspected, deleted or disconnected, and no Canva design was edited.
- After the first pass, the user explicitly approved fixing B1 through B4 as separate backend gaps. Those targeted fixes and their verification are recorded below; Tasks 8–12 are not implemented by these follow-ups.

## Canva references

| Reference | Design ID | Pages |
|---|---|---:|
| Identity & UI Foundations | `DAHV5FXxo-Y` | 2 |
| 01 Shopper — Complete Design | `DAHV6TgX59U` | 54 |
| 02 Seller Studio — Complete Design | `DAHV6aJI1OA` | 32 |
| 03 Marketplace Admin — Complete Design | `DAHV6Q6sV3g` | 41 |
| 04 Mobile Journeys | `DAHV6Uyk2Bs` | 6 |
| Interactive Design Prototype | `DAHV6TlcOVo` | 1, behavior unverified |

## Foundation to preserve

| Token / rule | Canva evidence |
|---|---|
| Forest | `#203C32`; primary text, navigation and principal actions |
| Ivory | `#F5F1E7`; dominant page surface |
| Stone | `#D6D0C3`; supporting neutral |
| Clay | `#A65E43`; accent, not the default body-text color |
| Typography | Editorial serif headings, clean sans-serif interface; exact font families not returned in the reviewed copy |
| Text scale | Body 16px, controls 15px, labels 12px |
| Spacing | 8px rhythm; generous editorial whitespace |
| Controls | 44–52px height, 2–4px corners, visible keyboard focus |
| Motion | Honor reduced-motion preferences; prototype timings unverified |
| Layout | Forest wordmark/navigation bar, ivory canvas, editorial fashion imagery, brand attribution on product cards; split-image account entry |

Exact font files/names, original logo assets and usable image assets still need extraction or a user-provided export before claiming design fidelity. Do not upscale a Canva thumbnail into a production logo or hero. Do not copy mock names, dates, prices, stock or analytics into live data.

## Screen-to-API map

All endpoint references use the `/api/v1` prefix. An endpoint's existence is not proof that every visible control or data field is supported. The corrections and blockers below override illustrative design copy.

### Shopper

| Canva pages | Journey | Existing contract / implementation requirement |
|---|---|---|
| 1 | Home | `GET /api/v1/content/banners`, `GET /api/v1/products`, `GET /api/v1/brands`, `GET /api/v1/categories` |
| 2–4, 47 | Catalogue, filtering, search, no results | `GET /api/v1/products`, `GET /api/v1/products/search/suggestions`; catalogue uses cursors, while brand listings use page/per_page. Only one seller_id filter is supported. |
| 5–6 | Brand directory / storefront | `GET /api/v1/brands`, `GET /api/v1/brands/{slug}`, `GET /api/v1/brands/{slug}/products`; use catalogue with seller_id when additional filters are needed. |
| 7–9, 52 | Product, quick add, reviews, unavailable sizes | Product detail/variant/review routes; do not infer availability from mock size chips. Guest quick-add stays local until guest checkout or authenticated cart sync. |
| 10 | Wishlist | `GET /api/v1/customers/me/wishlist`, `POST /api/v1/customers/me/wishlist`; authenticated persistence, explicit sign-in state for guests. |
| 11–12, 48 | Bag and promo feedback | `GET /api/v1/cart`, `POST /api/v1/cart`, `POST /api/v1/cart/sync`, `POST /api/v1/coupons/validate`; these require authentication. Guest clients use `POST /api/v1/orders/guest/quote` for authoritative current items and totals; guest coupons still require sign-in. |
| 13–16 | Account/guest delivery and review | `POST /api/v1/orders` consumes the server cart; `POST /api/v1/orders/guest/quote` previews explicit guest items without reserving them; `POST /api/v1/orders/guest` creates the order with guest details. Preserve the returned guest capability token. |
| 17–20 | Payment pending, confirmation, failure, COD verification | `POST /api/v1/payments/initiate`, `GET /api/v1/payments/{order_id}/status`, `POST /api/v1/payments/{order_id}/retry`; submit returned PayFast form fields. Only server-confirmed status can show paid success. |
| 21–26, 53–54 | Login, registration, email verification, reset, Google | Auth routes including `GET /api/v1/auth/google`, `GET /api/v1/auth/google/callback`, `POST /api/v1/auth/resend-verification`. Consume actual token/cookie responses; preview-only links are not real actions. |
| 27, 42–44 | Sign-in code and security | Rehome 2FA challenge/setup into admin-only flows. Keep password change for ordinary accounts. |
| 28–30 | Profile, avatar, addresses | Customer profile/avatar/address routes. Populate and validate API fields, including checkout recipient and phone separately from saved address fields. |
| 31–33 | Orders, multi-brand tracking, cancellation | `GET /api/v1/orders`, `GET /api/v1/orders/{order_id}`, `GET /api/v1/orders/number/{order_number}`, `POST /api/v1/orders/{order_id}/cancel`; cancellation is order-level, not arbitrary selected items. |
| 34–37 | Returns and disputes | `POST /api/v1/returns`, `GET /api/v1/returns/{return_id}`, `GET /api/v1/returns/{return_id}/dispute`; customer ownership applies. A return groups selected order items under one seller_order_id. Message writes now enforce the owner-only policy described in resolved finding B1. |
| 38–39 | Personal reviews | Customer review list/create/update/delete routes; respect moderation and one-review rules. |
| 40–41 | Notifications/preferences | Shared notification read routes; customer preference fields are from customer notification-preferences routes, not the differently shaped seller/shared preference model. Saving SMS/WhatsApp preference flags does not prove delivery integration. |
| 45–46 | Account deletion/help | `DELETE /api/v1/customers/me` with the required request body; reflect service eligibility checks. Help copy must match guest support and actual brand policy. |
| 49–51 | Network error, missing page, expired session | Shared route/error components; distinguish 401, 403, 404, 422, 429 and server/network errors. Never auto-replay an uncertain financial mutation. |

### Seller

| Canva pages | Journey | Existing contract / implementation requirement |
|---|---|---|
| 1–4 | Registration and onboarding | `GET /api/v1/seller/register/slot-price`, `POST /api/v1/seller/register`, `GET /api/v1/seller/me`; add pending_payment, pending_approval, active, rejected and suspended views, including zero-fee registration. |
| 5 | Dashboard | `GET /api/v1/seller/dashboard`; real totals and onboarding guards, no demo figures in live mode. |
| 6–8, 32 | Products, variants, images, deletion | Seller product/variant/image routes; add uploading/error/reorder/primary-image states. Separate draft, unpublished and admin-hidden states. |
| 9–11, 31 | Inventory | `GET /api/v1/seller/inventory`, `GET /api/v1/seller/inventory/low-stock`, `PUT /api/v1/seller/inventory/{variant_id}`, `POST /api/v1/seller/inventory/{variant_id}/adjust`; preserve reservations and refetch on conflicts. |
| 12–14 | Brand orders and fulfilment | Seller order list/detail/status routes. Use seller-order IDs, not parent order IDs. Shipped requires tracking; allowed transitions are enforced by the server. |
| 15 | Brand identity | `GET /api/v1/seller/me`, `PATCH /api/v1/seller/me`, `POST /api/v1/seller/logo`; keep marketplace shell consistent. |
| 16 | Slot purchase | `POST /api/v1/seller/slots/purchase` accepts payment_method=wallet only; load runtime quote and show insufficient balance. |
| 17–21, 30 | Wallet, ledger, withdrawals, payouts, commission | Seller wallet routes. Withdrawal requires saved bank_account_id and PKR 500–200,000 schema limits. Preserve available/pending separation and transfer references. |
| 22–23 | Payout destinations | Seller bank-account list/create/delete routes. Current create schema requires bank_name and account_number; mobile-wallet-only fields in Canva are unsupported. |
| 24–27 | Analytics | Four seller analytics endpoints: overview, revenue, top-products, inventory-health. Empty data is not a zero-filled mock chart. |
| 28–29 | Notifications/preferences | Shared notification endpoints and their actual preference schema; honor role-specific options. |
| Missing | Seller returns | Seller return list/detail and approve/reject/received routes now enforce brand ownership. Sellers cannot request or confirm refunds; those financial actions remain admin-only. |

### Admin and mobile

| Canva pages | Journey | Existing contract / implementation requirement |
|---|---|---|
| Admin 1 | Dashboard | `GET /api/v1/admin/dashboard`; preserve money/count units. |
| Admin 2–4 | Seller decisions | Admin seller list/detail/approve/reject/suspend/reinstate routes; add `POST /api/v1/admin/sellers/{seller_id}/registration-payment` with amount and reference before paid-registration approval. |
| Admin 5 | Product moderation | Admin product list/hide/unhide routes. Add a review-moderation surface for existing admin review routes; it is not in these 41 pages. |
| Admin 6–8 | Orders and COD | `GET /api/v1/admin/orders`, `GET /api/v1/admin/cod-queue`, `POST /api/v1/admin/cod-queue/{order_id}/verify`, `POST /api/v1/admin/cod-queue/{order_id}/cancel`; verification is not payment collection. |
| Admin 9–10 | Inventory | `GET /api/v1/admin/inventory`, `POST /api/v1/admin/inventory/bulk-update`; display per-item outcomes. |
| Admin 11–13 | Payments/refunds/gateway | `GET /api/v1/payments`, the admin refund queue/detail/payment-history routes, refund request/confirmation, gateway status, COD receipt and PayFast reconciliation actions. Never treat a pending manual refund as transferred. |
| Admin 14–17 | Payouts/wallet | Use one consistent admin payout route family, e.g. `/admin/wallet/payouts`; completion needs reference, not merely a note. Overview payout totals are counts, not PKR amounts. |
| Admin 18–22, 38–41 | Returns/disputes | Admin return actions and enriched detail plus dispute list/detail/reply/resolve routes. Customer read/reply remains owner-only. An initial admin reply moves an open dispute to under_review; terminal disputes reject further messages. |
| Admin 23–24 | Banners | Admin content banner list/create/update/delete routes; use supported position values and safe destination links, not arbitrary unsupported mock positions. |
| Admin 25 | Runtime settings | `GET /api/v1/admin/settings`, `PATCH /api/v1/admin/settings`; convert displayed percent to fractional commission_rate and retain zero-fee support. |
| Admin 26–27, 36–37 | Notifications/broadcast/email log | Admin broadcast/email-log routes plus shared read routes. Review recipient audience before send; distinguish accepted job from actual delivery. |
| Admin 28–35 | Analytics | Existing admin analytics endpoints for platform, revenue, top-sellers, cohort, payment-methods, cities, conversion and search-queries. |
| Mobile 1–6 | Compact versions of all roles | Same contracts/permissions as desktop. Mobile boards are desktop canvases with phone mockups, not evidence of responsive code or complete form fields. |

## Required design corrections

1. **Admin-only 2FA:** Shopper pages 27/42/44 cannot expose ordinary customer setup. Challenge only after the backend indicates 2FA is required; do not invent a separate customer OTP endpoint.
2. **Manual money states:** Separate refund requested → external transfer pending → receipt confirmed. `POST /api/v1/admin/returns/{return_id}/refund` requests a refund; it does not transfer money. Confirmation requires reference via `POST /api/v1/payments/refunds/{refund_id}/confirm`. Refetch ledger/order state rather than adjusting balances or stock in the UI.
3. **COD:** Order verified → fulfilment → delivered → cash collection receipt are distinct steps. `POST /api/v1/payments/{payment_id}/cod-collection` requires reference and delivery/completion eligibility; verification must never mark cash paid.
4. **Payouts:** Request, approval, external transfer and completion are distinct. `POST /api/v1/admin/wallet/payouts/{payout_id}/complete` requires reference. Do not label approval as money sent.
5. **Registration:** Use amount_due and runtime pricing, show a manual payment-pending state for nonzero fees, and bypass that payment step only for a server-confirmed zero amount. Add admin receipt recording.
6. **Unsupported payment choices:** Remove JazzCash/Easypaisa from slot purchases. Current bank-account API is bank-only despite earlier historical notes; restoring mobile-wallet payouts would be a backend requirement, not a field to fake.
7. **Live availability:** PayFast is disabled by default. Use the guest quote's per-method availability instead of querying admin gateway state, hardcoding 'Available' or enabling online checkout from mock design copy.
8. **Order scope:** Replace 'Cancel eligible items' with accurate whole-order cancellation unless a partial-cancellation contract is deliberately added. Guest cancellation and returns require the same signed `X-Guest-Token` capability as guest order reads/payments; email matching never grants access.
9. **Currency and counts:** Decimal money values may be strings and are PKR, not paisa. Treat arithmetic accurately. Admin wallet pending/completed payout fields are counts; do not format them as currency as page 17 does.
10. **Filters and states:** Replace generic 'Pending / Active / Completed' table filters with endpoint-specific values. Do not render a multi-brand checkbox filter as supported when the catalogue accepts a single seller_id.
11. **Mobile forms:** Preserve required guest email/name/phone, recipient details, province and review step even though the small mobile concept omits some fields.
12. **UI completeness:** Add loading/skeleton, empty, validation, submitting, saved, stale-stock/price, permission-denied, expired-link, rate-limit, timeout/unknown-result and provider-disabled states. Add role-correct mobile navigation, review moderation and missing receipt screens.

## Backend contract gaps and security finding

### B1 — dispute message authorization (fixed; owner-only customer route)

The original message-write path had no ownership check. A regression reproduced this with synthetic PostgreSQL records: an unrelated customer received HTTP 201 and inserted a message. The fix now checks the return against the authenticated sender before looking up the dispute:

- `app/api/v1/returns.py::add_dispute_message` requires CurrentUser (any authenticated role), then passes the user ID to the service.
- `app/services/return_service.py::add_message` first calls `ReturnRepository.get_by_id(return_id, sender_id)`. Only the return owner can continue. Missing and unowned returns both produce HTTP 404 without disclosing dispute state.
- The existing open/under-review and resolved/closed behavior remains. The persisted sender comes from authentication, never the request body.

This preserves the owner-only policy already used by customer read/open-dispute routes. Other customers, unrelated sellers, the assigned seller and non-owner admins cannot post through this customer route. B1 itself added no privileged messaging path; the later B4 work adds a separate admin-only reply endpoint without weakening this customer route. Seller dispute replies remain unsupported.

`tests/integration/test_dispute_authorization.py` adds 18 real-API/PostgreSQL cases covering those roles, owner replies, spoofed sender fields, missing returns/disputes, authentication, terminal states, direct service use and existing admin review/resolution. Tests verify rejected requests do not insert messages. This targeted ownership fix is not a concurrency or repository-wide security audit; concurrent resolution/message ordering was not changed.

### B2 — guest quote and public checkout capabilities (fixed; read-only)

`POST /api/v1/orders/guest/quote` now accepts explicit variant/quantity items and returns server-priced line snapshots, current available stock, subtotal, zero guest discount, runtime shipping, payable total, free-shipping progress and COD/PayFast availability with an unavailable reason. It exposes no provider credentials or admin settings. Guest coupons remain sign-in-only and are rejected consistently with guest order creation.

The quote and order creation share the same stock, effective-price and runtime-shipping calculation, including duplicate-item merging. Quoting creates no order and reserves no inventory. It is deliberately non-binding: `will_revalidate_on_order=true` tells the client that stock and prices are checked again during the atomic order workflow. A local guest cart must refresh this quote before its review/payment step and must not use Canva's illustrative PKR 250 value.

### B3 — durable refund administration (fixed; admin-only)

The admin read contract now includes:

- `GET /api/v1/payments/refunds` for a paginated queue/history filtered by pending/completed status and optional payment ID.
- `GET /api/v1/payments/refunds/{refund_id}` for order/payment context, the requested/completed event history and current payment-level balances.
- `GET /api/v1/payments/{payment_id}/refunds` for all refunds plus pending, completed, reserved and remaining refundable amounts.

All three reads require admin authorization. Pending refund amounts reserve refundable capacity, so the remaining balance cannot encourage an over-refund. New requests preserve `requested_by` separately from the confirmation actor and transfer reference. Revision 014 backfills historical `requested_by` from the only prior actor field; for already-completed historical refunds, that value may represent the confirmer because the original requester was not retained. Return-linked creation keeps its stable idempotency key, and direct requests continue to accept one. Never automatically resubmit an uncertain mutation with a new key.

### B4 — operational detail workflows (fixed)

- `GET /api/v1/admin/returns/{return_id}` now provides an admin-only item-level review contract without widening the owner-filtered customer route. It includes customer, seller, order and payment context; product/variant purchase snapshots; purchased and requested quantities; the exact discount-prorated estimated refund amount; linked refund/dispute state; and server-derived available actions. The estimate and refund request share one calculation path, preventing display/processing drift. Pending linked refunds suppress duplicate refund actions, while confirmed transfers expose their reference and completion time.
- `GET /api/v1/admin/disputes/{dispute_id}` and `POST /api/v1/admin/disputes/{dispute_id}/messages` provide admin-only deep-link reading and authenticated replies. The existing customer route remains owner-only, and terminal disputes reject new messages.
- `/api/v1/seller/returns` list/detail plus approve/reject/received actions are restricted to the authenticated seller's brand. Sellers can make operational decisions and acknowledge receipt, but only admins can request or confirm money movement. PostgreSQL row locks serialize competing seller/admin state decisions.
- Guest cancellation uses the existing order cancellation endpoint with `X-Guest-Token`. Guest return creation/detail uses `/api/v1/returns/guest` and `/api/v1/returns/guest/{return_id}` with the same signed, expiring, order-scoped capability. Wrong, forged, absent and valid-but-other-order tokens are rejected. Revision 015 makes `returns.user_id` nullable for this purpose; it does not infer ownership from email. Guest disputes remain account-only.

## Acceptance checklist for the next implementation stages

- [x] Resolve B1 with owner-only authorization and persisted cross-account regression tests. B4 later adds admin replies; seller dispute replies remain unsupported.
- [x] Resolve B2 with a read-only guest quote/capabilities contract and PostgreSQL regressions proving pricing parity and no reservation side effects.
- [x] Resolve B3 with durable admin refund queue/detail/history/balance reads and separate requester/confirmer audit fields.
- [x] Add the authorized admin return-detail contract required for item-level review, with lifecycle/refund-state regressions.
- [x] Complete B4 seller return decisions, admin dispute detail/replies and signed-capability guest cancellation/returns without widening financial or customer permissions.
- [ ] Extract/confirm font families, original logo and usable imagery; inspect representative product, seller and admin screens at adequate resolution.
- [ ] Review prototype interactions and close missing screens/states; apply/approve this supplement before claiming Task 7 complete.
- [ ] Foundation (Task 8, separately selected): new frontend folder, tokens, accessible components, responsive shells, role-aware auth and typed API/error handling.
- [ ] No access/refresh/guest tokens in analytics, logs or share links; preserve httpOnly refresh-cookie behavior and avoid unsafe token persistence.
- [ ] For a rotating refresh token, coordinate concurrent refreshes; clear role/session state on logout or expiry. Do not retry non-idempotent writes blindly.
- [ ] Keyboard/focus/labels/contrast and reduced motion verified in rendered UI; 320px, phone, tablet and desktop checks, including zoom and touch controls.
- [ ] Loading/error/empty/success and permission states tested for each screen family, not just the happy path.
- [ ] Guest, customer, pending seller, active seller, suspended seller and admin journeys tested with the actual API.

## Verification and stopping point

The initial pass was documentation-only. The user-approved B1 follow-up changes dispute-message ownership and adds 18 regression cases. B2 adds one public quote route and four PostgreSQL regressions. B3 adds three admin-only reads, two API/PostgreSQL regressions and revision 014. B4 adds ten backend capabilities across nine new operations plus the existing cancellation route: admin return detail, seller return list/detail/decisions, admin dispute detail/replies, and guest cancellation/return support. Five B4 workflow regressions and one native two-session race cover the new boundaries. Test records use disposable local PostgreSQL schemas. No live provider configuration, Canva content or frontend files changed.

Focused verification on 8 October: **53 passed, 15 deselected**, including all 18 new cases. New-test Ruff checks/formatting and Python compilation passed again on 9 October. The changed service has the same 15 pre-existing Ruff findings as its committed baseline; no new lint findings were introduced.

Fresh full-suite verification after B4 on 10 October: **602 passed, 1 skipped, 85.59% coverage** (7,339 of 8,575 statements), exit code 0, using native PostgreSQL and the dedicated Redis test service. The unchanged 85% gate passes. All five B4 workflow cases, the competing seller/admin decision race and the broader return/dispute/cancellation selection passed. The migration check completed a fresh 015 → 012 → 015 round trip and read every model table. The skipped legacy security module and broader release limits remain disclosed in KNOWN_LIMITS.md. The refreshed contract contains 188 operations.

Commands (from `drip-backend`, with the dedicated test URLs in SETUP.md):

```powershell
.venv/Scripts/python.exe -m pytest tests/integration/test_dispute_authorization.py tests/integration/test_return_api.py tests/unit/test_returns.py tests/integration/test_release_journeys.py -k 'dispute or return or TestAdminReturns' --no-cov --tb=short --disable-warnings
.venv/Scripts/python.exe -m pytest tests/integration/test_marketplace_regressions.py -k 'guest_quote' -q --no-cov
.venv/Scripts/python.exe -m pytest tests/integration/test_marketplace_regressions.py -k 'admin_refund' -q --no-cov
.venv/Scripts/python.exe -m pytest tests/integration/test_marketplace_regressions.py -k 'admin_return_detail' -q --no-cov
.venv/Scripts/python.exe -m pytest tests/integration/test_b4_workflows.py --no-cov -q
.venv/Scripts/python.exe -m pytest tests/integration/test_release_native.py -k 'competing_admin_and_seller_return_decisions or fresh_migrations_round_trip' --no-cov -q
.venv/Scripts/python.exe -m pytest tests/integration/test_marketplace_regressions.py tests/integration/test_release_native.py tests/integration/test_payment_api.py tests/unit/test_payments.py -k 'refund or fresh_migrations_round_trip' -q --no-cov
.venv/Scripts/python.exe -m pytest tests/integration/test_marketplace_regressions.py -q --no-cov
.venv/Scripts/python.exe -m pytest --tb=short --disable-warnings --cov-report=term:skip-covered
.venv/Scripts/python.exe -m ruff check tests/integration/test_dispute_authorization.py
.venv/Scripts/python.exe -m ruff check app/schemas/order.py app/api/v1/orders.py app/services/order_service.py tests/integration/test_marketplace_regressions.py --select I001,F401,F821,E501
.venv/Scripts/python.exe -m compileall -q app tests/integration/test_marketplace_regressions.py
.venv/Scripts/python.exe scripts/export_contract.py
```

Task 7 remains in progress because asset extraction, full visual/interaction review and design-state alignment are outstanding; B1–B4 backend work is complete. No Task 8 implementation, commit, push or launch action has been performed. Existing Task 6 reports and review ZIPs are historical and have not been regenerated for this follow-up.
