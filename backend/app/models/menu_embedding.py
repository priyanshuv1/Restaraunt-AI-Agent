from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


EMBEDDING_DIMENSIONS = 384


class MenuEmbedding(Base):
    """Searchable semantic representation of a menu item.

    PostgreSQL's menu_items table remains the source of truth. This table stores
    only the text/vector needed for semantic retrieval plus category metadata.
    """

    __tablename__ = "menu_embeddings"
    __table_args__ = (
        Index("ix_menu_embeddings_category", "category"),
        Index("ix_menu_embeddings_menu_item_id", "menu_item_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Normalized lowercase category to make category filters predictable.
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String(150), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
