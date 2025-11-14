from fastapi import APIRouter
from app.api.v1 import health, root, content

router = APIRouter()
router.include_router(content.router, prefix="/content", tags=["content"])
router.include_router(health.router)
router.include_router(root.router) 