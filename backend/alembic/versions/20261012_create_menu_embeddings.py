"""Add category-filtered menu embeddings for RAG.

Revision ID: 20261012_menu_rag
Revises: 20261011_inventory
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "20261012_menu_rag"
down_revision = "20261011_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "menu_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "menu_item_id",
            sa.Integer(),
            sa.ForeignKey("menu_items.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("embedding_model", sa.String(150), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_menu_embeddings_category", "menu_embeddings", ["category"]
    )
    op.create_index(
        "ix_menu_embeddings_menu_item_id", "menu_embeddings", ["menu_item_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_menu_embeddings_menu_item_id", table_name="menu_embeddings")
    op.drop_index("ix_menu_embeddings_category", table_name="menu_embeddings")
    op.drop_table("menu_embeddings")
    # Keep the vector extension installed: other tables may use it.
