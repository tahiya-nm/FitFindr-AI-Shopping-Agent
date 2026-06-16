"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:      The text the user typed into the search box.
        wardrobe_choice: Either "Example wardrobe" or "Empty wardrobe (new user)".

    Returns:
        A tuple of (listing_text, outfit_suggestion, fit_card) — one string
        per output panel. On error, the error message goes in the first panel.
    """
    # Step 1: Guard against an empty query
    if not user_query or not user_query.strip():
        return "Please enter a search query to get started.", "", ""

    # Step 2: Select the wardrobe based on the radio button choice
    wardrobe = (
        get_example_wardrobe()
        if wardrobe_choice == "Example wardrobe"
        else get_empty_wardrobe()
    )

    # Step 3: Run the planning loop
    session = run_agent(user_query, wardrobe)

    # Step 4: If the agent hit an error, surface it in the first panel
    if session["error"] and session["selected_item"] is None:
        return session["error"], "", ""

    # Step 5: Format the selected listing into a readable string for the first panel
    item = session["selected_item"]
    retry_note = f"\n\n⚠️ {session.get('retry_message', '')}" if session.get("retry_message") else ""

    # Build price assessment line for the listing panel (stretch)
    price_note = ""
    pa = session.get("price_assessment")
    if pa and pa.get("assessment") != "unknown":
        emoji = {"good deal": "✅", "fair": "➡️", "overpriced": "⚠️"}.get(pa["assessment"], "")
        price_note = f"\nPrice verdict: {emoji} {pa['assessment'].upper()} — {pa['reasoning']}"

    listing_text = (
        f"🛍️ {item.get('title', 'Unknown')}\n"
        f"💲 ${item.get('price', '?')} · {item.get('platform', '?')}\n"
        f"📏 Size: {item.get('size', '?')} · Condition: {item.get('condition', '?')}\n"
        f"🏷️ Brand: {item.get('brand', '?')}\n"
        f"🎨 Colors: {', '.join(item.get('colors', []))}\n"
        f"✨ Tags: {', '.join(item.get('style_tags', []))}"
        f"{price_note}"
        f"{retry_note}"
    )

    outfit = session.get("outfit_suggestion") or ""
    fit_card = session.get("fit_card") or ""

    # If fit card errored but outfit is fine, show the error inline in that panel
    if session["error"] and session["outfit_suggestion"]:
        fit_card = session["error"]

    return listing_text, outfit, fit_card


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
