from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InventoryUpdate(BaseModel):
    """PATCH /api/inventory/{menu_item_id} request body."""
    quantity_on_hand: int = Field(ge=0, description="Total physical units in the cafe")


class BulkInventoryUpdateItem(BaseModel):
    """One inventory quantity in a bulk save request."""
    menu_item_id: int = Field(gt=0)
    quantity_on_hand: int = Field(ge=0, description="Total physical units in the cafe")


class BulkInventoryUpdate(BaseModel):
    """PATCH /api/inventory/bulk request body."""
    items: list[BulkInventoryUpdateItem] = Field(min_length=1)

    @model_validator(mode="after")
    def menu_item_ids_must_be_unique(self):
        ids = [item.menu_item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each menu_item_id may appear only once in a bulk update")
        return self


class InventoryRead(BaseModel):
    """Response schema — returned for both GET list and PATCH."""

    model_config = ConfigDict(from_attributes=True)

    menu_item_id: int
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    updated_at: datetime

    # Flattened menu item fields for convenience (so the frontend gets
    # everything in one request without a join)
    item_id: int
    item_name: str
    item_category: str
    item_description: str
    item_price: Decimal
    item_is_available: bool
    item_dietary_tags: list[str]
