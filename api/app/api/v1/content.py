from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi_utils.cbv import cbv
from app.schemas.content import ContentCreateRequest, ChatRequest, SearchRequest
from app.services.ContentService import content_service
from app.db.session import get_db

router = APIRouter()


@cbv(router)
class ContentAPI:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    @router.post("/")
    def create_content(self, request: ContentCreateRequest):
        """Add content to the rfy_content_buffer table"""
        return content_service.add_content(
            self.db,
            source_id=request.source_id,
            collection_name=request.collection_name,
            payload=request.payload
        )

    @router.post("/process")
    def process_content(self, collection_name: str = Query(None, description="Optional collection name to process. If not provided, processes all collections.")):
        """Process content from buffer and sync to Qdrant"""
        return content_service.process_content(self.db, collection_name=collection_name)

    @router.post("/search")
    def search_content(self, request: SearchRequest):
        """Search content in Qdrant"""
        return content_service.search_content(request, self.db)

    @router.post("/chat")
    async def chat(self, request: ChatRequest):
        """Chat with content context from Qdrant"""
        return await content_service.chat(request, self.db)

