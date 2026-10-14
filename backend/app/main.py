import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.menu import router as menu_router
from app.api.routes.rag import router as rag_router

app = FastAPI(title="DineMate AI API", version="0.2.0")

_default_dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_configured_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
_origins = list(dict.fromkeys(_default_dev_origins + _configured_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(menu_router)
app.include_router(inventory_router)
app.include_router(rag_router)
app.include_router(agent_router)


@app.get("/")
def root():
    return {
        "name": "DineMate AI",
        "status": "running",
        "docs": "/docs",
        "menu": "/api/menu",
        "inventory": "/api/inventory",
        "rag_menu_search": "/api/rag/menu-search",
        "agent_chat": "/api/agent/chat",
        "agent_session": "/api/agent/session/{session_id}",
        "agent_order": "/api/agent/orders/{order_id}",
    }
