from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.menu import MenuItem
from app.schemas.menu import MenuItemCreate, MenuItemRead, MenuItemUpdate
from app.services.inventory import create_inventory_for_item
from app.services.menu import create_item, list_items, response_data, update_item

router = APIRouter(prefix="/api/menu", tags=["menu"])


@router.get("", response_model=list[MenuItemRead])
def get_menu(
    category: str | None = Query(default=None, max_length=50),
    search: str | None = Query(default=None, max_length=120),
    available_only: bool = False,
    db: Session = Depends(get_db),
):
    return [response_data(x) for x in list_items(db, category, search, available_only)]


@router.get("/{item_id}", response_model=MenuItemRead)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(404, "Menu item not found")
    return response_data(item)


@router.post("", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED)
def add_item(payload: MenuItemCreate, db: Session = Depends(get_db)):
    item = create_item(db, payload)
    # Automatically create the corresponding inventory row so the item
    # is immediately visible in the inventory dashboard.
    create_inventory_for_item(db, item.id)
    # Re-fetch so the ORM relationship is loaded (inventory backref)
    db.refresh(item)
    return response_data(item)


@router.patch("/{item_id}", response_model=MenuItemRead)
def edit_item(item_id: int, payload: MenuItemUpdate, db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(404, "Menu item not found")
    if not payload.model_fields_set:
        raise HTTPException(422, "Provide at least one field to update")
    return response_data(update_item(db, item, payload))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(404, "Menu item not found")
    db.delete(item)
    db.commit()
    return Response(status_code=204)
