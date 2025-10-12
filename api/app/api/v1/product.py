from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.product import ChatRequest, SearchRequest
from app.services.ProductService import product_service
from app.db.session import get_db

router = APIRouter()

@router.post("/sync")
def sync_products(db: Session = Depends(get_db)):
    return product_service.sync_products(db)

@router.post("/process")
def process_products(db: Session = Depends(get_db)):
    return product_service.process_products(db)

@router.post("/search")
def search_products(request: SearchRequest, db: Session = Depends(get_db)):
    return product_service.search_products(request, db)

@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return await product_service.chat(request, db) 