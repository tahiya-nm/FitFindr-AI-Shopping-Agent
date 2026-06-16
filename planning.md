# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Searches the mock listings dataset for secondhand items matching a natural language description, with optional size and price filters. Returns a ranked list of matching listings sorted by keyword relevance score.


**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Keywords describing the item the user wants (e.g., "vintage graphic tee"). Used to score each listing by keyword overlap against its title, description, and style_tags.
- `size` (str | None): Size string to filter by (e.g., "M", "S", "XL"). Case-insensitive. Pass `None` to skip size filtering.
- `max_price` (float | None): Maximum price in USD (inclusive). Pass `None` to skip price filtering.


**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of listing dicts, sorted by relevance score (highest first). Each dict contains:
`id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]),
`size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str), `platform` (str).
Returns an empty list `[]` if no listings match (does not raise an exception).


**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If the list is empty, the agent sets `session["error"]` to: *"No listings matched your search. Try broadening your description, adjusting your size, or raising your max price."* The agent stops; it does not call `suggest_outfit` with empty input. With retry logic enabled (stretch feature), the agent first retries with `size=None` before surfacing the error.


---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a specific thrifted listing and the user's wardrobe, calls the Groq LLM to suggest 1–2 complete outfit combinations. If the wardrobe is empty, it falls back to general styling advice for the item based on its style_tags and category.


**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A listing dict returned by `search_listings` — the item the user is considering buying.
- `wardrobe` (dict): A wardrobe dict with an `"items"` key containing a list of wardrobe item dicts (each with fields: `name`, `category`, `color`, `style`). May be empty.


**What it returns:**
<!-- Describe the return value -->
A non-empty string with 1–2 outfit suggestions. If the wardrobe has items, suggestions reference specific named pieces from the wardrobe. If the wardrobe is empty, the response is general style advice (e.g., what silhouettes, colors, or aesthetics pair well with the item).


**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If `wardrobe["items"]` is empty, the agent does not stop — it calls the LLM with a general styling prompt instead. If the LLM call raises an exception, the function catches it and returns the string: *"Could not generate outfit suggestions. Please try again."*


---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Generates a 2–4 sentence Instagram/TikTok-style caption for the thrifted outfit. Calls the Groq LLM with elevated temperature to ensure varied output across different inputs.


**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`.
- `new_item` (dict): The listing dict for the thrifted item (used for item name, price, and platform).


**What it returns:**
<!-- Describe the return value -->
A 2–4 sentence caption string written in casual, authentic "OOTD" voice. Mentions the item name, price, and platform naturally (once each). Captures the outfit vibe in specific terms. Returns a different result each time for different inputs due to higher LLM temperature.


**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If `outfit` is an empty or whitespace-only string, the function returns the string: *"Cannot generate a fit card — outfit description is missing."* It does not raise an exception. LLM exceptions are caught and return: *"Could not generate fit card. Please try again."*


---

### Additional Tools (if any)

### Tool 4: compare_price (stretch)

**What it does:**
Given a listing, finds comparable items in the dataset (same category and overlapping style_tags) and computes the median price of those comparables. Returns a price assessment with reasoning.

**Input parameters:**
- `item` (dict): A listing dict to evaluate.

**What it returns:**
A dict with: `assessment` (str — "good deal", "fair", or "overpriced"), `item_price` (float), `median_comparable_price` (float), `comparable_count` (int), `reasoning` (str explaining the comparison).

**What happens if it fails or returns nothing:**
If fewer than 2 comparable items are found, returns: `{"assessment": "unknown", "reasoning": "Not enough comparable listings to evaluate price."}`.

---


## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

The agent's planning loop in `run_agent()` uses explicit conditional branching on the contents of the session dict after each tool call:

```
1. Call search_listings(description, size, max_price).
   → If results == []:
       If retry logic is enabled AND size was provided:
           Retry with size=None. Inform user:
           "No results for size {size} — retrying without size filter..."
           If still []: set session["error"], return session early.
       Else: set session["error"], return session early.
   → If results is non-empty:
       Set session["selected_item"] = results[0]
       Optionally: run compare_price on results[0] and store in session.

2. Call suggest_outfit(session["selected_item"], wardrobe).
   → Store result in session["outfit_suggestion"].
   → If result is an error string (starts with "Could not"):
       Set session["error"], return session early.

3. Call create_fit_card(session["outfit_suggestion"], session["selected_item"]).
   → Store result in session["fit_card"].
   → If result is an error string: set session["error"], but still return
     the partial session (outfit_suggestion is still useful to the user).

