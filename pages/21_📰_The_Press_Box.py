# pages/XX__The_Pressbox.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import streamlit as st
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
if render_logo: render_logo()
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
# CSS
# ─────────────────────────────────────────────

def _inject_pb_css() -> None:
    st.markdown("""<style>
/* ── Hero cards ──────────────────────────────────────────────────────── */
.pb-hero-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 6px 0 22px;
}
.pb-hero-card {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border-radius: 14px;
    padding: 18px 20px 16px;
    border: 1px solid rgba(255,255,255,0.07);
    border-top-width: 3px;
}
.pb-hero-icon {
    font-size: 1.5rem;
    margin-bottom: 10px;
}
.pb-hero-title {
    font-size: 0.88rem;
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 6px;
}
.pb-hero-desc {
    font-size: 0.76rem;
    color: #94a3b8;
    line-height: 1.6;
}

/* ── Section pill ─────────────────────────────────────────────────────── */
.pb-section-head {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    border-radius: 999px;
    border: 1px solid rgba(96,165,250,0.35);
    background: rgba(96,165,250,0.07);
    font-size: 0.73rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #93c5fd;
    margin: 6px 0 14px;
}

/* ── Info card (right column) ─────────────────────────────────────────── */
.pb-info-card {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.15);
    border-left-width: 4px;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.pb-info-card-title {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.pb-info-item {
    font-size: 0.82rem;
    color: #e2e8f0;
    padding: 3px 0;
    line-height: 1.55;
}
.pb-info-item::before {
    content: "›  ";
    color: #60a5fa;
    font-weight: 700;
}

/* ── Step flow ────────────────────────────────────────────────────────── */
.pb-steps {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 4px;
}
.pb-step {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 14px;
    background: rgba(96,165,250,0.05);
    border: 1px solid rgba(96,165,250,0.12);
    border-radius: 10px;
}
.pb-step-num {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: rgba(96,165,250,0.20);
    color: #60a5fa;
    font-size: 0.72rem;
    font-weight: 900;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.pb-step-text {
    font-size: 0.82rem;
    color: #e2e8f0;
    line-height: 1.5;
}

/* ── Email CTA ────────────────────────────────────────────────────────── */
.pb-email-cta {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(74,222,128,0.25);
    border-radius: 12px;
    padding: 16px 20px;
    margin-top: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.pb-email-icon { font-size: 1.3rem; }
.pb-email-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 2px;
}
.pb-email-addr {
    font-size: 0.90rem;
    font-weight: 800;
    color: #4ade80;
}
</style>
""", unsafe_allow_html=True)


def _pb_section(icon: str, label: str, color: str = "#93c5fd",
                border: str = "rgba(96,165,250,0.35)", bg: str = "rgba(96,165,250,0.07)") -> None:
    st.markdown(
        f'<div class="pb-section-head" style="color:{color};border-color:{border};background:{bg};">'
        f'{icon} {label}</div>',
        unsafe_allow_html=True,
    )


def _info_card(title: str, items: list[str], border_color: str, title_color: str) -> str:
    items_html = "".join(f'<div class="pb-info-item">{item}</div>' for item in items)
    return (
        f'<div class="pb-info-card" style="border-left-color:{border_color};">'
        f'<div class="pb-info-card-title" style="color:{title_color};">{title}</div>'
        f'{items_html}'
        f'</div>'
    )


def _steps_html(steps: list[str]) -> str:
    inner = "".join(
        f'<div class="pb-step">'
        f'<div class="pb-step-num">{i+1}</div>'
        f'<div class="pb-step-text">{s}</div>'
        f'</div>'
        for i, s in enumerate(steps)
    )
    return f'<div class="pb-steps">{inner}</div>'


_inject_pb_css()

# ─────────────────────────────────────────────
# HERO CARDS
# ─────────────────────────────────────────────

