"""Index or refresh menu descriptions in Qdrant.

Run from backend/ after configuring QDRANT_URL (and QDRANT_API_KEY for cloud):
    python -m app.rag.index_menu
"""
from sqlalchemy import select
from qdrant_client.http import models as qmodels

from app.db.session import SessionLocal
from app.models.menu import MenuItem
from app.rag.embeddings import MODEL_NAME, embed_texts
from app.rag.service import (
    QDRANT_COLLECTION,
    build_menu_text,
    ensure_menu_collection,
    get_qdrant_client,
    normalize_category,
)

BATCH_SIZE = 32


def main() -> None:
    ensure_menu_collection()
    client = get_qdrant_client()
    with SessionLocal() as db:
        items = db.scalars(select(MenuItem).order_by(MenuItem.id)).all()
        if not items:
            print("No menu items found; nothing to index.")
            return

        indexed = 0
        for offset in range(0, len(items), BATCH_SIZE):
            batch = items[offset : offset + BATCH_SIZE]
            texts = [build_menu_text(item) for item in batch]
            vectors = embed_texts(texts)
            points = [
                qmodels.PointStruct(
                    id=item.id,
                    vector=vector.tolist(),
                    payload={
                        "menu_item_id": item.id,
                        "category": normalize_category(item.category),
                        "content": content,
                    },
                )
                for item, content, vector in zip(batch, texts, vectors, strict=True)
            ]
            client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=points,
                wait=True,
            )
            indexed += len(points)

    print(f"Qdrant indexing complete: {indexed} menu items using {MODEL_NAME}.")


if __name__ == "__main__":
    main()