4. Return session.
```

The agent never calls all three tools unconditionally. Steps 2 and 3 are only reached if the previous step produced valid output. The branch at step 1 is what makes the agent's behavior differ for non-standard inputs.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

A single `session` dict is initialized at the start of `run_agent()` and passed by reference through every tool call. It stores:

| Key | Set after | Value |
|---|---|---|
| `session["query"]` | Immediately | The original user query string |
| `session["selected_item"]` | `search_listings` succeeds | The top-matching listing dict |
| `session["outfit_suggestion"]` | `suggest_outfit` succeeds | The LLM outfit string |
| `session["fit_card"]` | `create_fit_card` succeeds | The caption string |
| `session["error"]` | Any tool fails | A specific, actionable error message string |
| `session["price_assessment"]` | `compare_price` runs (stretch) | The price assessment dict |
| `session["retry_attempted"]` | Retry logic fires (stretch) | Boolean |

No tool takes the session as a parameter; each tool receives only the specific values it needs, extracted from the session by the planning loop. This keeps tools independently testable.

---

## Error Handling

| Tool | Failure mode | Agent response |
|---|---|---|
| `search_listings` | No results match the query | Sets `session["error"]` = `"No listings matched your search. Try broadening your description, adjusting your size, or raising your max price."` Returns session early — does not proceed to `suggest_outfit`. |
| `search_listings` | Retry: no results even without size filter | Sets `session["error"]` = `"No listings found even after removing the size filter. Try a different description or price range."` |
| `suggest_outfit` | `wardrobe["items"]` is empty | Does not fail — calls LLM with a general styling prompt instead. Still returns a useful string. |
| `suggest_outfit` | LLM call raises exception | Returns string `"Could not generate outfit suggestions. Please try again."` Sets `session["error"]` and returns early. |
| `create_fit_card` | `outfit` is empty or whitespace | Returns string `"Cannot generate a fit card — outfit description is missing."` Does not raise an exception. |
| `create_fit_card` | LLM call raises exception | Returns string `"Could not generate fit card. Please try again."` Sets `session["error"]` but does NOT return early — `outfit_suggestion` is still surfaced to the user. |

---

## Architecture

```
User query (description, size, max_price, wardrobe)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                   Planning Loop                     │
│                   (run_agent)                       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
         search_listings(description, size, max_price)
                       │
           ┌───────────┴────────────────┐
     results == []               results non-empty
           │                            │
           ▼                            ▼
   [STRETCH] retry with     session["selected_item"] = results[0]
     size=None                          │
           │                    [STRETCH] compare_price(selected_item)
     still []?                  session["price_assessment"] = {...}
           │                            │
           ▼                            ▼
   session["error"] =        suggest_outfit(selected_item, wardrobe)
   "No listings found..."               │
   return session ◄──────   ┌───────────┴───────────┐
   (early exit)         error string           valid suggestion
                             │                       │
                             ▼                       ▼
                     session["error"]    session["outfit_suggestion"]
                     return session                  │
                     (early exit)                    ▼
                                          create_fit_card(outfit_suggestion,
                                                          selected_item)
                                                     │
                                          session["fit_card"] = caption
                                                     │
                                                     ▼
                                              return session
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

For `search_listings`: I'll give Claude the Tool 1 spec block from this file (inputs with types, return value description including all dict fields, failure mode) plus the `load_listings()` signature from `utils/data_loader.py`. I'll ask it to implement the function inside `tools.py` using `load_listings()`. Before running, I'll verify: does it filter by all three parameters? Does it compute a relevance score from keyword overlap? Does it return `[]` on no match rather than raising? I'll test with 3 queries — one that returns results, one that returns nothing, one that tests the price ceiling.

For `suggest_outfit`: I'll give Claude the Tool 2 spec block and the wardrobe schema structure (the `"items"` key, each item's fields). I'll ask for two separate prompt branches: one for empty wardrobe, one for non-empty. Before running, I'll verify: does it check `wardrobe["items"]` before prompting? Does it reference actual item names from the wardrobe in the non-empty branch? Does it catch LLM exceptions?

For `create_fit_card`: I'll give Claude the Tool 3 spec block and the caption style guidelines. I'll ask it to use `temperature=1.2` or higher. Before running, I'll run it 3 times on the same input and confirm outputs differ. I'll verify it guards the empty string case without raising.

**Milestone 4 — Planning loop and state management:**

I'll give Claude the full Architecture diagram above and the State Management table, and ask it to implement `run_agent()` in `agent.py`. Before running, I'll verify: does it branch on `results == []`? Does it pass `session["selected_item"]` directly into `suggest_outfit` rather than re-querying? Does it avoid calling all three tools unconditionally? I'll run the no-results test case and confirm `session["fit_card"]` is `None`.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1 — search_listings:**
Called with `description="vintage graphic tee"`, `size=None`, `max_price=30.0`. Loads all listings, filters to those priced ≤ $30, scores each by keyword overlap with "vintage graphic tee" against title, description, and style_tags. Returns a ranked list — top result: `{"title": "Faded Band Tee", "price": 22.0, "platform": "Depop", "condition": "Good", "style_tags": ["vintage", "graphic"], ...}`. Sets `session["selected_item"]` to that dict.

**Step 2 — suggest_outfit:**
Called with `new_item=session["selected_item"]` and a wardrobe containing wide-leg jeans, chunky sneakers, etc. Wardrobe is non-empty, so the LLM is prompted with item details and specific wardrobe pieces. Returns: `"Pair the faded band tee with your wide-leg jeans and chunky sneakers for a 90s grunge look. Roll the sleeves once and front-tuck slightly for shape."` Sets `session["outfit_suggestion"]` to that string.

**Step 3 — create_fit_card:**
Called with `outfit=session["outfit_suggestion"]` and `new_item=session["selected_item"]`. LLM generates a casual caption using the item name, $22 price, Depop platform, and the outfit vibe. Returns: `"thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 rolled sleeves, front tuck, done."` Sets `session["fit_card"]` to that string.

**Final output to user:**
All three panels populate in the Gradio UI:
- **Top Find:** Faded Band Tee — $22, Depop, Good condition
- **Outfit Suggestion:** `"Pair the faded band tee with your wide-leg jeans..."`
- **Fit Card:** `"thrifted this faded band tee off depop for $22..."`

**Error path (no results):**
If `search_listings` returns `[]`, `session["error"]` is set to the actionable message and the loop returns early. The UI displays: `"No listings matched your search. Try broadening your description, adjusting your size, or raising your max price."` — `suggest_outfit` and `create_fit_card` are never called.
