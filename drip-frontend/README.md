# WearHowZ frontend

Local React + TypeScript + Vite application, in the requested `drip-frontend` folder.
Initial frontend steps left the FastAPI backend unchanged. The approved backend
checkpoints below add targeted support. COD checkout requires
the backend checkout safeguards and migration 021 from the preceding step.

## Run locally

Requires Node 22.12+ and the backend at `http://127.0.0.1:8000`.

```powershell
cd drip-frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:3000`. The development server proxies `/api` to FastAPI.
No `.env` file is required for the defaults. Optional public settings are listed in
`.env.example`; do not put API keys or secrets in `VITE_*` variables.

Use the same hostname consistently across frontend and backend callback URLs;
`localhost` and `127.0.0.1` do not share cookies.

## Verify

```powershell
npm run build
npm test
npm run test:browser
```

Browser tests use installed Microsoft Edge, start/reuse the development server,
and check desktop/mobile layouts, accessibility and the read-only backend proxy.
The backend and its database/Redis must be running for the live proxy smoke test.
All other browser tests use isolated fixtures, not live account or payment writes.
The browser-test launcher uses a fresh temporary transform cache per run and
removes only that cache afterward; this avoids stale shared-cache discovery on
this Windows workspace.

Previous checkpoint, 20 October 2026: production build and strict TypeScript checks passed;
35 unit/component tests and 28 Edge desktop/mobile browser tests passed. The
scanned home, login, registration, catalogue, product and bag pages had no automated
WCAG 2 A/AA or WCAG 2.1 AA violations. This is not a complete accessibility
certification. Desktop/mobile screenshots were visually inspected. Source-only
Git whitespace checks passed; legacy tracked dependencies are excluded. The live
read-only proxy reached healthy PostgreSQL/Redis and the product catalogue.
Runtime dependency audit reported no known vulnerabilities.

## First build — scope

- Canva forest/ivory/stone/clay palette, serif/sans typography, compact controls.
- Responsive navigation, keyboard focus, reduced motion, forms and error states.
- Homepage and product/brand browsing with real API data.
- Product images, colour/size selection, effective variant prices and stock limits.
- Guest bag selections persisted on-device; authoritative prices/delivery from guest quotes.
- Signed-in bag additions, quantity updates, removal, clear confirmation and explicit guest merge.
- Multi-brand bag groups, failed-quote recovery and ambiguous-write review without automatic replay.
- Search, sorting and catalogue cursor pagination.
- Email login, registration, password-reset and verification screens.
- In-memory access token, HttpOnly-cookie refresh, deduplicated refresh requests.
- Account session summary and sign-out; no authentication tokens in browser storage.
- Admin-only authenticator input, not customer two-factor setup.
- Guest/account COD checkout: contact and delivery, signed quotes, review and confirmation.
- Signed-in coupon quotes with server totals and discount-aware COD availability.
- Stable retry keys, uncertain-response recovery and explicit price re-acceptance.
- Paginated account orders, read-only order details and per-brand shipment tracking.
- Private guest tracking with an in-memory checkout handoff or an explicit access code.

This is not the complete frontend or a production-readiness claim. Still needed:
payment retry/recovery controls, remaining customer account features, seller portal and admin portal.
Role-specific landing pages also remain.

## Product and bag verification scope

Product and bag browser fixtures exercise sold-out variants, effective prices,
guest persistence, quantity changes/removal, failed quotes, explicit signed-in
merging and a lost response after an additive write. Matching guest/account items
merge using the backend's maximum-quantity rule, not by adding quantities together.
Only identifiers and quantities are stored locally; tokens, prices and totals
are not persisted. Stock is not reserved by adding to the bag.

These tests do not establish a real-account purchase journey: the local catalogue
is empty and browser writes use isolated fixtures. No live orders, charges,
customer emails, backend edits or deployments were performed for this frontend step.

## COD checkout and recovery

Verified on 21 October 2026: production build/TypeScript, 61 unit/component
tests and 20 focused Edge desktop/mobile checkout tests passed. Checkout details,
review and confirmation passed automated WCAG 2 A/AA and 2.1 AA scans. Browser
writes were mocked; this is not a live purchase or full accessibility certification.
No backend services were started or migrations applied. The prior full browser
run's two offline-backend proxy failures were not reverified in this focused run.

The `/checkout` route follows the approved Canva Details → Payment → Review flow.
Guest quotes use `/orders/guest/quote`; account quotes use `/orders/quote` with
the authenticated server cart and optional coupon. Totals and COD availability
come from the signed server quote, including discounts. Refreshing, applying or
removing a coupon restarts review. Signed-in customers can explicitly copy a saved
address into delivery fields. PayFast initiation remains unimplemented; the
online-payment option stays disabled.

Explicit placement sends the accepted `quote_token` and a UUID4 `checkout_key`
to `/orders` or `/orders/guest`. Duplicate clicks are suppressed; uncertain writes
can only retry the identical in-memory payload or call the matching `/recover`
endpoint. Changed/expired quotes require another review, never automatic placement.
Confirmation uses returned order data; verification links are restricted to HTTPS
`wa.me`. Migration 021 must be applied by the backend operator before live use.

Contact details and the submission payload exist only in component memory until
explicit placement. Reload/account changes discard them. Only the owner-scoped
checkout key is saved in `sessionStorage` before writing; it is a sensitive guest
recovery capability, not an authentication token. Never copy it into URLs or logs.
Reload requires explicit status recovery. A not-found result retains the key for
the next reviewed submission, protecting against a delayed original request.
Guest recovery expires after 24 hours and stays blocked pending support; account
recovery requires authentication. Closing the tab can lose the key, so retain the
order number. A confirmed checkout retains its key until explicitly starting
another order from the confirmation screen.

