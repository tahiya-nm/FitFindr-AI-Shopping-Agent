"""
tools.py

The FitFindr tools plus the stretch compare_price tool. Each function is
independently testable before being wired into the planning loop.

Tools:
    search_listings(description, size, max_price) -> list[dict]
    suggest_outfit(new_item, wardrobe)             -> str
    create_fit_card(outfit, new_item)              -> str
    compare_price(item)                            -> dict  [stretch]
"""

# ── Summary ────────────────────────────────────────────────────────────────────
# search_listings:
#   1. Load all listings via load_listings()
#   2. Filter by max_price (<=) and size (case-insensitive substring) if provided
#   3. Tokenize description into lowercase keywords
#   4. Score each remaining listing by keyword hits across title, description,
#      style_tags, category, and brand
#   5. Drop listings with score == 0, sort highest-score first, return
#
# suggest_outfit:
#   1. Check if wardrobe["items"] is empty
#   2. Build an LLM prompt — general styling advice if empty, wardrobe-specific
#      outfit combinations if not
#   3. Call Groq, return response string; catch exceptions
#
# create_fit_card:
#   1. Guard against empty/whitespace outfit string
#   2. Build a prompt with item details + outfit, asking for a casual caption
#   3. Call Groq at temperature=1.3 for varied output; catch exceptions
#
# compare_price (stretch):
#   1. Find listings with same category and at least one overlapping style_tag
#   2. Require at least 2 comparables; compute median price
#   3. Return assessment dict with reasoning
#
# Time complexity:  O(n) for search_listings where n = number of listings
# Space complexity: O(n) for the filtered + scored results list

import os
import statistics
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()

# ── Groq client ────────────────────────────────────────────────────────────────

def _get_groq_client() -> Groq:
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ────────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user wants
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip.
                     Case-insensitive; "M" will match listing sizes "M", "S/M", "m".
        max_price:   Maximum price in USD (inclusive), or None to skip.

    Returns:
        A list of matching listing dicts sorted by relevance (highest score first).
        Returns [] if nothing matches — does NOT raise an exception.
        Each dict contains: id, title, description, category, style_tags (list),
        size, condition, price (float), colors (list), brand, platform.
    """
    # Step 1: Load all listings from the JSON data file
    listings = load_listings()

    # Step 2a: Filter by max_price if provided
    if max_price is not None:
        listings = [l for l in listings if l.get("price", 0) <= max_price]

    # Step 2b: Filter by size if provided (case-insensitive substring match)
    # e.g., searching "M" matches listing size "S/M" or "M"
    if size is not None:
        size_lower = size.lower()
        listings = [
            l for l in listings
            if size_lower in l.get("size", "").lower()
        ]

    # Step 3: Tokenize the description into lowercase keywords for scoring
    # Split on whitespace and strip punctuation characters
    keywords = [
        word.strip(".,!?-").lower()
        for word in description.split()
        if word.strip(".,!?-")
    ]

    # Step 4: Score each remaining listing by keyword overlap
    # Check title, description, style_tags, category, and brand fields
    scored = []
    for listing in listings:
        # Build a single searchable text blob from all relevant fields
        # Or "" coerces None to empty string regardless of why it's None
        searchable = " ".join([
            listing.get("title") or "",
            listing.get("description") or "",
            listing.get("category") or "",
            listing.get("brand") or "",
            " ".join(listing.get("style_tags") or []),
            " ".join(listing.get("colors") or []),
        ]).lower()

        # Count how many keywords appear in the searchable text
        score = sum(1 for kw in keywords if kw in searchable)
        if score > 0:
            scored.append((score, listing))

    # Step 5: Sort by score descending, return just the listing dicts
    scored.sort(key=lambda x: x[0], reverse=True)
    return [listing for _, listing in scored]


# ── Tool 2: suggest_outfit ─────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted listing and the user's wardrobe, suggest 1-2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an "items" key containing a list of
                  wardrobe item dicts. Each item has: name, category, color, style.
                  May be empty — handled gracefully.

    Returns:
        A non-empty string with outfit suggestions. If the wardrobe is empty,
        returns general styling advice for the item based on its style_tags
        and category rather than raising or returning "".
    """
    client = _get_groq_client()
    wardrobe_items = wardrobe.get("items", [])

    # Step 1: Format the new item details for the prompt
    item_details = (
        f"Item: {new_item.get('title', 'Unknown')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Condition: {new_item.get('condition', 'unknown')}\n"
        f"Brand: {new_item.get('brand', 'unknown')}"
    )

    # Step 2a: Empty wardrobe — ask for general styling advice
    if not wardrobe_items:
        prompt = (
            f"A user just thrifted this item:\n{item_details}\n\n"
            "They don't have a wardrobe on file yet. Give them 1-2 general outfit "
            "ideas: what silhouettes, colors, and aesthetics pair well with this piece. "
            "Be specific about the vibe and styling details (tucks, layering, footwear). "
            "Keep it conversational, 3-5 sentences."
        )

    # Step 2b: Non-empty wardrobe — suggest outfits using specific named pieces
    else:
        # Format each wardrobe item as a readable line
        wardrobe_lines = "\n".join(
            f"- {item.get('name', 'item')} ({item.get('category', '')},"
            f" {item.get('color', '')}, {item.get('style', '')})"
            for item in wardrobe_items
        )
        prompt = (
            f"A user just thrifted this item:\n{item_details}\n\n"
            f"Their current wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfit combinations using the new item and "
            "specific named pieces from their wardrobe above. "
            "Include styling details like tucking, layering, or footwear. "
            "Keep it conversational, 4-6 sentences total."
        )

    # Step 3: Call the LLM and return the response; catch any API exceptions
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate outfit suggestions. Please try again. ({e})"


