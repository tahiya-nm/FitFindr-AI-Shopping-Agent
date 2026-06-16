"""
agent.py

The FitFindr planning loop. Orchestrates all tools in response to a natural
language user query, passing state between them via a session dict.

Summary:
    1. Initialize session dict
    2. Parse the query via LLM to extract description, size, max_price
    3. Call search_listings — return early with error if no results
       (stretch: retry without size filter before giving up)
    4. Optionally run compare_price on the top result (stretch)
    5. Call suggest_outfit with selected_item and wardrobe
    6. Call create_fit_card with outfit_suggestion and selected_item
    7. Return completed session dict

Time complexity:  O(n) dominated by search_listings scan over n listings
Space complexity: O(n) for the session dict and search results
"""

import os
import json
import re
from dotenv import load_dotenv
from groq import Groq
from tools import search_listings, suggest_outfit, create_fit_card, compare_price

load_dotenv()


# ── session initializer ────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one user interaction."""
    return {
        "query": query,             # original user query string
        "parsed": {},               # extracted description, size, max_price
        "search_results": [],       # full list returned by search_listings
        "selected_item": None,      # top result passed into suggest_outfit
        "wardrobe": wardrobe,       # user's wardrobe dict
        "outfit_suggestion": None,  # string returned by suggest_outfit
        "fit_card": None,           # string returned by create_fit_card
        "price_assessment": None,   # dict returned by compare_price (stretch)
        "retry_attempted": False,   # True if size-filter retry was triggered
        "error": None,              # set on early termination; None on success
    }


# ── query parser ───────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Use the LLM to extract structured search parameters from a natural language query.

    Returns a dict with keys:
        description (str):        the clothing item type and style keywords
        size (str | None):        size string if mentioned, else None
        max_price (float | None): price ceiling if mentioned, else None
    Falls back to using the full query as description if LLM parsing fails.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        # Graceful fallback: treat full query as description
        return {"description": query, "size": None, "max_price": None}

    client = Groq(api_key=api_key)
    prompt = (
        "Extract search parameters from this clothing search query. "
        "Respond with ONLY a JSON object — no explanation, no markdown.\n\n"
        f'Query: "{query}"\n\n'
        "JSON format:\n"
        '{"description": "<item type and style keywords only>", '
        '"size": "<size string or null>", '
        '"max_price": <number or null>}'
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=100,
            temperature=0,  # deterministic parsing
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if the LLM added them despite instructions
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
        parsed = json.loads(raw)

        return {
            "description": parsed.get("description", query),
            "size": parsed.get("size") or None,
            "max_price": float(parsed["max_price"]) if parsed.get("max_price") else None,
        }
    except Exception:
        # If LLM parsing fails for any reason, fall back to full query as description
        return {"description": query, "size": None, "max_price": None}


# ── planning loop ──────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict from get_example_wardrobe() or
                  get_empty_wardrobe()

    Returns:
        The session dict. Check session["error"] first — if not None,
        the interaction ended early and outfit_suggestion / fit_card will be None.
    """
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse the natural language query into structured parameters
    parsed = _parse_query(query)
    session["parsed"] = parsed
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    # Step 3: Search listings with parsed parameters
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results

    # Step 3a (stretch): Retry without size filter if no results and size was provided
    if not results and size is not None:
        session["retry_attempted"] = True
        results = search_listings(description, size=None, max_price=max_price)
        session["search_results"] = results

        if results:
            # Inform user the retry loosened the size constraint
            session["retry_message"] = (
                f"No results found for size {size} — showing results without size filter."
            )
        else:
            # Still nothing after retry — return early
            session["error"] = (
                f"No listings found even after removing the size filter. "
                "Try a different description or price range."
            )
            return session

    elif not results:
        # No size filter was active, still no results — return early
        session["error"] = (
            "No listings matched your search. "
            "Try broadening your description, adjusting your size, or raising your max price."
        )
        return session

    # Step 4: Select the top result (highest relevance score)
    session["selected_item"] = results[0]

    # Step 4a (stretch): Run price comparison on the selected item
    try:
        session["price_assessment"] = compare_price(session["selected_item"])
    except Exception:
        session["price_assessment"] = None  # non-critical; don't block the main flow

    # Step 5: Generate outfit suggestions using the selected item and wardrobe
    outfit = suggest_outfit(session["selected_item"], wardrobe)
    session["outfit_suggestion"] = outfit

    # If suggest_outfit returned an error string, surface it and stop
    if outfit.startswith("Could not generate outfit"):
        session["error"] = outfit
        return session

    # Step 6: Generate the fit card caption
    fit_card = create_fit_card(outfit, session["selected_item"])
    session["fit_card"] = fit_card

    # If create_fit_card returned an error string, note it but still return partial results
    if fit_card.startswith("Could not generate fit card") or \
       fit_card.startswith("Cannot generate a fit card"):
        session["error"] = fit_card
        # Don't return early — outfit_suggestion is still valuable

    # Step 7: Return completed session
    return session


# ── CLI test ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found:    {session['selected_item']['title']} — ${session['selected_item']['price']}")
        print(f"Price assessment: {session['price_assessment']}")
        print(f"\nOutfit:   {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Retry attempted: {session2['retry_attempted']}")
    print(f"Error message:   {session2['error']}")

    print("\n\n=== Empty wardrobe path ===\n")
    session3 = run_agent(
        query="flowy midi skirt under $40",
        wardrobe=get_empty_wardrobe(),
    )
    if session3["error"]:
        print(f"Error: {session3['error']}")
    else:
        print(f"Found:    {session3['selected_item']['title']}")
        print(f"\nOutfit:   {session3['outfit_suggestion']}")
        print(f"\nFit card: {session3['fit_card']}")