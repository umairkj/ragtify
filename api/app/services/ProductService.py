import os
import json
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from requests_oauthlib import OAuth1Session
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from app.models.product import Product
from app.schemas.product import ChatRequest, SearchRequest


class ProductService:
    def __init__(self):
        self.ollama_base_url = "http://ollama:11434"
        self.qdrant_client = QdrantClient(host="qdrant", port=6333)
        self.collection_name = "products"
        self.vector_size = 4096

    def sync_products(self, db: Session):
        WC_URL = os.getenv('WC_URL', 'http://wordpress/wp-json/wc/v3/products/')
        WC_KEY = os.getenv('WC_KEY')
        WC_SECRET = os.getenv('WC_SECRET')
        if not WC_KEY or not WC_SECRET:
            raise HTTPException(status_code=500, detail="WooCommerce API credentials are not set.")
        oauth = OAuth1Session(WC_KEY, client_secret=WC_SECRET)
        try:
            response = oauth.get(WC_URL, timeout=30.0)
            response.raise_for_status()
            wc_products = response.json()
            for wc_product in wc_products:
                title = wc_product.get('name')
                description = wc_product.get('description')
                url = wc_product.get('permalink')
                variations = [a for a in wc_product.get('attributes', []) if a.get('variation')]
                variations_json = json.dumps(variations)
                attributes = [a for a in wc_product.get('attributes', []) if not a.get('variation')]
                attributes_json = json.dumps(attributes)
                product = Product(
                    id=wc_product['id'],
                    title=title,
                    description=description,
                    variations=variations_json,
                    attributes=attributes_json,
                    url=url
                )
                db.merge(product)
            db.commit()
            return {"status": "success", "products_synced": len(wc_products)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def process_products(self, db: Session):
        products = db.query(Product).all()
        if not products:
            return {"status": "no products found"}
        try:
            self.qdrant_client.get_collection(self.collection_name)
        except Exception:
            self.qdrant_client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )
        points = []
        for product in products:
            text = f"Title: {product.title}\nDescription: {product.description or ''}\nURL: {product.url or ''}\nAttributes: {product.attributes or ''}\nVariations: {product.variations or ''}"
            try:
                resp = httpx.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": "llama3", "prompt": text},
                    timeout=60.0
                )
                resp.raise_for_status()
                embedding = resp.json()["embedding"]
            except Exception:
                continue
            points.append(
                PointStruct(
                    id=product.id,
                    vector=embedding,
                    payload={
                        "title": product.title,
                        "description": product.description,
                        "url": product.url,
                        "variations": product.variations,
                        "attributes": product.attributes
                    }
                )
            )
        if points:
            self.qdrant_client.upsert(collection_name=self.collection_name, points=points)
        return {"status": "success", "products_processed": len(points)}

    def search_products(self, request: SearchRequest, db: Session):
        try:
            resp = httpx.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": "llama3", "prompt": request.query},
                timeout=60.0
            )
            resp.raise_for_status()
            query_embedding = resp.json()["embedding"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")
        try:
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=5
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
        try:
            resp = httpx.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": "llama3.2:1b", "prompt": request.prompt},
                timeout=60.0
            )
            resp.raise_for_status()
            query_embedding = resp.json()["embedding"]
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=5
            )
            if search_result:
                product_list = "\n".join([
                    f"- {hit.payload.get('title', 'No Title')} ({hit.payload.get('url', 'No URL')})" for hit in search_result
                ])
                rag_context = (
                    "You are a helpful customer support agent. The user asked: '" + request.prompt + "'.\n"
                    "Here are some relevant products from our catalog that may help answer their question:\n"
                    f"{product_list}\n"
                    "Please answer the user's question and, if relevant, mention these products and their URLs."
                )
            else:
                rag_context = (
                    "You are a helpful customer support agent. The user asked: '" + request.prompt + "'.\n"
                    "No relevant products were found in the catalog. Please answer as best as you can."
                )
        except Exception as e:
            rag_context = (
                "You are a helpful customer support agent. The user asked: '" + request.prompt + "'.\n"
                "(Product search failed, so just answer as best as you can.)"
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
product_service = ProductService()
