from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
    render_sidebar_shell,  # make sure this name matches your layout.py
)

# ---------- PAGE-SPECIFIC CSS (OPTIONAL) ----------


def _inject_page_css() -> None:
    """
    Extra CSS for this page only.
    Leave empty or add page-specific styles.
    """
    st.markdown(
        """
        <style>
        /* Example: tighten table fonts globally for this page */
        /* .my-page-table th, .my-page-table td { font-size: 0.8rem; } */
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------- PAGE-SPECIFIC FILTERS (OPTIONAL) ----------


def render_page_filters() -> None:
    """
    Filters that sit under the header for THIS page.
    Start simple; customize per page.
    """
    cols = st.columns(3)
    with cols[0]:
        st.selectbox("Gender", ["Boys", "Girls"], index=0, key="gender")
    with cols[1]:
        st.selectbox("Class", ["All", "A", "B", "C", "D", "S"], index=0, key="class")
    with cols[2]:
        st.selectbox("Region", ["All", "North", "South"], index=0, key="region")


# ---------- PAGE BODY (YOU EDIT THIS PER PAGE) ----------


def render_page_body() -> None:
    """
    Main content area for this page.
    Copy logic from Heal, Schedules, etc. into here when making a new page.
    """
    st.write("TODO: add main content here.")
    # Example placeholder:
    # st.markdown("This is where your table / charts go.")


# ---------- MAIN ----------


def main() -> None:
    # Global layout + sidebar nav (shared on all pages)
    apply_global_layout_tweaks()
    render_sidebar_shell()

    # Optional per-page CSS
    _inject_page_css()

    # Header stack
    render_logo()
    render_page_header(
        title="Page Title Here",
        definition="One-line definition of this page.",
        subtitle="Short subtitle describing what users see here.",
    )

    # Optional filters under header
    render_page_filters()

    # Main body
    render_page_body()

    # Shared footer
    render_footer()


if __name__ == "__main__":
    main()
