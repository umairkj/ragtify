from fastapi import APIRouter, HTTPException
from fastapi_utils.cbv import cbv
from qdrant_client import QdrantClient

router = APIRouter()
qdrant_client = QdrantClient(host="qdrant", port=6333)


@cbv(router)
class HealthAPI:
    def __init__(self):
        self.qdrant = qdrant_client

    @router.get("/health")
    async def health(self):
        """General health check endpoint"""
        return {"status": "ok"}

    @router.get("/qdrant-health")
    async def qdrant_health(self):
        try:
            # Try to get collections list as a health check
            collections = self.qdrant.get_collections()
            return {"qdrant_alive": True, "collections": len(collections.collections)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))