After confirmed in-page success, only unchanged purchased guest selections are
removed; changed selections are preserved. Recovery after reload leaves the guest
bag intact because its original selection snapshot is unavailable. Account bags
are reloaded, not cleared by a second frontend write. Storage failures block new
placement; backend/network failures do not produce a fictional success state.

Email delivery and real-account journeys have not been exercised by this build.
The local database currently has no products or approved labels; the UI shows
empty states rather than invented catalogue data.

Google initiation/callback handling was scaffolded at this historical checkpoint;
the Google callback checkpoint below completes local handling. It remains gated by
`VITE_ENABLE_GOOGLE_AUTH=false`. Enable only after backend credentials, trusted
origins and same-host callback URLs are aligned and the live flow is tested.

## Read-only order tracking

Verification on 21 October 2026: 65 unit/component tests and 34 focused Edge
desktop/mobile checkout + tracking tests passed. TypeScript/production build and
source whitespace checks passed. Tracking detail pages passed automated WCAG
2 A/AA and 2.1 AA scans; desktop/mobile screenshots were inspected. All order
reads/writes in browser tests used fixtures, not real customer records.

Order tracking is available at `/orders`, `/orders/:id` and `/track`. Account
history uses authenticated paginated reads. Order details show the original
monetary snapshot, delivery address and separate brand shipment statuses with
only the courier/tracking references and dates actually returned by the API.
The UI does not infer delivery estimates, refund balances or completed steps.

Guest access uses `X-Guest-Token`, never an email address as authorization.
Checkout confirmation transfers that token to tracking in memory; it is not
written to storage, URL parameters, router history or logs. Reload requires a
private access code or recent-checkout recovery. Changing accounts clears the
handoff. Reads use `no-store`, cancel stale requests and hide data on sign-out.
Denied access, missing/expired guest credentials, empty history and service
failures have explicit states. Cancellation and returns were draft-only previews at this checkpoint;
courier-site links are not implemented. Real emailed tracking-link compatibility has not been
verified; guest access is currently via confirmation/recovery or manual code.

This step preserves the existing design and local-only workflow. Backend files
and migrations are unchanged; fixture checks do not establish a live purchase.

## Cancellation and return drafts

Verified on 21 October 2026: 68 unit/component tests, the production build and
16 focused desktop/mobile order-page browser tests passed. Draft review passed
automated accessibility scans and desktop/mobile screenshot review. Tests assert
that cancellation/return drafts produce no order writes or persisted draft text.

At this checkpoint, order details included frontend-only cancellation and return draft screens. Cancellation and return submission are now connected as described below.
Cancellation drafts concern the whole order. Return drafts select existing order
items and quantities up to the purchased quantity, followed by a reason and review.
These are drafting bounds, not verified return eligibility or backend validation rules.

Submission buttons were disabled at this checkpoint. No cancellation/return API,
upload, approval, refund estimate or time window was implemented in that step.
Later sections document connected submission. No new backend contracts were
inspected or changed for the original frontend-only step.
Existing protected order reads supply the item names; drafts live only in component
memory and clear on discard, navigation, refresh or account changes. They are not
sent to the backend or stored in the browser. Actual submission requires a later,
explicitly approved API-contract verification and integration step.

## Device-local saved pieces

Verified on 21 October 2026: 77 unit/component tests, the production build and
18 focused desktop/mobile saved-pieces and bag browser tests passed. Saved-pieces
checks include automated accessibility scans, storage failures and cross-tab
updates. Browser checks use API fixtures, not live account-wishlist integration.

`/saved` collects pieces saved from catalogue cards or product details. This is
frontend-only browser storage, shared across accounts using that browser; it is
not the backend account wishlist and is not cleared automatically on sign-out.
The page states that limitation explicitly. Only validated product UUIDs are
persisted, with a 100-piece cap. Current product data is fetched using existing
public product reads, at most 12 saved cards per page; prices and stock are never
saved or reserved. Opening a piece lets the shopper select size/colour normally.

Unavailable products retain a removable reference without a fabricated price.
Read/write failures are surfaced, malformed storage is not silently overwritten,
and clearing requires confirmation and removes only the saved-pieces storage key.
Storage events update other tabs; writes re-read the current list first. There is
no cross-tab transaction guarantee or account synchronization. No backend wishlist
contracts were read or changed, and no wishlist write endpoints are called.

## Brand collection pagination

Verified on 21 October 2026: 77 unit/component tests, the production build and
6 focused desktop/mobile browser tests passed. Brand collections now use the
existing frontend cursor-pagination contract beyond the first 20 pieces. The
cursor survives reload and browser back/forward navigation. Empty later pages
can return to the same brand's first page; failed reads offer an explicit retry
without showing stale products. Repeated next cursors do not produce a stuck
next-page button. Desktop/mobile screenshots and automated accessibility scans
were checked. Browser tests use fixtures; live multi-page brand data has not
been verified. No backend files or contracts were inspected or changed.

## Catalogue categories and filters

Verified on 21 October 2026: 87 unit/component tests, the production build and
12 focused desktop/mobile filter and brand-pagination browser tests passed.
Automated accessibility scans and desktop/mobile screenshot review passed.
Browser coverage uses isolated API fixtures, not a live catalogue journey.

