"""MCP tools for the DineMate ordering agent.

Run with: python -m app.tools.mcp_server
The server uses the same DATABASE_URL and Qdrant environment as the API.
"""
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.inventory import InventoryItem
from app.models.menu import MenuItem
from app.models.orders import Order, OrderItem
from app.rag.service import search_menu_knowledge

mcp = FastMCP("dinemate-restaurant-tools")


def _json(data: Any) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)


@mcp.tool()
def search_menu(query: str, category: str | None = None, top_k: int = 5) -> str:
    """Find semantically relevant menu items. Results are candidates, not live prices."""
    with SessionLocal() as db:
        matches = search_menu_knowledge(db, query, category, max(1, min(top_k, 10)))
        return _json(matches)


@mcp.tool()
def get_menu_item(menu_item_id: int) -> str:
    """Get authoritative menu price, availability, and current stock for one item."""
    with SessionLocal() as db:
        item = db.get(MenuItem, menu_item_id)
        if item is None:
            return _json({"error": "Menu item not found", "menu_item_id": menu_item_id})
        inventory = db.scalar(
            select(InventoryItem).where(InventoryItem.menu_item_id == menu_item_id)
        )
        return _json(
            {
                "menu_item_id": item.id,
                "name": item.name,
                "category": item.category,
                "description": item.description,
                "price": str(item.price),
                "is_available": item.is_available,
                "dietary_tags": [x.strip() for x in (item.dietary_tags or "").split(",") if x.strip()],
                "quantity_on_hand": inventory.quantity_on_hand if inventory else None,
                "quantity_reserved": inventory.quantity_reserved if inventory else None,
                "quantity_available": inventory.quantity_available if inventory else None,
            }
        )


@mcp.tool()
def check_inventory(menu_item_id: int) -> str:
    """Read current available stock for a menu item from PostgreSQL."""
    with SessionLocal() as db:
        inventory = db.scalar(
            select(InventoryItem).where(InventoryItem.menu_item_id == menu_item_id)
        )
        if inventory is None:
            return _json({"error": "Inventory record not found", "menu_item_id": menu_item_id})
        return _json(
            {
                "menu_item_id": menu_item_id,
                "quantity_on_hand": inventory.quantity_on_hand,
                "quantity_reserved": inventory.quantity_reserved,
                "quantity_available": inventory.quantity_available,
            }
        )


@mcp.tool()
def place_order(session_id: str, items_json: str, confirmed: bool) -> str:
    """Create an order only when confirmed=true; validate current price and stock atomically.

    items_json must be a JSON array of objects with menu_item_id and quantity.
    """
    if confirmed is not True:
        return _json({"error": "Explicit customer confirmation is required."})
    try:
        requested = json.loads(items_json)
        if not isinstance(requested, list) or not requested:
            return _json({"error": "The order must contain at least one item."})
        quantities: dict[int, int] = {}
        for entry in requested:
            item_id = int(entry["menu_item_id"])
            quantity = int(entry["quantity"])
            if item_id <= 0 or quantity <= 0 or quantity > 50:
                return _json({"error": "Item IDs and quantities must be positive; max quantity is 50."})
            quantities[item_id] = quantities.get(item_id, 0) + quantity
        if not session_id or len(session_id) > 36:
            return _json({"error": "Invalid session ID."})
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return _json({"error": "Invalid order payload."})

    with SessionLocal() as db:
        try:
            with db.begin():
                inventory_rows = db.scalars(
                    select(InventoryItem)
                    .where(InventoryItem.menu_item_id.in_(quantities))
                    .order_by(InventoryItem.menu_item_id)
                    .with_for_update(of=InventoryItem)
                ).all()
                inventory_by_id = {row.menu_item_id: row for row in inventory_rows}
                menu_rows = db.scalars(
                    select(MenuItem).where(MenuItem.id.in_(quantities))
                ).all()
                menu_by_id = {row.id: row for row in menu_rows}

                missing = sorted(set(quantities) - set(menu_by_id))
                if missing:
                    return _json({"error": f"Menu item(s) no longer exist: {missing}"})
                missing_inventory = sorted(set(quantities) - set(inventory_by_id))
                if missing_inventory:
                    return _json({"error": f"Inventory record missing for item(s): {missing_inventory}"})

                problems = []
                total = Decimal("0.00")
                order_lines = []
                for item_id, quantity in sorted(quantities.items()):
                    item = menu_by_id[item_id]
                    inventory = inventory_by_id[item_id]
                    available = inventory.quantity_available
                    if not item.is_available:
                        problems.append(f"{item.name} is currently unavailable.")
                        continue
                    if available < quantity:
                        problems.append(f"{item.name}: requested {quantity}, only {available} available.")
                        continue
                    unit_price = Decimal(item.price)
                    line_total = unit_price * quantity
                    total += line_total
                    order_lines.append(
                        {
                            "menu_item_id": item.id,
                            "item_name": item.name,
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "line_total": line_total,
                            "inventory": inventory,
                        }
                    )
                if problems:
                    return _json({"error": "Order validation failed.", "details": problems})

                order = Order(
                    session_id=session_id,
                    status="confirmed",
                    total_amount=total.quantize(Decimal("0.01")),
                )
                db.add(order)
                db.flush()
                for line in order_lines:
                    line["inventory"].quantity_reserved += line["quantity"]
                    db.add(
                        OrderItem(
                            order_id=order.id,
                            menu_item_id=line["menu_item_id"],
                            item_name=line["item_name"],
                            quantity=line["quantity"],
                            unit_price=line["unit_price"],
                            line_total=line["line_total"],
                        )
                    )
                db.flush()
                result = {
                    "order_id": order.id,
                    "status": order.status,
                    "total_amount": str(order.total_amount),
                    "items": [
                        {
                            "menu_item_id": line["menu_item_id"],
                            "name": line["item_name"],
                            "quantity": line["quantity"],
                            "unit_price": str(line["unit_price"]),
                            "line_total": str(line["line_total"]),
                        }
                        for line in order_lines
                    ],
                }
            return _json(result)
        except Exception:
            db.rollback()
            raise


@mcp.tool()
def get_order_status(order_id: int) -> str:
    """Read an order and its item summary by order ID."""
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if order is None:
            return _json({"error": "Order not found", "order_id": order_id})
        return _json(
            {
                "order_id": order.id,
                "status": order.status,
                "total_amount": str(order.total_amount),
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "items": [
                    {
                        "menu_item_id": item.menu_item_id,
                        "name": item.item_name,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "line_total": str(item.line_total),
                    }
                    for item in order.items
                ],
            }
        )


if __name__ == "__main__":
    mcp.run()
