"""
app.py

Gradio interface for FitFindr — editorial thrift-fashion aesthetic.
Fixes: forces light mode via theme .set() + JS, full-viewport background,
CSS variable overrides so no dark boxes bleed through.

Run with:
    python app.py
"""

import gradio as gr
from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── Theme ──────────────────────────────────────────────────────────────────────
# Using Soft() as base (already light), then overriding every dark variant
# so dark-mode OS preference can't bleed into the UI.

theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.green,
    secondary_hue=gr.themes.colors.stone,
    neutral_hue=gr.themes.colors.stone,
    font=[gr.themes.GoogleFont("DM Sans"), "ui-sans-serif", "system-ui"],
).set(
    # Page background
    body_background_fill="#F5F2EC",
    body_background_fill_dark="#F5F2EC",

    # Block / card surfaces
    block_background_fill="#FDFAF6",
    block_background_fill_dark="#FDFAF6",
    block_border_color="#D8D2C8",
    block_border_color_dark="#D8D2C8",
    block_border_width="1px",
    block_shadow="0 1px 3px rgba(28,25,23,0.05)",

    # Labels
    block_label_background_fill="#F5F2EC",
    block_label_background_fill_dark="#F5F2EC",
    block_label_text_color="#1C1917",
    block_label_text_color_dark="#1C1917",
    block_title_text_color="#1C1917",
    block_title_text_color_dark="#1C1917",

    # Body text
    body_text_color="#1C1917",
    body_text_color_dark="#1C1917",
    body_text_color_subdued="#6B6460",
    body_text_color_subdued_dark="#6B6460",

    # Inputs
    input_background_fill="#FDFAF6",
    input_background_fill_dark="#FDFAF6",
    input_border_color="#D0CAC0",
    input_border_color_dark="#D0CAC0",
    input_border_color_focus="#4D6B46",
    input_border_color_focus_dark="#4D6B46",
    input_border_color_hover="#B0A89E",
    input_placeholder_color="#B0A89E",
    input_placeholder_color_dark="#B0A89E",

    # Primary button
    button_primary_background_fill="#1C1917",
    button_primary_background_fill_dark="#1C1917",
    button_primary_background_fill_hover="#4D6B46",
    button_primary_background_fill_hover_dark="#4D6B46",
    button_primary_text_color="#F5F2EC",
    button_primary_text_color_dark="#F5F2EC",
    button_primary_border_color="transparent",
    button_primary_border_color_dark="transparent",

    # Panel (group / search card background)
    panel_background_fill="#EDEAE3",
    panel_background_fill_dark="#EDEAE3",
    panel_border_color="#D8D2C8",
    panel_border_color_dark="#D8D2C8",

    # Examples table
    table_even_background_fill="#FDFAF6",
    table_even_background_fill_dark="#FDFAF6",
    table_odd_background_fill="#F5F2EC",
    table_odd_background_fill_dark="#F5F2EC",
    table_border_color="#D8D2C8",
    table_border_color_dark="#D8D2C8",
    table_row_focus="#E6EEE5",
    table_row_focus_dark="#E6EEE5",
)


# ── CSS ────────────────────────────────────────────────────────────────────────
# CSS handles typography, custom components, and anything theme can't reach.
# The :root.dark + .dark overrides are a safety net — they force light values
# even if Gradio's JS re-adds the dark class after page load.

