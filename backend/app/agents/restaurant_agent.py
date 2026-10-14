"""Five-stage LangGraph restaurant ordering agent backed by MCP tools."""
import json
import os
import re
import sys
from difflib import SequenceMatcher
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


class RequestedItem(BaseModel):
    name: str = Field(description="Menu item name or phrase from the customer's message")
    quantity: int = Field(default=1, ge=1, le=50)


class RequestPlan(BaseModel):
    intent: Literal["recommend", "add", "review", "confirm", "cancel", "other"]
    query: str = Field(default="", description="Short semantic menu search query")
    category: str | None = None
    items: list[RequestedItem] = Field(default_factory=list)
    explicit_confirmation: bool = Field(
        default=False,
        description="True only when the current message clearly authorizes placing the current draft order",
    )
    emotion: Literal["neutral", "happy", "curious", "empathetic", "apologetic", "excited"] = Field(
        default="neutral",
        description="Concise assistant delivery emotion for a future voice/avatar client; choose a natural, restrained expression.",
    )


class AgentState(TypedDict, total=False):
    session_id: str
    message: str
    history: list[dict[str, str]]
    draft_order: list[dict[str, Any]]
    plan: dict[str, Any]
    resolved: list[dict[str, Any]]
    reply: str
    confirmed: bool
    emotion: str
    total: str
    order_result: dict[str, Any]


SYSTEM_PROMPT = """You are DineMate, a polite restaurant ordering assistant.
You only help customers discover menu items and prepare or place restaurant orders.
Use intent=add when the customer asks to add/order specific items; recommend when they are exploring.
Use intent=review to review the cart, confirm only when the current message explicitly authorizes placing the pending order, cancel to clear the draft, and other for unrelated or unclear requests.
Choose an appropriate assistant emotion from neutral, happy, curious, empathetic, apologetic, or excited. Keep it subtle and suitable for a restaurant assistant.
Never invent menu items, prices, stock, ingredients, or dietary facts. Tool results and PostgreSQL are authoritative.
Do not treat a question, a hypothetical, or a request to show the draft as confirmation.
If the customer is ambiguous, ask a concise clarification instead of guessing.
Extract quantities and item phrases faithfully. A bare 'yes' may confirm only if a pending draft exists and the message is an unambiguous response to the previous confirmation prompt."""


def _client() -> MultiServerMCPClient:
    env = dict(os.environ)
    return MultiServerMCPClient(
        {
            "dinemate": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "app.tools.mcp_server"],
                "env": env,
            }
        }
    )


async def _tools_by_suffix() -> dict[str, Any]:
    tools = await _client().get_tools()
    return {tool.name.split("__")[-1]: tool for tool in tools}


def _decode_tool_result(result: Any) -> Any:
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"text": result}
    if isinstance(result, dict):
        return result
    if isinstance(result, list):
        for part in result:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                try:
                    return json.loads(part["text"])
                except json.JSONDecodeError:
                    return {"text": part["text"]}
    return result


async def _call(tools: dict[str, Any], name: str, **kwargs: Any) -> Any:
    tool = tools.get(name)
    if tool is None:
        # Some MCP adapter versions prefix names with the server identifier.
        tool = next((t for key, t in tools.items() if key.endswith(name)), None)
    if tool is None:
        raise RuntimeError(f"Required MCP tool is not available: {name}")
    return _decode_tool_result(await tool.ainvoke(kwargs))


def _model() -> ChatGroq:
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is missing. Add your Groq API key to backend/.env.")
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
        api_key=os.environ["GROQ_API_KEY"],
    )


def _money(value: Any) -> str:
    return f"₹{float(value):.2f}"


