from fastapi import APIRouter, HTTPException
from fastapi_utils.cbv import cbv
from qdrant_client import QdrantClient

router = APIRouter()
qdrant_client = QdrantClient(host="qdrant", port=6333)


@cbv(router)
class HealthAPI:
    def __init__(self):
        self.qdrant = qdrant_client

    @router.get("/qdrant-health")
    async def qdrant_health(self):
        try:
            status = self.qdrant.get_liveness()
            return {"qdrant_alive": status}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))