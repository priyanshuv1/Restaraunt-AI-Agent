"""Index or refresh every menu item in the RAG vector table.

Run from backend/ after applying migrations:
    python -m app.rag.index_menu
"""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.menu import MenuItem
from app.rag.embeddings import MODEL_NAME, embed_texts
from app.rag.service import _upsert_embedding, build_menu_text


def main() -> None:
    with SessionLocal() as db:
        items = db.scalars(select(MenuItem).order_by(MenuItem.id)).all()
        if not items:
            print("No menu items found; nothing to index.")
            return

        texts = [build_menu_text(item) for item in items]
        vectors = embed_texts(texts)
        for item, content, vector in zip(items, texts, vectors, strict=True):
            _upsert_embedding(db, item, content, vector.tolist())
        db.commit()

    print(f"RAG indexing complete: {len(items)} menu items using {MODEL_NAME}.")


if __name__ == "__main__":
    main()
