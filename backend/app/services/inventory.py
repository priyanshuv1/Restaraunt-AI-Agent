"""Inventory service.

Business rules enforced here:
  1. quantity_on_hand must be >= 0  (also enforced by DB CHECK constraint)
  2. quantity_on_hand must be >= quantity_reserved; otherwise available stock
     would go negative, which would represent a broken reservation state.
  3. An inventory row is created automatically whenever a menu item is created.

This service is intentionally kept stateless (no in-memory cache) so that a
future MCP tool can call check_inventory(menu_item_id) and always read the
latest committed value from PostgreSQL.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.models.menu import MenuItem
from app.schemas.inventory import InventoryRead, InventoryUpdate


# ---------------------------------------------------------------------------
# Internal helper: build InventoryRead dict from ORM object
# ---------------------------------------------------------------------------

def _to_read(inv: InventoryItem) -> dict:
    item = inv.menu_item
    return {
        "menu_item_id": inv.menu_item_id,
        "quantity_on_hand": inv.quantity_on_hand,
        "quantity_reserved": inv.quantity_reserved,
        "quantity_available": inv.quantity_available,
        "updated_at": inv.updated_at,
        # Flattened menu item fields
        "item_id": item.id,
        "item_name": item.name,
        "item_category": item.category,
        "item_description": item.description,
        "item_price": item.price,
        "item_is_available": item.is_available,
        "item_dietary_tags": [x for x in (item.dietary_tags or "").split(",") if x],
    }


# ---------------------------------------------------------------------------
# Public API (called by routes and future MCP tools)
# ---------------------------------------------------------------------------

def list_inventory(db: Session) -> list[dict]:
    """Return all inventory rows joined with menu item data, ordered by category + name."""
    rows = db.scalars(
        select(InventoryItem)
        .join(InventoryItem.menu_item)
        .order_by(MenuItem.category, MenuItem.name)
    ).all()
    return [_to_read(r) for r in rows]


def check_inventory(db: Session, menu_item_id: int) -> dict:
    """
    Retrieve the current inventory for a single menu item.

    Designed to be called by the future DineMate AI agent via an MCP tool.
    Always reads from the database — never returns stale cached values.

    Raises 404 if the menu item does not exist.
    """
    inv = _get_or_404(db, menu_item_id)
    return _to_read(inv)


def update_inventory(
    db: Session, menu_item_id: int, payload: InventoryUpdate
) -> dict:
    """
    Update the physical stock count for a menu item.

    Rules:
    - The new quantity_on_hand must be >= the current quantity_reserved.
      If active reservations exist, we cannot set on_hand below them —
      that would cause available to go negative.
    - Staff set the *absolute* on_hand count (not a delta).
    - quantity_reserved is not touched by this endpoint; only order
      processing adjusts reservations.
    """
    inv = _get_or_404(db, menu_item_id)

    if payload.quantity_on_hand < inv.quantity_reserved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Cannot set on-hand quantity to {payload.quantity_on_hand}. "
                f"There are {inv.quantity_reserved} units currently reserved by "
                f"open orders. Available stock would become negative. "
                f"Minimum allowed on-hand quantity: {inv.quantity_reserved}."
            ),
        )

    inv.quantity_on_hand = payload.quantity_on_hand
    db.commit()
    db.refresh(inv)
    return _to_read(inv)


def create_inventory_for_item(db: Session, menu_item_id: int) -> InventoryItem:
    """
    Create a new inventory row for a freshly created menu item.
    Called automatically by the menu creation route.
    """
    inv = InventoryItem(menu_item_id=menu_item_id, quantity_on_hand=0, quantity_reserved=0)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, menu_item_id: int) -> InventoryItem:
    inv = db.scalar(
        select(InventoryItem).where(InventoryItem.menu_item_id == menu_item_id)
    )
    if inv is None:
        # Check whether the menu item itself exists to give a better error
        item = db.get(MenuItem, menu_item_id)
        if item is None:
            raise HTTPException(404, f"Menu item {menu_item_id} not found")
        # Item exists but inventory row is missing (shouldn't happen after migration)
        raise HTTPException(
            500,
            f"Inventory record missing for menu item {menu_item_id}. "
            "Run the migration and re-seed.",
        )
    return inv
