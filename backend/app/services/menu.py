from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.menu import MenuItem
from app.schemas.menu import MenuItemCreate, MenuItemUpdate


def list_items(
    db: Session,
    category: str | None = None,
    search: str | None = None,
    available_only: bool = False,
):
    stmt = select(MenuItem).order_by(MenuItem.category, MenuItem.name)
    if category:
        stmt = stmt.where(MenuItem.category.ilike(category.strip()))
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                MenuItem.name.ilike(term),
                MenuItem.description.ilike(term),
                MenuItem.category.ilike(term),
            )
        )
    if available_only:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    return list(db.scalars(stmt).all())


def response_data(item: MenuItem) -> dict:
    """Serialize a MenuItem ORM object to a response dict.

    Includes inventory fields when a joined InventoryItem is present on
    the item (via the 'inventory' backref). Falls back to None so that
    existing tests using SQLite (which don't run the Alembic migration)
    continue to pass.
    """
    inv = item.inventory if hasattr(item, "inventory") else None
    # 'inventory' backref is a list when not unique — but we declared it unique,
    # so SQLAlchemy may give us a list of one or the object directly depending on
    # how the relationship is configured. Normalise to a single object or None.
    if isinstance(inv, list):
        inv = inv[0] if inv else None

    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "description": item.description,
        "price": item.price,
        "is_available": item.is_available,
        "dietary_tags": [x for x in (item.dietary_tags or "").split(",") if x],
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        # Inventory — None when no inventory row exists (e.g. in unit tests)
        "quantity_on_hand": inv.quantity_on_hand if inv is not None else None,
        "quantity_reserved": inv.quantity_reserved if inv is not None else None,
        "quantity_available": inv.quantity_available if inv is not None else None,
    }


def create_item(db: Session, payload: MenuItemCreate) -> MenuItem:
    data = payload.model_dump()
    data["dietary_tags"] = ",".join(
        x.strip().lower() for x in data["dietary_tags"] if x.strip()
    )
    item = MenuItem(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: MenuItem, payload: MenuItemUpdate) -> MenuItem:
    data = payload.model_dump(exclude_unset=True)
    if "dietary_tags" in data and data["dietary_tags"] is not None:
        data["dietary_tags"] = ",".join(
            x.strip().lower() for x in data["dietary_tags"] if x.strip()
        )
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item
