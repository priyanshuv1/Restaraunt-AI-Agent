# DineMate AI menu module

Adds a basic cafe menu API independent of the LangGraph/LangChain agent code. Sample INR prices are placeholders; verify them before real use.

From `backend/`, activate the project's virtual environment, configure `DATABASE_URL` in `.env`, and ensure the PostgreSQL database exists:

```bash
alembic -c alembic.ini upgrade head
python seed_menu.py
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

- `GET /api/menu` list all items
- `GET /api/menu?category=Coffee` filter by category
- `GET /api/menu?search=latte` search items
- `GET /api/menu?available_only=true` available items only
- `POST /api/menu` create item
- `PATCH /api/menu/{id}` update item/availability
- `DELETE /api/menu/{id}` delete item

Run tests with `pytest -q`; tests use SQLite. The sample menu is not yet connected to LangGraph tools. Add authentication and restaurant ownership before public deployment.
