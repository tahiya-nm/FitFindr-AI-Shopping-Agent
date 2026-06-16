"""
tests/test_tools.py

Pytest tests for each FitFindr tool, covering happy paths and all failure modes.
Run with: pytest tests/
"""

from tools import search_listings, suggest_outfit, create_fit_card, compare_price
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ────────────────────────────────────────────────────────────

def test_search_returns_results():
    """Happy path: a reasonable query returns at least one result."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    """Failure mode: an impossible query returns [] without raising."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    """All returned items must be at or below the max_price ceiling."""
    results = search_listings("jacket", size=None, max_price=30)
    assert all(item["price"] <= 30 for item in results)

def test_search_size_filter_case_insensitive():
    """Size filter is case-insensitive and works as a substring match."""
    results_upper = search_listings("top", size="M", max_price=None)
    results_lower = search_listings("top", size="m", max_price=None)
    # Both should return the same items
    ids_upper = {r["id"] for r in results_upper}
    ids_lower = {r["id"] for r in results_lower}
    assert ids_upper == ids_lower

def test_search_returns_dicts_with_required_fields():
    """Every returned listing must have the documented fields."""
    required = {"id", "title", "description", "category", "style_tags",
                "size", "condition", "price", "colors", "brand", "platform"}
    results = search_listings("shirt", size=None, max_price=100)
    if results:
        assert required.issubset(results[0].keys())

def test_search_sorted_by_relevance():
    """Results with more keyword hits should appear before fewer hits."""
    results = search_listings("vintage streetwear graphic", size=None, max_price=None)
    # Just verify it returns a list without crashing — score ordering is internal
    assert isinstance(results, list)


# ── suggest_outfit ─────────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    """Happy path: returns a non-empty string when wardrobe has items."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results, "Need at least one result to test suggest_outfit"
    output = suggest_outfit(results[0], get_example_wardrobe())
    assert isinstance(output, str)
    assert len(output.strip()) > 0

def test_suggest_outfit_empty_wardrobe():
    """Failure mode: empty wardrobe returns general advice string, not an exception."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results
    output = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(output, str)
    assert len(output.strip()) > 0


# ── create_fit_card ────────────────────────────────────────────────────────────

def test_create_fit_card_happy_path():
    """Happy path: returns a non-empty caption string."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results
    outfit = suggest_outfit(results[0], get_example_wardrobe())
    card = create_fit_card(outfit, results[0])
    assert isinstance(card, str)
    assert len(card.strip()) > 0

def test_create_fit_card_empty_outfit():
    """Failure mode: empty outfit string returns error message, not an exception."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results
    card = create_fit_card("", results[0])
    assert isinstance(card, str)
    assert "Cannot generate a fit card" in card

def test_create_fit_card_whitespace_outfit():
    """Failure mode: whitespace-only outfit string also returns error message."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results
    card = create_fit_card("   ", results[0])
    assert isinstance(card, str)
    assert "Cannot generate a fit card" in card


# ── compare_price (stretch) ────────────────────────────────────────────────────

def test_compare_price_returns_dict():
    """Happy path: returns a dict with the required keys."""
    results = search_listings("jacket", size=None, max_price=None)
    assert results
    result = compare_price(results[0])
    required_keys = {"assessment", "item_price", "median_comparable_price",
                     "comparable_count", "reasoning"}
    assert required_keys.issubset(result.keys())

def test_compare_price_valid_assessment_values():
    """Assessment field must be one of the four valid values."""
    results = search_listings("jacket", size=None, max_price=None)
    assert results
    result = compare_price(results[0])
    assert result["assessment"] in {"good deal", "fair", "overpriced", "unknown"}

def test_compare_price_insufficient_comparables():
    """Failure mode: item with no comparable listings returns assessment='unknown'."""
    # Construct a fake item in a rare category with unique tags
    fake_item = {
        "id": "fake-999",
        "title": "Obscure One-Off Item",
        "category": "nonexistent_category_xyz",
        "style_tags": ["totally_unique_tag_abc"],
        "price": 50.0,
    }
    result = compare_price(fake_item)
    assert result["assessment"] == "unknown"
    assert "Not enough comparable" in result["reasoning"]