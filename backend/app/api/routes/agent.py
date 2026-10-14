"""Customer-facing API for the DineMate ordering agent."""
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.agent_session import AgentSession
from app.models.orders import Order
from app.agents.restaurant_agent import run_agent_turn

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, min_length=1, max_length=36)


class AgentChatResponse(BaseModel):
    session_id: str
    reply: str
    draft_order: list[dict[str, Any]]
    total: str
    order: dict[str, Any] | None = None


def _draft_total(draft: list[dict[str, Any]]) -> str:
    from decimal import Decimal

    total = sum(
        Decimal(str(item["unit_price"])) * int(item["quantity"])
        for item in draft
    )
    return f"{total:.2f}"


@router.post("/chat", response_model=AgentChatResponse)
async def chat(payload: AgentChatRequest, db: Session = Depends(get_db)):
    session_id = payload.session_id or str(uuid4())
    session = db.get(AgentSession, session_id)
    if session is None:
        session = AgentSession(session_id=session_id, messages=[], draft_order=[])
        db.add(session)
        db.commit()
        db.refresh(session)

    history = list(session.messages or [])
    draft = list(session.draft_order or [])
    try:
        result = await run_agent_turn(session_id, payload.message.strip(), history, draft)
    except Exception as exc:
        # Keep implementation details out of the customer response; server logs retain traceback.
        import logging
        logging.getLogger(__name__).exception("DineMate agent turn failed")
        detail = str(exc) if "GROQ_API_KEY" in str(exc) or "GROQ_MODEL" in str(exc) else "The ordering assistant is temporarily unavailable. Check backend logs and configuration."
        raise HTTPException(status_code=503, detail=detail) from exc

    reply = str(result.get("reply") or "How can I help with your order?")
    new_messages = history + [
        {"role": "user", "content": payload.message.strip()},
        {"role": "assistant", "content": reply},
    ]
    session.messages = new_messages[-24:]
    session.draft_order = result.get("draft_order", draft)
    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    return AgentChatResponse(
        session_id=session_id,
        reply=reply,
        draft_order=session.draft_order or [],
        total=_draft_total(session.draft_order or []),
        order=result.get("order_result") if isinstance(result.get("order_result"), dict) and not result["order_result"].get("error") else None,
    )


@router.get("/session/{session_id}")
def get_agent_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(AgentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return {
        "session_id": session.session_id,
        "messages": session.messages or [],
        "draft_order": session.draft_order or [],
        "total": _draft_total(session.draft_order or []),
        "updated_at": session.updated_at,
    }


@router.get("/orders/{order_id}")
def get_agent_order(order_id: int, db: Session = Depends(get_db)):
    order = db.scalar(
        select(Order).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": order.id,
        "session_id": order.session_id,
        "status": order.status,
        "total_amount": str(order.total_amount),
        "created_at": order.created_at,
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
