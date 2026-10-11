# Menu RAG (local embeddings)

This feature adds semantic search over menu descriptions. PostgreSQL's `menu_items` table remains the source of truth for prices, availability, and inventory. The vector table stores searchable text and embeddings only.

## Components

- Model: `sentence-transformers/all-MiniLM-L6-v2`, running locally on CPU; output dimension is 384.
- Vector storage: PostgreSQL + the `pgvector` extension.
- Category filtering: `menu_embeddings.category` is normalized to lowercase and applied in SQL before results are returned.
- Search endpoint: `GET /api/rag/menu-search?q=spicy%20vegetarian%20burger&category=Burgers&top_k=5`.
- Reindex command: `python -m app.rag.index_menu`.
- Latency benchmark: `python -m app.rag.benchmark --query "spicy vegetarian burger" --category Burgers --runs 10`.

## Setup

From the repository's `backend/` directory:

1. Activate the project's virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Ensure PostgreSQL is running and `DATABASE_URL` in `.env` points at the correct database.
4. Apply migrations: `alembic -c alembic.ini upgrade head`. The migration enables `vector`; the PostgreSQL role needs permission to create the extension, or an administrator must enable it first.
5. Ensure the menu is populated (for example, run `python seed_menu.py` if you use the sample menu).
6. Build embeddings for all current items: `python -m app.rag.index_menu`.
7. Start the API: `uvicorn app.main:app --reload --env-file .env`.
8. Open `http://127.0.0.1:8000/docs` and try `GET /api/rag/menu-search`.

The first model load downloads model files if they are not already cached and can take noticeably longer than subsequent requests. Keep the model cached on the machine/container that runs the API.

## Benchmarking

Run the benchmark after indexing. It warms the model once, then measures query-embedding latency and database retrieval latency separately. It prints the model's first-load time, average latency for each stage, approximate p95 end-to-end latency, and the final result set. Run it on the same machine/database you intend to evaluate; don't treat one run as a universal performance guarantee.

## Index maintenance

New menu items and updates enqueue a FastAPI background task to refresh that item's embedding. A full reindex is the recovery path after deployment, model changes, or any missed background task. Deleting a menu item deletes its embedding through the database foreign key cascade.

If `RAG_EMBEDDING_MODEL` is changed, reindex all menu items. All embeddings in a single table must use the same vector dimensions and compatible model.

## Design constraints

- The embedding text includes item name, category, description, and dietary tags.
- It intentionally excludes price, stock, and availability. Use normal menu/inventory APIs or future MCP tools for those live facts.
- This first version uses exact cosine-distance ordering, which is appropriate for a small restaurant menu. Benchmark before adding an approximate vector index.
- The embedding model does not incur a per-request embedding API charge, but it uses local CPU/RAM and adds model startup/first-request latency.
