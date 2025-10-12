import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from requests_oauthlib import OAuth1Session
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance

# The main FastAPI app entry point will be simplified after refactor.
# All logic will be moved to app/ submodules.

from app.main import app

# Qdrant setup
qdrant_client = QdrantClient(host="qdrant", port=6333)

# Database setup
MYSQL_USER = os.getenv('MYSQL_USER', 'llmuser')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'llmpassword')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3307')
MYSQL_DB = os.getenv('MYSQL_DATABASE', 'llm')
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    variations = Column(Text)
    attributes = Column(Text)
    url = Column(String(1024))

@app.get("/qdrant-health")
async def qdrant_health():
    try:
        status = qdrant_client.get_liveness()
        return {"qdrant_alive": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"status": "ok"}

OLLAMA_BASE_URL = "http://ollama:11434"

class ChatRequest(BaseModel):
    model: str
    prompt: str
    collection_name = "products"
    # Generate embedding for the query
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": "llama3", "prompt": request.query},
            timeout=60.0
        )
        resp.raise_for_status()
        query_embedding = resp.json()["embedding"]
        print("Query embedding:", query_embedding[:5], "...")
    except Exception as e:
        print("Embedding error:", e)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    # Search Qdrant
    try:
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=5
        )
        print("Qdrant search result:", search_result)
        results = []
        for hit in search_result:
            results.append({
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            })
        print("Results to return:", results)
        return {"results": results}
    except Exception as e:
        print("Qdrant search error:", e)
        raise HTTPException(status_code=500, detail=f"Qdrant search failed: {e}") 