# The main FastAPI app entry point will be simplified after refactor.
# All logic will be moved to app/ submodules.

from app.main import app

# Qdrant setup
qdrant_client = QdrantClient(host="qdrant", port=6333)

# Database setup
MYSQL_USER = os.getenv('MYSQL_USER', 'llmuser')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'llmpassword')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
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

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok"}

OLLAMA_BASE_URL = "http://ollama:11434"

class ChatRequest(BaseModel):
    model: str
    prompt: str

@app.post("/chat")
async def chat(request: ChatRequest):
    # --- RAG: Search Qdrant for relevant products ---
    collection_name = "products"
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": "llama3", "prompt": request.prompt},
            timeout=60.0
        )
        resp.raise_for_status()
        query_embedding = resp.json()["embedding"]
        search_result = qdrant_client.search(
            collection_name=collection_name,
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

    # --- Stream response from Ollama with RAG context ---
    try:
        async def stream_response():
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={"model": request.model, "prompt": rag_context, "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_response(), media_type="application/x-ndjson")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/syncProducts")
def sync_products():
    WC_URL = os.getenv('WC_URL', 'http://wordpress/wp-json/wc/v3/products/')
    WC_KEY = os.getenv('WC_KEY')
    WC_SECRET = os.getenv('WC_SECRET')

    if not WC_KEY or not WC_SECRET:
        raise HTTPException(status_code=500, detail="WooCommerce API credentials are not set.")

    # Use requests_oauthlib for OAuth 1.0a
    oauth = OAuth1Session(WC_KEY, client_secret=WC_SECRET)

    try:
        response = oauth.get(WC_URL, timeout=30.0)
        response.raise_for_status()
        wc_products = response.json()

        db = SessionLocal()
        try:
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
        finally:
            db.close()
        return {"status": "success", "products_synced": len(wc_products)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/processProducts")
def process_products():
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        if not products:
            return {"status": "no products found"}

        # Ensure Qdrant collection exists
        collection_name = "products"
        vector_size = 4096  # llama3 embedding size
        try:
            qdrant_client.get_collection(collection_name)
        except Exception:
            qdrant_client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )

        points = []
        for product in products:
            # Combine fields for embedding
            text = f"Title: {product.title}\nDescription: {product.description or ''}\nURL: {product.url or ''}\nAttributes: {product.attributes or ''}\nVariations: {product.variations or ''}"
            # Get embedding from Ollama
            try:
                resp = httpx.post(
                    f"{OLLAMA_BASE_URL}/api/embeddings",
                    json={"model": "llama3", "prompt": text},
                    timeout=60.0
                )
                resp.raise_for_status()
                embedding = resp.json()["embedding"]
            except Exception as e:
                continue  # skip this product if embedding fails
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
            qdrant_client.upsert(collection_name=collection_name, points=points)
        return {"status": "success", "products_processed": len(points)}
    finally:
        db.close()

class SearchRequest(BaseModel):
    query: str

@app.post("/searchProducts")
def search_products(request: SearchRequest):
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