The clothing edit now reads active categories from `/categories` and sends
category, whole-PKR price bounds, repeated letter/numeric sizes and colours,
on-sale and last-14-days filters to `/products`. Filters persist in the URL through
search, sorting, reload and pagination; applying or clearing them resets the cursor.
Invalid URL filters block product reads until corrected or cleared. Category read
failures have an explicit retry without disabling the remaining controls.

Category matching is exact, not recursive. Sizes/colours use exact variant labels
entered as comma-separated values; no exhaustive facet list or stock availability
is inferred. Price filtering uses product sale/base price, not variant prices.
Only the necessary catalogue/category route and imported query/schema/policy
sections were inspected; backend files were not changed. Live filtering against
a populated backend catalogue remains unverified.

## Product reviews

Verified on 21 October 2026: 87 unit/component tests, the production build and
18 focused desktop/mobile review and bag browser tests passed. Review-list
accessibility scans and desktop/mobile screenshot review passed. Requests used
isolated fixtures, not live account submissions or a real moderation journey.

Product pages display newest approved reviews, server-provided average/count and
rating breakdown, verified-purchase badges only when returned by the API, review
photos and previous/next pagination. Review text renders as plain text. Loading,
empty and failed-read states are distinct; failed reads have an explicit retry.

Signed-in accounts can submit a 1–5 rating, optional title (200 characters) and
body (2,000 characters). The existing backend allows one review per account per
product and moderates new reviews. The product-page form does not link an order;
purchase-linked reviews start from delivered/completed account orders (below).
Photo uploads remain blocked pending a backend contract. Review voting is
available on approved public reviews. Account review editing/deletion is
available under `/account/reviews`. Submission
success requires a matching pending response and
does not insert the review into the approved public list or change its averages.

Drafts remain in memory and reset on navigation/product/account changes. Duplicate
clicks are blocked and writes are never automatically retried. A network/5xx or
unrecognized response is treated as uncertain and locks the form for that mounted
session, with instructions not to resubmit. This is not durable reconciliation:
reload can lose that guard, and the backend remains responsible for uniqueness.
No real reviews were posted during verification. Only required review contracts
and eligibility logic were inspected; backend files remain unchanged.

## Order-linked reviews

Verified on 21 October 2026: 89 unit/component tests and 32 focused desktop/mobile
order/review browser tests and the production build passed. Initial concurrent runs had unit/browser
timeouts; isolated reruns passed without increasing test timeouts. Accessibility
scans passed for the two-product order-review forms. Browser tests use fixtures,
not real purchases or a live moderation journey.

Delivered/completed account order details offer a review form for each distinct
product. Multiple variants of one product share one entry point. Other order
statuses and guest-access order views do not offer these forms. Product-page
review copy links to account orders as the purchase-linked entry point.

Submission includes the product ID and order ID from the authenticated order
read. Nothing is added to the product URL, router state or browser storage.
Separate product forms preserve their own pending/success/uncertain state while
mounted. Order refresh, navigation or account changes discard drafts and guards;
backend uniqueness and ownership checks remain authoritative. The server rechecks
order ownership, product membership and purchase status; the frontend never grants
a verified badge or bypasses moderation. No new backend inspection or changes
were needed for this step, and no live reviews were submitted.

## Account review management

Verified on 22 October 2026: 89 unit/component tests and 22 focused desktop/mobile
account/public-review browser tests passed. Edit-form accessibility scans and
desktop/mobile screenshot checks passed. All review writes used isolated fixtures.

`/account/reviews`, linked from the account page, reads the current account's
reviews using authenticated no-store requests. Responses are checked against the
current account before display. Account changes unmount the private view and drafts.
The API returns a plain paginated list without totals, so Next is available for a
full 20-row page; an empty subsequent page can return to the previous one.

Pending/approved reviews can be edited; saving returns them to moderation.
Rejected reviews cannot be edited. Empty title/body values are sent as empty
strings so they clear existing text. UI bounds retain the creation limits of
200 title characters and 2,000 body characters. Deletion requires explicit
confirmation and is only reported successful after the API's empty success response.
Neither write is replayed automatically, and list paging/refresh is disabled while
a write is in flight. An uncertain write blocks further changes for the mounted
account review page, including after a read-only refresh; navigating away can lose
that guard. Users are told to resolve uncertainty before repeating a change.

Drafts stay in memory; no review text is persisted locally. Backend ownership and
moderation remain authoritative. No backend files were modified and browser writes
use fixtures, not real reviews. Live edit/delete journeys remain unverified.

## Review helpfulness voting

Verified on 22 October 2026: the production build, 89 unit/component tests and
20 focused desktop/mobile review/voting browser tests passed. Accessibility scans
passed; desktop/mobile screenshots were inspected. API writes used fixtures only.

Signed-in readers can mark another author's approved review helpful or not
helpful using `POST /reviews/{id}/helpful`. Guests see a sign-in link and authors
cannot vote on their own reviews. The server keeps the first vote and silently
ignores later votes, even if a later request chooses the opposite option. Because
the response is empty and does not disclose the saved choice, the UI confirms
request acceptance only, never claims a vote changed, and does not invent count
increments or a selected state. Counts are explicitly the last loaded snapshot.

Both controls are disabled while submitting and after an accepted or uncertain
response. Writes are not automatically retried. Vote UI state is in memory and
resets on review unmount/account changes; no personal vote-history endpoint was
verified. The backend remains authoritative across reloads or repeat requests.

At this historical checkpoint, no review-photo upload route existed and backend
files were unchanged. The subsequently approved Review photo management checkpoint
below adds upload/removal support. Voting tests do not submit real votes.

