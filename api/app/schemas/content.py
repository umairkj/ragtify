from pydantic import BaseModel
from typing import Optional, Dict, Any

class ContentCreateRequest(BaseModel):
    source_id: Optional[str] = None
    collection_name: str
    payload: Dict[str, Any]

class ChatRequest(BaseModel):
    model: str
    prompt: str
    collection_name: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    collection_name: Optional[str] = None
    limit: Optional[int] = 5



