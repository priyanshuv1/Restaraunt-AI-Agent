from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.inventory import InventoryRead, InventoryUpdate
from app.services.inventory import check_inventory, list_inventory, update_inventory

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryRead])
def get_inventory(db: Session = Depends(get_db)):
    """Return all inventory rows joined with menu item data.

    The staff dashboard calls this once on load; the AI agent's MCP tool
    will call check_inventory() per item instead of listing all.
    """
    return list_inventory(db)


@router.get("/{menu_item_id}", response_model=InventoryRead)
def get_inventory_item(menu_item_id: int, db: Session = Depends(get_db)):
    """Return inventory for a single menu item.

    Designed to be the backing endpoint for the future MCP check_inventory tool.
    Always returns live database data.
    """
    return check_inventory(db, menu_item_id)


@router.patch("/{menu_item_id}", response_model=InventoryRead)
def patch_inventory(
    menu_item_id: int,
    payload: InventoryUpdate,
    db: Session = Depends(get_db),
):
    """Update the physical stock count for a menu item.

    Supply the new absolute quantity_on_hand value.
    Returns 422 if the new value would undercut active reservations.
    """
    return update_inventory(db, menu_item_id, payload)
