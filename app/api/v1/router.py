"""
app/api/v1/router.py — Master v1 API router.
Adding a new block = one include_router line here.
"""
from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1 import sellers
from app.api.v1 import products
from app.api.v1          import orders     
from app.api.v1          import cart 
from app.api.v1 import payments
from app.api.v1 import wallet 
from app.api.v1.admin import (    # ← add
    dashboard as admin_dashboard,
    brands    as admin_brands,
    orders    as admin_orders,
    cod_queue as admin_cod,
    payouts   as admin_payouts,
    content   as admin_content,
    settings  as admin_settings,
)
api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router,     prefix="/auth", tags=["auth"])
api_router.include_router(sellers.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)   
api_router.include_router(cart.router) 
api_router.include_router(payments.router)
api_router.include_router(wallet.router)
api_router.include_router(admin_dashboard.router)   
api_router.include_router(admin_brands.router)      
api_router.include_router(admin_orders.router)     
api_router.include_router(admin_cod.router)         
api_router.include_router(admin_payouts.router)     
api_router.include_router(admin_content.router)    
api_router.include_router(admin_settings.router) 
