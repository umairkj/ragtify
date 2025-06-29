from pydantic import BaseModel

class ChatRequest(BaseModel):
    model: str
    prompt: str

class SearchRequest(BaseModel):
    query: str 