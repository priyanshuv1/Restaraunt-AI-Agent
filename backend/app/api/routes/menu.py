from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.menu import MenuItem
from app.rag.service import delete_menu_vector, index_menu_item
from app.schemas.menu import MenuItemCreate, MenuItemRead, MenuItemUpdate
from app.services.inventory import create_inventory_for_item
from app.services.menu import create_item, list_items, response_data, update_item

router = APIRouter(prefix="/api/menu", tags=["menu"])
RAG_FIELDS = {"name", "category", "description", "dietary_tags"}


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
    if (item := db.get(MenuItem, item_id)) is None:
        raise HTTPException(404, "Menu item not found")
    return response_data(item)


@router.post("", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED)
def add_item(
    payload: MenuItemCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    item = create_item(db, payload)
    create_inventory_for_item(db, item.id)
    db.refresh(item)
    background_tasks.add_task(index_menu_item, item.id)
    return response_data(item)


@router.patch("/{item_id}", response_model=MenuItemRead)
def edit_item(
    item_id: int,
    payload: MenuItemUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(404, "Menu item not found")
    changed_fields = set(payload.model_fields_set)
    if not changed_fields:
        raise HTTPException(422, "Provide at least one field to update")
    updated = update_item(db, item, payload)
    # Price and availability are live SQL fields, so only descriptive changes
    # require a new embedding. Inventory updates never trigger menu re-indexing.
    if changed_fields & RAG_FIELDS:
        background_tasks.add_task(index_menu_item, updated.id)
    return response_data(updated)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(404, "Menu item not found")
    db.delete(item)
    db.commit()
    delete_menu_vector(item_id)
    return Response(status_code=204)
