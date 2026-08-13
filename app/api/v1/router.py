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

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router,     prefix="/auth", tags=["auth"])
api_router.include_router(sellers.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)   
api_router.include_router(cart.router) 