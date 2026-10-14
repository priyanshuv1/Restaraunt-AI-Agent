import logging
import os
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.menu import MenuItem
from app.rag.embeddings import MODEL_NAME, embed_texts

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "dinemate_menu")
EMBEDDING_DIMENSIONS = 384


def normalize_category(category: str | None) -> str | None:
    """Normalize category metadata and filters consistently."""
    if category is None:
        return None
    normalized = category.strip().casefold()
    return normalized or None


def build_menu_text(item: MenuItem) -> str:
    """Build semantic text without volatile price, stock, or availability."""
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


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Create one Qdrant client per API process."""
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def ensure_menu_collection() -> None:
    """Create the DineMate collection if it does not exist yet."""
    client = get_qdrant_client()
    if not client.collection_exists(collection_name=QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=qmodels.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=qmodels.Distance.COSINE,
            ),
        )
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION,
            field_name="category",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
            wait=True,
        )


def index_menu_item(menu_item_id: int) -> None:
    """Refresh one menu item's semantic point in Qdrant."""
    try:
        with SessionLocal() as db:
            item = db.get(MenuItem, menu_item_id)
            if item is None:
                delete_menu_vector(menu_item_id)
                return
            content = build_menu_text(item)
            vector = embed_texts([content])[0].tolist()
            ensure_menu_collection()
            get_qdrant_client().upsert(
                collection_name=QDRANT_COLLECTION,
                points=[
                    qmodels.PointStruct(
                        id=item.id,
                        vector=vector,
                        payload={
                            "menu_item_id": item.id,
                            "category": normalize_category(item.category),
                            "content": content,
                        },
                    )
                ],
                wait=True,
            )
    except Exception:
        logger.exception("Failed to index menu item %s in Qdrant", menu_item_id)


def delete_menu_vector(menu_item_id: int) -> None:
    """Delete a menu item's Qdrant point; failures are logged for later cleanup."""
    try:
        client = get_qdrant_client()
        if client.collection_exists(collection_name=QDRANT_COLLECTION):
            client.delete(
                collection_name=QDRANT_COLLECTION,
                points_selector=qmodels.PointIdsList(points=[menu_item_id]),
                wait=True,
            )
    except Exception:
        logger.exception("Failed to delete menu item %s from Qdrant", menu_item_id)


def search_menu_by_embedding(
    db: Session,
    query_embedding: list[float],
    category: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Search Qdrant, then hydrate candidates from the authoritative SQL database."""
    ensure_menu_collection()
    normalized_category = normalize_category(category)
    query_filter = None
    if normalized_category:
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="category",
                    match=qmodels.MatchValue(value=normalized_category),
                )
            ]
        )

    response = get_qdrant_client().query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_embedding,
        query_filter=query_filter,
        limit=max(1, min(int(top_k), 50)),
        with_payload=True,
    )

    ranked_ids: list[tuple[int, float]] = []
    for point in response.points:
        payload = point.payload or {}
        item_id = payload.get("menu_item_id", point.id)
        try:
            ranked_ids.append((int(item_id), float(point.score)))
        except (TypeError, ValueError):
            logger.warning("Skipping Qdrant point with invalid menu item ID: %s", point.id)

    if not ranked_ids:
        return []

    item_ids = [item_id for item_id, _ in ranked_ids]
    items = db.scalars(select(MenuItem).where(MenuItem.id.in_(item_ids))).all()
    items_by_id = {item.id: item for item in items}

    matches = []
    for item_id, score in ranked_ids:
        item = items_by_id.get(item_id)
        if item is None:
            continue
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
                "similarity": round(max(-1.0, min(1.0, score)), 4),
            }
        )
    return matches


def search_menu_knowledge(
    db: Session,
    query: str,
    category: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Embed a query locally and retrieve relevant menu candidates from Qdrant."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []
    query_embedding = embed_texts([cleaned_query])[0].tolist()
    return search_menu_by_embedding(db, query_embedding, category, top_k)
