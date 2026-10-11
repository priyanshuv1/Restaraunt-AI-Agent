from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.rag.service import search_menu_knowledge

router = APIRouter(prefix="/api/rag", tags=["rag"])


class MenuKnowledgeMatch(BaseModel):
    menu_item_id: int
    name: str
    category: str
    description: str
    dietary_tags: list[str]
    similarity: float = Field(ge=-1.0, le=1.0)


@router.get("/menu-search", response_model=list[MenuKnowledgeMatch])
def menu_search(
    q: str = Query(min_length=1, max_length=500),
    category: str | None = Query(default=None, max_length=50),
    top_k: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Semantic search over menu descriptions; price and stock stay live in DB."""
    return search_menu_knowledge(db, q, category, top_k)