## Account wishlist

Verified on 22 October 2026: production build, 89 unit/component tests and 22
focused desktop/mobile wishlist/device-save browser tests passed. Automated
accessibility scans passed and desktop/mobile screenshots were inspected.

The Saved page now includes a separate authenticated account wishlist. It uses
`GET /me/wishlist`, explicit single-piece `POST /me/wishlist` copies from device
saves, and `DELETE /me/wishlist/{product_id}` removals. Catalogue/product save
buttons still save to this device; nothing is automatically uploaded or merged.
Removing an account item does not remove its device copy, and vice versa.

Account data stays in memory, uses no-store reads and is discarded on account
change or sign-out. Guests make no private wishlist requests. Failed or invalid
reads block account changes. Writes are never automatically retried; ambiguous
responses lock further writes for the mounted page, even after a read refresh.
Navigation/reload loses that guard; server idempotency remains authoritative.

The inspected backend stores the account list in Redis with a 90-day expiry
renewed by additions and omits unavailable products. This is not permanent
archival storage. The UI does not claim unavailable additions are visible, display
the misleading backend added_at value as a save date, or reserve stock/prices.
Refresh explicitly to see changes from other devices; no live push sync is added.
Backend files are unchanged. Browser verification uses fixtures, not real accounts.

## Profile and saved addresses

Verified on 22 October 2026: the production build, 102 unit/component tests and
20 focused desktop/mobile profile/address browser tests passed. Automated
accessibility scans passed; desktop/mobile screenshots were inspected. Tests
cover profile ownership, input validation, address CRUD/defaults, the address cap,
guest access, sign-out privacy and uncertain writes without automatic replay.

Account navigation now links to `/account/profile` and `/account/addresses`.
Profile reads/updates use `/me`; only changed name/phone fields are submitted.
The backend ignores null updates and rejects empty strings, so existing profile
values cannot be cleared. The form explains this rather than claiming a deletion.
Confirmed name changes update the in-memory account greeting, not auth tokens or roles.

Saved addresses support list, add, edit, explicit deletion confirmation and default
selection through `/me/addresses` and its item/set-default routes. The form uses
creation bounds for both new and edited addresses. Empty address labels are sent
as empty strings. The ten-address cap is surfaced; the server remains authoritative.
Deleting a default does not choose a replacement or change existing order addresses.
Saved-address selection at checkout is now connected through explicit copying.

Private reads use no-store and validate response shapes; profile owner IDs must
match the signed-in account. Keyed account views discard drafts on account changes.
No profile/address data is written to browser storage. Writes are not replayed;
ambiguous outcomes lock changes for the mounted page, including after read refresh.
Navigation/reload loses that guard, so users must resolve uncertainty before retrying.
Address creation has no verified idempotency key; lost responses must not be replayed.

Password changes and profile-photo uploads have separate account screens (below).
Email changes and other account settings remain outside this step. Backend files
are unchanged, and browser writes use isolated fixtures.
No real account updates, customer emails or deployment were performed.

## Saved-address selection at checkout

Verified on 23 October 2026: final production build and all 28 focused desktop/mobile
checkout browser tests passed, including accessibility scans and screenshot review.
The 102 unit/component tests passed during implementation on 22 October; the interrupted
browser run was rerun to completion on 23 October. No live purchases were made.

Signed-in checkout reads `/me/addresses` using authenticated no-store requests.
Selecting an option does not change the draft until Use selected address is pressed.
Only street, city and province are copied; recipient, phone and notes are preserved.
Defaults are labelled but never applied automatically. Manual edits and refreshing
the saved list do not update stored addresses or overwrite delivery drafts.

The existing checkout submits the reviewed shipping-address snapshot, not a saved
address ID. Nonstandard province labels are preserved as selectable values because
the backend accepts text, not an enum. Invalid saved-address lengths require manual
correction. Failed/empty address reads leave manual delivery entry available.
Guests never request saved addresses. Drafts stay in memory and existing account
change, review, placement and recovery safeguards remain in effect. Backend files
are unchanged; automated orders use fixtures, not live purchases.

## Customer notification preferences

Verified on 23 October 2026: production build, 111 unit/component tests and 18
focused desktop/mobile browser tests passed. Automated accessibility scans passed;
desktop/mobile screenshots were inspected. Backend files and live accounts were
not changed, and no notifications were sent.

`/account/notifications`, linked from the account page, reads and partially updates
`/me/notification-preferences`. The five customer controls cover order emails,
promotional emails, new-arrival emails, SMS order updates and WhatsApp order updates.
Only explicit changes are sent after Save; reading or toggling never submits a write.
False values are preserved. Unsupported seller/admin settings are not exposed.

Authenticated no-store reads require all five boolean fields before displaying
controls; failed/incomplete responses never invent defaults. Success requires a
valid response matching every submitted change. Definite rejections retain drafts;
uncertain/mismatched responses lock writes for the mounted page, even after read
refresh. There is no automatic replay. Reload/navigation loses that guard.

Discard restores the loaded settings; refresh discards drafts and reads current
server settings. Account changes/sign-out unmount the private view. Preferences are
not persisted in browser storage. Saving records choices, not proof that a delivery
channel is configured or working; no test messages are sent. This screen is not a
global account/security-message opt-out. Backend files remain unchanged and browser
writes use fixtures only; live preference enforcement/delivery remain unverified.

## Customer notification inbox

Verified on 23 October 2026: production build, 125 unit/component tests and 20
focused desktop/mobile inbox browser tests passed. Automated accessibility scans
passed and both layouts were visually inspected. Live notification arrival and
real-account read marking remain unverified; test requests used isolated fixtures.

