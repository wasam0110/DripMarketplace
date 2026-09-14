# DRIP Frontend

React/Vite storefront and operations UI for the DRIP multi-vendor marketplace. The frontend runs separately from the FastAPI backend in the sibling `drip-backend` folder.

The frontend contains no database, private keys, service-role secrets, or payment credentials. All persistent data and protected operations are handled by the backend.

## Current Status

The frontend is connected to the backend API at `/api/v1` and currently includes:

- Public DRIP storefront and responsive catalogue.
- Search, category filtering, price sorting, brand storefronts, product cards, and cart drawer.
- Local cart persistence with `localStorage`.
- Login and registration screens connected to backend authentication.
- Refresh-token cookie support and access-token storage for authenticated API calls.
- Customer account workspace with profile and order loading.
- Seller workspace with live profile, dashboard, product list, and wallet data.
- Seller **Add Product** form connected to `POST /seller/products`.
- Admin control room with dashboard KPIs, seller list, and order list.
- Checkout form with shipping details, coupon validation, order creation, and payment initiation.
- PayFast, card, and COD payment method selection in checkout. PayFast gateway signing still requires provider credentials and implementation details.
- Backend-origin CORS support for both `localhost:5173` and `127.0.0.1:5173`.

## Technology

- React
- Vite
- JavaScript modules
- `lucide-react` icons
- FastAPI backend
- PostgreSQL and Redis through the backend
- `fetch` API client with auth retry handling
- CSS design system with responsive layouts

## Project Structure

```text
drip-frontend/
	.env
	.env.example
	index.html
	package.json
	vite.config.js
	src/
		main.jsx              # App shell, storefront, auth, checkout, role workspaces
		data.js               # Fallback catalogue and brand presentation data
		styles.css            # Main design system and responsive layout
		brand-pages.css       # Brand storefront styling
		checkout.css          # Filters, checkout, and seller product form styling
		api/
			client.js           # Backend API client and endpoint map
```

## Run Locally

Use two terminals.

### 1. Start the backend

```powershell
cd C:\Users\wasam\OneDrive\Desktop\MultiMarket\drip-backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
python -m uvicorn main:create_application --factory --host 127.0.0.1 --port 8000
```

Backend URLs:

- API: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/api/v1/health
- API docs in development: http://127.0.0.1:8000/docs

The backend requires its own configured `drip-backend/.env`, PostgreSQL, and Redis.

### 2. Start the frontend

```powershell
cd C:\Users\wasam\OneDrive\Desktop\MultiMarket\drip-frontend
npm install
npm run dev
```

Frontend URL:

http://127.0.0.1:5173/

## Frontend Environment

The local `.env` should contain:

```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

Use `.env.example` as the template. Never put backend secrets, JWT private keys, Supabase service-role keys, or payment credentials in this frontend environment file.

## Backend API Integration

The endpoint map lives in `src/api/client.js`. It currently covers:

### Authentication

- Register, login, logout, refresh, current user.
- Email verification and password reset flows.
- Change password.
- Admin 2FA setup and verification.
- Google OAuth redirect endpoint.

### Customer Commerce

- Product catalogue, product detail, variants, search suggestions, and reviews.
- Cart read, add, update, remove, clear, and sync.
- Authenticated and guest order creation.
- Order list, detail, tracking, cancellation, and coupon validation.
- Payment initiation, payment status, retry, refund, and gateway status.

### Seller Operations

- Seller registration, profile, logo, dashboard, and slot pricing.
- Slot purchase.
- Product list, create, update, delete, publish, unpublish, and image upload.
- Seller order list, detail, and status updates.
- Wallet summary, transactions, withdrawal, payouts, and commission breakdown.
- Bank account management.
- Revenue analytics.

### Admin Operations

- Admin dashboard.
- Seller list, detail, approval, rejection, suspension, and reinstatement.
- Admin order list.
- COD verification and cancellation queue.
- Payout list, approval, completion, and rejection.
- Payment list and refunds.
- Banner content management.
- Platform settings.
- Product list and hide action.

The API client sends credentials with requests, adds request IDs, attaches the access token, and attempts refresh-token rotation after a `401` response.

## Verified Local Checks

The following have been verified locally:

- Frontend production build passes with `npm run build`.
- Backend health returns `200`.
- PostgreSQL and Redis connect during backend startup.
- Products endpoint returns `200`.
- Signup returns `201` with valid input.
- CORS accepts `http://127.0.0.1:5173`.
- Seller and admin protected endpoints reject unauthenticated requests with `401`.
- Storefront navigation, categories, brand pages, quick add, cart drawer, login, registration, and checkout render.
- Seller product creation form is present and submits to the backend endpoint.

## Test Seller

A development seller account was created for local testing:

```text
Email:    test-seller-drip@example.com
Password: DripSeller123
Role:     seller
Brand:    DRIP Test Supply
```

Use the account through the frontend login screen. Do not use these credentials outside local development.

## Fallback Catalogue

The database currently may contain no products. When the backend returns an empty catalogue, the storefront uses the presentation data in `src/data.js` so the UI remains visible during development.

Once real products are created through the seller workspace, the frontend uses backend catalogue data instead.

## Remaining Work

The following work is still needed for complete production parity with every backend capability:

1. Replace the single-file app shell with dedicated React route/page modules.
2. Add full customer order detail, cancellation, profile editing, password change, email verification, forgot-password, and reset-password screens.
3. Add complete seller product management: edit, delete, publish/unpublish, image upload, variant builder, and category selection.
4. Add seller order management, order status updates, bank accounts, withdrawals, payout history, commission ledger, and revenue charts.
5. Add full admin workflows for seller moderation, COD queue actions, payouts, refunds, banners, settings, and product moderation.
6. Add product detail pages with backend variants, stock selection, reviews, and real seller information.
7. Add real PayFast integration after merchant credentials, signing rules, callback format, and sandbox URLs are available.
8. Add frontend unit and integration tests for auth, checkout, seller product creation, and admin actions.
9. Resolve remaining backend async relationship/service issues before production use.
10. Add role-aware route guards, stronger error boundaries, loading skeletons, and production observability.

## Production Notes

- Do not expose `SUPABASE_SERVICE_ROLE_KEY` or JWT private keys to the frontend.
- Use HTTPS in staging and production.
- Replace the local API URL with the deployed API URL at build time.
- Configure PayFast only in the backend environment.
- Use real verified customer, seller, and admin accounts for end-to-end testing.
