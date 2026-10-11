from types import SimpleNamespace

from app.rag.service import build_menu_text, normalize_category


def test_normalize_category_handles_case_and_whitespace():
    assert normalize_category("  BURGERS ") == "burgers"
    assert normalize_category("  ") is None
    assert normalize_category(None) is None


def test_build_menu_text_includes_searchable_fields_but_not_price_or_stock():
    item = SimpleNamespace(
        id=7,
        name="Paneer Tikka Burger",
        category="Burgers",
        description="Grilled paneer tikka and fresh vegetables.",
        dietary_tags="vegetarian, spicy",
        price=179,
    )

    text = build_menu_text(item)

    assert "Paneer Tikka Burger" in text
    assert "Category: Burgers" in text
    assert "Grilled paneer tikka" in text
    assert "vegetarian, spicy" in text
    assert "179" not in text
    assert "stock" not in text.lower()
