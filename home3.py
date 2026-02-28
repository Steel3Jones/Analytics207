from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import streamlit as st

import layout as L
from components.home_card import inject_home_card_css


# ----------------------------
# Page config (call once, at top)
# ----------------------------
st.set_page_config(
    page_title="🏀 ANALYTICS207 | Home",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------
# Global constants
# ----------------------------
APP_ROOT = Path(r"C:\ANALYTICS207\web")

# ----------------------------
# Card CSS
# ----------------------------
inject_home_card_css()

# ----------------------------
# Layout helpers (optional)
# ----------------------------
def _pick(*names: str) -> Optional[Callable]:
    for n in names:
        fn = getattr(L, n, None)
        if callable(fn):
            return fn
    return None

# IMPORTANT: Home should NOT call apply_layout (it broke your sidebar reopen).
render_logo = _pick("render_logo", "renderlogo")
render_header = _pick("render_page_header", "renderpageheader")
render_footer = _pick("render_footer", "renderfooter")
spacer = _pick("spacer", "spacerlines")

def _sp(n: int = 1) -> None:
    if callable(spacer):
        try:
            spacer(n)
            return
        except Exception:
            pass
    for _ in range(max(0, int(n))):
        st.write("")

# ----------------------------
# Header / brand
# ----------------------------
if callable(render_logo):
    render_logo()

if callable(render_header):
    render_header(
        title="",
        definition="Inside the data model behind our sports insights.",
        subtitle="Schedules • Ratings • Tournaments • Predictions • Community • Analytics",
    )
else:
    st.caption("Inside the data model behind our sports insights.")

_sp(1)

# ----------------------------
# Home-only CSS (safe: no sidebar/header selectors)
# ----------------------------
st.markdown(
    """
    <style>
    .block-container { padding-top: 0.7rem; }

    /* HERO CARD */
    .a207-hero-card {
        position: relative;
        border-radius: 24px;
        padding: 1.5rem 1.6rem;
        background: radial-gradient(circle at 0% 0%, #020617, #020617);
        box-shadow:
            0 28px 50px rgba(15,23,42,0.95),
            inset 0 0 0 1px rgba(148,163,184,0.35);
        color: #e5e7eb;
        margin-bottom: 1.6rem;
        overflow: hidden;
    }
    .a207-hero-card::before {
        content: "";
        position: absolute;
        inset: -40%;
        background:
            radial-gradient(circle at 5% 0%, rgba(59,130,246,0.32), transparent 60%),
            radial-gradient(circle at 75% 0%, rgba(244,114,182,0.26), transparent 60%),
            radial-gradient(circle at 100% 40%, rgba(34,197,94,0.16), transparent 60%);
        mix-blend-mode: screen;
        opacity: 0.95;
        pointer-events: none;
    }

    /* FAKE CHART (decorative) */
    .a207-fakechart{
        position: absolute;
        right: 10px;
        top: 6px;
        width: 58%;
        height: 120px;
        opacity: 0.55;
        pointer-events: none;
        z-index: 0;
        mask-image: radial-gradient(circle at 70% 40%, rgba(0,0,0,1), rgba(0,0,0,0) 72%);
        -webkit-mask-image: radial-gradient(circle at 70% 40%, rgba(0,0,0,1), rgba(0,0,0,0) 72%);
    }
    .a207-fakechart svg{ width: 100%; height: 100%; display:block; }

    .a207-hero-inner {
        position: relative;
        overflow: hidden;
        z-index: 1;
        display: grid;
        grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.6fr);
        gap: 1.4rem;
        align-items: stretch;
    }
    @media (max-width: 1100px) {
        .a207-hero-inner { grid-template-columns: minmax(0, 1fr); }
        .a207-fakechart{ display:none; }
    }

    .a207-hero-tag {
        font-size: 0.78rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #a5b4fc;
        margin-bottom: 0.35rem;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    .a207-hero-tag-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: #22c55e;
        box-shadow: 0 0 0 4px rgba(34,197,94,0.35);
    }

    .a207-hero-title {
        font-size: 2rem;
        line-height: 1.1;
        font-weight: 800;
        letter-spacing: 0.02em;
        margin-bottom: 0.35rem;
    }
    .a207-hero-sub {
        font-size: 0.95rem;
        color: #e5e7eb;
        max-width: 32rem;
        margin-bottom: 0.7rem;
    }

    .a207-hero-highlight {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.28rem 0.75rem;
        border-radius: 999px;
        border: 1px solid rgba(248,250,252,0.5);
        background: rgba(15,23,42,0.9);
        font-size: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .a207-hero-highlight-badge {
        padding: 0.08rem 0.45rem;
        border-radius: 999px;
        background: rgba(34,197,94,0.22);
        color: #bbf7d0;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
    }

    .a207-hero-pricing-row {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        margin-bottom: 0.7rem;
        flex-wrap: wrap;
    }
    .a207-hero-price-main { font-size: 1.5rem; font-weight: 800; }
    .a207-hero-price-sub { font-size: 0.78rem; color: #9ca3af; }

    .a207-hero-cta-row {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        flex-wrap: wrap;
    }
    .a207-hero-cta-primary {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.4rem 1.1rem;
        border-radius: 999px;
        border: 1px solid rgba(251,113,133,1);
        background: linear-gradient(135deg, #fb7185, #f97316);
        color: #111827;
        font-size: 0.86rem;
        font-weight: 700;
        cursor: pointer;
    }
    .a207-hero-cta-secondary { font-size: 0.8rem; color: #9ca3af; }
    .a207-hero-social-proof { margin-top: 0.55rem; font-size: 0.75rem; color: #9ca3af; }

    .a207-hero-board {
        border-radius: 18px;
        padding: 0.9rem 1rem;
        background: radial-gradient(circle at 10% 0%, rgba(15,23,42,1), #020617);
        box-shadow:
            0 18px 30px rgba(15,23,42,0.9),
            inset 0 0 0 1px rgba(15,23,42,1);
        display: flex;
        flex-direction: column;
        gap: 0.65rem;
    }
    .a207-hero-board-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.78rem;
        color: #9ca3af;
    }
    .a207-hero-board-header span:first-child {
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 600;
        color: #e5e7eb;
    }
    .a207-hero-board-games {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.6rem;
    }
    @media (max-width: 900px) {
        .a207-hero-board-games { grid-template-columns: minmax(0, 1fr); }
    }
    .a207-hero-game {
        border-radius: 14px;
        padding: 0.6rem 0.7rem;
        background: linear-gradient(135deg, rgba(15,23,42,1), rgba(30,64,175,0.45));
        border: 1px solid rgba(148,163,184,0.6);
        font-size: 0.8rem;
    }
    .a207-hero-game-title {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 0.2rem;
    }
    .a207-hero-game-teams { font-weight: 600; }
    .a207-hero-game-tip { font-size: 0.72rem; color: #cbd5f5; }
    .a207-hero-game-metrics {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        margin-top: 0.25rem;
        color: #e5e7eb;
    }
    .a207-hero-game-tag {
        font-size: 0.7rem;
        padding: 0.06rem 0.45rem;
        border-radius: 999px;
        background: rgba(15,23,42,0.95);
        border: 1px solid rgba(251,191,36,0.9);
        color: #facc15;
    }
    .a207-hero-board-footer {
        margin-top: 0.3rem;
        font-size: 0.76rem;
        color: #9ca3af;
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------
# Rendering helpers
# ----------------------------
def _render_hero_card() -> None:
    st.markdown('<div class="a207-hero-inner">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="a207-fakechart" aria-hidden="true">
          <svg viewBox="0 0 900 220" preserveAspectRatio="none">
            <g stroke="rgba(148,163,184,0.18)" stroke-width="1">
              <line x1="0" y1="40" x2="900" y2="40"/>
              <line x1="0" y1="95" x2="900" y2="95"/>
              <line x1="0" y1="150" x2="900" y2="150"/>
              <line x1="0" y1="205" x2="900" y2="205"/>
            </g>
            <path d="M0,160 L120,140 L240,150 L360,145 L480,110 L600,85 L720,60 L900,62"
                  fill="none" stroke="rgba(56,189,248,0.95)" stroke-width="3.2"/>
            <path d="M0,185 L120,175 L240,180 L360,176 L480,166 L600,158 L720,132 L900,128"
                  fill="none" stroke="rgba(251,113,133,0.85)" stroke-width="2.6"/>
            <path d="M0,205 L120,198 L240,202 L360,199 L480,192 L600,188 L720,170 L900,168"
                  fill="none" stroke="rgba(250,204,21,0.85)" stroke-width="2.4"/>
          </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.2, 1.6])

    with col_left:
        st.markdown(
            """
            <div>
              <div class="a207-hero-tag">
                <span class="a207-hero-tag-dot"></span>
                <span>TONIGHT'S BOARD • RATINGS. PREDICTIONS. EDGES.</span>
              </div>
              <div class="a207-hero-title">
                Every game, every edge,<br>🧠The model for the entire state.
              </div>
              <div class="a207-hero-sub">
                True Strength ratings, projected scores, and calculated spreads driven by real data analytics.
              </div>
              <div class="a207-hero-highlight">
                <span class="a207-hero-highlight-badge">NEW</span>
                <span>Full 2025–26 coverage for boys and girls programs statewide.</span>
              </div>
              <div class="a207-hero-pricing-row">
                <div>
                  <div class="a207-hero-price-main">$6<span style="font-size:0.9rem;">/mo</span></div>
                  <div class="a207-hero-price-sub">or $60 for the full season • cancel anytime</div>
                </div>
              </div>
              <div class="a207-hero-cta-row">
                <div class="a207-hero-cta-primary">
                  <span>Unlock EVERYTHING Now!</span>
                  <span>→</span>
                </div>
                <div class="a207-hero-cta-secondary">
                  Get projections—spreads and projected scores—updated nightly.
                </div>
              </div>
              <div class="a207-hero-social-proof">
                Trusted by coaches, media, and hoops sickos across Maine.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            """
            <div class="a207-hero-board">
              <div class="a207-hero-board-header">
                <span>TONIGHT'S GAMES</span>
                <span>Model edges, TSR gaps, upset radar</span>
              </div>
              <div class="a207-hero-board-games">
                <div class="a207-hero-game">
                  <div class="a207-hero-game-title">
                    <div class="a207-hero-game-teams">Oceanside at Cony</div>
                    <div class="a207-hero-game-tip">TSR Δ 7.4 • 7:00 PM</div>
                  </div>
                  <div class="a207-hero-game-metrics">
                    <div>Cony win prob: <strong>68%</strong></div>
                    <div class="a207-hero-game-tag">EDGE: CONY</div>
                  </div>
                </div>
                <div class="a207-hero-game">
                  <div class="a207-hero-game-title">
                    <div class="a207-hero-game-teams">Bangor at Portland</div>
                    <div class="a207-hero-game-tip">TSR Δ 1.2 • 6:30 PM</div>
                  </div>
                  <div class="a207-hero-game-metrics">
                    <div>Portland win prob: <strong>54%</strong></div>
                    <div class="a207-hero-game-tag">COIN FLIP</div>
                  </div>
                </div>
                <div class="a207-hero-game">
                  <div class="a207-hero-game-title">
                    <div class="a207-hero-game-teams">Brewer at Hampden</div>
                    <div class="a207-hero-game-tip">Back‑to‑back • 7:00 PM</div>
                  </div>
                  <div class="a207-hero-game-metrics">
                    <div>Upset chance: <strong>31%</strong></div>
                    <div class="a207-hero-game-tag">UPSET RADAR</div>
                  </div>
                </div>
                <div class="a207-hero-game">
                  <div class="a207-hero-game-title">
                    <div class="a207-hero-game-teams">Edward Little at Lewiston</div>
                    <div class="a207-hero-game-tip">Derby • TSR Δ 0.3</div>
                  </div>
                  <div class="a207-hero-game-metrics">
                    <div>Over 135.5: <strong>59%</strong></div>
                    <div class="a207-hero-game-tag">WATCH</div>
                  </div>
                </div>
              </div>
              <div class="a207-hero-board-footer">
                <span>Subscribers get data on every game statewide.</span>
                <span>Powered by 🧠 The Model.</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Shot share (TSR)")
            st.caption("Coming soon")
        with c2:
            st.caption("Rating trend")
            st.caption("Coming soon")
        with c3:
            st.caption("Edge breakdown")
            st.caption("Coming soon")

    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------
# Render page (TOP ONLY)
# ----------------------------
_render_hero_card()

_sp(2)
if callable(render_footer):
    render_footer()
else:
    st.caption("© 2026 Analytics207")
