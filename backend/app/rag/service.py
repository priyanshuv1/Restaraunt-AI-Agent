import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.menu import MenuItem
from app.models.menu_embedding import MenuEmbedding
from app.rag.embeddings import MODEL_NAME, embed_texts

logger = logging.getLogger(__name__)


def normalize_category(category: str | None) -> str | None:
    """Normalize category metadata and filters consistently."""
    if category is None:
        return None
    normalized = category.strip().casefold()
    return normalized or None


def build_menu_text(item: MenuItem) -> str:
    """Build the descriptive text embedded for one menu item.

    Deliberately excludes price, stock and availability: those values must be
    read from the live database/backend rather than semantic search results.
    """
    raw_tags = item.dietary_tags or ""
    if isinstance(raw_tags, list):
        tags = [str(tag).strip().lower() for tag in raw_tags if str(tag).strip()]
    else:
        tags = [tag.strip().lower() for tag in raw_tags.split(",") if tag.strip()]

    parts = [
        f"Menu item: {item.name.strip()}",
        f"Category: {item.category.strip()}",
        f"Description: {(item.description or '').strip()}",
    ]
    if tags:
        parts.append(f"Dietary tags: {', '.join(tags)}")
    return "\n".join(parts)


def _upsert_embedding(
    db: Session, item: MenuItem, content: str, vector: list[float]
) -> None:
    category = normalize_category(item.category)
    if category is None:
        raise ValueError(f"Menu item {item.id} has an empty category")

    record = db.scalar(
        select(MenuEmbedding).where(MenuEmbedding.menu_item_id == item.id)
    )
    if record is None:
        record = MenuEmbedding(
            menu_item_id=item.id,
            category=category,
            content=content,
            embedding=vector,
            embedding_model=MODEL_NAME,
        )
        db.add(record)
    else:
        record.category = category
        record.content = content
        record.embedding = vector
        record.embedding_model = MODEL_NAME


def index_menu_item(menu_item_id: int) -> None:
    """Background task: index the current database version of one menu item."""
    try:
        with SessionLocal() as db:
            item = db.get(MenuItem, menu_item_id)
            if item is None:
                # Deleting a menu item cascades to its embedding row.
                return
            content = build_menu_text(item)
            vector = embed_texts([content])[0].tolist()
            _upsert_embedding(db, item, content, vector)
            db.commit()
    except Exception:
        # Indexing must not turn a successful menu CRUD response into a failure.
        # The exception is logged so an operator can diagnose missing embeddings.
        logger.exception("Failed to index menu item %s for RAG", menu_item_id)


def search_menu_by_embedding(
    db: Session,
    query_embedding: list[float],
    category: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Run exact cosine-distance search, optionally filtered by category."""
    distance = MenuEmbedding.embedding.cosine_distance(query_embedding)
    stmt = (
        select(MenuEmbedding, MenuItem, distance.label("cosine_distance"))
        .join(MenuItem, MenuItem.id == MenuEmbedding.menu_item_id)
    )

    normalized_category = normalize_category(category)
    if normalized_category:
        stmt = stmt.where(MenuEmbedding.category == normalized_category)

    stmt = stmt.order_by(distance).limit(top_k)
    rows = db.execute(stmt).all()

    matches = []
    for embedding_record, item, cosine_distance in rows:
        similarity = max(-1.0, min(1.0, 1.0 - float(cosine_distance)))
        raw_tags = item.dietary_tags or ""
        matches.append(
            {
                "menu_item_id": item.id,
                "name": item.name,
                "category": item.category,
                "description": item.description,
                "dietary_tags": [
                    tag.strip() for tag in raw_tags.split(",") if tag.strip()
                ],
                "similarity": round(similarity, 4),
            }
        )
    return matches


def search_menu_knowledge(
    db: Session,
    query: str,
    category: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Embed a natural-language query and retrieve relevant menu knowledge."""
    query_embedding = embed_texts([query.strip()])[0].tolist()
    return search_menu_by_embedding(db, query_embedding, category, top_k)
