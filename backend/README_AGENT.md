# DineMate restaurant agent

The backend agent is a five-stage LangGraph workflow:

1. Understand the current customer request with Groq structured output.
2. Resolve requested dishes with the MCP `search_menu` and `get_menu_item` tools.
3. Maintain a persistent draft, validate current price/availability/stock, and calculate the displayed total deterministically.
4. Require explicit confirmation before order placement.
5. Place the order in one PostgreSQL transaction, lock inventory rows, reserve stock, and save an order/item price snapshot.

PostgreSQL remains authoritative for prices, availability, inventory, and orders. Qdrant is used only to retrieve semantically relevant candidates. The agent does not process payments.

## Configuration

In `backend/.env`, configure:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
QDRANT_URL=https://your-qdrant-cluster-url
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=dinemate_menu
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Keep `.env` out of Git. Never send API keys in chat or logs.

## Database migration and grants

The new migration adds `agent_sessions`, `orders`, and `order_items`. Back up important data before applying schema changes. Run migrations with a `DATABASE_URL` that authenticates as a database owner/administrator. The limited runtime role may not have permission to create tables. Do not paste the admin URL or password into chat.

From `backend/`, with the virtual environment active, set the admin connection only in your local shell and run:

```bash
# Set DATABASE_URL to your local PostgreSQL administrator connection.
export DATABASE_URL='postgresql+psycopg://ADMIN_USER:ADMIN_PASSWORD@localhost:5432/dinemate'
alembic upgrade head
```

After migration, configure the runtime application's normal DATABASE_URL again and apply the grants below as an administrator.

If the runtime role is `dinemate_app`, grant only the permissions needed by the agent. Run as a PostgreSQL administrator after the migration:

```sql
GRANT SELECT ON TABLE public.menu_items TO dinemate_app;
GRANT SELECT ON TABLE public.inventory TO dinemate_app;
GRANT UPDATE (quantity_reserved) ON TABLE public.inventory TO dinemate_app;
GRANT SELECT, INSERT, UPDATE ON TABLE public.agent_sessions TO dinemate_app;
GRANT SELECT, INSERT ON TABLE public.orders TO dinemate_app;
GRANT SELECT, INSERT ON TABLE public.order_items TO dinemate_app;
GRANT USAGE, SELECT ON SEQUENCE public.orders_id_seq TO dinemate_app;
GRANT USAGE, SELECT ON SEQUENCE public.order_items_id_seq TO dinemate_app;
```

The runtime role also needs `SELECT` on menu and inventory tables, including any existing grants required by the current menu API. Do not grant blanket superuser privileges.

## Run the API

From `backend/`:

```bash
source .venv/bin/activate
set -a
source .env
set +a
uvicorn app.main:app --reload --env-file .env
```

Open `http://127.0.0.1:8000/docs` to inspect the API.

## Chat API

```http
POST /api/agent/chat
Content-Type: application/json

{
  "message": "Recommend a spicy vegetarian dish"
}
```

The response contains `session_id`. Reuse it on subsequent messages to continue the same conversation:

```json
{
  "session_id": "the-session-id-from-the-previous-response",
  "message": "Add two of the second item"
}
```

Useful endpoints:

- `GET /api/agent/session/{session_id}` — retrieve persisted messages and draft order.
- `GET /api/agent/orders/{order_id}` — retrieve a saved order.
- `GET /api/rag/menu-search?q=spicy%20vegetarian%20food` — test retrieval without the LLM.

## Order safety

- The LLM never supplies authoritative prices or stock.
- The order tool re-reads prices and availability from PostgreSQL, locks inventory rows, validates requested quantities, and reserves stock atomically.
- An order is not created until the agent accepts an explicit confirmation for the current draft.
- Payment processing, authentication/customer identity, cancellation/refund handling, and production-grade idempotency are not implemented in this milestone. Do not expose this development API publicly before adding authentication and rate limiting.