def _draft_summary(draft: list[dict[str, Any]]) -> tuple[str, str]:
    if not draft:
        return "Your order draft is empty. Tell me what you'd like to order.", "0.00"
    total = sum(float(line["unit_price"]) * int(line["quantity"]) for line in draft)
    lines = [
        f"- {line['name']} × {line['quantity']} — {_money(float(line['unit_price']) * int(line['quantity']))}"
        for line in draft
    ]
    return "Here's your current order draft:\n" + "\n".join(lines) + f"\nTotal: {_money(total)}\nWould you like me to place this order? Please confirm explicitly.", f"{total:.2f}"


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _match_candidate(requested_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    requested = _normalize(requested_name)
    scored = []
    for item in candidates:
        name = _normalize(str(item.get("name", "")))
        ratio = SequenceMatcher(None, requested, name).ratio()
        if requested and (requested in name or name in requested):
            ratio = max(ratio, 0.9)
        scored.append((ratio, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if scored[0][0] < 0.52:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.04 and scored[0][0] < 0.85:
        return None
    return scored[0][1]


async def run_agent_turn(
    session_id: str,
    message: str,
    history: list[dict[str, str]],
    draft_order: list[dict[str, Any]],
) -> dict[str, Any]:
    tools = await _tools_by_suffix()
    model = _model()

    async def understand(state: AgentState) -> dict[str, Any]:
        history_text = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in state.get("history", [])[-8:]
        )
        planner = model.with_structured_output(RequestPlan)
        plan = await planner.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"Recent conversation:\n{history_text or '(new conversation)'}\n\n"
                        f"Current draft order:\n{json.dumps(state.get('draft_order', []), ensure_ascii=False)}\n\n"
                        f"Current customer message:\n{state['message']}"
                    )
                ),
            ]
        )
        return {"plan": plan.model_dump(), "emotion": plan.emotion, "confirmed": False}

    async def resolve_and_validate(state: AgentState) -> dict[str, Any]:
        plan = state["plan"]
        intent = plan["intent"]
        draft = [dict(line) for line in state.get("draft_order", [])]
        if intent == "cancel":
            return {"draft_order": [], "resolved": [], "reply": "I've cleared your unsubmitted order draft. What would you like instead?"}
        if intent == "review":
            reply, _ = _draft_summary(draft)
            return {"resolved": [], "reply": reply}
        if intent == "recommend":
            query = (plan.get("query") or state["message"]).strip()
            matches = await _call(
                tools, "search_menu", query=query, category=plan.get("category"), top_k=5
            )
            if isinstance(matches, dict) and matches.get("error"):
                return {"resolved": [], "reply": "I couldn't search the menu just now. Please try again."}
            details = []
            for match in matches if isinstance(matches, list) else []:
                item_id = match.get("menu_item_id")
                if item_id is not None:
                    live = await _call(tools, "get_menu_item", menu_item_id=int(item_id))
                    if isinstance(live, dict) and not live.get("error"):
                        details.append(live)
            if not details:
                return {"resolved": [], "reply": "I couldn't find a matching menu item. Try a different dish or category."}
            lines = []
            for item in details[:5]:
                availability = "available" if item.get("is_available") and (item.get("quantity_available") or 0) > 0 else "currently unavailable"
                tags = ", ".join(item.get("dietary_tags") or [])
                lines.append(f"- {item['name']} ({item['category']}) — {_money(item['price'])}; {availability}" + (f"; tags: {tags}" if tags else ""))
            return {"resolved": details[:5], "reply": "Here are some menu matches:\n" + "\n".join(lines) + "\nTell me which item and quantity you'd like to add."}
        if intent == "add":
            requested_items = plan.get("items") or []
            if not requested_items:
                return {"draft_order": draft, "resolved": [], "reply": "Which menu item and quantity would you like me to add?"}
            resolved_lines = []
            problems = []
            for requested in requested_items[:10]:
                name = str(requested.get("name", "")).strip()
                quantity = max(1, min(int(requested.get("quantity", 1)), 50))
                if not name:
                    continue
                candidates = await _call(tools, "search_menu", query=name, category=plan.get("category"), top_k=5)
                candidates = candidates if isinstance(candidates, list) else []
                candidate = _match_candidate(name, candidates)
                if candidate is None:
                    problems.append(f"I couldn't confidently match '{name}' to one menu item. Please choose a name from the menu.")
                    continue
                item_id = int(candidate["menu_item_id"])
                live = await _call(tools, "get_menu_item", menu_item_id=item_id)
                if not isinstance(live, dict) or live.get("error"):
                    problems.append(f"I couldn't verify {name} against the live menu.")
                    continue
                if not live.get("is_available"):
                    problems.append(f"{live['name']} is currently marked unavailable.")
                    continue
                available = live.get("quantity_available")
                if available is None:
                    problems.append(f"I can't verify current stock for {live['name']}, so I haven't added it.")
                    continue
                existing = next((line for line in draft if int(line["menu_item_id"]) == item_id), None)
                desired = quantity + (int(existing["quantity"]) if existing else 0)
                if int(available) < desired:
                    problems.append(f"{live['name']}: only {available} available; your draft would need {desired}.")
                    continue
                if existing:
                    existing["quantity"] = desired
                    existing["unit_price"] = str(live["price"])
                else:
                    draft.append(
                        {
                            "menu_item_id": item_id,
                            "name": live["name"],
                            "quantity": quantity,
                            "unit_price": str(live["price"]),
                        }
                    )
                resolved_lines.append(live)
            reply, _ = _draft_summary(draft)
            if problems:
                reply = "\n".join(problems) + ("\n\n" + reply if draft else "")
            elif not resolved_lines:
                reply = "I couldn't add that item. Please choose an item from the menu."
            return {"draft_order": draft, "resolved": resolved_lines, "reply": reply}
        if intent == "confirm":
            return {"draft_order": draft, "resolved": [], "reply": ""}
        return {"draft_order": draft, "resolved": [], "reply": "I can help you find menu items, build an order, review it, or place it after you confirm. What would you like?"}

    async def manage_draft_and_calculate(state: AgentState) -> dict[str, Any]:
        plan = state["plan"]
        if plan["intent"] == "confirm":
            return {}
        if plan["intent"] in {"add", "review"}:
            reply, total = _draft_summary(state.get("draft_order", []))
            # Preserve a more useful clarification or validation message from resolve.
            existing_reply = state.get("reply", "")
            if plan["intent"] == "add" and existing_reply and ("couldn't" in existing_reply.lower() or "only " in existing_reply.lower() or "unavailable" in existing_reply.lower() or "can't verify" in existing_reply.lower()):
                return {"reply": existing_reply, "total": total}
            return {"reply": reply, "total": total}
        return {}

    async def confirm(state: AgentState) -> dict[str, Any]:
        plan = state["plan"]
        if plan["intent"] != "confirm":
            return {"confirmed": False}
        message_text = state["message"].casefold().strip()
        explicit_words = re.search(
            r"\b(yes|yes please|yep|yeah|confirm|place (the )?order|submit order|go ahead|proceed)\b",
            message_text,
        )
        if not state.get("draft_order"):
            return {"confirmed": False, "reply": "There isn't an order draft to confirm. Tell me what you'd like to order first."}
        if not plan.get("explicit_confirmation") or not explicit_words:
            reply, _ = _draft_summary(state.get("draft_order", []))
            return {"confirmed": False, "reply": reply}
        return {"confirmed": True, "reply": ""}

    async def execute(state: AgentState) -> dict[str, Any]:
        if not state.get("confirmed"):
            return {}
        result = await _call(
            tools,
            "place_order",
            session_id=state["session_id"],
            items_json=json.dumps(
                [
                    {"menu_item_id": line["menu_item_id"], "quantity": line["quantity"]}
                    for line in state.get("draft_order", [])
                ]
            ),
            confirmed=True,
        )
        if not isinstance(result, dict) or result.get("error"):
            details = result.get("details", []) if isinstance(result, dict) else []
            reason = "; ".join(details) if details else (result.get("error", "Please review the draft and try again.") if isinstance(result, dict) else "Please review the draft and try again.")
            return {"reply": f"I couldn't place the order: {reason}", "order_result": result, "confirmed": False, "emotion": "apologetic"}
        return {
            "order_result": result,
            "draft_order": [],
            "emotion": "happy",
            "reply": (
                f"Your order #{result['order_id']} is confirmed. Total: {_money(result['total_amount'])}. "
                "Your items have been reserved. Payment is not handled in this version."
            ),
        }

    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("understand_request", understand)
    graph_builder.add_node("resolve_validate", resolve_and_validate)
    graph_builder.add_node("manage_draft_calculate", manage_draft_and_calculate)
    graph_builder.add_node("confirm", confirm)
    graph_builder.add_node("execute", execute)
    graph_builder.set_entry_point("understand_request")
    graph_builder.add_edge("understand_request", "resolve_validate")
    graph_builder.add_edge("resolve_validate", "manage_draft_calculate")
    graph_builder.add_edge("manage_draft_calculate", "confirm")
    graph_builder.add_conditional_edges(
        "confirm", lambda state: "execute" if state.get("confirmed") else END
    )
    graph_builder.add_edge("execute", END)

    initial: AgentState = {
        "session_id": session_id,
        "message": message,
        "history": history,
        "draft_order": draft_order,
        "confirmed": False,
    }
    return await graph_builder.compile().ainvoke(initial)