`/account/inbox`, linked from the account page, shows authenticated no-store pages
from `/notifications` (20 per page), unread filtering and the server's unread count.
The list/count exclude archived items; they are refresh snapshots, not live push
updates or a global navigation badge. Opening the inbox or following a link never
marks a notification read automatically. Text renders as text, not HTML.

Explicit read marking calls `/notifications/{id}/read`; a false `marked` response
is reported as not found, not success. Mark all requires confirmation and calls
`/notifications/read-all`. Its backend scope includes archived unread items and
all pages, so its returned affected count can exceed the visible unread count.
The UI explains this and refreshes server data instead of adjusting counts locally.

Only allowlisted existing internal destinations are linked (order/product UUID
routes and selected static customer pages). External, unsafe, parameterized and
unimplemented destinations are disabled. Existing destination authorization still
applies. Failed/invalid reads hide content and write controls; guests do not fetch
the inbox. Account changes/sign-out discard private state. Nothing is persisted
in browser storage, and there is no notification creation/delivery in this step.

Uncertain writes lock further changes for the mounted page, including after read
refresh or pagination/filter changes; no write is automatically replayed. Navigation
or reload loses that guard. Backend ownership is authoritative because inbox rows
do not expose owner IDs. Backend files are unchanged and test writes use fixtures.

## Customer password changes

Verified on 23 October 2026: production build, 134 unit/component tests and 16
focused desktop/mobile password browser tests passed. Automated accessibility scans
passed, and desktop/mobile screenshots were inspected. No real credentials were used.

`/account/password`, linked from the account page, submits current password, new
password and exact confirmation to `/me/change-password` only after explicit action.
The form mirrors the new-password length/character rules and does not trim passwords.
The server verifies the current password and rejects accounts without a local hash.
No provider type is inferred from the frontend user object.

An empty successful response clears the local auth state and shows a sign-in prompt;
no redundant logout or automatic sign-in request follows. The inspected backend
increments auth_version and removes sessions; protected requests compare token and
account versions. Real multi-session invalidation has not been exercised here.

Passwords are kept only in form/request memory, never browser storage, URLs or app
logs. Form fields clear when a request starts, including on rejection; browser/password
manager behavior is outside app storage control. Duplicate submissions are blocked.
Writes are never refreshed/replayed automatically. Network/server or unexpected
responses lock the mounted form and explain that the change may have succeeded.
An explicit local-session-clear action leads to sign-in without claiming server logout.
Navigation/reload loses the uncertainty guard, so users must resolve the outcome
before another attempt. Account changes/navigation discard drafts and ignore stale
responses. Tests use synthetic credentials and mocked writes; no real passwords or
backend files were changed.

## Profile photo uploads

Verified on 23 October 2026: production build, 148 unit/component tests and 16
focused desktop/mobile avatar tests passed. Automated accessibility scans passed;
desktop/mobile screenshots were inspected. Upload requests used isolated fixtures.

`/account/photo`, linked from account/profile pages, reads the current owner-scoped
profile image from `/me` and explicitly posts a multipart `avatar` field to
`/me/avatar`. JPEG/PNG/WebP selections must be nonempty and no larger than 2 MiB.
Local decoding checks that the image is readable and no larger than 25 megapixels;
the backend still validates bytes and converts to bounded WebP output.

Selection previews use revocable object URLs. Replacing, discarding, refreshing or
leaving the view releases local preview resources; no file data or URLs are stored
in browser storage. Discard clears an unsubmitted selection only. There is no
verified removal endpoint, cropping tool, or promise that replacement deletes the
previous stored file. Profile photos may appear with public reviews.

Stored URLs must be HTTPS without embedded credentials; broken image reads show a
fallback. Upload success requires a valid returned URL, then refreshes the saved
profile. Failed profile reads hide upload controls. Unknown/network/server outcomes
lock further uploads on the mounted page even after read refresh, with no automatic
replay. Reload/navigation loses that guard. Owner/account changes discard drafts.
No backend files or live storage objects were changed. Real Supabase upload,
conversion and public-image delivery remain unverified by these fixture tests.

## Order cancellation — 23 October 2026

Account and guest order screens now submit `POST /orders/{id}/cancel` only after
review and explicit whole-order confirmation. Guest access stays in a header;
lookup by order number still uses the returned UUID for cancellation. Current
order and shipment statuses gate submission; the server remains authoritative
for payment status and eligibility. Paid orders require support, not this flow.
Confirmed responses refresh order data. Unknown outcomes lock further writes
on the mounted page, including after read refresh; navigation/reload loses that
guard. Requests are never automatically replayed. Return submission was connected in the following checkpoint.

Verified production build, unit/component suite and 32 desktop/mobile order
browser tests with fixture responses. Backend files were read-only; no live
orders were cancelled. Live authorization, inventory release and notification
delivery still require integration verification. The Sites local-only workflow
was used; nothing was published.

## Return submission — 23 October 2026

The existing order draft now submits one brand shipment at a time to `POST
/returns` (account) or `POST /returns/guest` (private guest-token header). Review
and explicit confirmation are required. Delivered/completed order status,
10–1,000-character reasons, single-brand selections and purchased quantity bounds
are checked locally; the server owns authorization and prior-claim validation.
Only a matching `requested` response confirms submission, never approval/refund.
The reference remains visible across order refresh. Successful submission locks
further returns on this mounted page; uncertain writes lock all order changes,
including after read refresh. Navigation/reload loses these in-memory guards.
No automatic retries, financial details, attachments or local draft persistence
were added. Return history and guest lookup were connected in the following
checkpoint; account disputes were connected in the later dispute checkpoint.