hero_cards = [
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

cards_html = "".join(
    f'<div class="pb-hero-card" style="border-top-color:{color};">'
    f'<div class="pb-hero-icon">{icon}</div>'
    f'<div class="pb-hero-title">{title}</div>'
    f'<div class="pb-hero-desc">{desc}</div>'
    f'</div>'
    for icon, title, desc, color in hero_cards
)
st.markdown(f'<div class="pb-hero-grid">{cards_html}</div>', unsafe_allow_html=True)

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
        _pb_section("🔧", "Report a Data Error", "#fbbf24", "rgba(245,158,11,0.40)", "rgba(245,158,11,0.07)")

        st.caption(
            "Wrong score, missing game, misclassified team, bad record — "
            "anything that looks off. We review every submission."
        )

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
        st.write("")
        _pb_section("📋", "How It Works", "#fbbf24", "rgba(245,158,11,0.35)", "rgba(245,158,11,0.06)")

        st.markdown(
            _steps_html([
                "Submit the form with as much detail as possible — date, opponent, what's wrong, what's correct.",
                "Submission lands in our review queue, verified against MPA source data.",
                "Fix is applied in the next nightly build.",
                "Data refreshes automatically across all pages within 24 hours.",
            ]),
            unsafe_allow_html=True,
        )

        st.write("")
        st.markdown(
            _info_card("What We Can Fix", [
                "Game scores and results",
                "Team classification (Class / Region)",
                "Missing games from the schedule",
                "Team name spelling / duplicates",
                "Stat anomalies (PPG, margin, NetEff)",
            ], "#f59e0b", "#fbbf24"),
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="font-size:0.78rem;color:#94a3b8;margin-top:6px;padding:0 4px;">'
            '📌 MPA official results are the source of truth. If something conflicts, official data wins.'
            '</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# TAB 2 — CONTENT & STORIES
# ─────────────────────────────────────────────

with tab_content:
    st.write("")
    col_form, col_info = st.columns([0.55, 0.45], gap="large")

    with col_form:
        _pb_section("✍️", "Pitch a Story or Submit Content", "#93c5fd", "rgba(96,165,250,0.40)", "rgba(96,165,250,0.07)")

        st.caption(
            "We're actively looking for contributors — writers, photographers, "
            "and analysts who want to cover Maine high school basketball."
        )

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
        st.write("")
        _pb_section("🔍", "What We're Looking For", "#93c5fd", "rgba(96,165,250,0.40)", "rgba(96,165,250,0.07)")

        st.markdown(
            _info_card("Written Content", [
                "Recaps with data context (not just box scores)",
                "Class-specific season previews",
                "Bracket analysis and tournament breakdowns",
                "Opinion pieces backed by numbers",
            ], "#3b82f6", "#60a5fa"),
            unsafe_allow_html=True,
        )

        st.markdown(
            _info_card("Photography", [
                "Game action from gyms across Maine",
                "Student sections and atmosphere shots",
                "High resolution preferred (JPG/PNG)",
                "Rights must be yours to share",
            ], "#8b5cf6", "#a78bfa"),
            unsafe_allow_html=True,
        )

        st.markdown(
            _info_card("Analytics Contributions", [
                "Novel metrics or model ideas",
                "Opponent breakdown templates",
                "Anything that helps coaches or fans understand the game better",
            ], "#10b981", "#34d399"),
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="font-size:0.78rem;color:#94a3b8;margin-top:6px;padding:0 4px;">'
            '✅ All contributors are credited. We want to build something worth reading.'
            '</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# TAB 3 — PARTNER / WORK WITH US
# ─────────────────────────────────────────────

with tab_partner:
    st.write("")
    col_form, col_info = st.columns([0.55, 0.45], gap="large")

    with col_form:
        _pb_section("🤝", "Let's Work Together", "#4ade80", "rgba(74,222,128,0.35)", "rgba(74,222,128,0.06)")

        st.caption(
            "Sponsorships, school partnerships, custom builds, media integrations — "
            "tell us what you're thinking."
        )

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
        st.write("")
        _pb_section("💼", "What We Offer", "#4ade80", "rgba(74,222,128,0.35)", "rgba(74,222,128,0.06)")

        st.markdown(
            _info_card("Schools & Programs", [
                "Full-season custom dashboards",
                "Opponent scouting breakdowns",
                "Model-driven prep packages",
                "End-of-season analytics reports",
            ], "#10b981", "#34d399"),
            unsafe_allow_html=True,
        )

        st.markdown(
            _info_card("Media & Journalists", [
                "Data feeds and stat exports",
                "Embeddable rankings and tables",
                "Story angles backed by the model",
            ], "#3b82f6", "#60a5fa"),
            unsafe_allow_html=True,
        )

        st.markdown(
            _info_card("Sponsors & Businesses", [
                "Branded placement on rankings pages",
                "Weekly email sponsorship",
                "Custom integrations with your brand",
            ], "#f59e0b", "#fbbf24"),
            unsafe_allow_html=True,
        )

        st.markdown(
            _info_card("Coaches & ADs", [
                "Program-specific analytics tools",
                "Recruit evaluation frameworks",
                "Schedule strength and performance context",
            ], "#8b5cf6", "#a78bfa"),
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="pb-email-cta">'
            '<div class="pb-email-icon">📧</div>'
            '<div>'
            '<div class="pb-email-label">Prefer email?</div>'
            '<div class="pb-email-addr">analytics207@mainesports.com</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

_sp(2)
if render_footer:
    render_footer()
else:
    st.caption("© 2026 Analytics207")
