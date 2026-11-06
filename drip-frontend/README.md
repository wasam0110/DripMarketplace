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

Browser tests use installed Microsoft Edge and start their own development server
at `http://127.0.0.1:4173` (the normal development URL remains port 3000),
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
Role-specific landing pages are now connected; see the role-entry checkpoint below.

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
The database/browser verification limitations above describe that checkpoint;
the follow-up below supersedes them.

## PayFast verification follow-up — 25 October 2026

The final distinct-attempt/order-ID browser fixtures passed all 10 desktop/mobile
scenarios. Provider navigation and API calls were intercepted; no real payment
requests were made. Feature flags were set only in the test process, not saved.

Native PostgreSQL 15 verification passed all 45 tests in
`tests/integration/test_payment_api.py` and
`tests/integration/test_payfast_attempt_races.py`. The two race cases use independent,
committed database sessions and confirm that concurrent initiation or retry cannot
issue two new attempts. Provider transport remains mocked: these results do not
verify PayFast's own concurrency, callbacks or settlement behaviour.

Testing used a dedicated localhost-only Docker container, a database ending in
`_test`, disposable per-test schemas and temporary database storage. No application
database, environment file or existing Docker volume was used. The initial run had
44 passes and one stale COD response assertion; adding the expected nullable
`attempt_id` field restored the exact response check. No COD business logic changed.

Malformed/non-object token responses and non-string tokens now raise controlled
PayFast protocol errors before any follow-up provider request. The four focused
unit files (`test_payments.py`, `test_payfast_attempts.py`,
`test_payfast_evidence.py`, `test_payment_return_urls.py`) passed all 61 tests.
Ruff passed for the adapter and both changed payment test files. Existing Pydantic
and UTC datetime deprecation warnings remain.

