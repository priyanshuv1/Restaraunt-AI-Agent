# Menu RAG with Qdrant

DineMate uses two stores for different jobs:

- **PostgreSQL is authoritative** for menu records, prices, availability, inventory quantities, and orders.
- **Qdrant stores semantic vectors** and searchable descriptive payloads for menu discovery. It does not store authoritative prices or stock.

The local embedding model is `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) and runs on CPU. It has no per-request embedding API fee, but uses local RAM/CPU and downloads model files on first use.

## Configuration

Add these variables to `backend/.env`:

```dotenv
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=dinemate_menu
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

For Qdrant Cloud, set `QDRANT_URL` to your cluster URL and `QDRANT_API_KEY` to its API key. Do not commit your real `.env` or API key. The local URL is the default and requires Qdrant to be running locally on port 6333.

Install dependencies from `backend/`:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## How retrieval works

1. The API embeds the user's natural-language query locally.
2. Qdrant searches the `dinemate_menu` collection by cosine similarity. If a category is provided, the category filter is applied inside Qdrant before returning results.
3. The returned menu item IDs are hydrated from PostgreSQL so names, descriptions, and dietary tags come from the authoritative menu rows.
4. The response returns a small ranked candidate set, not the full menu.

Price and stock are intentionally excluded from embedded text and Qdrant payloads. Use the existing PostgreSQL-backed `GET /api/menu/{item_id}` endpoint for live price, availability, and quantity fields. Exact price/stock questions should use the database directly rather than infer values from semantic similarity.

## Indexing

After PostgreSQL is configured and contains menu items, configure Qdrant, then run from `backend/`:

```bash
python -m app.rag.index_menu
```

The indexer processes at most 32 menu descriptions per embedding batch to limit memory usage. It upserts Qdrant points using the PostgreSQL menu item ID as the point ID. Re-running it refreshes the index without creating duplicate points.

Creating a new menu item or editing its description/category/name/dietary tags schedules a background re-index. Deleting a menu item also attempts to delete its Qdrant point. Price and inventory changes do not trigger re-embedding.

## API

Start the backend:

```bash
uvicorn app.main:app --reload --env-file .env
```

Semantic search:

```text
GET /api/rag/menu-search?q=spicy%20vegetarian%20burger&category=Burgers&top_k=5
```

Each match includes the menu item ID, descriptive fields, and similarity score. Use `GET /api/menu/{item_id}` to fetch live price, availability, and inventory values for a selected match.

## Latency benchmark

```bash
python -m app.rag.benchmark --query "spicy vegetarian burger" --category Burgers --runs 10
```

Run the benchmark against the configured Qdrant service and the same PostgreSQL database you intend to evaluate. Measure results on the target machine; do not assume a benchmark from another system represents your latency.

## Notes

- Qdrant must be reachable and configured before indexing or semantic search.
- If Qdrant is unavailable during menu CRUD, the database operation still succeeds; the failure is logged. Re-run the indexer to repair missing/stale points.
- PostgreSQL remains the source of truth. Never answer live price or stock questions from Qdrant payloads.