Validation: production build, 153 unit/component tests and 42 desktop/mobile
order browser tests passed, including accessibility checks for draft review.
Desktop/mobile confirmation screenshots were inspected. Tests use fixture API
responses, not live return creation. Backend files
remain unchanged. The Sites workflow was local-only; nothing was published.

## Return history and status — 23 October 2026

`/returns` reads paginated account history; `/returns/:id` reads current details.
`/track-return` requires a return UUID and the original order's private guest code.
Guest credentials remain in component memory/header only, never URLs, router state
or browser storage. Reload or owner changes clear guest access. Protected reads
abort on unmount and use no-store. Account views are keyed to the signed-in owner.
Confirmation links open account detail or an in-place guest status view.

The views cover loading, empty lists, refresh, denied access and malformed data.
Response references, dates, pagination and item quantities are validated before
display. Unknown statuses do not imply success. Product names, refund amounts,
bank-transfer receipts and shipping instructions are not invented where the API
does not supply them. Item references are shown as references, not product names.
No return mutations or dispute actions are added by these status screens.

Verified: production build, 156 unit/component tests, 42 existing order browser
tests and 16 return-history/status browser tests passed. The return suite was
rerun after stabilising its status-change fixture. Desktop/mobile screenshots
and automated detail-page accessibility checks passed review.
Checks use fixture APIs, not live customer data. Backend files remain unchanged;
the Sites workflow remains local-only with no deployment.

## Account return disputes — 23 October 2026

`/returns/:id/dispute` reads the owning account's return and dispute, opens a
dispute for a rejected return, and sends messages only in `open`/`under_review`.
Opening text is trimmed to 10–2,000 characters; replies to 1–2,000. Each write
requires review and explicit confirmation. Matching response references, message
text/sender and dates are checked before success is shown. A confirmed reply must
appear in refreshed history before another message can be sent.

Only the backend's explicit missing-dispute error enables creation; generic
404/permission/malformed responses do not. Unknown write outcomes remain locked
across read refresh on the mounted page, without automatic replay. Reload or
navigation loses that guard. Conversation drafts are in-memory only. Resolved,
closed and unknown states disable messaging; no refund amount or approval is
inferred from a dispute outcome. Other senders are labelled neutrally because
the response supplies IDs, not names or roles.

Guest disputes are unsupported by the current backend API and direct guests to
support. No guest endpoint, admin action, attachment or backend change was added.
Verified: production build, 160 unit/component tests and 34 desktop/mobile
dispute/return browser tests passed. Conversation accessibility checks and
desktop/mobile screenshot review passed. Verification is fixture-only and local
under the Sites workflow; no real disputes
or messages were sent and nothing was published.

## Review photo management — 24 October 2026

`/account/reviews/:id/photos` supports owned-photo reads, local preview, explicit
upload and confirmed removal. JPEG/PNG/WebP files are limited to 5 MiB and 25
megapixels, with five photos per review. Rejected/hidden reviews are read-only.
Unknown writes remain locked across read refresh in the mounted page; navigation
or reload loses that guard. No image bytes or credentials are stored in browser
storage. Saved-image load failures have a fallback.

The user approved this backend expansion because no review-photo write API existed.
New authenticated `GET/POST /me/reviews/{review_id}/images` and `DELETE
/me/reviews/{review_id}/images/{image_id}` return the owned review. The multipart
field is `image`; reads are bounded to the byte limit plus one. Services validate
actual image bytes and decoded dimensions, convert to WebP, lock the active account
and review, and reset changed reviews to pending moderation with rating refresh.
The existing review-image table is reused; no migration is needed.

Photo removal and whole-review deletion queue durable storage cleanup. Cleanup
accepts only a generated UUID.webp in the review's exact storage prefix and checks
all known asset-reference columns before deletion. The orphan scan now protects
referenced review images. Unknown upload/commit failures queue reference-checked
cleanup; if the database also prevents queuing, an image-ID reconciliation event is
logged and the orphan scan/manual reconciliation remains necessary. Physical file
deletion is asynchronous and depends on the worker/outbox. No live assets were used.

Frontend production build, 163 unit/component tests and 26 desktop/mobile review
browser tests passed; desktop/mobile photo previews were visually inspected.
All 51 focused backend tests passed. New backend modules and targeted tests pass
Ruff; touched legacy modules still have lint findings. Backend tests use
mocked storage and database calls: native PostgreSQL concurrency, actual outbox
worker execution and Supabase delivery remain integration checks, not proven here.
The Sites workflow remained local-only; no deployment or commit was performed.

## Customer account deletion — 24 October 2026

`/account/delete` connects to the existing authenticated `DELETE /customers/me`
endpoint. Only customer accounts see the form. A password, the case-sensitive
`DELETE MY ACCOUNT` phrase (outer whitespace trimmed) and a retention acknowledgement
are required before submission. Password characters are preserved; confirmation
fields clear on submission and are never persisted by the app.

The screen explains active-order, return/dispute and pending-refund blockers,
retained financial/dispute records and internal identity keys, removed profile
credentials/addresses/review text/photo links/notifications, retained review
ratings/status, and asynchronous cache/image cleanup. It does not promise full
erasure, immediate external cleanup or removal of device-local saves/guest data.
Passwordless accounts need password access resolved first; seller/admin offboarding
is not implemented by this screen.

