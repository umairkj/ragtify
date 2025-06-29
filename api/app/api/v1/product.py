from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.product import ChatRequest, SearchRequest
from app.services.product_service import (
    sync_products_service,
    process_products_service,
    search_products_service,
    chat_service,
)
from app.db.session import get_db

router = APIRouter()

@router.post("/sync")
def sync_products(db: Session = Depends(get_db)):
    return sync_products_service(db)

@router.post("/process")
def process_products(db: Session = Depends(get_db)):
    return process_products_service(db)

@router.post("/search")
def search_products(request: SearchRequest, db: Session = Depends(get_db)):
    return search_products_service(request, db)

@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return await chat_service(request, db) 