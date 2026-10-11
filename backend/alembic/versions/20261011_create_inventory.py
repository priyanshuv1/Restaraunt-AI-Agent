"""Create inventory table linked to menu_items.

Each menu item gets exactly one inventory row (UNIQUE constraint on menu_item_id).
Existing menu_items rows receive a default row with quantity_on_hand = 0.

Columns:
    id               – serial PK
    menu_item_id     – FK → menu_items.id (CASCADE DELETE, UNIQUE)
    quantity_on_hand – total physical units on hand (>= 0)
    quantity_reserved– units locked by open orders  (>= 0, <= on_hand)
    updated_at       – auto-updated timestamp

Revision ID: 20261011_inventory
"""

from alembic import op
import sqlalchemy as sa

revision = "20261011_inventory"
down_revision = "20261010_menu"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "menu_item_id",
            sa.Integer(),
            sa.ForeignKey("menu_items.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "quantity_on_hand",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "quantity_reserved",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_on_hand_nonneg"),
        sa.CheckConstraint(
            "quantity_reserved >= 0", name="ck_inventory_reserved_nonneg"
        ),
        sa.CheckConstraint(
            "quantity_on_hand >= quantity_reserved",
            name="ck_inventory_available_nonneg",
        ),
    )

    op.create_index("ix_inventory_menu_item_id", "inventory", ["menu_item_id"])

    # Seed one inventory row for every existing menu item (on_hand = 0 by default).
    # Staff can then update quantities through the dashboard.
    op.execute(
        """
        INSERT INTO inventory (menu_item_id, quantity_on_hand, quantity_reserved)
        SELECT id, 0, 0
        FROM menu_items
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_menu_item_id", table_name="inventory")
    op.drop_table("inventory")
