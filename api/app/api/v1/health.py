from fastapi import APIRouter, HTTPException
from qdrant_client import QdrantClient

router = APIRouter()
qdrant_client = QdrantClient(host="qdrant", port=6333)

@router.get("/qdrant-health")
async def qdrant_health():
    try:
        status = qdrant_client.get_liveness()
        return {"qdrant_alive": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 