CSS = """
/* ── Force Google Fonts (DM Serif Display for headings) ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600&display=swap');

/* ── Full-page background — covers the area outside .gradio-container ── */
html, body {
    background: #F5F2EC !important;
    min-height: 100vh !important;
    margin: 0 !important;
}

/* Gradio's outermost app wrapper */
.app, footer.svelte-mpyp4e, footer {
    background: #F5F2EC !important;
}

/* ── Safety net: override dark-mode CSS variables at root level ── */
:root, :root.dark, .dark {
    color-scheme: light !important;
    --body-background-fill:        #F5F2EC !important;
    --block-background-fill:       #FDFAF6 !important;
    --input-background-fill:       #FDFAF6 !important;
    --panel-background-fill:       #EDEAE3 !important;
    --body-text-color:             #1C1917 !important;
    --block-label-text-color:      #1C1917 !important;
    --block-title-text-color:      #1C1917 !important;
    --input-border-color:          #D0CAC0 !important;
    --neutral-950:                 #F5F2EC !important;
    --neutral-900:                 #F0EDE7 !important;
    --neutral-800:                 #EDEAE3 !important;
    --neutral-700:                 #D8D2C8 !important;
    --neutral-600:                 #B0A89E !important;
    --neutral-500:                 #8A827A !important;
    --neutral-400:                 #6B6460 !important;
    --neutral-300:                 #4A4540 !important;
    --neutral-200:                 #2C2A27 !important;
    --neutral-100:                 #1C1917 !important;
}

/* ── Gradio container ── */
.gradio-container {
    background: #F5F2EC !important;
    font-family: 'DM Sans', sans-serif !important;
    max-width: 1060px !important;
    margin: 0 auto !important;
    padding: 0 20px 56px !important;
}

/* ── Header ── */
#fitfindr-header {
    text-align: center;
    padding: 52px 24px 36px;
    border-bottom: 1px solid #D8D2C8;
    margin-bottom: 28px;
}

#fitfindr-header .eyebrow {
    display: inline-block;
    font-family: 'DM Sans', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #4D6B46;
    background: #E6EEE5;
    border: 1px solid #C2D4C0;
    padding: 5px 14px;
    border-radius: 20px;
    margin-bottom: 20px;
}

#fitfindr-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: clamp(42px, 7vw, 70px);
    font-weight: 400;
    color: #1C1917;
    line-height: 1.02;
    letter-spacing: -0.025em;
    margin: 0 0 14px;
}

#fitfindr-header h1 em {
    font-style: italic;
    color: #4D6B46;
}

#fitfindr-header .tagline {
    font-family: 'DM Sans', sans-serif;
    font-size: 15px;
    font-weight: 300;
    color: #6B6460;
    line-height: 1.65;
    letter-spacing: 0.01em;
    max-width: 460px;
    margin: 0 auto;
}

/* ── Search panel ── */
#search-panel {
    background: #EDEAE3 !important;
    border: 1px solid #D8D2C8 !important;
    border-radius: 16px !important;
    padding: 24px !important;
    margin-bottom: 24px !important;
    gap: 16px !important;
}

/* Force all inner blocks in the search panel to light */
#search-panel .block,
#search-panel label,
#search-panel .wrap,
#search-panel .gap {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Query textbox label */
#query-input > label > span,
#query-input .label-wrap span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    color: #6B6460 !important;
}

/* Textbox input */
#query-input textarea {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14.5px !important;
    background: #FDFAF6 !important;
    border: 1.5px solid #D0CAC0 !important;
    border-radius: 10px !important;
    color: #1C1917 !important;
    padding: 13px 15px !important;
    resize: none !important;
    line-height: 1.6 !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
}

#query-input textarea:focus {
    border-color: #4D6B46 !important;
    box-shadow: 0 0 0 3px rgba(77, 107, 70, 0.12) !important;
    outline: none !important;
}

#query-input textarea::placeholder {
    color: #B0A89E !important;
    font-style: italic !important;
}

/* Wardrobe radio label */
#wardrobe-radio > label > span,
#wardrobe-radio .label-wrap span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    color: #6B6460 !important;
}

#wardrobe-radio .wrap {
    gap: 8px !important;
    flex-direction: column !important;
    background: transparent !important;
}

#wardrobe-radio .wrap label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13.5px !important;
    color: #1C1917 !important;
    background: transparent !important;
    cursor: pointer !important;
}

/* Submit button */
#submit-btn {
    background: #1C1917 !important;
    color: #F5F2EC !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 15px 28px !important;
    cursor: pointer !important;
    transition: background 0.18s ease, transform 0.1s ease !important;
    width: 100% !important;
    margin-top: 4px !important;
    box-shadow: 0 2px 8px rgba(28,25,23,0.15) !important;
}

#submit-btn:hover {
    background: #4D6B46 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(77,107,70,0.25) !important;
}

#submit-btn:active {
    transform: translateY(0) !important;
}

/* ── "Results" section divider ── */
#results-label {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 4px 0 16px;
}

#results-label .label-text {
    font-family: 'DM Sans', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #B0A89E;
    white-space: nowrap;
}

#results-label .dash {
    flex: 1;
    height: 1px;
    background: #D8D2C8;
}

/* ── Output cards ── */
/* The hang-tag signature: 4px sage gradient bar on top of each card */
#listing-output,
#outfit-output,
#fitcard-output {
    background: #FDFAF6 !important;
    border: 1px solid #D8D2C8 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 4px rgba(28,25,23,0.05) !important;
    transition: box-shadow 0.18s ease, transform 0.18s ease !important;
    padding: 0 !important;
}

#listing-output:hover,
#outfit-output:hover,
#fitcard-output:hover {
    box-shadow: 0 6px 18px rgba(28,25,23,0.09) !important;
    transform: translateY(-2px) !important;
}

/* Top bar via a border-top — more reliable than ::before in Gradio */
#listing-output {
    border-top: 4px solid #4D6B46 !important;
}
#outfit-output {
    border-top: 4px solid #7A9E73 !important;
}
#fitcard-output {
    border-top: 4px solid #A0C49A !important;
}

/* Panel label — editorial serif */
#listing-output label span,
#outfit-output label span,
#fitcard-output label span {
    font-family: 'DM Serif Display', serif !important;
    font-size: 15px !important;
    font-weight: 400 !important;
    font-style: normal !important;
    color: #1C1917 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    background: #F5F2EC !important;
    padding: 12px 16px 10px !important;
    display: block !important;
    border-bottom: 1px solid #E8E3DC !important;
}

/* Panel text */
#listing-output textarea,
#outfit-output textarea,
#fitcard-output textarea {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13.5px !important;
    line-height: 1.78 !important;
    color: #1C1917 !important;
    background: #FDFAF6 !important;
    border: none !important;
    padding: 15px 16px !important;
    cursor: default !important;
}

/* ── Examples ── */
#examples-section {
    margin-top: 10px !important;
}

#examples-section .label-wrap span,
#examples-section label span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    color: #B0A89E !important;
}

/* Examples table */
.examples-holder table {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    border-collapse: collapse !important;
    background: #FDFAF6 !important;
    border: 1px solid #D8D2C8 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    width: 100% !important;
}

.examples-holder td, .examples-holder th {
    color: #1C1917 !important;
    background: #FDFAF6 !important;
    border-color: #E8E3DC !important;
    padding: 10px 16px !important;
}

.examples-holder tr:hover td {
    background: #E6EEE5 !important;
    cursor: pointer !important;
}

/* ── Footer ── */
#fitfindr-footer {
    text-align: center;
    padding: 30px 0 0;
    margin-top: 44px;
    border-top: 1px solid #D8D2C8;
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 400;
    color: #B0A89E;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

/* ── Responsive ── */
@media (max-width: 720px) {
    .gradio-container {
        padding: 0 12px 40px !important;
    }

    #fitfindr-header {
        padding: 36px 16px 28px;
    }

    #search-panel {
        padding: 18px !important;
    }

    /* Stack output cards vertically on mobile */
    #results-row {
        flex-direction: column !important;
        gap: 14px !important;
    }

    #listing-output,
    #outfit-output,
    #fitcard-output {
        width: 100% !important;
    }
}
"""

