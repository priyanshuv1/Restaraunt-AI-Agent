from app.agents.restaurant_agent import _draft_summary, _match_candidate, _normalize


def test_normalize_item_name():
    assert _normalize("  Spicy Veg-Burger! ") == "spicy veg burger"


def test_match_candidate_prefers_exact_name():
    candidates = [
        {"menu_item_id": 1, "name": "Veg Burger"},
        {"menu_item_id": 2, "name": "Spicy Veg Burger"},
    ]
    result = _match_candidate("Spicy Veg Burger", candidates)
    assert result is not None
    assert result["menu_item_id"] == 2


def test_match_candidate_rejects_ambiguous_or_unrelated_name():
    candidates = [
        {"menu_item_id": 1, "name": "Classic Burger"},
        {"menu_item_id": 2, "name": "Crispy Burger"},
    ]
    assert _match_candidate("something unrelated", candidates) is None


def test_empty_draft_summary():
    reply, total = _draft_summary([])
    assert "draft is empty" in reply
    assert total == "0.00"


def test_draft_summary_calculates_total_from_live_price_snapshot():
    reply, total = _draft_summary(
        [
            {"menu_item_id": 1, "name": "Veg Burger", "quantity": 2, "unit_price": "120.00"},
            {"menu_item_id": 2, "name": "Lime Soda", "quantity": 1, "unit_price": "40.00"},
        ]
    )
    assert total == "280.00"
    assert "₹280.00" in reply
    assert "Veg Burger × 2" in reply
