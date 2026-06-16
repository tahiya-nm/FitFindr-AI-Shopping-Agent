# FitFindr — AI Shopping Agent

FitFindr is a multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. Given a natural language search query, it searches a mock listings dataset, generates outfit suggestions using the user's wardrobe, and produces a shareable Instagram-style caption, all in one flow. Built with Python, Groq (llama-3.3-70b-versatile), and a Gradio front end.

---

## Tool Inventory

### `search_listings(description, size, max_price)`

**Purpose:** Searches the mock listings dataset for secondhand items matching a natural language description, with optional size and price filters. Returns results ranked by keyword relevance.

**Inputs:**
- `description` (str): Keywords describing the item (e.g. `"vintage graphic tee"`). Used to score each listing by keyword overlap across title, description, style_tags, category, and brand fields.
- `size` (str | None): Size string to filter by (e.g. `"M"`, `"XL"`). Case-insensitive substring match — `"M"` matches `"S/M"`. Pass `None` to skip size filtering.
- `max_price` (float | None): Price ceiling in USD, inclusive. Pass `None` to skip price filtering.

**Returns:** A list of listing dicts sorted by relevance score (highest first). Each dict contains: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str), `platform` (str). Returns `[]` if nothing matches — does not raise an exception.

---

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Given a thrifted listing and the user's wardrobe, calls the Groq LLM to suggest 1–2 complete outfit combinations. Falls back to general styling advice if the wardrobe is empty.

**Inputs:**
- `new_item` (dict): A listing dict returned by `search_listings` — the item the user is considering buying.
- `wardrobe` (dict): A wardrobe dict with an `"items"` key containing a list of wardrobe item dicts. Each item has: `name` (str), `category` (str), `color` (str), `style` (str). May be empty.

**Returns:** A non-empty string with 1–2 outfit suggestions. If the wardrobe has items, suggestions reference specific named pieces from it. If the wardrobe is empty, returns general style advice — what silhouettes, colors, and aesthetics pair well with the item — rather than raising or returning an empty string.

---

### `create_fit_card(outfit, new_item)`

**Purpose:** Generates a 2–4 sentence Instagram/TikTok-style caption for the thrifted outfit. Runs at elevated LLM temperature (1.3) to ensure output varies across different inputs.

**Inputs:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`.
- `new_item` (dict): The listing dict for the thrifted item. Used for item name, price, and platform.

**Returns:** A 2–4 sentence caption string in casual OOTD voice. Mentions the item name, price, and platform naturally (once each). Returns a descriptive error string — not an exception — if `outfit` is empty or the LLM call fails.

---

### `compare_price(item)` *(stretch)*

**Purpose:** Estimates whether a listing's price is fair relative to comparable items in the dataset. Comparables are defined as listings with the same `category` AND at least one overlapping `style_tag`.

**Inputs:**
- `item` (dict): A listing dict to evaluate (requires `category`, `style_tags`, `price`, `id` fields).

**Returns:** A dict with: `assessment` (str — `"good deal"`, `"fair"`, `"overpriced"`, or `"unknown"`), `item_price` (float), `median_comparable_price` (float | None), `comparable_count` (int), `reasoning` (str). Assessment thresholds: ≥15% below median = good deal, within 15% = fair, >15% above = overpriced. Returns `assessment: "unknown"` with a reasoning string if fewer than 2 comparables are found — does not raise.

---

## How the Planning Loop Works

The planning loop lives in `run_agent()` in `agent.py`. It does not call all tools unconditionally — each step only executes if the previous step produced valid output.

```
Step 1 — Parse query
    LLM extracts description, size, and max_price from the natural
    language query. Stores result in session["parsed"].

Step 2 — Search listings
    Calls search_listings(description, size, max_price).
    Stores result in session["search_results"].

    → If results == [] AND size was provided (stretch retry):
        Retry with size=None.
        If results now non-empty: store retry message in session,
        continue to Step 3.
        If still []: set session["error"], return session early.
        suggest_outfit and create_fit_card are NOT called.

    → If results == [] and no size was given:
        Set session["error"], return session early.

    → If results non-empty:
        session["selected_item"] = results[0]
        Run compare_price(selected_item), store in session["price_assessment"].
        Continue to Step 3.