# ── JS — strip dark class immediately on page load ─────────────────────────────
JS = """
() => {
    const strip = () => {
        document.documentElement.classList.remove('dark');
        document.body.classList.remove('dark');
        const c = document.querySelector('.gradio-container');
        if (c) c.classList.remove('dark');
    };
    strip();
    // Re-run after Gradio hydrates in case it re-adds the class
    setTimeout(strip, 100);
    setTimeout(strip, 500);
}
"""


# ── Query handler ──────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:      The text the user typed into the search box.
        wardrobe_choice: "Example wardrobe" or "Empty wardrobe (new user)".

    Returns:
        (listing_text, outfit_suggestion, fit_card) — one string per panel.
        On error, the message goes in the first panel and the others are empty.
    """
    # Guard empty query
    if not user_query or not user_query.strip():
        return "Enter a search to get started — try 'vintage graphic tee under $30'.", "", ""

    # Select wardrobe
    wardrobe = (
        get_example_wardrobe()
        if wardrobe_choice == "Example wardrobe"
        else get_empty_wardrobe()
    )

    # Run planning loop
    session = run_agent(user_query, wardrobe)

    # Unrecoverable error — no item found at all
    if session["error"] and session["selected_item"] is None:
        return session["error"], "", ""

    # Format listing card
    item = session["selected_item"]

    retry_note = (
        f"\n\n⚠️  {session['retry_message']}"
        if session.get("retry_message") else ""
    )

    price_note = ""
    pa = session.get("price_assessment")
    if pa and pa.get("assessment") != "unknown":
        badge = {
            "good deal":  "✅  Good deal",
            "fair":       "➡️  Fair price",
            "overpriced": "⚠️  Overpriced",
        }
        price_note = (
            f"\n\nPrice check  {badge.get(pa['assessment'], '')}\n"
            f"{pa['reasoning']}"
        )

    listing_text = (
        f"{item.get('title', 'Unknown')}\n"
        f"{'─' * 32}\n"
        f"💲  ${item.get('price', '?')}   ·   {item.get('platform', '?')}\n"
        f"📏  Size {item.get('size', '?')}   ·   {item.get('condition', '?')} condition\n"
        f"🏷   {item.get('brand') or 'Unknown brand'}\n"
        f"🎨  {', '.join(item.get('colors', []))}\n"
        f"✦   {' · '.join(item.get('style_tags', []))}"
        f"{price_note}"
        f"{retry_note}"
    )

    outfit   = session.get("outfit_suggestion") or ""
    fit_card = session.get("fit_card") or ""

    # If fit card failed but outfit is valid, surface the error in that panel
    if session["error"] and session["outfit_suggestion"]:
        fit_card = session["error"]

    return listing_text, outfit, fit_card


# ── Interface ──────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results demo
]


def build_interface():
    with gr.Blocks(css=CSS, theme=theme, js=JS, title="FitFindr") as demo:

        # Header
        gr.HTML("""
        <div id="fitfindr-header">
            <div class="eyebrow">✦ AI Style Agent</div>
            <h1>Fit<em>Findr</em></h1>
            <p class="tagline">
                Describe what you're hunting for — we'll find it,
                style it with your wardrobe, and write the caption.
            </p>
        </div>
        """)

        # Search panel
        with gr.Group(elem_id="search-panel"):
            with gr.Row():
                query_input = gr.Textbox(
                    label="What are you looking for?",
                    placeholder="e.g. vintage graphic tee under $30, size M...",
                    lines=3,
                    scale=3,
                    elem_id="query-input",
                    show_label=True,
                )
                wardrobe_choice = gr.Radio(
                    choices=["Example wardrobe", "Empty wardrobe (new user)"],
                    value="Example wardrobe",
                    label="Wardrobe",
                    scale=1,
                    elem_id="wardrobe-radio",
                )

            submit_btn = gr.Button(
                "Find my fit  →",
                variant="primary",
                elem_id="submit-btn",
            )

        # Results divider
        gr.HTML("""
        <div id="results-label">
            <div class="dash"></div>
            <span class="label-text">Results</span>
            <div class="dash"></div>
        </div>
        """)

        # Output panels
        with gr.Row(elem_id="results-row", equal_height=True):
            listing_output = gr.Textbox(
                label="🛍️  Top listing found",
                lines=13,
                interactive=False,
                elem_id="listing-output",
            )
            outfit_output = gr.Textbox(
                label="👗  How to wear it",
                lines=13,
                interactive=False,
                elem_id="outfit-output",
            )
            fitcard_output = gr.Textbox(
                label="✨  Your fit card",
                lines=13,
                interactive=False,
                elem_id="fitcard-output",
            )

        # Examples
        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these searches",
            elem_id="examples-section",
        )

        # Footer
        gr.HTML("""
        <div id="fitfindr-footer">
            FitFindr &nbsp;·&nbsp; AI-powered secondhand style agent
            &nbsp;·&nbsp; Groq &nbsp;·&nbsp; llama-3.3-70b-versatile
        </div>
        """)

        # Wire events
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