Only the expected empty 204 response confirms success and clears local authentication.
Known rejections require fresh confirmation. Network/server/unexpected outcomes
lock further writes while mounted and do not claim deletion succeeded. Leaving or
reloading loses this in-memory guard; the warning explicitly says not to repeat
an unresolved deletion. No automatic write retries or redundant logout are sent.

Backend inspection was read-only. Browser tests use fixtures, not real deletions;
live database blockers, session revocation and external cleanup were not executed.
Production build passed, all 163 unit/component tests passed with `--maxWorkers=2`,
and all 16 focused desktop/mobile deletion tests passed. An initial default-worker
unit run timed out in an existing cancellation test; the reduced-concurrency rerun
passed without changing that test or its timeout. Automated accessibility scans
passed and desktop/mobile screenshots were inspected; this is not a full audit.
The Sites workflow stayed local-only; nothing was committed or deployed.

## Google sign-in callback — 24 October 2026

`/auth/callback` now displays session restoration, confirmed active session,
cancelled attempt and failed/missing-session states. It relies on the existing
cookie-backed refresh and authenticated profile read, not URL tokens or a second
refresh loop. Cancellation/failure remains visible even if an older session exists.
Query/hash data is removed from the address bar and provider error details are not
rendered. A callback without error hints only establishes an active session, not
proof that a new Google sign-in occurred. No arbitrary return destination is used.

Google initiation accepts only HTTPS `accounts.google.com/o/oauth2/v2/auth`, without
credentials, nonstandard ports or fragments. The default feature gate remains off.

The approved backend change wraps the existing Google callback with fixed 303
failure/cancellation redirects, rollback attempts, state-cookie removal, no-store
and no-referrer response headers. Cancellation requires matching browser state and
consumes its single-use Redis record before returning `error=cancelled`; invalid or
expired state and other failures return only `error=failed`. Existing nonce, PKCE,
identity validation, account-linking restrictions and successful session creation
remain in the original handler. Unexpected failures are logged without provider
payloads, authorization codes or tokens. No credentials or deployment config changed.

The focused backend tests mock Google/Redis/database behavior. Browser tests use
isolated session fixtures, not real Google accounts. Live consent, registered
redirect URIs, cookie delivery across deployed origins, Redis and PostgreSQL still
require integration verification before enabling Google sign-in. Desktop/mobile
screenshots were inspected and automated callback accessibility scans passed.
Production build, 173 frontend unit/component tests (`--maxWorkers=2`), 14 focused
desktop/mobile browser tests and 13 focused backend callback tests passed.
The changed OAuth service and new tests pass Ruff; the existing auth route module
still has nine unrelated lint findings. Local-only Sites workflow; no commit/deploy.

## PayFast return/status checkpoint — 24 October 2026

`/payments/:id` and the existing provider success destination `/order/success/:id`
now show protected backend payment status. The approved backend change makes new
PayFast failure destinations `/payments/{order_id}?payment=failed`, preserving the
order reference without guest credentials. Existing already-issued checkout payloads
retain their old failure URL; this change does not rewrite them.

Neither return route treats its path, query or fragment as payment evidence. Query
and fragment data is removed from the address bar. Account access uses the existing
session; guests must explicitly enter the order's private code again. The code stays
in component memory and travels only in `X-Guest-Token`, not storage or navigation.
Signed-in customers can switch to guest-code access for a separate guest order.

`GET /payments/{order_id}/status` responses are checked for matching order ID,
payment ID, decimal amount and expected field shapes. Pending, processing, completed,
failed and refunded states use distinct wording; unknown states are neutral. Access
errors and malformed replies do not expose a payment panel or imply failure.
Manual refresh replaces the previous snapshot; there is no automatic polling,
initiation, reconciliation, payment retry, new order or provider request here.
Refund status is not presented as a bank receipt or refund allocation report.

At this historical checkpoint checkout supported COD only; the opt-in handoff
checkpoint below adds order creation/form submission. Retry controls remain separate.
No backend gateway flag or credentials were changed. Backend verification uses a mocked provider/database, and browser checks
use isolated fixtures. Real provider callbacks, database access controls and guest
email recovery were not exercised. Local-only Sites workflow; no commit/deployment.
Production build, 180 frontend unit/component tests (`--maxWorkers=2`), all 20
focused desktop/mobile browser tests and the backend return-URL regression test
passed. Automated accessibility scans passed and both screenshot layouts were
inspected. Browser assertions account for development Strict Mode restarting
initial reads and verify that payment requests remain GET-only. The new backend
test passes Ruff; the payment service retains four unrelated lint findings.

## Opt-in PayFast checkout/handoff — 24 October 2026

The frontend can select PayFast only when `VITE_ENABLE_PAYFAST=true` and the backend
quote marks it available. The example and default remain disabled. Changing payment
method obtains a method-specific signed quote, restarts review and removes the coupon
so it must be reapplied. Contact details stay in memory. COD uses its existing flow.
Order creation/recovery retains the existing checkout key; new responses must match
the requested payment method. Creating an order does not initiate or confirm payment.

After a newly confirmed pending PayFast order, explicit preparation calls
`POST /payments/initiate` with account authorization or the private guest header.
Guests must acknowledge keeping their private code before leaving. The handoff
validates the exact configured sandbox/live destination, complete string field set,
attempt basket, decimal amount, currency, return URLs and callback origin. A separate
Continue button submits a native same-tab POST to the provider. No card details are
collected. Provider tokens, form contents and guest codes are not persisted by the app.

