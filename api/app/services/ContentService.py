import os
import json
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from app.models.rfy_content_buffer import RfyContentBuffer
from app.models.settings import Settings
from app.schemas.content import ChatRequest, SearchRequest


class ContentService:
    def __init__(self):
        self._settings_cache = {}
        self._qdrant_client = None
    
    def _get_setting(self, db: Session, key: str, default: str = None):
        """Get a setting from database with caching"""
        if key in self._settings_cache:
            return self._settings_cache[key]
        
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting:
            value = setting.value
        else:
            value = default
        
        self._settings_cache[key] = value
        return value
    
    def _invalidate_settings_cache(self):
        """Invalidate the settings cache"""
        self._settings_cache.clear()
        self._qdrant_client = None
    
    def _get_ollama_url(self, db: Session):
        """Get Ollama URL from settings"""
        return self._get_setting(db, "ollama_url", "http://ollama:11434")
    
    def _get_default_collection_name(self, db: Session):
        """Get default collection name from settings"""
        return self._get_setting(db, "default_collection_name", "content")
    
    def _get_vector_size(self, db: Session):
        """Get vector size from settings"""
        return int(self._get_setting(db, "vector_size", "4096"))
    
    def _get_llama_model(self, db: Session):
        """Get llama model from settings"""
        return self._get_setting(db, "llama_model", "llama3:latest")
    
    def _get_qdrant_client(self, db: Session):
        """Get or create Qdrant client with settings"""
        if self._qdrant_client is not None:
            return self._qdrant_client

        host = self._get_setting(db, "qdrant_host", "qdrant")
        port = int(self._get_setting(db, "qdrant_port", "6333"))
        self._qdrant_client = QdrantClient(url=f"http://{host}:{port}")
        return self._qdrant_client
    
    def _get_rag_context_template(self, db: Session):
        """Get RAG context template from settings"""
        return self._get_setting(
            db, 
            "rag_context_template",
            "You are a helpful assistant. The user asked: '{prompt}'.\nHere is some relevant content that may help answer their question:\n{content_list}\nPlease answer the user's question using this context when relevant."
        )
    
    def _get_rag_context_search_failed(self, db: Session):
        """Get RAG context for search failed from settings"""
        return self._get_setting(
            db,
            "rag_context_search_failed",
            "You are a helpful assistant. The user asked: '{prompt}'.\n(Content search failed, so just answer as best as you can.)"
        )
    
    def _get_rag_context_no_results(self, db: Session):
        """Get RAG context for no results from settings"""
        return self._get_setting(
            db,
            "rag_context_no_results",
            "You are a helpful assistant. The user asked: '{prompt}'.\nNo relevant content was found. Please answer as best as you can."
        )

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
    
    def delete_content(self, db: Session, content_id: int):
        """Delete content from database and Qdrant"""
        try:
            content = db.query(RfyContentBuffer).filter(RfyContentBuffer.id == content_id).first()
            if not content:
                raise HTTPException(status_code=404, detail="Content not found")
            
            collection_name = content.collection_name
            qdrant_client = self._get_qdrant_client(db)
            
            # Delete from Qdrant
            try:
                qdrant_client.delete(
                    collection_name=collection_name,
                    points_selector=[content_id]
                )
            except Exception as e:
                # Log but don't fail if Qdrant deletion fails
                print(f"Warning: Failed to delete from Qdrant: {e}")
            
            # Delete from database
            db.delete(content)
            db.commit()
            
            return {"status": "success", "id": content_id}
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete content: {str(e)}")
    
    def get_all_content(self, db: Session, collection_name: str = None):
        """Get all content from database"""
        try:
            query = db.query(RfyContentBuffer)
            if collection_name:
                query = query.filter(RfyContentBuffer.collection_name == collection_name)
            contents = query.all()
            return [
                {
                    "id": content.id,
                    "source_id": content.source_id,
                    "collection_name": content.collection_name,
                    "payload": content.payload
                }
                for content in contents
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get content: {str(e)}")

    def process_content(self, db: Session, collection_name: str = None):
        """Process content from buffer and sync to Qdrant"""
        try:
            qdrant_client = self._get_qdrant_client(db)
            ollama_url = self._get_ollama_url(db)
            llama_model = self._get_llama_model(db)
            vector_size = self._get_vector_size(db)
            
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
                    qdrant_client.get_collection(coll_name)
                except Exception:
                    qdrant_client.recreate_collection(
                        collection_name=coll_name,
                        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                    )
                
                points = []
                for content in coll_contents:
                    # Convert payload to text for embedding - format for better searchability
                    text_parts = []
                    if content.source_id:
                        text_parts.append(f"Source ID: {content.source_id}")
                    
                    # Convert payload fields to a more searchable text format
                    if isinstance(content.payload, dict):
                        for key, value in content.payload.items():
                            if isinstance(value, str):
                                text_parts.append(f"{key}: {value}")
                            else:
                                text_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
                        text = " ".join(text_parts)
                    else:
                        text = json.dumps(content.payload, ensure_ascii=False)
                    
                    try:
                        resp = httpx.post(
                            f"{ollama_url}/api/embeddings",
                            json={"model": llama_model, "prompt": text},
                            timeout=60.0
                        )
                        resp.raise_for_status()
                        embedding = resp.json()["embedding"]
                    except Exception as e:
                        print(f"Failed to generate embedding for content {content.id}: {e}")
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
                    qdrant_client.upsert(collection_name=coll_name, points=points)
                    total_processed += len(points)
            
            return {"status": "success", "content_processed": total_processed, "collections": list(collections.keys())}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process content: {str(e)}")

    def search_content(self, request: SearchRequest, db: Session):
        """Search content in Qdrant"""
        collection_name = request.collection_name or self._get_default_collection_name(db)
        limit = request.limit or 5
        qdrant_client = self._get_qdrant_client(db)
        ollama_url = self._get_ollama_url(db)
        llama_model = self._get_llama_model(db)
        
        try:
            resp = httpx.post(
                f"{ollama_url}/api/embeddings",
                json={"model": llama_model, "prompt": request.query},
                timeout=60.0
            )
            resp.raise_for_status()
            query_embedding = resp.json()["embedding"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")
        
        try:
            # Qdrant search via REST API
            host = self._get_setting(db, "qdrant_host", "qdrant")
            port = int(self._get_setting(db, "qdrant_port", "6333"))
            # Check if collection exists
            check_resp = httpx.get(f"http://{host}:{port}/collections/{collection_name}", timeout=10.0)
            if check_resp.status_code != 200:
                return {"results": []}
            resp = httpx.post(
                f"http://{host}:{port}/collections/{collection_name}/points/search",
                json={"vector": query_embedding, "limit": limit, "with_payload": True},
                timeout=60.0
            )
            resp.raise_for_status()
            search_data = resp.json()
            results = []
            for hit in search_data.get("result", []):
                results.append({
                    "id": hit["id"],
                    "score": hit["score"],
                    "payload": hit["payload"]
                })
            return {"results": results}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Qdrant search failed: {e}")

    async def chat(self, request: ChatRequest, db: Session):
        """Chat with content context from Qdrant"""
        collection_name = request.collection_name or self._get_default_collection_name(db)
        ollama_url = self._get_ollama_url(db)
        llama_model = self._get_llama_model(db)

        try:
            # Check if collection exists first
            host = self._get_setting(db, "qdrant_host", "qdrant")
            port = int(self._get_setting(db, "qdrant_port", "6333"))
            check_resp = httpx.get(f"http://{host}:{port}/collections/{collection_name}", timeout=10.0)
            if check_resp.status_code != 200:
                # Collection doesn't exist - return helpful error message
                error_msg = f"Collection '{collection_name}' does not exist in Qdrant. Please sync your payloads first using the 'Sync to Qdrant' button in the Context Browser."
                template = self._get_rag_context_search_failed(db)
                rag_context = f"{template.format(prompt=request.prompt)}\n\nNote: {error_msg}"
            else:
                # Generate embedding for the search query
                resp = httpx.post(
                    f"{ollama_url}/api/embeddings",
                    json={"model": llama_model, "prompt": request.prompt},
                    timeout=60.0
                )
                resp.raise_for_status()
                query_embedding = resp.json()["embedding"]
                
                # Search in Qdrant via REST API
                host = self._get_setting(db, "qdrant_host", "qdrant")
                port = int(self._get_setting(db, "qdrant_port", "6333"))
                resp = httpx.post(
                    f"http://{host}:{port}/collections/{collection_name}/points/search",
                    json={"vector": query_embedding, "limit": 5, "with_payload": True},
                    timeout=60.0
                )
                resp.raise_for_status()
                search_data = resp.json()
                search_result = search_data.get("result", [])

                # Log search results for debugging
                # print(f"Chat search query: '{request.prompt}' in collection '{collection_name}'")
                # print(f"Found {len(search_result)} results")
                # if search_result:
                #     for i, hit in enumerate(search_result):
                #         score = hit.get('score', 'N/A')
                #         payload = hit.get('payload', {})
                #         print(f"  Result {i+1}: score={score}, payload={payload}")
                
                if search_result:
                    content_list = "\n".join([
                        f"- {payload.get('title', 'No title')}: {payload.get('url', 'No url')}"
                        for hit in search_result
                        if (payload := hit.get('payload', {}))
                    ])
                    template = self._get_rag_context_template(db)
                    rag_context = template.format(prompt=request.prompt, content_list=content_list)
                else:
                    template = self._get_rag_context_no_results(db)
                    rag_context = template.format(prompt=request.prompt)
                    print(f"Warning: No results found for query '{request.prompt}' in collection '{collection_name}'")
        except HTTPException:
            raise
        except Exception as e:
            template = self._get_rag_context_search_failed(db)
            rag_context = template.format(prompt=request.prompt)
        
        # Stream response from Ollama with RAG context
        try:
            async def stream_response():
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        f"{ollama_url}/api/generate",
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





