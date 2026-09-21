# DRIP Marketplace — Frontend

React 18 + TypeScript + Vite + TailwindCSS

## Stack
| Layer       | Choice |
|-------------|--------|
| Build       | Vite 5 + TypeScript |
| UI          | React 18, Tailwind CSS 3 |
| Routing     | React Router DOM 6 |
| Server state| TanStack Query v5 |
| Client state| Zustand 4 |
| Forms       | React Hook Form + Zod |
| Animation   | Framer Motion |
| HTTP        | Axios (auto token refresh) |

## Setup
```bash
npm install
cp .env.example .env          # set VITE_API_URL
npm run dev                   # http://localhost:3000
```

## Structure
```
src/
  api/          API layer (client, per-domain api files, query keys)
  components/   UI, layout, product, cart, checkout, seller, admin
  config/       env.ts
  hooks/        TanStack Query hooks
  lib/schemas/  Zod validation schemas
  pages/        auth/, customer/, seller/, admin/
  store/        Zustand stores (auth, cart, ui)
  styles/       globals.css, themes.ts
  types/        TypeScript interfaces
  utils/        currency, errors, whatsapp, validation
  App.tsx       Router + lazy imports
  main.tsx      Entry point + providers
```

## Routes
| Path | Page | Auth |
|------|------|------|
| `/` | Home | Public |
| `/shop` | Catalogue | Public |
| `/product/:slug` | Product detail | Public |
| `/checkout` | Checkout | Customer |
| `/account/*` | Account | Customer |
| `/dashboard/*` | Seller dashboard | Seller |
| `/admin/*` | Admin panel | Admin |
