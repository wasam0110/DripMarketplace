"""
app/api/v1/router.py
─────────────────────
Master v1 API router.
Each module registers its own router here as it is built.
Adding a new module = one line in this file.
"""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router

# Routers are imported and included here as each block is built:
# Block 3: from app.api.v1.sellers import router as sellers_router
# Block 4: from app.api.v1.products import router as products_router
# Block 5: from app.api.v1.orders import router as orders_router
# Block 6: from app.api.v1.payments import router as payments_router
# Block 7: from app.api.v1.wallet import router as wallet_router
# Block 8: from app.api.v1.admin import router as admin_router

api_router = APIRouter()

# ── Health (always registered) ────────────────────────────────────────────────
api_router.include_router(health_router)

# ── Auth (Block 2) ✅ ─────────────────────────────────────────────────────────
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# ── Customer (Block 2) ────────────────────────────────────────────────────────
# api_router.include_router(customer_router, prefix="/customer", tags=["customer"])

# ── Seller (Block 3) ──────────────────────────────────────────────────────────
# api_router.include_router(sellers_router, prefix="/seller", tags=["seller"])

# ── Products (Block 4) ────────────────────────────────────────────────────────
# api_router.include_router(products_router, prefix="/products", tags=["products"])
# api_router.include_router(categories_router, prefix="/categories", tags=["categories"])

# ── Cart + Orders (Block 5) ───────────────────────────────────────────────────
# api_router.include_router(cart_router, prefix="/cart", tags=["cart"])
# api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
# api_router.include_router(coupons_router, prefix="/coupons", tags=["coupons"])

# ── Payments (Block 6) ────────────────────────────────────────────────────────
# api_router.include_router(payments_router, prefix="/payments", tags=["payments"])

# ── Wallet (Block 7) ──────────────────────────────────────────────────────────
# api_router.include_router(wallet_router, prefix="/seller/wallet", tags=["wallet"])
# api_router.include_router(payouts_router, prefix="/seller/wallet", tags=["payouts"])

# ── Notifications ─────────────────────────────────────────────────────────────
# api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

# ── Admin (Block 8) ───────────────────────────────────────────────────────────
# api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

# ── Analytics ─────────────────────────────────────────────────────────────────
# api_router.include_router(analytics_router, prefix="/seller/analytics", tags=["analytics"])
# api_router.include_router(admin_analytics_router, prefix="/admin/analytics", tags=["admin-analytics"])