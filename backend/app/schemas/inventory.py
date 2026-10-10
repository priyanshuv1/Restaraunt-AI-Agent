from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InventoryUpdate(BaseModel):
    """PATCH /api/inventory/{menu_item_id} request body.

    Staff supply the new *total physical* quantity on hand.
    The service will enforce:
      - new_on_hand >= 0
      - new_on_hand >= quantity_reserved  (available stays non-negative)
    """
    quantity_on_hand: int = Field(ge=0, description="Total physical units in the cafe")


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