A non-secret per-order tab marker is written before initiation and blocks repeat
attempts after failure/reload. Recovered orders cannot start a new payment here;
they link to backend status instead. There is no automatic initiation, provider POST,
payment retry, payment-method switch on existing orders or duplicate-order shortcut.
The marker is not a server-wide idempotency guarantee and does not coordinate tabs.
Unresolved attempts require status checks/support; retry design remains unfinished.

Public configuration: `VITE_PAYFAST_ENVIRONMENT=sandbox` selects only the inherited
UAT endpoint; `live` explicitly selects the inherited production endpoint.
`VITE_PAYFAST_CALLBACK_ORIGIN` must match the backend's public API origin (no trailing
slash). Return URLs must match the frontend's current origin. Custom provider endpoints
are rejected, not implicitly trusted. These checks validate the inherited contract;
they do not independently certify provider endpoints or production readiness.

The narrowly approved backend compatibility fix falls back to the saved order-address
phone when an authenticated customer's profile phone is absent. Order ownership,
guest authorization and all payment verification remain server-side and unchanged.

Default browser tests skip `payfast-checkout.spec.ts`; run its opt-in fixture scenarios
in a fresh test process with `VITE_ENABLE_PAYFAST=true`,
`VITE_PAYFAST_ENVIRONMENT=sandbox`,
`VITE_PAYFAST_CALLBACK_ORIGIN=http://127.0.0.1:3000`, and `CI=1`, then run
`npm run test:browser -- tests/browser/payfast-checkout.spec.ts`. The fixtures intercept
provider navigation and all API calls. Do not enable real payments to run these tests.
No real provider requests, charges, saved runtime configuration changes, commits or
deployments were performed. The Sites workflow remained local-only.
Verified: default-disabled production build, all 195 frontend unit/component tests,
28 existing COD desktop/mobile checkout tests, 10 opt-in PayFast desktop/mobile
tests and 2 focused backend guest/account initiation tests passed. Handoff automated
accessibility scans passed and desktop/mobile guest screenshots were inspected.
The targeted backend test passes Ruff; four unrelated payment-service lint findings
remain. Real provider acceptance, payment completion, native database races and
cross-tab retry safety are not established by these fixtures.

## Backend PayFast retry hardening — 24 October 2026

New attempts use a unique UUID basket, returned as `attempt_id`, rather than reusing
the order UUID. The frontend requires that basket to match the returned attempt ID;
success/failure URLs still identify the order. Deploy these contract changes together.
Old response shapes fail closed in the updated handoff validator.

Attempt records reuse `payment_callbacks` with `gateway=payfast_attempt`, linked to
the existing payment. These are durable business records, not disposable logs:
retain them with payment history. No migration was needed. The attempt claim and
active-attempt pointer commit before provider I/O. A lost response/crash leaves a
blocked starting attempt instead of allowing another token request. Order/payment
state is rechecked under the order lock before handing a form to the browser.

Repeated initiation is rejected. PayFast retry requires a verified failed attempt
and a fresh provider response with consistent terminal-failure status, the same
attempt/transaction, amount and currency. Unresolved, completed/refunded, legacy or
unverified attempts cannot retry automatically; online-to-COD switching is blocked.
A newly discovered successful payment is preserved rather than retried. New retries
create another attempt record and retain the prior record.

Failure callbacks now require provider reconciliation just as success callbacks do.
Callbacks resolve their attempt before the order lock, then refresh cached payment
state after acquiring it. A stale attempt is audited without changing the current
payment. Conflicting provider statuses and mismatched evidence do not authorize a
transition. Provider tokens/signatures are not stored in attempt records. Customer
retry UI and live payments remain disabled; this is not a production-readiness claim.

The frontend build and all 197 unit/component tests passed. Offline backend
validation: 45 focused tests passed. The dedicated PostgreSQL suite
reported 45 skips (including the two new concurrent-session tests) because no
`TEST_DATABASE_URL` was configured. Docker's local engine was unavailable, so native
concurrency remains unverified. Earlier attempt-contract browser checks passed all
10 scenarios; the final fixture using a distinct attempt/order ID was updated but
its rerun was not approved. Real provider acceptance of attempt baskets and terminal
failure semantics must also be verified before enabling payments. No charges,
deployment or commit occurred. Three pre-existing payment-service lint findings remain.

## Design and assets

Source: Canva `WearHowZ — Identity & UI Foundations` (`DAHV5FXxo-Y`) and
`WearHowZ · 01 Shopper — Complete Design` (`DAHV6TgX59U`).
The Canva inspection transaction was discarded; the designs were not changed.

`public/assets/wearhowz-logo.png` and `editorial.png` are approved asset **previews**
returned by Canva (200×66 and 200×100). Replace these with original-resolution
exports before final visual approval. No new imagery or sample products were
invented. Georgia and Segoe UI are provisional system fonts matching the supplied
serif/sans direction; exact font-family specifications remain to be confirmed.

## Deployment later

Nothing is published. `npm run build` creates `dist/`. A production host must serve
SPA fallback routes and proxy `/api` to FastAPI (or supply an explicitly configured
API origin with compatible CORS/cookies). Do not expose the Vite development
server publicly. Production headers, callback URLs, secrets and end-to-end
verification belong to the deployment stage.

## Existing Git history

The old frontend was already absent from disk when this build began, but its
files (including 6,247 `node_modules` paths) are still tracked in the repository.
The new `.gitignore` prevents new dependency/build files from being added; it does
not untrack old entries. No staging, commits, or index cleanup were performed.
Review the legacy deletions and untrack generated dependencies before committing;
do not blindly stage the entire workspace.
