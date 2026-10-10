"""Inventory service.

Business rules enforced here:
  1. quantity_on_hand must be >= 0 (also enforced by DB CHECK constraint)
  2. quantity_on_hand must be >= quantity_reserved.
  3. Inventory reads always come from the database; no in-memory cache is used.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.models.menu import MenuItem
from app.schemas.inventory import BulkInventoryUpdate, InventoryUpdate


def _to_read(inv: InventoryItem) -> dict:
    item = inv.menu_item
    return {
        "menu_item_id": inv.menu_item_id,
        "quantity_on_hand": inv.quantity_on_hand,
        "quantity_reserved": inv.quantity_reserved,
        "quantity_available": inv.quantity_available,
        "updated_at": inv.updated_at,
        "item_id": item.id,
        "item_name": item.name,
        "item_category": item.category,
        "item_description": item.description,
        "item_price": item.price,
        "item_is_available": item.is_available,
        "item_dietary_tags": [x for x in (item.dietary_tags or "").split(",") if x],
    }


def list_inventory(db: Session) -> list[dict]:
    """Return all inventory rows joined with menu item data, ordered by category + name."""
    rows = db.scalars(
        select(InventoryItem)
        .join(InventoryItem.menu_item)
        .order_by(MenuItem.category, MenuItem.name)
    ).all()
    return [_to_read(row) for row in rows]


def check_inventory(db: Session, menu_item_id: int) -> dict:
    """Read the latest committed inventory for one menu item."""
    inv = _get_or_404(db, menu_item_id)
    return _to_read(inv)


def _validate_quantity(inv: InventoryItem, quantity_on_hand: int) -> None:
    if quantity_on_hand < inv.quantity_reserved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Cannot set on-hand quantity to {quantity_on_hand}. "
                f"There are {inv.quantity_reserved} units currently reserved by "
                f"open orders. Minimum allowed on-hand quantity: {inv.quantity_reserved}."
            ),
        )


def update_inventory(
    db: Session, menu_item_id: int, payload: InventoryUpdate
) -> dict:
    """Update one item's absolute physical stock count."""
    inv = _get_or_404(db, menu_item_id)
    _validate_quantity(inv, payload.quantity_on_hand)

    inv.quantity_on_hand = payload.quantity_on_hand
    db.commit()
    db.refresh(inv)
    return _to_read(inv)


def bulk_update_inventory(db: Session, payload: BulkInventoryUpdate) -> list[dict]:
    """Save all requested inventory counts in one database transaction.

    All rows are fetched and validated before any quantity is mutated. A single
    commit applies the batch; any error rolls the entire transaction back.
    """
    requested = {item.menu_item_id: item.quantity_on_hand for item in payload.items}
    try:
        rows = db.scalars(
            select(InventoryItem)
            .where(InventoryItem.menu_item_id.in_(requested.keys()))
            .order_by(InventoryItem.menu_item_id)
            # The relationship uses lazy="joined", which adds a LEFT OUTER JOIN
            # to menu_items. Lock only inventory rows; PostgreSQL cannot apply
            # FOR UPDATE to the nullable side of that outer join.
            .with_for_update(of=InventoryItem)
        ).all()
        by_menu_id = {row.menu_item_id: row for row in rows}

        missing_ids = sorted(set(requested) - set(by_menu_id))
        if missing_ids:
            missing_menu_ids = [
                item_id for item_id in missing_ids if db.get(MenuItem, item_id) is None
            ]
            if missing_menu_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Menu item(s) not found: {missing_menu_ids}",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Inventory record missing for menu item(s): {missing_ids}",
            )

        # Validate every requested quantity before changing any ORM object.
        for menu_item_id, quantity in requested.items():
            _validate_quantity(by_menu_id[menu_item_id], quantity)

        for menu_item_id, quantity in requested.items():
            by_menu_id[menu_item_id].quantity_on_hand = quantity

        db.flush()
        db.commit()

        for menu_item_id in requested:
            db.refresh(by_menu_id[menu_item_id])
        return [_to_read(by_menu_id[item_id]) for item_id in requested]
    except Exception:
        db.rollback()
        raise


def create_inventory_for_item(db: Session, menu_item_id: int) -> InventoryItem:
    """Create a zero-stock inventory row for a newly created menu item."""
    inv = InventoryItem(menu_item_id=menu_item_id, quantity_on_hand=0, quantity_reserved=0)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def _get_or_404(db: Session, menu_item_id: int) -> InventoryItem:
    inv = db.scalar(
        select(InventoryItem).where(InventoryItem.menu_item_id == menu_item_id)
    )
    if inv is None:
        item = db.get(MenuItem, menu_item_id)
        if item is None:
            raise HTTPException(404, f"Menu item {menu_item_id} not found")
        raise HTTPException(
            500,
            f"Inventory record missing for menu item {menu_item_id}. Run the migration and re-seed.",
        )
    return inv
