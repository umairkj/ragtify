import os
import json
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from app.models.rfy_content_buffer import RfyContentBuffer
from app.schemas.content import ChatRequest, SearchRequest


class ContentService:
    def __init__(self):
        self.ollama_base_url = "http://ollama:11434"
        self.qdrant_client = QdrantClient(host="qdrant", port=6333)
        self.default_collection_name = "content"
        self.vector_size = 4096

    def add_content(self, db: Session, source_id: str, collection_name: str, payload: dict):
        """Add content to the rfy_content_buffer table"""
        try:
            content = RfyContentBuffer(
                source_id=source_id,
                collection_name=collection_name,
                payload=payload
            )
            db.add(content)
            db.commit()
            db.refresh(content)
            return {"status": "success", "id": content.id, "source_id": source_id, "collection_name": collection_name}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to add content: {str(e)}")

    def process_content(self, db: Session, collection_name: str = None):
        """Process content from buffer and sync to Qdrant"""
        try:
            query = db.query(RfyContentBuffer)
            if collection_name:
                query = query.filter(RfyContentBuffer.collection_name == collection_name)
            
            contents = query.all()
            if not contents:
                return {"status": "no content found"}
            
            # Group by collection_name
            collections = {}
            for content in contents:
                if content.collection_name not in collections:
                    collections[content.collection_name] = []
                collections[content.collection_name].append(content)
            
            total_processed = 0
            for coll_name, coll_contents in collections.items():
                # Ensure collection exists in Qdrant
                try:
                    self.qdrant_client.get_collection(coll_name)
                except Exception:
                    self.qdrant_client.recreate_collection(
                        collection_name=coll_name,
                        vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
                    )
                
                points = []
                for content in coll_contents:
                    # Convert payload to text for embedding
                    text = json.dumps(content.payload, ensure_ascii=False)
                    if content.source_id:
                        text = f"Source ID: {content.source_id}\n{text}"
                    
                    try:
                        resp = httpx.post(
                            f"{self.ollama_base_url}/api/embeddings",
                            json={"model": "llama3:latest", "prompt": text},
                            timeout=60.0
                        )
                        resp.raise_for_status()
                        embedding = resp.json()["embedding"]
                    except Exception as e:
                        continue
                    
                    points.append(
                        PointStruct(
                            id=content.id,
                            vector=embedding,
                            payload={
                                "source_id": content.source_id,
                                "collection_name": content.collection_name,
                                **content.payload
                            }
                        )
                    )
                
                if points:
                    self.qdrant_client.upsert(collection_name=coll_name, points=points)
                    total_processed += len(points)
            
            return {"status": "success", "content_processed": total_processed, "collections": list(collections.keys())}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process content: {str(e)}")

    def search_content(self, request: SearchRequest, db: Session):
        """Search content in Qdrant"""
        collection_name = request.collection_name or self.default_collection_name
        limit = request.limit or 5
        
        try:
            resp = httpx.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": "llama3:latest", "prompt": request.query},
                timeout=60.0
            )
            resp.raise_for_status()
            query_embedding = resp.json()["embedding"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")
        
        try:
            search_result = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit
            )
            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                })
            return {"results": results}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Qdrant search failed: {e}")

    async def chat(self, request: ChatRequest, db: Session):
        """Chat with content context from Qdrant"""
        collection_name = request.collection_name or self.default_collection_name
        
        try:
            resp = httpx.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": "llama3:latest", "prompt": request.prompt},
                timeout=60.0
            )
            resp.raise_for_status()
            query_embedding = resp.json()["embedding"]
            search_result = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=5
            )
            if search_result:
                content_list = "\n".join([
                    f"- {json.dumps(hit.payload, ensure_ascii=False)}" for hit in search_result
                ])
                rag_context = (
                    "You are a helpful assistant. The user asked: '" + request.prompt + "'.\n"
                    "Here is some relevant content that may help answer their question:\n"
                    f"{content_list}\n"
                    "Please answer the user's question using this context when relevant."
                )
            else:
                rag_context = (
                    "You are a helpful assistant. The user asked: '" + request.prompt + "'.\n"
                    "No relevant content was found. Please answer as best as you can."
                )
        except Exception as e:
            rag_context = (
                "You are a helpful assistant. The user asked: '" + request.prompt + "'.\n"
                "(Content search failed, so just answer as best as you can.)"
            )
        
        # Stream response from Ollama with RAG context
        try:
            async def stream_response():
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        f"{self.ollama_base_url}/api/generate",
                        json={"model": request.model, "prompt": rag_context, "stream": True},
                    ) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_text():
                            if chunk.strip():
                                try:
                                    # Parse the Ollama response chunk
                                    data = json.loads(chunk)
                                    # Extract the response text
                                    if 'response' in data:
                                        # Format as JSON for frontend consumption
                                        json_chunk = json.dumps({"response": data['response']}) + "\n"
                                        yield json_chunk.encode('utf-8')
                                    # Check if streaming is done
                                    if data.get('done', False):
                                        break
                                except json.JSONDecodeError:
                                    # Skip malformed JSON chunks
                                    continue
            from fastapi.responses import StreamingResponse
            return StreamingResponse(stream_response(), media_type="application/x-ndjson")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# Create a global instance of the service
content_service = ContentService()



