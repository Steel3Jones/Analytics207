# components/cards.py

import streamlit as st
import pandas as pd
from typing import Optional, Tuple

# Pure CSS (no indentation-sensitive HTML here)
_CARD_CSS = """
<style>
.analytics-card {
    background: #050816;
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.04);
    box-shadow: 0 18px 45px rgba(0,0,0,0.55);
    min-height: 190px;              /* force uniform card height */
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

/* Kicker (small label at top) */
.analytics-card .card-kicker {
    font-size: 0.7rem;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.9);
    margin-bottom: 6px;
}

/* Main title */
.analytics-card .card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f9fafb;
    line-height: 1.25;
}

/* Subtitle / subtext */
.analytics-card .card-sub {
    font-size: 0.85rem;
    color: rgba(156, 163, 175, 0.95);
    margin-top: 4px;
}

/* Metric / footer area */
.analytics-card .card-metric {
    font-size: 0.8rem;
    color: rgba(209, 213, 219, 0.95);
    margin-top: 10px;
}

/* Progress bar wrapper */
.analytics-card .card-progress {
    margin-top: 10px;
    height: 6px;
    width: 100%;
    background: rgba(31, 41, 55, 0.9);
    border-radius: 999px;
    overflow: hidden;
}

/* Progress bar fill */
.analytics-card .card-progress-fill {
    height: 100%;
    border-radius: 999px;
}
</style>
"""


def inject_card_css() -> None:
    """Call once per page (near the top)."""
    st.markdown(_CARD_CSS, unsafe_allow_html=True)


def render_card(
    container,
    kicker: str,
    title: str,
    sub: str = "",
    metric: Optional[str] = None,
    progress: Optional[Tuple[float, float, str]] = None,  # (value, max_value, color)
) -> None:
    # Build bar HTML in a single line to avoid Markdown code-block rendering.
    bar_html = ""
    if progress is not None:
        value, max_value, bar_color = progress
        if pd.isna(value) or pd.isna(max_value) or float(max_value) <= 0:
            width_pct = 0.0
        else:
            width_pct = 100.0 * float(value) / float(max_value)
            width_pct = max(0.0, min(100.0, width_pct))
        bar_html = (
            f'<div class="card-progress">'
            f'  <div class="card-progress-fill" '
            f'style="width:{width_pct:.1f}%;background:{bar_color};"></div>'
            f'</div>'
        )

    metric_html = metric or ""

    with container:
        st.markdown(
            f"""
            <div class="analytics-card">
              <div>
                <div class="card-kicker">{kicker}</div>
                <div class="card-title">{title}</div>
                <div class="card-sub">{sub}</div>
              </div>
              <div>
                <div class="card-metric">{metric_html}</div>
                {bar_html}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
