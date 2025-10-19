from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi_utils.cbv import cbv
from app.schemas.product import ChatRequest, SearchRequest
from app.services.ProductService import product_service
from app.db.session import get_db

router = APIRouter()


@cbv(router)
class ProductAPI:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    @router.post("/sync")
    def sync_products(self):
        return product_service.sync_products(self.db)

    @router.post("/process")
    def process_products(self):
        return product_service.process_products(self.db)

    @router.post("/search")
    def search_products(self, request: SearchRequest):
        return product_service.search_products(request, self.db)

    @router.post("/chat")
    async def chat(self, request: ChatRequest):
        return await product_service.chat(request, self.db)