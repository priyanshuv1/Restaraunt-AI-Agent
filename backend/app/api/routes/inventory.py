from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.inventory import (
    BulkInventoryUpdate,
    InventoryRead,
    InventoryUpdate,
)
from app.services.inventory import (
    bulk_update_inventory,
    check_inventory,
    list_inventory,
    update_inventory,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryRead])
def get_inventory(db: Session = Depends(get_db)):
    """Return inventory rows joined with menu item data."""
    return list_inventory(db)


@router.get("/{menu_item_id}", response_model=InventoryRead)
def get_inventory_item(menu_item_id: int, db: Session = Depends(get_db)):
    """Return live inventory for one menu item; suitable for the future MCP tool."""
    return check_inventory(db, menu_item_id)


@router.patch("/bulk", response_model=list[InventoryRead])
def patch_inventory_bulk(
    payload: BulkInventoryUpdate,
    db: Session = Depends(get_db),
):
    """Atomically save multiple stock counts in a single database transaction."""
    return bulk_update_inventory(db, payload)


@router.patch("/{menu_item_id}", response_model=InventoryRead)
def patch_inventory(
    menu_item_id: int,
    payload: InventoryUpdate,
    db: Session = Depends(get_db),
):
    """Update the physical stock count for one menu item."""
    return update_inventory(db, menu_item_id, payload)
