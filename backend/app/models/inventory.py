"""
Inventory model: one record per menu_items row.

Design notes:
  - quantity_on_hand  : total physical units in the cafe
  - quantity_reserved : units held by open/pending orders (not yet paid or cancelled)
  - quantity_available: computed property = on_hand - reserved  (read-only, always consistent)

Constraints:
  - quantity_on_hand  >= 0
  - quantity_reserved >= 0
  - quantity_on_hand  >= quantity_reserved  (available can never go negative)

A future order service will atomically increment/decrement reserved using
SELECT ... FOR UPDATE to prevent overselling under concurrent load.
"""

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref

from app.db.base import Base


class InventoryItem(Base):
    __tablename__ = "inventory"

    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_on_hand_nonneg"),
        CheckConstraint("quantity_reserved >= 0", name="ck_inventory_reserved_nonneg"),
        CheckConstraint(
            "quantity_on_hand >= quantity_reserved",
            name="ck_inventory_available_nonneg",
        ),
        Index("ix_inventory_menu_item_id", "menu_item_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    menu_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one row per menu item
    )

    quantity_on_hand: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    quantity_reserved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ORM relationship (lazy load is fine for staff dashboard reads)
    menu_item: Mapped["app.models.menu.MenuItem"] = relationship(  # type: ignore[name-defined]
        "MenuItem",
        backref=backref("inventory", passive_deletes=True),
        lazy="joined",
        passive_deletes=True,
    )

    @property
    def quantity_available(self) -> int:
        """Available stock = on_hand - reserved. Always >= 0 by DB constraint."""
        return self.quantity_on_hand - self.quantity_reserved
