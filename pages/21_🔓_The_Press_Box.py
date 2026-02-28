# pages/XX__The_Pressbox.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import layout as L
from auth import login_gate, logout_button


from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

st.set_page_config(
    page_title="🏟️ The Pressbox | ANALYTICS207",
    page_icon="🏟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# LAYOUT RESOLVER
# ─────────────────────────────────────────────

def _pick(*names: str) -> Optional[Callable]:
    for n in names:
        fn = getattr(L, n, None)
        if callable(fn): return fn
    return None

apply_layout  = _pick("apply_global_layout_tweaks", "applygloballayouttweaks")
render_logo   = _pick("render_logo", "renderlogo")
render_header = _pick("render_page_header", "renderpageheader")
render_footer = _pick("render_footer", "renderfooter")
spacer        = _pick("spacer", "spacerlines")

def _sp(n: int = 1) -> None:
    if callable(spacer):
        try: spacer(n); return
        except Exception: pass
    for _ in range(max(0, int(n))): st.write("")

if apply_layout: apply_layout()
login_gate(required=False)
logout_button()
if render_logo:  render_logo()
if render_header:
    render_header(
        title="🏟️ The Pressbox",
        definition="The Pressbox (n.): Where data meets the people who care about it.",
        subtitle="Flag a data error, pitch a story, partner with us, or reach out about working together.",
    )
else:
    st.title("🏟️ The Pressbox")

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR     = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTACT_FILE = DATA_DIR / "contact_messages.csv"

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def is_valid_email(s: str) -> bool:
    return bool(EMAIL_RE.match((s or "").strip()))

def append_row_csv(path: Path, row: dict, columns: list[str]) -> None:
    df = pd.read_csv(path, dtype=str, keep_default_na=False) if path.exists() else pd.DataFrame(columns=columns)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8")

def save_contact(name: str, email: str, reason: str, message: str) -> None:
    append_row_csv(CONTACT_FILE, {
        "Timestamp": pd.Timestamp.now().isoformat(),
        "Name":      (name    or "").strip(),
        "Email":     (email   or "").strip(),
        "Reason":    (reason  or "").strip(),
        "Message":   (message or "").strip(),
    }, ["Timestamp", "Name", "Email", "Reason", "Message"])

# ─────────────────────────────────────────────
# HERO CARDS
# ─────────────────────────────────────────────

def render_pressbox_hero() -> None:
    cards = [
        ("🔧", "Data Corrections",
         "Spot a wrong score, missing result, or misclassified team? Tell us and we'll fix it.",
         "#f59e0b"),
        ("✍️", "Content & Stories",
         "We're looking for data-driven game articles, film breakdowns, and game photography.",
         "#3b82f6"),
        ("🤝", "Partner With Us",
         "Sponsorships, school partnerships, and custom analytics builds. Let's talk.",
         "#10b981"),
        ("📡", "Work Together",
         "Media outlets, coaches, and programs — we build tools that help you tell better stories.",
         "#8b5cf6"),
    ]
    card_html = ""
    for icon, title, desc, color in cards:
        card_html += f"""
        <div style="
            flex:1; min-width:190px;
            background:#0d1626;
            border:1px solid rgba(255,255,255,0.09);
            border-top:3px solid {color};
            border-radius:14px;
            padding:18px 20px 16px;
        ">
            <div style="font-size:22px;margin-bottom:8px;">{icon}</div>
            <div style="font-size:13px;font-weight:800;color:#f1f5f9;margin-bottom:6px;">{title}</div>
            <div style="font-size:11px;color:rgba(203,213,225,0.7);line-height:1.55;">{desc}</div>
        </div>"""

    html = f"""<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="display:flex;gap:14px;flex-wrap:wrap;padding:4px 0 8px;">
    {card_html}
  </div>
</body></html>"""
    components.html(html, height=150, scrolling=False)

# ─────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────

st.write("")
render_pressbox_hero()
st.write("")

tab_correction, tab_content, tab_partner = st.tabs([
    "🔧 Data Correction",
    "✍️ Content & Stories",
    "🤝 Partner / Work With Us",
])

# ─────────────────────────────────────────────
# TAB 1 — DATA CORRECTIONS
# ─────────────────────────────────────────────

with tab_correction:
    st.write("")
    col_form, col_info = st.columns([0.55, 0.45], gap="large")

    with col_form:
        st.markdown("### 🔧 Report a Data Error")
        st.caption(
            "Wrong score, missing game, misclassified team, bad record — "
            "anything that looks off. We review every submission."
        )
        st.write("")

        with st.form("correction_form", clear_on_submit=True):
            name_c    = st.text_input("Your name (optional)")
            email_c   = st.text_input("Email", placeholder="So we can follow up if needed")
            team_name = st.text_input("Team(s) involved", placeholder="e.g. Fort Kent Community Boys")
            error_type = st.selectbox("Type of error", [
                "Wrong score / result",
                "Missing game",
                "Wrong team classification (Class/Region)",
                "Duplicate entry",
                "Team name spelling",
                "Stats error (PPG, margin, etc.)",
                "Other",
            ])
            message = st.text_area(
                "Details",
                height=140,
                placeholder="The more specific the better — date of game, opponent, what's wrong, what's correct.",
            )
            submitted = st.form_submit_button("→ Submit Correction", use_container_width=True)

        if submitted:
            if not is_valid_email(email_c) and (email_c or "").strip():
                st.error("That email doesn't look valid.")
            elif len((message or "").strip()) < 10:
                st.error("Please describe the issue (at least 10 characters).")
            else:
                save_contact(name_c, email_c, f"Data Correction: {error_type} — {team_name}", message)
                st.success("✅ Correction submitted — thank you. We review daily.")

    with col_info:
        st.markdown("### How Corrections Work")
        st.write("")
        st.markdown("""
**What we can fix:**
- Game scores and results
- Team classification (Class / Region)
- Missing games from the schedule
- Team name spelling / duplicates
- Stat anomalies (PPG, margin, NetEff)


**What happens after you submit:**
1. Submission lands in our review queue
2. We verify against source data (MPA, live stats)
3. Fix is applied in the next nightly build
4. Data refreshes automatically across all pages


**Turnaround:** Most corrections go live within 24 hours.


**Source of truth:** We use MPA official results as the primary source.
If something conflicts, official MPA data wins.
        """)

# ─────────────────────────────────────────────
# TAB 2 — CONTENT & STORIES
# ─────────────────────────────────────────────

with tab_content:
    st.write("")
    col_form, col_info = st.columns([0.55, 0.45], gap="large")

    with col_form:
        st.markdown("### ✍️ Pitch a Story or Submit Content")
        st.caption(
            "We're actively looking for contributors — writers, photographers, "
            "and analysts who want to cover Maine high school basketball."
        )
        st.write("")

        with st.form("content_form", clear_on_submit=True):
            name_w    = st.text_input("Your name")
            email_w   = st.text_input("Email", placeholder="you@example.com")
            content_type = st.selectbox("What are you pitching?", [
                "Data-driven game article / recap",
                "Season preview or breakdown",
                "Player or team feature",
                "Game photography",
                "Film / video breakdown",
                "Stat analysis or opinion piece",
                "Other",
            ])
            message_w = st.text_area(
                "Tell us about it",
                height=140,
                placeholder="Give us the idea, the angle, and why it fits Analytics207.",
            )
            submitted_w = st.form_submit_button("→ Send Pitch", use_container_width=True)

        if submitted_w:
            if not is_valid_email(email_w):
                st.error("Please enter a valid email so we can respond.")
            elif len((message_w or "").strip()) < 10:
                st.error("Please describe your pitch (at least 10 characters).")
            else:
                save_contact(name_w, email_w, f"Content Pitch: {content_type}", message_w)
                st.success("✅ Pitch received — we'll be in touch within a few days.")

    with col_info:
        st.markdown("### What We're Looking For")
        st.write("")
        st.markdown("""
**Written content:**
- Recaps with data context (not just box scores)
- Class-specific season previews
- Bracket analysis and tournament breakdowns
- Opinion pieces backed by numbers


**Photography:**
- Game action from gyms across Maine
- Student sections, atmosphere shots
- High resolution preferred (JPG/PNG)
- Rights must be yours to share


**Analytics contributions:**
- Novel metrics or model ideas
- Opponent breakdown templates
- Anything that helps coaches or fans
  understand the game better


All contributors are credited. Reach out —
we want to build something worth reading.
        """)

# ─────────────────────────────────────────────
# TAB 3 — PARTNER / WORK WITH US
# ─────────────────────────────────────────────

with tab_partner:
    st.write("")
    col_form, col_info = st.columns([0.55, 0.45], gap="large")

    with col_form:
        st.markdown("### 🤝 Let's Work Together")
        st.caption(
            "Sponsorships, school partnerships, custom builds, media integrations — "
            "tell us what you're thinking."
        )
        st.write("")

        with st.form("partner_form", clear_on_submit=True):
            name_p    = st.text_input("Your name")
            org_p     = st.text_input("Organization / School / Outlet")
            email_p   = st.text_input("Email", placeholder="you@example.com")
            interest  = st.selectbox("What are you interested in?", [
                "Sponsorship or advertising",
                "School or program partnership",
                "Custom dashboard or scouting tool",
                "Media outlet data integration",
                "Coaching analytics package",
                "General collaboration inquiry",
                "Other",
            ])
            message_p = st.text_area(
                "Tell us more",
                height=140,
                placeholder="What are you looking to do? The more context, the better.",
            )
            submitted_p = st.form_submit_button("→ Start the Conversation", use_container_width=True)

        if submitted_p:
            if not is_valid_email(email_p):
                st.error("Please enter a valid email so we can respond.")
            elif len((message_p or "").strip()) < 10:
                st.error("Please add some detail (at least 10 characters).")
            else:
                save_contact(name_p, email_p, f"Partnership: {interest} — {org_p}", message_p)
                st.success("✅ Message received — we'll follow up within 48 hours.")

    with col_info:
        st.markdown("### What We Offer")
        st.write("")
        st.markdown("""
**For schools & programs:**
- Full-season custom dashboards
- Opponent scouting breakdowns
- Model-driven prep packages
- End-of-season analytics reports


**For media & journalists:**
- Data feeds and stat exports
- Embeddable rankings and tables
- Story angles backed by the model


**For sponsors & businesses:**
- Branded placement on rankings pages
- Weekly email sponsorship
- Custom integrations with your brand


**For coaches & ADs:**
- Program-specific analytics tools
- Recruit evaluation frameworks
- Schedule strength and performance context


---
📧 Prefer email?
        """)
        st.link_button(
            "analytics207@mainesports.com",
            "mailto:analytics207@mainesports.com",
            use_container_width=True,
        )

_sp(2)
if render_footer:
    render_footer()
else:
    st.caption("© 2026 Analytics207")