Remaining provider gate: confirm merchant UAT credentials and status API access,
acceptance of per-attempt baskets, authoritative amount/currency evidence, terminal
failure semantics, callbacks and reconciliation with actual sandbox responses.
The [published PayFast status example](https://gopayfast.com/docs/) does not include
the monetary evidence required by this backend; do not weaken verification to match
an incomplete example. Live payments and customer retry controls remain disabled.
This is targeted verification, not full backend release certification.

## Role-specific workspace entry — 25 October 2026

The `/seller` and `/admin` routes are now role-gated landing pages. Email sign-in,
restored login sessions, email-verification continuation and the successful Google
callback continuation choose a fixed destination from the server-returned role:
customer/unknown roles go to `/account`, sellers to `/seller`, admins to `/admin`.
URL parameters cannot choose or grant a privileged role. Only exact `seller` and
`admin` matches can render the corresponding workspace; there is no implicit role
hierarchy. Loading, missing-session, restoration-error and wrong-role states are
explicit. A cleared or changed session removes the workspace content.

Existing `/account` links remain available, including account settings and sign-out.
Seller/admin accounts now have a link back to their own workspace. Administrator
authenticator input remains admin-only. No backend authorization was changed:
frontend route checks are a presentation boundary, never an API security control.

These are entry pages, not operational dashboards. They show only the authenticated
account information, existing account/storefront links and an explicit description
of tools not yet connected. Seller role does not imply seller approval. No invented
balances, counters, approval state or privileged operations were added. Next:
seller onboarding/approval-state contracts and UI, then seller operational tools;
admin operational tools remain a separate checkpoint. PayFast gates are unchanged.

Validation: production build/TypeScript and all 219 frontend unit/component tests
passed. The focused browser run passed 46 desktop/mobile tests across
`role-entry.spec.ts` and `google-callback.spec.ts`, including sign-in destinations,
wrong-role/anonymous access, logout, verification/callback links and admin-only
authenticator submission. Workspace automated WCAG 2 A/AA and 2.1 AA scans and
horizontal-overflow checks passed; desktop/mobile screenshots were visually
reviewed. These are mocked-API checks, not live authentication/provider acceptance
or complete accessibility certification. The Sites skill kept this checkpoint
local-only and reused the existing WearHowZ styling; no publication, new backend
edits, real account writes, payment requests, commit or push occurred in this step.

## Seller application status — 27 October 2026

The seller workspace now reads `/seller/me` for verified seller accounts only.
It shows the server's pending-payment, pending-approval, active, suspended or
rejected state, registration amount outstanding and recorded payment date.
Zero fees do not imply a paid receipt or approval. Unknown states remain
unavailable, and malformed or contradictory displayed fields fail validation.
The API does not expose rejection reasons or transfer instructions; none are
invented. No registration, receipt, approval, payment or operational writes occur.

Reads use the existing authenticated, no-store request hook. Owner changes
remount the reader, stale responses are discarded, and refresh failures remove
previously displayed status. Unverified accounts see verification guidance instead
of making a seller-profile request. Existing exact-role/session guards remain.
The Sites local-only workflow reused existing WearHowZ styling without publishing.

Validation: production build/TypeScript, all 244 unit/component tests and 44
focused desktop/mobile browser tests passed. Automated accessibility and overflow
checks passed; payment-pending screenshots were visually reviewed at both sizes.
Browser APIs were mocked, including assertions that seller requests are GET-only.
This does not verify real seller onboarding or email delivery. Backend files,
payment flags and provider configuration are unchanged. No commit or push occurred.

Seller registration follows in the next checkpoint below. Profile and operational
tools remain unfinished; admin tools remain a separate checkpoint.

## Seller registration and pricing — 27 October 2026

`/seller/register` is linked from login/customer registration. It creates a new
seller account, not a conversion of an existing account. Signed-in users are sent
back to their workspace/account controls; restoration failures block the form.
The form matches the inspected seller request schema, including optional surname,
Pakistani mobile validation, brand description/return policy and 0–10,000 extra slots.

Pricing comes from `/seller/register/slot-price?extra_slots=...`; no fee defaults
are invented. The client validates quantities and decimal arithmetic, requires
explicit review, and rechecks pricing before `POST /seller/register`. Changed
prices restart review without submission. This is not a signed/locked quote:
pricing can still change before the server creates the account. The confirmed
response supplies the final amount, and a difference is explicitly surfaced.
No transfer, PayFast initiation, receipt upload or approval is performed here.

Drafts/passwords remain in memory. A non-secret sessionStorage marker is saved
before submission; a missing response or malformed success blocks another attempt
in that tab, including after reload. Double clicks are suppressed. Explicit 409/422
rejections permit corrections, clear the password and never retry automatically.
Storage failure prevents writes. Successful submission retains the guard and asks
the applicant to verify email/sign in; email delivery is not assumed successful.
The API has no idempotency/recovery key for registration. This local tab guard does
not coordinate other tabs/devices and is not a substitute for server idempotency.
Uncertain applicants must check their account/email or contact support, not resubmit.

Validation: production build/TypeScript and all 269 unit/component tests passed.
The 32 role-entry browser cases passed alongside the initial registration checks;
all 22 final registration cases passed on desktop/mobile Edge. They cover zero/nonzero
fees, exact payloads, review, duplicate clicks, changed/unavailable prices, lost or
malformed responses, 422 correction, storage failure, reload and signed-in guards.
Automated accessibility scans and overflow checks passed, with desktop/mobile
review screenshots inspected. Tests use mocked APIs and create no real accounts.
The Sites local-only workflow preserved existing styling. Backend files and payment
flags remain unchanged; no live provider/email test, commit, push or deployment.

Brand-profile editing follows below; remaining seller operational tools are separate.

## Seller brand-profile editing — 27 October 2026

`/seller/profile` is linked from the loaded seller application panel. Only verified
seller sessions mount its private reader/editor; exact-role checks do not grant
admins access to another seller's form. Backend authorization remains authoritative.
The existing `/seller/me` GET/PATCH contract permits onboarding/profile access
without requiring an active brand; editing does not change approval or payment state.

The editor whitelists description, return policy, WhatsApp number, Instagram handle
and six-digit hex brand colour. Only changed fields are sent. Null optional text
renders empty without creating changes; explicitly clearing saved text sends an
empty string, matching the inspected update contract. Brand name, fees, slots,
status and logo are never included in profile patches. Logo upload is covered below.

Save confirmation requires a valid response, the same seller ID and exact returned
values for every requested change. Double clicks are suppressed. Uncertain or
mismatched responses lock writes on the mounted page; refreshing only reads the
server state and does not retry or unlock the change. Explicit validation errors
remain editable. Drafts stay in memory, and refresh/discard/owner changes remove
them. No automatic replay, optimistic success or cross-tab version-conflict
protection is claimed; avoid concurrent edits from multiple tabs.

Validation: build/TypeScript and all 289 unit/component tests passed. All 32 focused
desktop/mobile browser tests across seller profile and status passed, including
exact patches, explicit clearing, discard/refresh, lost responses, mismatched
confirmation, 422 correction, denied reads and role/verification gates. Automated
accessibility and overflow checks passed; both profile layouts were visually
reviewed. API writes were mocked, not applied to real seller records. The Sites
local-only workflow reused existing styling. Backend files and payment flags are
unchanged; no commit, push or deployment occurred.

## Seller brand-logo upload — 27 October 2026

`/seller/logo`, linked from the brand-profile editor, supports local preview,
discard and explicit multipart upload using the existing `/seller/logo` endpoint
and its `logo` field. Only verified seller sessions can load the page's private
data. JPEG, PNG and WebP files are checked locally for size (2 MiB), decodability
and dimensions (25 megapixels); backend validation remains authoritative.
Selections remain in memory and object URLs are revoked when discarded or replaced.

Successful uploads require an HTTPS logo URL and a fresh `/seller/me` read matching
both the uploaded URL and the original seller ID. The loaded seller identity is
pinned for the mounted session. Duplicate clicks are suppressed; uncertain or
mismatched results lock uploads on that page without automatic retries. Refresh
only reads saved state and discards the local selection; it does not unlock an
uncertain write. Definite validation rejections allow explicit correction.

The UI explains public visibility, server conversion/resizing and local-only
discard. The API does not support removing a saved logo, and replacement does not
promise deletion of previously stored image objects. No crop editor is provided.
The existing backend contract supports this flow without backend changes.

Validation: build/TypeScript and all 306 unit/component tests passed. All 46 focused
desktop/mobile browser tests across seller logo and profile passed, including
multipart requests, file rejection, read-back confirmation, identity mismatch,
uncertain responses, explicit correction and role gates. Accessibility and
overflow checks passed; desktop/mobile logo screenshots were visually reviewed.
Browser API/provider responses were mocked; no live storage upload was performed.
The Sites local-only workflow preserved existing styling. No commit, push or
deployment occurred.

## Seller catalogue browsing — 27 October 2026

`/seller/products` is linked from active seller status. Verified seller sessions
read the authenticated `/seller/products` API; backend active-account checks
remain authoritative. All/published/draft filters reset pagination to page one.
The list displays base price, recorded stock, image count and server-reported
slot capacity without claiming available-to-buy stock or moderation clearance.

Responses are validated before rendering. Loading, empty and failed reads are
distinct; private reads use no-store requests and cancel stale responses. The
mounted reader is keyed to the signed-in owner. The API supplies 20 rows per page
but no total count, so a full page enables Next and may lead to an empty page.
Previous remains available there; changing filters resets the page.

Validation: production build/TypeScript, 35 focused catalogue/status unit tests
and 12 mocked desktop/mobile browser tests passed. Browser checks cover filtering,
pagination, refresh, denied reads, role/verification gates, accessibility and
horizontal overflow. Both layouts were visually reviewed. Initial browser test
counting was adjusted to allow React StrictMode's duplicate initial GET while
retaining exact subsequent request checks. No live backend data was changed.
The Sites local-only workflow reused existing styles; backend changes were not
needed. No commit, push or deployment occurred.

The catalogue browsing checkpoint is read-only. Basic creation/editing follows
below; images, variants and publishing controls remain separate.

## Seller product drafts and basic editing — 27 October 2026

`/seller/products/new` creates an unpublished, uncategorized draft without images
or variants. `/seller/products/:id/edit` reads the private seller detail endpoint
and updates only changed name, description, regular/sale price and SEO fields.
Both are linked from the catalogue. Existing category, inventory and publishing
state are omitted from edits. Editing a published product can affect its live
listing immediately; this warning is shown before saving.

Verified exact-role seller sessions must load an active seller profile before the
form mounts. Product IDs and seller ownership are checked on reads and returned
saves. Price inputs follow the API's whole-PKR range of 100–500,000, with sale price
strictly below regular price. Clearing sale/SEO fields sends null. Save confirmation
compares every requested value; duplicate clicks and automatic write replay are
blocked. Uncertain edits stay locked through read-only refresh on the mounted page.
Refresh and discard remove local unsaved edits, not server data.

Creation sets a non-secret per-seller pending marker in sessionStorage before POST.
Uncertain/mismatched responses retain it across same-tab reloads; confirmed success
or known rejection removes it. A confirmed draft opens its owned editor. No draft
content or credentials are stored. This safeguard is not cross-tab/server-side
idempotency; unresolved creation requires catalogue inspection/support before a new
attempt. The API also has no optimistic version-conflict protection for edits.

Validation: final production build/TypeScript passed; all 327 unit/component tests
passed with `npm test -- --maxWorkers=2`. The first concurrent run had two unrelated
5000 ms timeouts; the lower-concurrency rerun passed without relaxing timeouts.
All 38 mocked desktop/mobile editor and catalogue browser tests passed after fixing
an ambiguous discard-button test selector. Accessibility/overflow checks passed;
both editor layouts were visually reviewed. The Sites local-only workflow reused
existing form styles. Backend files were unchanged; no live writes, commit, push
or deployment occurred.

## Seller categories and variants — 28 October 2026

`/seller/products/:id/options`, linked from the basic editor, manages an existing
owned product's category and variants. The verified seller/active-account gate
is reused. Private product responses are checked for product and seller identity;
backend ownership enforcement remains authoritative. Public `/categories` supplies
selectable categories. Missing saved categories remain visible and unchanged until
an explicit replacement or Uncategorized selection; failed reads never clear them.
Category saves send only `category_id` and verify the returned assignment.

Variants can be added with size type/value, colour, initial stock and optional
whole-PKR override. The server generates the SKU. Existing variants allow changed
size/colour, active status and explicit pricing actions; stock and SKU are never
included in update payloads. The API reports effective price rather than raw
override state, so the editor never infers whether an override exists. Keep sends
no price change, inherit sends null and set sends a validated override. Returned
variant identity, SKU, changed fields and requested effective price are checked.
New variants are identified by comparing returned IDs with the loaded product.
Stock is displayed as a snapshot and may change concurrently after creation.

All option writes share a mounted-page lock. Uncertain results stay locked through
read refresh; no writes are automatically retried. Variant creation also uses a
per-seller/product sessionStorage pending marker, containing no draft or credentials,
to block another creation after same-tab reload. This is not server-side or cross-tab
idempotency. Unresolved creation requires inspection/support before another attempt.
Refresh/cancel discard local variant drafts. Existing stock adjustment, SKU renaming,
variant deletion and publishing are not offered by this screen.

Validation: production build/TypeScript and all 339 frontend unit/component tests
passed (`npm test -- --maxWorkers=2`). All 58 mocked desktop/mobile browser tests
for product options and the basic editor passed, covering category assignment and
removal, unavailable categories, price actions, stock preservation, creation,
uncertain writes, cancellation, access gates and owner mismatch. Accessibility and
overflow checks passed; desktop/mobile layouts were visually reviewed. The Sites
local-only workflow preserved existing styling. Backend changes were unnecessary;
no live API writes, commit, push or deployment occurred.

## Seller product images and publishing — 28 October 2026

`/seller/products/:id/media` is linked from the basic editor and category/variant
screen. It reuses verified-seller, active-account and owned-product checks. The
backend detail schema now requires `is_published`, populated from the persisted
product in `ProductService._to_detail`; deploy/restart that backend change with
this frontend. A missing publication field blocks media controls rather than
assuming draft state. No database migration or publishing-rule change was needed.

The page supports single-image uploads (multipart `images`), local preview/discard,
primary selection, complete-list reordering and confirmed removal. Local checks
enforce JPEG/PNG/WebP, non-empty files up to 5 MiB and 25 megapixels; the six-image
product limit is shown and backend validation remains authoritative. Local object
URLs are revoked. Saved previews require safe HTTPS URLs and have load-failure
fallbacks. Removal verifies attachment absence, not completed storage cleanup.

Publish/unpublish and image removal require explicit confirmation. Publishing is
locally disabled without an image or variant; the backend makes final capacity
and eligibility decisions. The last image of a published product cannot be removed
through this UI. Published status does not promise moderation clearance or public
visibility. Unpublishing does not cancel existing orders.

Each mutation is followed by a fresh authenticated owned-product read to confirm
the specific result. Failed read-back (including 4xx), malformed results and
mismatches lock writes on the mounted page; refresh inspects state without replay
or unlocking. Duplicate clicks are suppressed. These locks do not provide
cross-tab or server-side idempotency; resolve uncertain outcomes before retrying.

Validation: production build/TypeScript, all 349 frontend unit/component tests
(`npm test -- --maxWorkers=2`), 94 mocked desktop/mobile browser regressions, and
the 3 focused backend publication-response tests passed. Accessibility/overflow
checks and desktop/mobile screenshot review passed. Backend tests used the project
root virtual environment; global Python lacked test dependencies. Ruff 0.17.3 was
installed into that environment with approval. The new test is lint-clean; the two
existing backend files retain the same 74 diagnostic codes/messages as HEAD, so
full-file Ruff is not green. No unrelated lint rewrites were made.

The build now warns about a JavaScript chunk exceeding 500 kB (approximately 502 kB
minified / 142 kB gzip); code splitting remains a later performance checkpoint.
The Sites local-only workflow preserved existing styles. No live upload, real
product publication, full backend-suite run, commit, push or deployment occurred.

## Seller inventory — 28 October 2026

`/seller/inventory` is linked from the active seller workspace and catalogue.
Verified seller sessions load active-account status before inventory access.
The authenticated list supports product/SKU search, low-stock filtering and
20-row pagination. It displays physical, reserved and available units plus reorder
thresholds. Response validation checks variant/product identity, stock arithmetic,
low-stock classification and pagination. A stock editor fetches fresh private
variant detail before allowing changes; failed reads never produce an empty form.

Both relative adjustments and absolute physical counts require review and explicit
confirmation. Adjustments require a reason and delta from -10,000 to +10,000,
excluding zero. Physical counts and thresholds accept 0–999,999. Local checks
protect the displayed reserved quantity; existing backend row locks and reservation
checks enforce this against current database state. Absolute counts explicitly
replace physical units, including reserved units. Only a changed threshold is sent.
Stock receipts are validated before reporting success: adjustment arithmetic uses
the server's previous quantity, which may differ after concurrent order activity.
An untouched threshold is not compared with a stale snapshot. The list refreshes
after confirmed writes to show the latest quantities.

Duplicate clicks are suppressed. A non-secret, per-account pending marker is set
in sessionStorage before stock writes. Uncertain responses or malformed receipts
retain it through refresh and same-tab reload; confirmed success or known request
rejection clears it. Pending writes block further stock mutations while leaving
inventory reads available. This is not cross-tab/server-side idempotency or a
reconciliation ledger; unresolved writes require inspection/support before another
adjustment. No reasons, draft quantities or credentials are persisted. Unsaved
editor changes are discarded by filter/page changes, close or refresh.

The seller inventory query now sorts by product ID and variant ID before applying
offset/limit, giving unchanged catalogues a deterministic page order. This does not
provide a snapshot across concurrent catalogue changes. A focused backend regression
checks ordering, seller/deletion scope, low-stock condition and pagination SQL.
Stock mutation and reservation rules were not changed.

Validation: production build/TypeScript, all 363 frontend unit/component tests and
42 mocked desktop/mobile inventory/status browser tests passed. Browser checks
cover reviewed adjustments/counts, reservations, concurrent receipt arithmetic,
uncertain response locks through reload, correction, filters, pagination and access
gates. Accessibility/overflow checks passed and both layouts were visually reviewed.
The backend ordering test passed; its Ruff check is clean. Inventory service retains
the same 22 lint findings as HEAD. Native database races, real stock mutations and
the full backend suite were not run for this UI checkpoint. The existing bundle-size
warning remains (approximately 513 kB minified / 145 kB gzip).
The Sites local workflow reused existing styling. No commit, push or deployment.

## Seller fulfilment — 28 October 2026

`/seller/orders` and `/seller/orders/:id` are linked from the active seller
workspace. Verified seller sessions load active-account status before private
order reads. The queue supports the API's status filters and 25-row pagination.
The detail screen displays the seller's brand items, subtotal, delivery address,
tracking and timestamps. Seller-order UUIDs are kept distinct from parent order
UUIDs. Reads validate identity, amounts, item arithmetic and pagination; backend
ownership checks remain authoritative. Unknown statuses have no write action.
Empty/failed reads and incomplete delivery addresses do not enable fulfilment.

The UI follows the existing pending → processing → shipped → delivered transitions.
Each action requires review and confirmation. Shipping requires a trimmed tracking
number (up to 100 characters) and accepts an optional courier name. Tracking fields
are sent only with shipping. Delivered/cancelled orders offer no further transition.
The existing backend enforces payment/COD verification, stock deduction and
settlement rules; this checkpoint does not add a payment-verification action.
The delivery confirmation explains that delivery can start earnings settlement.

After PUT, a fresh authenticated detail read must match seller-order ID, parent
order ID, requested state and any submitted tracking fields. A success message
alone is not treated as confirmation. Duplicate clicks are suppressed; failed
read-back (including 4xx), malformed/mismatched state or uncertain writes keep the
order locked. A non-secret per-account/order sessionStorage marker preserves the
lock across same-tab reloads. Known request rejection or confirmed success clears
the marker. Customer addresses, tracking and form drafts are never persisted.
This safeguard is not cross-tab/server-side idempotency or automatic reconciliation;
unresolved updates require order inspection/support before further changes.

Validation: production build/TypeScript, all 374 frontend unit/component tests and
38 mocked desktop/mobile fulfilment browser tests passed. Tests cover preparation,
tracking/shipping, delivery, payment/COD rejection, review cancellation, uncertain
results through refresh/reload, queue filters/pages, terminal/unknown states,
address completeness and access gates. Accessibility and overflow checks passed;
both layouts were visually reviewed. The Sites local workflow reused existing
styling. No backend source changes or live order/stock/settlement operations were
needed for this checkpoint; no commit, push or deployment occurred. The existing
bundle warning remains (approximately 525 kB minified / 147 kB gzip).

## Seller returns — 28 October 2026

`/seller/returns` and `/seller/returns/:id` are linked from the active seller
workspace. Verified seller sessions load active-account status before private
reads. The queue uses seller pagination (25 rows), API-supported status filters
and distinct loading/empty/error states. All-status reads omit the status parameter.
Detail displays named items, purchased/requested quantities, item reasons, notes,
the server's discounted refund estimate, refund/dispute status and a link to the
brand fulfilment order. Monetary/item arithmetic, quantities and IDs are validated.

Actions are the intersection of server `available_actions` and the current return
state: requested supports approve/reject, approved supports mark received. Unknown
or terminal states and empty action lists enable no seller writes. Refund processing
and dispute messaging are not exposed by the seller contract. The estimate is
labelled separately from recorded refund status; receipt confirms physical arrival
and leaves administrator refund processing separate.

Every action requires review and confirmation. Optional decision notes use the
existing API's `admin_note` field; the UI explains that a new note replaces shared
return notes and may be visible to the customer. Blank notes send no replacement.
After POST, a fresh owned detail read must match return, order and shipment IDs,
requested item IDs/quantities, target state and any submitted note. Failure of
read-back (including 4xx), malformed/mismatched results or uncertain writes keeps
the return locked, with no automatic replay. A non-secret per-account/return
sessionStorage marker preserves the lock through same-tab reload. Known rejection
or confirmed success clears it. Notes, reasons and drafts are not persisted.
Unresolved writes require inspection/support; this is not server-side or cross-tab
idempotency. Refresh discards local edits while preserving uncertain-write locks.

Validation: final production build/TypeScript, all 384 frontend unit/component tests
and 42 mocked desktop/mobile seller-return browser tests passed. Tests cover partial
quantities, refund estimates, approval/rejection/receipt, note preservation,
confirmation, uncertain responses through reload, pagination/filtering, dispute
status, terminal/unknown states and access gates. Accessibility/overflow checks
passed; both layouts were visually reviewed. Long text wraps within the page.
The Sites local workflow reused existing styling. No backend changes, live returns,
refunds, stock credits, commit, push or deployment occurred for this checkpoint.
The existing bundle warning remains (approximately 538 kB minified / 149 kB gzip).

## Seller wallet and payouts — 28 October 2026

`/seller/wallet` and `/seller/wallet/accounts` are linked from the active seller
workspace. Verified seller sessions load active-account status before private
reads. Wallet balances distinguish available funds and pending release, with
recorded earnings/commission. Transaction and payout histories support the API's
filters and 25-row pagination. Payout history shows status, admin notes, completion
dates and transfer references; transfer destinations remain hidden until revealed.
Platform completion records are not presented as bank-statement confirmation.

Wallet summary now includes `minimum_withdrawal_amount` and
`maximum_withdrawal_amount`, populated from the backend's configured withdrawal
limits. The request schema and service limits remain unchanged. Deploy/restart
the updated backend with this frontend. Missing/inconsistent limits block payout
requests. The existing exact-response integration assertion was updated, and a
unit regression verifies non-default configured limits are exposed correctly.

Payout requests require explicit account selection, an exact decimal PKR amount
and review/confirmation. The frontend checks precision, current published limits
and available funds using integer paisa. Before POST, it reloads the wallet and
accounts to catch changed eligibility, limits or destination details. The server's
locking and ownership checks remain authoritative against changes after this read.
The returned payout must match the amount, bank destination, method and requested
status before success is shown. Success records a request for admin processing;
it does not report a completed transfer. Balances refresh after confirmation.

Bank accounts can be added with optional title/default selection, reviewed before
submission and removed after confirmation. New responses and subsequent account
list reads must match the requested details; deletion is confirmed by absence.
Saved account numbers are masked in listings. Existing payout requests retain their
destination snapshots. The API does not offer bank-account editing or an existing
account default-change endpoint; this screen adds neither. Bank transfers are the
supported destination method exposed by the current seller payout contract.

All wallet/account writes share a mounted-page lock and a non-secret per-account
pending marker in sessionStorage. Ambiguous responses or failed/mismatched
post-write confirmation retain it through same-tab reload. Known rejection or
confirmed success clears it. Preflight failures send no write and permit correction.
No credentials, account numbers, amounts or notes are stored in browser storage.
This is not cross-tab/server-side idempotency or automatic reconciliation; resolve
uncertain requests using saved records/support before another payout.

Validation: final production build/TypeScript, 50 focused frontend unit/component
tests (wallet contracts, seller status and App), and 38 mocked desktop/mobile wallet
browser tests passed. Accessibility/overflow checks passed and wallet/account layouts were visually
reviewed on both viewports. All 23 backend withdrawal-limit tests and all 36 wallet
API integration tests passed. Integration checks used a separate PostgreSQL 15
container with synthetic accounts and isolated schemas; that container and its
temporary volume were removed afterward. Application database/Redis containers
were untouched. Test files are Ruff-clean; the schema/service pair retains the
same 16 lint findings as HEAD. The full backend suite was not run.

The Sites local workflow preserved existing styling. No real transfer, commit,
push or deployment occurred. The existing bundle warning remains (approximately
557 kB minified / 153 kB gzip). Commission/settlement breakdown belongs to the next
seller analytics checkpoint.

The seller analytics checkpoint below completes the next step.

## Seller analytics and commission breakdown — 28 October 2026

`/seller/analytics` is linked from the active seller workspace. Only verified
seller sessions with an active profile load private analytics. Reads are scoped
to the mounted owner and selected period; stale responses are aborted and never
replace the current selection. Every section has loading, error and refresh
states, and empty series are not filled with invented data. This checkpoint
changes only frontend files; the existing backend contracts are unchanged.

Performance supports 7/30/90/365-day windows, settlement buckets grouped by
day/week/month, the top 10 products ranked by order value/units/lifetime views,
and current inventory health. Labels distinguish refund-adjusted settlements
from qualifying order-item sales, lifetime product views/ratings and current
stock. Low-stock variants are included in in-stock counts. The settlement/view
ratio is not presented as unique-customer conversion, nor as capped at 100%.
Settlement bucket dates are UTC and only returned buckets are listed.

The commission view has 25-entry pagination and all-time totals independent of
the current page. Entries link to the seller's shipment and show original and
refund-adjusted amounts, original commission rate, reversal totals, wallet
recoveries, settlement offsets, platform-covered shortfalls and release records.
Release timestamps do not imply bank payouts or withdrawable funds; wallet
balances and payout history remain separate. All decimal money validation,
reconciliation and formatting use integer paisa/BigInt without floating-point
rounding, including aggregate totals above Number's safe integer range.

Scope limit: the backend commission query currently ignores its optional date
arguments. This UI therefore offers only explicitly all-time ledger reads and
does not send or claim working commission date filters. Performance period
filters use the separate analytics endpoints. Analytics and ledger sections
are independent snapshots, not an atomic cross-endpoint financial report.
Ledger ordering remains the backend's settlement-time ordering.

Validation: production build/TypeScript, 52 focused frontend unit/component
tests (analytics, seller status and App), and all 28 mocked desktop/mobile
analytics browser tests passed. Browser checks cover period/ranking/bucket
queries, commission pagination, release/refund distinctions, invalid payloads,
denied reads/retry, empty states, access gates and stale period responses.
Accessibility and horizontal-overflow checks passed; performance and expanded
ledger screenshots were reviewed at both viewports. No live provider calls,
backend tests, real-money operations, commits, pushes or deployment occurred.
The Sites local workflow preserved the existing design. The existing bundle
warning remains (approximately 573 kB minified / 156 kB gzip).

The admin seller-review checkpoint below completes the next frontend step.

## Admin seller reviews — 28 October 2026

`/admin/sellers` and `/admin/sellers/:id` are connected from the admin workspace.
Private reads require an exact admin role and verified email. Owner/route changes
unmount private state and abort stale reads. Invalid references never reach the
review API; unknown seller statuses are read-only. Backend authorization remains
authoritative. Existing administrator sign-in/2FA policy was not changed.

The application list defaults to awaiting approval and supports all five known
status filters, brand-name search and 25-row pagination. Detail screens show the
submitted brand/profile/return-policy fields, published-product and slot counts,
quoted registration fee, saved review reason and recorded financial context.
Delivered-shipment value is not presented as refund-adjusted settlement revenue.
Money validation/formatting preserves decimal precision through integer paisa.
Submitted logos are displayed only for credential-free HTTPS URLs, without a
referrer; contact/profile text is rendered as text rather than executable links.

Actions follow the existing service rules: awaiting-approval sellers can be
approved/rejected; pending-payment applications can only be rejected; active
sellers can be suspended; suspended sellers can be reinstated. Rejected/unknown
states offer no action. Rejection/suspension require a trimmed 10–1,000-character
reason. Each decision has explicit review and confirmation, then rechecks the
latest status and reviewed application fields before POST. A changed application
requires another review. Success requires a subsequent detail read matching the
seller ID, target status and any submitted reason, not just a success message.
Reinstatement does not claim to restore independently moderated products.

Writes have a mounted-page lock and a non-secret owner/seller-scoped pending
marker that survives same-tab reload. Ambiguous writes or failed/mismatched
readback stay locked; known rejections allow correction without automatic replay.
No token, reason, balance or application contents are saved in browser storage.
This is not server idempotency or cross-tab/cross-admin concurrency control.

The frontend checkpoint found that the review service read seller state without
a row lock, then updated by seller ID. No backend files changed during that
frontend step. The follow-up concurrency checkpoint below resolves that
decision-transition race; frontend preflight alone is not the concurrency guard.

At the review checkpoint, registration-payment recording was still separate.
The follow-up below adds that form and receipt readback. A zero fee or approval
is never treated as a paid receipt. Suspension/rejection do not cancel orders or
settle financial balances.

Validation: production build/TypeScript, 59 focused unit/component tests (admin
contracts/page, portal and App), and all 52 mocked desktop/mobile browser tests
passed. The owner-isolation tests were rerun after strengthening the valid delayed
response/abort assertion (7 passed). Browser fixtures change application data
explicitly after review rather than depending on initial-read counts in Strict
Mode. Browser coverage includes all four decisions, state/reason readback,
changed-application preflight, uncertain outcomes across reload, known rejection,
status/search/page controls, invalid payloads, access gates and stale responses.
Accessibility and horizontal-overflow checks passed. List/detail screenshots were
visually reviewed at both viewports. The Sites local workflow preserved styling.

No real seller decisions, external notifications, backend tests, commits, pushes
or deployments occurred. Existing unrelated changes were preserved. The existing
bundle warning remains (approximately 587 kB minified / 160 kB gzip).

Concurrent admin decisions are addressed in the follow-up below.

## Admin decision concurrency — 28 October 2026

`AdminService._get_seller()` now uses PostgreSQL `SELECT ... FOR UPDATE` and
`populate_existing=True`. Approval, rejection, suspension and reinstatement all
use this helper, so each locks the seller before checking status and holds the
lock through the existing update/outbox/commit transaction. A waiting request
validates the latest committed state, even if its SQLAlchemy session already
cached that seller. Missing/soft-deleted sellers remain excluded. Read-only list
and detail queries, transition eligibility, API contracts and migrations are
unchanged.

The original race was reproduced on native PostgreSQL before changing the
service: a competing rejection completed while the approval was paused after
loading its seller. After the fix, tests explicitly observe the second database
connection waiting on the first connection's lock via `pg_blocking_pids` before
releasing the first operation. Tests do not infer locking from a fixed sleep.

Eight native cases passed: approval versus rejection in both orders; duplicate
approval/rejection; duplicate rejection while registration payment is pending;
duplicate suspension/reinstatement; and rollback after an actual approval outbox
insert followed by a successful waiting rejection. Each uses independent real
transactions and deliberately preloads the second session's seller identity.
Checks cover final status, decision actor/reason/timestamp, correct notification
payloads and absence of phantom outbox events after rollback. Notification workers
are not run and no external messages are sent.

Verification: 45 focused tests passed (14 admin unit tests, 23 mocked admin API
tests and 8 native PostgreSQL races). Both changed test files are Ruff-clean.
The admin service has the same 34 pre-existing Ruff findings as HEAD, with no new
codes/messages. The full backend suite, coverage gate and migration checks were
not run for this query-only change. No frontend runtime files changed, so the
previous frontend build/browser results remain the UI verification baseline.

Database execution used a dedicated PostgreSQL 15 container with synthetic test
accounts, per-test disposable schemas and real commits. The test container and
its temporary volume were removed after verification; the application database
and Redis containers were untouched. No commits, pushes or deployment occurred.

Limits: this serializes the existing server-side transitions; it does not add
cross-request idempotency keys or an optimistic version check binding a decision
to the exact application content reviewed earlier in the browser. A later,
independently eligible decision can still run after the first commits. These
checks use the default PostgreSQL READ COMMITTED behavior, not every isolation
level or a complete operational load test.

Registration-payment recording is completed in the follow-up below.

## Admin registration-payment records — 28 October 2026

The seller detail screen now records an externally verified registration transfer
for an eligible pending-payment application. An administrator enters the exact
outstanding decimal PKR amount and transfer reference, explicitly confirms they
verified receipt in the receiving account, reviews the details, then confirms the
record. This does not charge money, contact a payment provider or approve a seller.
A newly recorded payment moves the application to awaiting approval; any later
approval/rejection remains a separate decision.

Admin seller details now require `registration_amount_due`,
`registration_paid_at`, `registration_payment_reference` and
`registration_paid_by`. These expose existing stored receipt metadata; no new
database column or migration is needed. Outstanding amount is the stored fee
only while awaiting payment without a paid timestamp, otherwise zero. Recorded
amount uses the stored registration fee that the endpoint matched at recording.
Deploy/restart the updated backend before using this frontend: missing or
inconsistent receipt fields block the detail screen rather than guessing.

References are trimmed and must contain 3–255 usable characters without embedded
control characters. Amounts remain exact decimal strings/integer paisa. The
endpoint retains its seller row lock and now refreshes a cached ORM identity
before checking receipt/state. An identical amount/reference replay preserves
the original actor, timestamp and current seller status, including after a later
approval. Conflicting replays fail. Partial legacy metadata is not overwritten;
it requires reconciliation. Zero-fee applications never acquire invented receipts.

The UI rechecks reviewed application/receipt fields before writing and confirms
the saved seller ID, amount, reference, paid timestamp, recording admin and zero
outstanding amount afterward. A separate later status change does not invalidate
a matching receipt. Ambiguous writes or mismatched/failed readback retain the
existing owner/seller pending marker across same-tab reload, locking both payment
and decision writes. Known rejections permit correction without automatic replay.
References, amounts and credentials are not saved in browser storage. Historical
receipts with missing actor/reference are shown as incomplete, not silently repaired.

Validation: 54 focused backend tests passed, including 20 native registration API/
race cases and the 8 existing native decision-race regressions. Coverage includes
permission gates, exact amounts, zero/partial records, idempotency, conflicting
references, competing payment/rejection/approval operations, stale ORM identities
and rollback. Test files are Ruff-clean. Changed backend source has no new lint
findings: 8 old route findings were removed, leaving 55 existing findings across
the route/schema/service files. The full backend suite, coverage gate and migration
checks were not run for this additive response/query-validation change.

Frontend production build/TypeScript passed. The initial 59 related unit/component
regressions passed; after adding three receipt cases, all 19 admin contract tests
passed. The final workspace copy was checked with all 23 portal tests passing.
All 92 mocked desktop/mobile payment and seller-review browser tests
passed after the final form-key fix. The payment regression also rejects duplicate
component-key console warnings. Accessibility and overflow checks passed, and
payment-review/receipt screenshots were visually reviewed at both viewports.
The Sites local workflow preserved existing styling. The existing bundle warning
remains (approximately 592 kB minified / 161 kB gzip).

Native tests used a dedicated PostgreSQL 15 container with synthetic accounts and
per-test disposable schemas. That container and temporary volume were removed;
the application database and Redis were untouched. No real transfer, provider
charge, notification delivery, commit, push or deployment occurred.

Limits: this is manual receipt recording, not bank verification, file upload or
automated reconciliation. Replay protection is per seller; no global cross-seller
transfer-reference uniqueness policy was added. Existing uncertain browser writes
still need reconciliation rather than automatic unlocking. The recorded fee is
not credited to seller wallet balances by this workflow.

Product moderation is completed in the follow-up below.

## Admin product moderation — 28 October 2026

`/admin/products` and `/admin/products/:id` are linked from the verified admin
workspace. Seller review pages link to the corresponding filtered catalogue.
The list supports the API's seller UUID and admin-hidden filters with stable
25-row pagination; no unsupported name-search filter is invented. URL filters
and product references are validated before reads. Exact admin role and verified
email gates precede private requests, with mounted-owner isolation and aborted
stale reads. Server authorization remains authoritative.

Added `GET /api/v1/admin/products/{product_id}` and the separate
`AdminProductDetailResponse`. This permits inspection of non-deleted products
even when draft, admin-hidden or owned by a suspended/archived seller. It exposes
the existing product detail plus `admin_hidden`, `seller_status` and
`seller_deleted`; public response contracts gain none of those private flags.
The existing repository fully hydrates images, category, seller, variants and
inventory. Unlike public product reads, admin inspection creates no analytics
view event and does not increment product views. No migration was needed.
Deploy/restart the updated backend before using the new detail screen.

Detail screens show content, prices, images, category, brand return policy,
effective variant prices and physical/available stock. Non-HTTPS or
credential-bearing image URLs are not rendered. Moderation status, seller
publication, seller approval/deletion and stock are kept separate: removing an
admin restriction does not publish a draft, activate a seller or guarantee stock.
The UI adds neither product deletion nor seller-side editing/publication actions.
Existing seller publication and moderation fields remain independent.

Hide/unhide require review and explicit confirmation. Preflight rereads the
reviewed content, identities, prices, variants and seller/moderation flags; changed
content requires another review. Volatile inventory counts are excluded from
that content comparison and never submitted by the moderation form. Success
requires both the returned product/flag receipt and a private detail readback
matching the target product, seller and requested flag. Unknown outcomes or
failed/mismatched confirmation retain an owner/product-scoped non-secret pending
marker across same-tab reload. Known rejections permit correction without replay.
No content, credentials or prices are stored in browser storage.

Validation: production build/TypeScript and 48 focused frontend unit/component
tests passed. All 60 mocked desktop/mobile browser tests passed, including filter
pagination/reset, exact money, hide/unhide, drafts, inactive/archived sellers,
changed-content preflight, stock changes, invalid payloads, permission gates,
uncertain responses/reload, empty states and stale reads. Accessibility/overflow
checks passed and list/detail screenshots were visually reviewed at both sizes.
The Sites local workflow preserved the existing styling. Existing bundle-size
warning remains (approximately 606 kB minified / 163 kB gzip).

All 46 focused backend tests passed: 12 unit/OpenAPI contract cases and 34 native
PostgreSQL read/moderation cases. These prove permission boundaries, non-public
inspection, deleted/missing exclusions, exact prices, non-mutating admin reads,
stable pagination and idempotent hide/unhide without stock, slot, seller-status
or publication changes. Both changed backend test files are Ruff-clean. The
route's 30 and service's 41 existing lint findings match their baselines, with no
new findings. Schema Ruff verification was not run after its approval was
declined; it was not retried. Schema contracts were exercised by tests/build.
The full backend suite, coverage gate and migration checks were not run here.

Native execution used synthetic data and per-test disposable schemas in a
separate PostgreSQL 15 container. Its container and temporary volume were removed;
the app database and Redis were untouched. No live product moderation, external
storage changes, commits, pushes or deployments occurred. Unrelated work was
preserved, including earlier product publication-response repairs.

Limits: the existing row-locked hide/unhide operations set an absolute flag and
are idempotent, not optimistic-version checks against the exact browser snapshot.
Another authorized decision may change the flag after a read. No moderation
reason, actor-history, bulk-edit or deletion API was added. Uncertain browser
writes require reconciliation rather than automatic unlocking.

Admin review moderation is completed in the checkpoint below.

## Admin customer review moderation — 28 October 2026

Verified administrators can open `/admin/reviews` from their workspace and
inspect `/admin/reviews/:id`. Lists default to pending, support all four real
statuses plus all-status browsing, and use the API's 25-row pagination. The
all-status URL survives navigation/reload without accidentally reverting to pending.
Detail shows customer content, author reference, rating, purchase-verification
flag, photos, vote counts, private note and recorded timestamps. Product links
open the existing private admin product detail, not a public visibility bypass.

Approved, rejected and hidden decisions are explicitly reviewed before PATCH.
The optional private note is limited to 1,000 characters; whitespace-only clears
it. No customer text/photo deletion, order changes or financial operations are
offered. Only approved reviews contribute to the product rating aggregate.
The existing warm ivory/forest design and responsive account-card styles are reused.

Backend changes are confined to `app/api/v1/admin/reviews.py`: typed private
list/detail/decision responses, a protected detail GET, note normalization and
setting `moderated_at` plus `updated_at` when saving decisions. Admin fields
remain absent from the public/customer review schema. The existing review row
lock now reloads stale identity-map state. The new frontend supplies
`expected_updated_at`; the server compares it under that lock and returns 409
for a stale decision, with rating refresh in the same transaction. Legacy callers
may still omit the version (backward compatibility), so they do not receive
optimistic conflict protection. This is latest moderation metadata, not an
actor-attributed, append-only moderation audit history. No migration was needed.

The UI rechecks reviewed content before writing, verifies the PATCH receipt and
a fresh private readback, and prevents duplicate clicks. Uncertain outcomes lock
further writes across same-tab reload/refresh using an owner/review-scoped pending
marker; tokens, content and notes are not stored there. Known rejections are not
replayed. Private results are discarded when the admin changes, and a pending
preflight cannot send a decision after its owner screen is unmounted.

Verification:

- `npm run build` passed; JavaScript is 618.08 kB minified / 165.16 kB gzip.
  The existing >500 kB bundle warning remains.
- Focused Vitest run for `reviews.test.ts`, `AdminReviewsPage.test.tsx`,
  `PortalPage.test.tsx` and `App.test.tsx` with `--maxWorkers=2`: **49 passed**.
- `npm run test:browser -- tests/browser/admin-reviews.spec.ts`: **52 passed**
  across desktop/mobile. Confirmation screenshots were subsequently refreshed
  with two additional passing repetitions. List and confirmation screenshots
  were visually reviewed; those representative states had no tested Axe
  WCAG A/AA violations or horizontal overflow.
- Backend `tests/unit/test_admin_review_contract.py` and
  `tests/integration/test_admin_reviews.py`, using `-q -o addopts="" --tb=short
  --disable-warnings`: **26 passed**, with 83 warnings. Native PostgreSQL 15
  used synthetic data in a dedicated disposable test container, now removed.
  Checks cover permissions, private contracts, status filters, tied-date
  pagination, note clearing, aggregate updates, stale versions and competing
  decisions from independently preloaded sessions (one winner).
- Ruff passed on the changed backend route and both new backend test files;
  `git diff --check` passed. No full-suite or coverage-gate claim is made here.

Browser APIs and images were mocked; no real provider/storage calls occurred.
Deploy the frontend with the updated private backend contracts. Nothing was
committed, pushed or deployed. Content management and remaining admin operations
are separate checkpoints, not completed by this moderation screen.

## Admin banner content management — 28 October 2026

Verified administrators can open `/admin/content`, create banners at
`/admin/content/banners/new` and manage `/admin/content/banners/:id`.
This checkpoint covers the existing banner APIs only; it does not add a generic
CMS, category editor or new storefront placement rendering.

The saved list follows server sort order and shows artwork, placement, active
flag, schedule limits and destination text. New banners default inactive in this
UI. JPEG/PNG/WebP selections are locally decoded and previewed before an explicit
review/confirmation; limits are 5 MiB and 25 megapixels. The server's existing
image processor converts/resizes to WebP. Scheduling is available after creation,
matching the existing create/update API split. Metadata edits support all three
positions, non-negative 32-bit order, active state, optional safe destination and
UTC start/end limits. Clearing a limit/link is explicit. Unchanged schedule
seconds are preserved despite minute-resolution form controls.

The existing warm ivory/forest account-card design is reused. Editing does not
replace artwork: that action is not supported by this API. Deletion requires a
separate review and confirmation and removes only the banner database record;
stored images are retained. No shared or historical media was deleted here.
Live storage verification and orphan-media reconciliation remain separate work;
an upload followed by a persistence failure is not claimed to have automatic
storage compensation. Active/schedule flags do not by themselves verify that a
placement is displayed in the storefront.

Backend changes stay in `admin/content.py`, the banner portion of
`schemas/admin.py` and banner methods of `AdminService`. Creation now validates
title, link, placement and order before storage calls. Destinations must be
site-relative paths or credential-free HTTPS URLs, without control characters,
spaces, protocol-relative paths or backslashes. Schedule inputs require timezone
offsets; merged start/end validation occurs before mutation. Lists have a stable
ID tie-breaker. Responses include the already-persisted `updated_at`; edits and
deletes lock/reload the row and compare optional `expected_updated_at`. The new
frontend always supplies that version. Legacy callers may omit it, so they do
not receive optimistic stale-decision protection. No migration was needed.

The UI rechecks the saved list before writes, verifies receipts and fresh list
readback, and discards private state when the admin/record changes. Unknown
create/edit/delete outcomes retain owner/action-scoped session markers across
same-tab reload/refresh; no tokens, artwork or banner content are stored in those
markers. Writes are never automatically replayed. This is not a server-side
cross-request idempotency key; inspect records before resolving an uncertain
creation. Known validation/conflict responses permit correction.

Verification:

- `npm run build` passed: 633.35 kB JavaScript / 168.77 kB gzip. The existing
  >500 kB bundle warning remains.
- Focused Vitest run for `content.test.ts`, `AdminContentPage.test.tsx`,
  `PortalPage.test.tsx` and `App.test.tsx`, `--maxWorkers=2`: **50 passed**.
- `npm run test:browser -- tests/browser/admin-content.spec.ts`: **50 passed**
  across desktop/mobile, with mocked API/storage responses. List, edit-review
  and creation screenshots were visually reviewed. Tested list/edit states had
  no Axe WCAG A/AA violations or horizontal overflow.
- Backend `tests/unit/test_admin_banner_contract.py`, `tests/unit/test_admin.py`
  and `tests/integration/test_admin_banners.py`, using `-q -x -o addopts=""
  --tb=short --disable-warnings`: **71 passed**, 83 warnings. Tests used a
  disposable native PostgreSQL 15 database and synthetic users; image processing
  ran with storage upload mocked. Coverage includes all CRUD permissions,
  metadata-before-upload validation, corrupt/oversized images, schedule clearing,
  stable order, stale update/delete checks and independent-session conflicts.
  The banner test module removes the shared client's forced JSON header so
  HTTPX can generate real multipart boundaries; the global fixture is unchanged.
- Ruff passed for the changed content route and both new backend test files.
  Schema/service lint remains at its pre-change baseline: **19 + 34 findings**,
  no new findings. `git diff --check` passed. No full-suite/coverage-gate claim.

The disposable database was removed after checks. No real storage calls,
commits, pushes or deployment occurred. Deploy with the updated backend response
contract. Next checkpoint: admin order management.

## Admin order inspection — 29 October 2026

Implementation and automated checks completed on 28 October; screenshot review
and this handoff were finished after the interrupted session resumed on 29 October.
Verified administrators can open `/admin/orders` and `/admin/orders/:id` from
the admin workspace. This is read-only inspection, not COD verification,
cancellation, payment reconciliation or refund execution.

Lists support the existing order-status, COD/PayFast and optional seller filters,
with 25-row pages, refresh, empty/error states and browser-history restoration.
Historical payment methods remain readable under All methods but are not offered
as new individual filters. Seller filtering selects whole parent orders: other
brands and the full checkout amounts remain visible. The matching-order summary
covers all matching pages, not merely the current page. Original checkout totals
may include unpaid, cancelled or refunded orders and are not collected revenue.
Recorded net commission uses settlement entries after commission reversals; it
is not a wallet balance, payout receipt or completed customer-refund claim.

Detail shows stored checkout values, notes, address and item snapshots, plus
current brand fulfilment records, tracking and recorded dates. Links open the
existing private product/seller inspection screens. Historical missing addresses,
items/splits and inconsistent amounts are explicitly flagged without repairing
or fabricating data on read. Private responses are owner/record-scoped, aborted
when superseded and never stored in local/session storage. No write actions or
provider calls were added. The existing ivory/forest account-card design is reused.

Backend changes add protected `GET /api/v1/admin/orders/{order_id}` with the
separate `AdminOrderDetailResponse`; public/customer schemas remain unchanged.
The private response excludes checkout hashes, guest-access secrets, guest email
and phone fields and authentication secrets. The stored delivery phone remains
available to verified administrators for order operations. List responses add
`per_page` and `total_pages`. A stable created-date/ID order prevents tied-date
page drift. Seller filtering uses EXISTS rather than a multiplying join, so
legacy duplicate brand splits do not duplicate parent orders. Per-page commission
reads are batched; matching totals and detail use all relevant brands. No database
migration or COD/refund mutation changes were made.

Verification from the 28 October run:

- `npm run build` passed: 648.54 kB JavaScript / 171.69 kB gzip. The existing
  >500 kB bundle warning remains.
- Focused Vitest run for `orders.test.ts`, `AdminOrdersPage.test.tsx`,
  `PortalPage.test.tsx` and `App.test.tsx`, `--maxWorkers=2`: **50 passed**.
- `npm run test:browser -- tests/browser/admin-orders.spec.ts`: **46 passed**
  across desktop/mobile, using mocked API responses. List/detail screenshots
  were visually reviewed on resume; representative tested states had no Axe
  WCAG A/AA violations or horizontal overflow.
- Backend `tests/unit/test_admin_order_contract.py`, `tests/unit/test_admin.py`
  and `tests/integration/test_admin_order_reads.py`, using `-q -x -o addopts=""
  --tb=short --disable-warnings`: **44 passed**, 83 warnings. Native PostgreSQL
  15 used synthetic accounts/orders. Checks cover role/email restrictions,
  snapshot/ledger values, whole-order filtered totals, legacy records, stable
  pagination, duplicate splits and unchanged persisted order/accounting/stock
  records after reads. No real payment or storage calls occurred.
- Ruff passed on the changed admin order route and both new backend test files.
  Existing schema/service findings are now **19 + 33**, down from 19 + 34;
  no new findings. `git diff --check` passed. No full-suite or coverage-gate claim.

Cleanup was initially unconfirmed because Docker was stopped. On 1 November,
after Docker became available, the `com.wearhowz.task=admin-orders-check` label
and PostgreSQL image were verified and `wearhowz-admin-orders-check-20261028`
was removed with its disposable test volume. Application containers were untouched.

Deploy with the updated private backend contracts. Nothing was committed, pushed
or deployed. Next checkpoint: admin COD queue and verification, selected separately.

## Admin COD decisions — 1 November 2026

Verified administrators can open `/admin/cod` and `/admin/cod/:id` from the
workspace. The complete pending queue includes expired records awaiting
cancellation. Review shows saved contact, checkout total, brands, delivery/items,
current order status and the exact UTC deadline. Zero rounded minutes does not
mean the exact deadline has passed. Missing/inconsistent records are flagged;
approval requires an eligible order and contact phone.

Both actions require an explicit checkbox and a second review step. Cancellation
requires a 10–500 character reason in this UI. Approval permits preparation only:
it does not record cash collection, settle seller funds or issue a refund.
Cancellation releases held reservations, not physical-stock credits or refunds.
The Sites local workflow preserved the existing ivory/forest account-card design;
no new imagery or hosted deployment was needed.

Immediately before writing, the UI rechecks the private order and queue against
the reviewed snapshot. It submits the parent version and runtime deadline, checks
the structured receipt, then reads back the saved status and original checkout
content. Double submits are locked; writes are never automatically retried.
An ambiguous result stays locked across same-tab refresh/reload using only an
owner/order-scoped pending marker. No contact data, notes or tokens are persisted.
Owner changes discard old reads and prevent an old preflight from sending a write.

Backend COD decisions lock and refresh the parent row, check current method,
status, fulfilment eligibility, optional reviewed version and runtime deadline.
Approval at or after the deadline is rejected. Optional version fields preserve
legacy callers, which still receive the current server-side eligibility checks.
Cancellation and expiry use strict reservation decrements and transactional
history/outbox updates. A stale SQLAlchemy identity map after waiting for a lock
was fixed in the shared order repository. Timeout jobs now reject non-COD parents;
both expiry paths release inventory in deterministic variant order. No migration.

Verification:

- `npm run build` passed: 661.51 kB JavaScript / 174.32 kB gzip. The existing
  >500 kB bundle warning remains.
- Focused Vitest (`cod.test.ts`, `AdminCODPage.test.tsx`, `PortalPage.test.tsx`,
  `App.test.tsx`, `--maxWorkers=2`): **51 passed** on the final sequential run.
- `npm run test:browser -- tests/browser/admin-cod.spec.ts`: **52 passed** on
  the final isolated run across Edge desktop/mobile. Queue/review screenshots
  were visually inspected; representative tested states had no Axe WCAG A/AA
  violations or horizontal overflow. This is not an accessibility certification.
- Backend unit/admin/task-dispatch checks: **64 passed**. Native PostgreSQL COD
  flow checks: **27 passed**, including independent-session decision races,
  an expiry worker proved blocked behind an uncommitted admin cancellation,
  duplicate decisions, expired/stale-policy rejection, reservation inconsistency,
  outbox-failure rollback, permissions and unchanged wallet/ledger balances.
- Existing marketplace COD fulfilment, dashboard totals and pre-settlement
  refund regressions: **3 passed**, 46 deselected. Each backend invocation used
  `-q -x -o addopts="" --tb=short --disable-warnings` and reported 29 warnings.
- Ruff passed on the COD route, expiry task and new COD test files. The scoped
  schema/service/repository check still reports **68 existing-style findings**
  (down from the recorded pre-change 76); this is not a lint-clean or full-suite
  claim. The unchanged release coverage gate was not rerun.

Browser isolation now owns port 4173 and refuses to reuse another server. The
initial port-3000 run hit an unrelated server's 404 page and was stopped. A later
concurrent run had one navigation-unit and one role-gate browser timeout; the
focused unit and full COD browser runs passed when repeated sequentially.
Browser APIs are mocked;
native tests use synthetic data, not real charges, delivery or notification sends.

The labelled `wearhowz-admin-cod-check-20261101` disposable PostgreSQL container
and test volume were removed after native verification. Application PostgreSQL,
Redis and the unrelated port-3000 server were left untouched. Deploy frontend and
updated backend contracts together. Nothing was committed, pushed or deployed.
Next separately selected checkpoint: admin payment operations, including COD
collection as a distinct financial action, followed by refund handling.

## Admin payments and COD cash collection — 1 November 2026

Verified administrators can open `/admin/payments` and `/admin/payments/:id`.
The list starts with pending COD payments, supports status/method filters,
25-row pagination, history restoration, refresh and empty/error states. All
methods includes historical payment records; only COD/PayFast are new filter
options. Saved amounts use the recorded currency, not an invented revenue total.
Payment states have their own labels, separate from fulfilment states.

Private detail shows the saved payment amount/currency, order status, reference,
payment date, collection administrator when recorded and eligibility blockers.
It links to full order inspection. This is local evidence, not independent
verification by a bank, courier or PayFast. Old payments without an administrator
audit remain readable without inventing an actor. Partial collections, PayFast
reconciliation, refunds and seller payouts are not actions in this checkpoint.

An eligible full-amount COD collection requires an actual receipt reference and
an explicit confirmation that cash was received, then a second review. The UI
rechecks the private snapshot before POST, submits the saved amount and parent
order version, validates the structured receipt and reads back the saved evidence.
Synchronous locking prevents double submission; mutations are never auto-retried.
Ambiguous outcomes remain locked across same-tab reload/refresh using only an
owner/payment-scoped pending marker. References, financial data and tokens are
not stored in local/session storage. Owner changes discard stale reads/preflights.

Backend additions/changes:

- Protected `GET /api/v1/payments/{payment_id}` exposes a dedicated private detail
  contract, excluding provider payloads, callback bodies and guest capabilities.
  Payment lists add currency, `per_page` and `total_pages`, with stable date/ID
  ordering. Frontend and backend contracts must be deployed together.
- `POST /api/v1/payments/{payment_id}/cod-collection` returns a structured receipt
  and accepts optional reviewed amount/order-version fields. Reference-only
  legacy callers remain supported but still receive current eligibility checks.
- Collection locks/refreshes the parent, rechecks the payment and requires COD,
  PKR, the full matching checkout amount and delivered fulfilment for every brand.
  Inconsistent item/brand allocations, partial/cancelled/returned fulfilment and
  existing inconsistent receipt evidence require reconciliation instead of a write.
- A `PaymentCallback` audit with gateway `cod_collection` records the acting admin,
  reference, amount/currency and timestamp inside the settlement transaction.
  Its verified flag denotes administrator confirmation, not provider verification.
  No migration or historical evidence backfill was needed.
- Payment completion, audit and seller settlement are atomic. Brand settlement
  order is deterministic. Proceeds enter existing held balances; collection does
  not issue payouts, release the hold early or change physical/reserved stock.
  Same-reference repeats return the original receipt without new credits/audits;
  different-reference repeats are rejected.

Verification on synthetic data:

- `npm run build` passed: 675.43 kB JavaScript / 176.45 kB gzip. The existing
  >500 kB bundle warning remains.
- Focused Vitest (`payments.test.ts`, `AdminPaymentsPage.test.tsx`,
  `PortalPage.test.tsx`, `App.test.tsx`, `--maxWorkers=2`): **51 passed**.
- `npm run test:browser -- tests/browser/admin-payments.spec.ts`: **54 passed**
  on the final run after correcting payment labels, using mocked API responses.
  Desktop/mobile list/review screenshots were visually inspected. Representative
  tested states had no Axe WCAG A/AA violations or horizontal overflow; this is
  not a complete accessibility certification.
- Backend `tests/unit/test_cod_collection.py`, `tests/unit/test_payments.py` and
  `tests/integration/test_admin_collection_flow.py`: **77 passed**, 29 warnings.
  Native PostgreSQL checks cover role/email gates, read-only/private contracts,
  exact PKR receipts, version/amount rejection, unsupported/inconsistent states,
  repeat requests, independent-session races and unchanged stock. Two-brand
  settlement verifies rounded held proceeds and whole-transaction rollback after
  a failure following the second brand's wallet credit.
- Existing marketplace COD fulfilment, dashboard totals and pre-settlement
  refund regressions: **3 passed**, 46 deselected, 29 warnings. Backend invocations
  used `-q -x -o addopts="" --tb=short --disable-warnings` with the disposable
  `admin_collection_test` database, not application data.
- Existing `tests/integration/test_payment_api.py -k 'admin_payment or admin_gateway'`:
  **16 passed**, 27 deselected, 29 warnings. Admin authorization, actual-row
  filters, authenticated query validation and static gateway-status routing
  remain compatible. Across these final invocations, **96 backend tests passed**.
- New schemas/tests pass scoped Ruff. There are **20 inherited findings** across
  the payment route (1), repository (17) and service (2), with no new findings.
  This is not a full-suite, lint-clean or release-coverage-gate claim.

The Sites local workflow reused the existing ivory/forest design and screenshot
review corrected the misleading shared pending-status copy. No new assets,
dependencies, real provider requests, charges, transfers or notification sends
were needed. The verified task-labelled `wearhowz-admin-collection-check-20261101`
container and disposable test volume were removed after checks; application
PostgreSQL/Redis and unrelated servers were untouched. The browser-owned server
was stopped and `git diff --check` passed. Nothing was staged, committed, pushed
or deployed. Next separately
selected checkpoint: admin refund inspection and manual-transfer confirmation;
PayFast reconciliation, payouts/settings and production verification remain separate.

## Admin refund inspection and transfer records — 5 November 2026

The admin workspace now links to `/admin/refunds`, individual refund inspection,
and `/admin/payments/:id/refunds` for payment history and direct refund requests.
Verified administrators can filter/paginate records, inspect actors, references,
return links and seller/platform accounting, request an exact PKR amount, and
record a manual transfer that has already happened externally. Creating a request
reserves refundable balance; it does not send money or credit stock. A manual
reference is not independent bank/provider verification.

Both write flows require acknowledgement, a separate review, fresh authenticated
state and verification of the saved result. Stale amounts, balances, identities
or return links stop the write. Double submissions are locked. Ambiguous network,
server or readback outcomes remain locked across same-tab reloads instead of
automatically replaying a write; stored markers contain no receipt, amount,
reason or credentials. Unsupported currencies, inconsistent records and
unreconciled accounting remain explicit rather than being presented as success.

Targeted backend changes preserve refund idempotency and add optional expected
amount/payment/remaining-balance/return-link fields for compatibility with older
clients. Explicit null return linkage is distinguished from an omitted field.
Confirmation locks the return before its payment, refreshes locked state, and
checks the received return, order ownership, positive item quantities, prior
restocks and inventory existence before crediting stock. Direct refunds never
credit stock. Return completion, stock, transfer records and seller/platform
reversals share one transaction. Same-reference repeats return the original
receipt; conflicting references are rejected. A cyclic eager-loading path that
expired the refund's payment relationship was removed, and refund detail uses
explicitly loaded payment history to avoid asynchronous lazy-loading failures.
New confirmations require a completed PKR payment, including collected COD.
The historical pre-collection regression now asserts rejection of a new
confirmation and separately seeds an already-recorded legacy transfer to verify
that its seller settlement offset remains supported. Historical records are not
silently converted into permission to issue new refunds against uncollected cash.

Frontend verification completed on 4 November; native verification resumed on
5 November after restarting Docker Desktop:

- `npm run build` passed: 700.40 kB JavaScript / 180.79 kB gzip. The existing
  >500 kB bundle warning remains.
- Focused Vitest (`refunds.test.ts`, `AdminRefundsPage.test.tsx`,
  `PortalPage.test.tsx`, `App.test.tsx`, `--maxWorkers=2`): **51 passed**.
- `npm run test:browser -- tests/browser/admin-refunds.spec.ts`: **76 passed**,
  using mocked APIs on desktop/mobile. List, request review, confirmation review
  and unreconciled accounting screenshots were visually reviewed at both sizes.
  Tested representative states include Axe checks and horizontal-overflow checks;
  this is not a complete accessibility certification.
- Scoped Ruff passes for the payment route, schemas and new refund tests.
  The repository/service retain **19 inherited findings** (17/2 respectively).
  The adjusted historical marketplace regression file has **5 existing findings**
  outside its changed function; these were left outside this checkpoint's scope.
- Backend `tests/unit/test_refund_review.py`, `tests/unit/test_payments.py` and
  `tests/integration/test_admin_refunds_flow.py`: **64 passed**, 29 warnings,
  against disposable native PostgreSQL 15. Checks include private role gates,
  partial/full refunds, idempotency, stale reviews, received-return stock limits,
  whole-transaction rollback and independent-session confirmation races.
  Pytest used `-q -x -o addopts="" --tb=short --show-capture=no --disable-warnings`;
  no full-suite or coverage-gate claim is made.
- Existing `test_marketplace_regressions.py`, `test_payment_api.py` and
  `test_return_api.py`, selected with `-k refund` and the same pytest flags:
  **22 passed**, 102 deselected, 29 warnings. These cover pending/available
  balances, multi-brand allocation, paid-out shortfalls, historical settlement
  offsets, hold/release and existing payment/return contracts. Together with
  the focused run, **86 backend tests passed** on native PostgreSQL.

The Sites local workflow preserved the existing ivory/forest interface; no new
assets or dependencies were added. No migrations, real provider requests, charges
or transfers were needed. This checkpoint does not replace full-suite coverage
or production verification. Admin return/dispute handling, payouts/settings and
PayFast reconciliation remain separately selected work.

After verification, the task-labelled `wearhowz-admin-refunds-check-20261104`
container and disposable synthetic-data volume were removed. No checkpoint
preview server remained listening on port 4173. Application containers were not
changed by the test commands. Nothing was staged, committed, pushed or deployed.

## Admin returns and disputes — 5 November 2026

The admin workspace connects `/admin/returns`, `/admin/returns/:id`,
`/admin/disputes` and `/admin/disputes/:id`. Verified administrators can filter
and paginate records, inspect customer/brand/order/item details and text evidence,
approve or reject requested returns, record physical receipt, and request a
pending return-linked refund. Links connect orders, returns, disputes and the
existing refund-transfer inspection screen. A request or item-receipt decision
does not send money or credit stock; transfer confirmation stays in the refund
workflow. New refund requests require a completed PKR payment.

Dispute tools support reviewed messages and customer/seller resolutions. A
customer resolution reopens an eligible rejected return as approved, subject to
the backend's returnable-quantity checks. Resolution does not initiate a refund.
Resolved/closed disputes are read-only. The existing API exposes current return
notes plus requested/resolved timestamps, not a complete return-decision audit
trail. Dispute message history is available; evidence attachments are not part
of this contract. The UI does not invent missing history or attachment support.

Writes require an acknowledgement and separate confirmation, re-read the current
record before submission, and verify saved state afterward. Ownership changes
stop an unsent action. Synchronous submission locks prevent double clicks, while
ambiguous writes or failed readbacks remain locked across same-tab reloads.
Session markers store only a pending flag, not notes, messages or credentials.
Return refund readback checks the linked refund ID, amount and pending status;
customer dispute resolution also checks the linked return transition.

Targeted backend changes add optional reviewed status/notes/refund-estimate
expectations to admin return actions and status/message-count expectations to
admin dispute messages/resolutions. Checks run under existing row locks and
return a conflict when the reviewed state changed. Older callers can omit the
new fields. Dispute repository reads now refresh cached state, preventing a
preloaded unresolved dispute from accepting a message after another session has
resolved it. Blank admin messages and whitespace-only resolution notes are
rejected. No migrations or external services were required.

Verification:

- `tests/integration/test_admin_return_review.py`,
  `tests/integration/test_return_api.py`, `tests/unit/test_returns.py`:
  **53 passed**, 29 warnings, against disposable native PostgreSQL 15.
  Tests cover lifecycle/linked requests, stale notes and estimates, unread
  messages, both resolution outcomes, independent-session stale-cache rejection,
  blank text, existing permissions and return/dispute regressions.
  Flags: `-q -x -o addopts="" --tb=short --show-capture=no --disable-warnings`.
- Focused Vitest (`returns.test.ts`, `AdminReturnsPage.test.tsx`,
  `PortalPage.test.tsx`, `App.test.tsx`, `--maxWorkers=2`): **50 passed** on the
  final frontend source.
- `npm run test:browser -- tests/browser/admin-returns.spec.ts`: **52 passed**
  with mocked API responses across desktop/mobile. After form styling and focus
  improvements, **10 affected checks passed** again, including explicit review
  focus, successful writes, queues, Axe checks and horizontal-overflow checks.
  A final six-check screenshot run also passed. Return refund review, dispute
  resolution review and dispute queue images were visually checked at both sizes.
  This is not a complete accessibility certification or live-provider test.
- `npm run build` passed: **720.81 kB JavaScript / 184.87 kB gzip**. The existing
  >500 kB bundle warning remains.
- The new backend test file passes Ruff. The three touched backend files retain
  **51 existing lint findings**, verified against their committed versions:
  schema 23, service 13, repository 15. No full-suite coverage-gate claim is made.

The Sites local workflow preserved the approved ivory/forest direction, reused
existing form styles and added keyboard focus to review panels. No new assets
or dependencies were needed. Nothing was staged, committed, pushed or deployed.
The task-labelled `wearhowz-admin-returns-check-20261105` PostgreSQL container and
its disposable synthetic-data volume were removed. The browser-owned preview
server stopped; no listener remained on port 4173. Application data was not used.
Next separately selected checkpoint: admin payouts and transfer receipts;
platform settings, PayFast reconciliation and production verification remain
separate work.

## Admin payouts checkpoint — 5 November 2026

Added `/admin/payouts` and `/admin/payouts/:id`, with a verified-admin workspace
link, status filters, pagination, loading/error/empty states, saved destination
inspection and reviewed approval, rejection and transfer-record actions.
The Sites local workflow reused the ivory/forest styles and focused confirmation
panels; desktop/mobile screenshots were inspected. No assets or dependencies changed.

Requests already reserve funds. Approval does not debit again; rejection restores
the original amount once. Completion records an **already-made external transfer**;
it never initiates a bank or PayFast payment. Check the actual beneficiary and receipt
independently. Saved destinations are request-time snapshots, not current bank edits.
The last recorded administrator is not a complete audit history.

The new admin detail endpoint exposes supported actions and saved evidence. Both
canonical and legacy mutation routes accept an optional reviewed snapshot for backward
compatibility; the new UI always supplies it. The service compares it under the payout
row lock. Existing transfer evidence blocks conflicting actions, whitespace-only
rejection notes and invalid references are rejected, and a missing seller wallet
blocks a false reversal. Same-reference completion remains idempotent.

The frontend rechecks details before sending, validates the response and saved
readback, prevents duplicate clicks and keeps uncertain outcomes locked across reloads.
Session storage holds only an owner/payout uncertainty marker, not bank details or
receipt contents. Unknown outcomes require reconciliation; never repeat a transfer
because recording its result failed.

Verification:

- **70 distinct backend tests passed**: 66 in the initial payout/wallet run, followed
  by 5 final guard/concurrency checks (one repeats the existing rejection test).
  Integration checks used disposable native PostgreSQL 15, including independent
  sessions racing completion against rejection and duplicate decisions. Unit wallet
  checks were included. No full-suite or coverage-gate claim is made.
- **40 frontend tests passed** across payout helpers, seller wallet and workspace tests.
- **36 mocked desktop/mobile browser tests passed**, covering approval/rejection,
  completion, stale reviews, duplicate clicks, uncertain outcomes/reloads, filters,
  malformed responses and role/email restrictions. Representative transfer-review
  screens had no axe WCAG A/AA violations; this is not a full accessibility audit.
- `npm run build` passed: **733.02 kB JavaScript / 187.21 kB gzip**. The existing
  >500 kB bundle warning remains.
- New backend tests pass Ruff. Touched backend source retains **27 baseline lint
  findings** (legacy routes 4, wallet routes 7, schemas 7, service 9), compared with
  29 in their committed versions. No broad lint rewrite was performed.

Commands: focused pytest for `test_admin_payout_review.py`, `test_wallet_api.py`
and `test_wallet.py` with `-o addopts=""`; final pytest selection
`missing_wallet or independent_sessions or rejection_credits_original`;
`npm test -- src/admin/payouts.test.ts src/seller/wallet.test.ts src/pages/PortalPage.test.tsx`;
`npm run test:browser -- tests/browser/admin-payouts.spec.ts`; `npm run build`.

No real transfers, provider calls, commits, pushes or deployments were made.
The task-labelled payout-test PostgreSQL container and synthetic-data volume were
removed after verification. The browser-owned preview stopped; port 4173 had no
remaining listener. Application databases were not used or removed.
Platform settings and PayFast reconciliation remain separately selected checkpoints.

## Admin platform settings checkpoint — 5 November 2026

Added `/admin/settings` and a verified-admin workspace link. The screen reads the
seven effective business settings: commission rate, registration fee, extra-slot
price, free-shipping threshold, standard shipping fee, COD timeout and wallet hold.
Values are loaded from the backend rather than fabricated frontend defaults.

The form validates bounds and whole-rupee/day/minute fields, supports permitted
zero values, requires an explicit acknowledgement and shows a before/after review.
Only changed fields are sent. Loading, malformed/denied responses, stale reviews,
duplicate clicks and uncertain outcomes fail safely. Successful writes require a
matching response and fresh readback. A per-admin session marker locks uncertain
saves across reloads without storing setting values or credentials.

Backend updates now accept an optional complete `expected_settings` snapshot.
The UI always supplies it; existing supported callers can omit it. A PostgreSQL
transaction-scoped advisory lock serializes updates even when override rows do not
exist yet. A stale snapshot receives 409 before writes. The response is read inside
the transaction, and unknown fields or empty changes are rejected. No migration
was needed. Existing settings are not reset or automatically changed by this work.

The page does not manage provider enablement, credentials, deployment configuration,
historical order repricing or retention policy. Runtime consumers may apply current
policy to operational work; reducing hold/timeout values warrants operational review.
This is not a complete settings audit history or scheduled-change workflow.

Frontend verification: **27 focused tests** and **28 mocked desktop/mobile browser
tests passed**. Screenshots were visually inspected, with no axe WCAG A/AA violations
on the representative confirmation screen. This is not full accessibility certification.
The Sites local-only workflow preserved the existing ivory/forest design and focused
the confirmation panel for keyboard users. No new dependencies or assets were added.

**32 focused backend tests passed**, including native PostgreSQL 15 authorization,
validation, partial updates, attribution, stale snapshots and concurrent updates
with both missing and existing override rows. Only disposable synthetic data was used.
The final production build passed: **740.69 kB JavaScript / 189.04 kB gzip**;
the existing >500 kB bundle warning remains.

New backend tests pass Ruff. The two touched backend source files retain **45 existing
lint findings** (schema 19, service 26); their committed versions have 53. Unrelated
pre-existing work was preserved. No full-suite or coverage-gate claim is made.

Focused commands: pytest `tests/integration/test_admin_settings_flow.py
tests/unit/test_admin.py -q -x -o addopts=""`; `npm test -- src/admin/settings.test.ts
src/pages/PortalPage.test.tsx`; `npm run test:browser -- tests/browser/admin-settings.spec.ts`;
`npm run build`.

No live settings, provider calls, commits, pushes or deployments were performed.
The task-labelled settings-test container and disposable synthetic-data volume were
removed after verification; application databases were untouched. The browser-owned
preview stopped and port 4173 had no remaining listener.
Next separately selected checkpoint: PayFast reconciliation; production verification
remains separate.

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