# ── Tool 3: create_fit_card ────────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2-4 sentence casual caption string (Instagram/TikTok OOTD style).
        Mentions item name, price, and platform once each. Returns a descriptive
        error string — NOT an exception — if outfit is empty or the LLM fails.
    """
    # Step 1: Guard against an empty or whitespace-only outfit string
    if not outfit or not outfit.strip():
        return "Cannot generate a fit card — outfit description is missing."

    # Step 2: Build the caption prompt with item details and style guidelines
    item_name = new_item.get("title", "thrifted piece")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "")
    style_tags = ", ".join(new_item.get("style_tags", []))

    prompt = (
        f"Write a 2-4 sentence Instagram/TikTok outfit caption for this thrifted find.\n\n"
        f"Item: {item_name}\n"
        f"Price: ${price}\n"
        f"Platform: {platform}\n"
        f"Style: {style_tags}\n"
        f"Outfit: {outfit}\n\n"
        "Rules:\n"
        "- Sound like a real person posting an OOTD, not a product description\n"
        "- Mention the item name, price, and platform naturally (each once)\n"
        "- Capture the outfit vibe in specific terms\n"
        "- Lowercase, casual tone, can include 1-2 relevant emojis\n"
        "- Do NOT use hashtags"
    )

    # Step 3: Call LLM at temperature=1.3 to ensure varied output per run
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=150,
            temperature=1.3,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate fit card. Please try again. ({e})"


# ── Tool 4: compare_price (stretch) ───────────────────────────────────────────

def compare_price(item: dict) -> dict:
    """
    Estimate whether an item's price is fair based on comparable listings.

    Args:
        item: A listing dict to evaluate (must have "category", "style_tags",
              "price", and "title" fields).

    Returns:
        A dict with:
            assessment (str):               "good deal", "fair", or "overpriced"
            item_price (float):             the item's price
            median_comparable_price (float): median price of comparable listings
            comparable_count (int):         number of comparables found
            reasoning (str):                human-readable explanation
        If fewer than 2 comparables exist, returns assessment="unknown" with
        a reasoning string explaining why — does NOT raise an exception.
    """
    all_listings = load_listings()
    item_price = item.get("price", 0)
    item_category = item.get("category", "").lower()
    item_tags = set(t.lower() for t in item.get("style_tags", []))
    item_id = item.get("id")

    # Step 1: Find comparables — same category AND at least one overlapping style_tag
    comparables = [
        l for l in all_listings
        if l.get("id") != item_id                          # exclude the item itself
        and l.get("category", "").lower() == item_category # same category
        and item_tags & set(t.lower() for t in l.get("style_tags", []))  # tag overlap
    ]

    # Step 2: Require at least 2 comparables for a meaningful assessment
    if len(comparables) < 2:
        return {
            "assessment": "unknown",
            "item_price": item_price,
            "median_comparable_price": None,
            "comparable_count": len(comparables),
            "reasoning": (
                "Not enough comparable listings to evaluate price. "
                f"Found {len(comparables)} item(s) in the same category with overlapping style tags."
            ),
        }

    # Step 3: Compute median price of comparables
    comparable_prices = [l["price"] for l in comparables]
    median_price = statistics.median(comparable_prices)

    # Step 4: Assess — within 15% below median = good deal, within 15% above = fair, else overpriced
    ratio = item_price / median_price if median_price > 0 else 1.0
    if ratio <= 0.85:
        assessment = "good deal"
        verdict = f"${item_price:.2f} is at least 15% below the median comparable price of ${median_price:.2f}"
    elif ratio <= 1.15:
        assessment = "fair"
        verdict = f"${item_price:.2f} is within 15% of the median comparable price of ${median_price:.2f}"
    else:
        assessment = "overpriced"
        verdict = f"${item_price:.2f} is more than 15% above the median comparable price of ${median_price:.2f}"

    return {
        "assessment": assessment,
        "item_price": item_price,
        "median_comparable_price": round(median_price, 2),
        "comparable_count": len(comparables),
        "reasoning": (
            f"{verdict}. Based on {len(comparables)} comparable "
            f"{item_category} listings with similar style tags."
        ),
    }