# WearHowZ frontend

Local React + TypeScript + Vite application, in the requested `drip-frontend` folder.
The existing FastAPI backend is unchanged.

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

Verified on 20 October 2026: production build and strict TypeScript checks passed;
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
- Account session summary and sign-out; no tokens in local/session storage.
- Admin-only authenticator input, not customer two-factor setup.

This is not the complete frontend or a production-readiness claim. Still needed:
full reviews, filters/categories, wishlist,
checkout/payment flows, customer account features, seller portal and admin portal.
Brand collection pagination and role-specific landing pages also remain.

## Product and bag verification scope

Product and bag browser fixtures exercise sold-out variants, effective prices,
guest persistence, quantity changes/removal, failed quotes, explicit signed-in
merging and a lost response after an additive write. Matching guest/account items
merge using the backend's maximum-quantity rule, not by adding quantities together.
Only identifiers and quantities are stored locally; tokens, prices and totals
are not persisted. Stock is not reserved by adding to the bag.

These tests do not establish a real-account purchase journey: the local catalogue
is empty, signed-in bag writes use isolated browser fixtures, and checkout remains
disabled. No orders, charges, customer emails, backend edits or deployments were
performed for this slice.

Email delivery and real-account journeys have not been exercised by this build.
The local database currently has no products or approved labels; the UI shows
empty states rather than invented catalogue data.

Google initiation/callback handling is scaffolded but hidden behind
`VITE_ENABLE_GOOGLE_AUTH=false`. Enable only after backend credentials, trusted
origins and same-host callback URLs are aligned and the flow is tested.

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