Step 3 — Suggest outfit
    Calls suggest_outfit(session["selected_item"], wardrobe).
    Stores result in session["outfit_suggestion"].

    → If result starts with "Could not generate":
        Set session["error"], return session early.
        create_fit_card is NOT called.

Step 4 — Create fit card
    Calls create_fit_card(session["outfit_suggestion"], session["selected_item"]).
    Stores result in session["fit_card"].

    → If result is an error string:
        Set session["error"] but do NOT return early —
        outfit_suggestion is still surfaced to the user.

Step 5 — Return session.
```

**What triggers each branch:** The agent checks `results == []` after `search_listings`. If empty, it sets `session["error"]` and returns immediately — `suggest_outfit` is never called with empty input. If `suggest_outfit` returns an error string, `create_fit_card` is skipped. This means a query like `"designer ballgown size XXS under $5"` produces only an error message in panel 1 and leaves panels 2 and 3 blank, while a valid query flows through all three tools.

---

## State Management

A single `session` dict is initialized at the start of `run_agent()` and updated in place as each tool runs. No tool receives the session as a parameter — each tool receives only the specific values it needs, extracted from the session by the planning loop. This keeps every tool independently testable.

| Key | Set after | Value |
|---|---|---|
| `session["query"]` | Initialization | Original user query string |
| `session["parsed"]` | Query parsing | Dict with `description`, `size`, `max_price` |
| `session["search_results"]` | `search_listings` runs | Full list of matching listing dicts |
| `session["selected_item"]` | `search_listings` succeeds | Top-ranked listing dict (passed into `suggest_outfit` and `create_fit_card`) |
| `session["outfit_suggestion"]` | `suggest_outfit` succeeds | LLM outfit string (passed into `create_fit_card`) |
| `session["fit_card"]` | `create_fit_card` succeeds | Caption string |
| `session["price_assessment"]` | `compare_price` runs | Price assessment dict |
| `session["retry_attempted"]` | Retry logic fires | Boolean |
| `session["retry_message"]` | Retry produces results | Human-readable note shown in UI |
| `session["error"]` | Any tool fails | Actionable error message string; `None` on success |

**How it flows between tools:** After `search_listings` succeeds, the planning loop does `session["selected_item"] = results[0]` and then passes `session["selected_item"]` directly into `suggest_outfit`. The user never re-enters the item. After `suggest_outfit` returns, `session["outfit_suggestion"]` is passed directly into `create_fit_card`. At no point does any tool re-query the dataset or re-prompt the user for information already captured.

---

## Error Handling

### `search_listings`
**Failure mode:** Returns `[]` — no listings match the description, size, and price constraints.

**Agent response:** If a size filter was active, the agent first retries without the size filter (stretch retry logic) and notifies the user: *"No results for size M — showing results without size filter."* If the retry also returns `[]`, or no size was given to begin with, the agent sets `session["error"]` to: *"No listings found even after removing the size filter. Try a different description or price range."* It returns the session immediately. `suggest_outfit` and `create_fit_card` are not called.

**Tested with:**
```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
# Output: []
```

---

### `suggest_outfit`
**Failure mode:** `wardrobe["items"]` is empty (new user with no wardrobe on file).

**Agent response:** The function does not fail or return an empty string. It detects the empty wardrobe, constructs a different LLM prompt asking for general styling advice (silhouettes, color pairings, aesthetic vibe), and returns a useful suggestion. The planning loop continues normally to `create_fit_card`.

**Secondary failure mode:** LLM API call raises an exception.

**Agent response:** The exception is caught; the function returns the string `"Could not generate outfit suggestions. Please try again."` The planning loop detects this error string, sets `session["error"]`, and returns early.

**Tested with:**
```bash
python -c "
from tools import search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(suggest_outfit(results[0], get_empty_wardrobe()))
"
# Output: general styling advice string, no exception
```

---

### `create_fit_card`
**Failure mode:** `outfit` argument is an empty or whitespace-only string.

**Agent response:** The function guards against this before calling the LLM. It returns the string `"Cannot generate a fit card — outfit description is missing."` — no exception raised, no LLM call made.

**Secondary failure mode:** LLM API call raises an exception.

**Agent response:** The exception is caught; the function returns `"Could not generate fit card. Please try again."` The planning loop sets `session["error"]` but does **not** return early, because `session["outfit_suggestion"]` is still valid and useful to the user.

**Tested with:**
```bash
python -c "
from tools import search_listings, create_fit_card
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(create_fit_card('', results[0]))
"
# Output: "Cannot generate a fit card — outfit description is missing."
```

---

### `compare_price` *(stretch)*
**Failure mode:** Fewer than 2 comparable listings found (same category + overlapping style tags).

**Agent response:** Returns `{"assessment": "unknown", "reasoning": "Not enough comparable listings to evaluate price..."}`. The planning loop stores this in `session["price_assessment"]` and continues — a missing price assessment does not block the rest of the flow.

---

## Stretch Features

### Price Comparison Tool
`compare_price(item)` finds listings with the same `category` as the target item AND at least one overlapping `style_tag`. It requires at least 2 comparables to make an assessment; if fewer exist it returns `assessment: "unknown"`. For sufficient comparables, it computes the median price and classifies the item: more than 15% below median = good deal, within 15% = fair, more than 15% above = overpriced. The result appears in the listing panel as a "Price check" line with a ✅ / ➡️ / ⚠️ badge and a sentence explaining the comparison.

### Retry Logic with Fallback
If `search_listings` returns no results AND a size filter was active in the parsed query, `run_agent()` automatically retries the search with `size=None`. If the retry produces results, `session["retry_message"]` is set to inform the user what was relaxed (e.g. *"No results for size XXS — showing results without size filter."*) and the flow continues normally. If the retry also returns nothing, the agent surfaces the no-results error and stops. The UI displays the retry note in the listing panel so the user knows the constraint was dropped.

---

## Spec Reflection

**One way the spec helped:** Writing out the planning loop's conditional logic in `planning.md` before touching `agent.py` made it clear that `suggest_outfit` and `create_fit_card` needed to be gated and not just sequenced. Having the explicit "if results == [], return early" written in the spec meant the implementation matched the intended behavior on the first pass rather than discovering the empty-input problem during testing.

**One way implementation diverged from the spec:** The spec described query parsing as a simple regex or string-split approach (extract size like "size M", extract price like "under $30"). In practice this broke on natural phrasings like "I'm looking for something under thirty dollars in a medium" as no regex handles that reliably. The implementation switched to LLM-based parsing with a structured JSON prompt and a regex-based fallback. The spec was updated to reflect this after the fact, but the original assumption that string parsing would be sufficient was wrong.

---

## AI Usage

### Instance 1 — Implementing `search_listings`

**What I directed the AI to do:** I gave Claude the Tool 1 spec block from `planning.md` — the input parameters with types, the return value description listing all dict fields, and the failure mode — along with the `load_listings()` signature from `utils/data_loader.py`. I asked it to implement the function body inside `tools.py` using `load_listings()`.

**What I reviewed and revised:** The generated code used `dict.get(key, "")` as a null guard, which fails when a field exists in the JSON with an explicit `null` value (as `brand` does in several listings). The default only fires when the key is absent, not when it's present and null. I identified this during test failures (`TypeError: sequence item 3: expected str instance, NoneType found`) and replaced every `.get(key, "")` in the searchable text builder with `or ""` coercion, which handles both missing keys and explicit nulls. The scoring logic and keyword tokenization were kept as generated.

### Instance 2 — Implementing `run_agent()` planning loop

**What I directed the AI to do:** I gave Claude the full architecture diagram from `planning.md` (the ASCII flow showing the early-exit branches) and the State Management table (all session keys, when they're set, what they contain). I asked it to implement `run_agent()` in `agent.py` following the diagram exactly.

**What I reviewed and revised:** The generated loop did not include the stretch retry logic — it branched on empty results but didn't attempt a second call with `size=None`. I added the retry block manually, including setting `session["retry_attempted"]` and `session["retry_message"]` so the UI could surface it. I also changed the error string detection for `suggest_outfit` from checking `if not outfit` (which would suppress a short but valid suggestion) to checking `if outfit.startswith("Could not generate")`, which is precise to the actual error strings the function returns.