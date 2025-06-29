from fastapi import APIRouter
from app.api.v1 import product, health, root

router = APIRouter()
router.include_router(product.router, prefix="/products", tags=["products"])
router.include_router(health.router)
router.include_router(root.router) 