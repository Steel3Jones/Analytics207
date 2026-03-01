from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from auth import logout_button
import layout as L
from sidebar_auth import render_sidebar_auth

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="🏀 ANALYTICS207 | Offseason Home",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar_auth()
logout_button()

render_logo = getattr(L, "render_logo", None)
render_footer = getattr(L, "render_footer", None)


def _sp(n: int = 1) -> None:
    for _ in range(max(0, int(n))):
        st.write("")


def img_to_b64(path: str) -> str:
    data = Path(path).read_bytes()
    ext = Path(path).suffix.lstrip(".")
    b64 = base64.b64encode(data).decode()
    return f"data:image/{ext};base64,{b64}"


# ─────────────────────────────────────────────
# OFFSEASON STYLES
# ─────────────────────────────────────────────

st.markdown(
    """
<style>
.block-container { padding-top: 0.7rem; }

.a207-hero-card {
  position:relative; border-radius:24px; padding:1.5rem 1.6rem;
  background:radial-gradient(circle at 0% 0%,#020617,#020617);
  box-shadow:0 28px 50px rgba(15,23,42,0.95),inset 0 0 0 1px rgba(148,163,184,0.35);
  color:#e5e7eb; margin-bottom:1.6rem; overflow:hidden;
}
.a207-hero-card::before {
  content:""; position:absolute; inset:-40%;
  background:
    radial-gradient(circle at 5% 0%,rgba(59,130,246,0.50),transparent 60%),
    radial-gradient(circle at 75% 0%,rgba(244,114,182,0.42),transparent 60%),
    radial-gradient(circle at 100% 40%,rgba(34,197,94,0.28),transparent 60%);
  mix-blend-mode:screen; opacity:0.95; pointer-events:none;
}
.a207-hero-tag {
  font-size:.78rem; letter-spacing:.18em; text-transform:uppercase;
  color:#a5b4fc; margin-bottom:.35rem;
  display:inline-flex; align-items:center; gap:.4rem;
}
.a207-hero-tag-dot {
  width:8px; height:8px; border-radius:999px; background:#4ade80;
  box-shadow:0 0 0 4px rgba(74,222,128,0.40);
}
.a207-hero-title {
  font-size:2rem; line-height:1.1; font-weight:800;
  letter-spacing:.02em; margin-bottom:.35rem;
}
.a207-hero-sub {
  font-size:.95rem; color:#e5e7eb; max-width:32rem; margin-bottom:.7rem;
}
.a207-hero-highlight {
  display:inline-flex; align-items:center; gap:.45rem;
  padding:.28rem .75rem; border-radius:999px;
  border:1px solid rgba(248,250,252,0.5);
  background:rgba(15,23,42,0.9); font-size:.8rem; margin-bottom:.8rem;
}
.a207-hero-highlight-badge {
  padding:.08rem .45rem; border-radius:999px;
  background:rgba(34,197,94,0.30); color:#86efac;
  font-size:.72rem; text-transform:uppercase; letter-spacing:.12em;
}
.a207-hero-pricing-row {
  display:flex; align-items:center; gap:.9rem; margin-bottom:.7rem; flex-wrap:wrap;
}
.a207-hero-price-main { font-size:1.5rem; font-weight:800; }
.a207-hero-price-sub  { font-size:.78rem; color:#9ca3af; }
.a207-hero-cta-row    { display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; }
.a207-hero-cta-primary {
  display:inline-flex; align-items:center; gap:.5rem;
  padding:.4rem 1.1rem; border-radius:999px;
  border:1px solid rgba(251,113,133,1);
  background:linear-gradient(135deg,#fb7185,#f97316);
  color:#111827; font-size:.86rem; font-weight:700; cursor:pointer;
}
.a207-hero-cta-secondary { font-size:.8rem; color:#9ca3af; }
.a207-hero-social-proof  { margin-top:.55rem; font-size:.75rem; color:#9ca3af; }

.feat-card-shell {
  background:#0f1e35; border:1px solid rgba(255,255,255,0.14);
  border-radius:14px; padding:12px 14px;
  font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
}
.feat-card-header {
  display:flex; justify-content:space-between; align-items:center;
  margin-bottom:6px;
}
.feat-card-title {
  font-size:10px; font-weight:800; letter-spacing:.14em;
  text-transform:uppercase; color:#f59e0b;
}
.feat-card-link { font-size:10px; color:rgba(148,163,184,0.55); }
.feat-card-body { font-size:11px; color:#cbd5e1; margin-bottom:6px; }
.feat-card-footer {
  font-size:9px; color:rgba(148,163,184,0.60);
  border-top:1px solid rgba(255,255,255,0.08);
  padding-top:6px; margin-top:6px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

if callable(render_logo):
    render_logo()
_sp(1)

# ─────────────────────────────────────────────
# HERO (OFFSEASON)
# ─────────────────────────────────────────────

season_start = pd.Timestamp(year=2026, month=12, day=1)
days_to_tip = max(0, (season_start.normalize() - pd.Timestamp.now().normalize()).days)

col_left, col_right = st.columns([1.4, 1.0], gap="large")

with col_left:
    st.markdown(
        f"""
<div class="a207-hero-card" style="position:relative;z-index:1;">
  <div class="a207-hero-tag">
    <span class="a207-hero-tag-dot"></span>
    <span>OFFSEASON LAB · 2025–26 RECAP · 2026–27 PREVIEW</span>
  </div>
  <div class="a207-hero-title">
    Be ready on opening night.<br>The model for Maine high school hoops.
  </div>
  <div class="a207-hero-sub">
    Season-long ratings, matchup projections, bracket simulations, and team
    resume tools built for coaches, media, and hardcore fans.
  </div>
  <div class="a207-hero-highlight">
    <span class="a207-hero-highlight-badge">COUNTDOWN</span>
    <span>Tip-off in <strong>{days_to_tip} days</strong></span>
  </div>
  <div class="a207-hero-pricing-row">
    <div>
      <div class="a207-hero-price-main">Season Pass — $19.99</div>
      <div class="a207-hero-price-sub">
        One pass for the entire 2026–27 season: every ranking, prediction, and bracket tool.
      </div>
    </div>
  </div>
  <div class="a207-hero-cta-row">
    <a href="/My_Account" target="_self" style="text-decoration:none;">
      <div class="a207-hero-cta-primary">
        <span>Get ready for 2026–27</span> <span>→</span>
      </div>
    </a>
    <div class="a207-hero-cta-secondary">
      Or create a free account to explore top-5 rankings and sample tools.
    </div>
  </div>
  <div class="a207-hero-social-proof">
    Used by coaches, media, and hoops diehards across Maine all season long.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with col_right:
    st.markdown(
        """
<div class="feat-card-shell">
  <div class="feat-card-header">
    <span class="feat-card-title">📋 2025–26 Season Report Card</span>
    <span class="feat-card-link">Model performance</span>
  </div>
  <div class="feat-card-body">
    How the prediction engine performed across all boys and girls games last season.
  </div>
  <div style="font-size:11px;color:#e5e7eb;">
    <ul style="padding-left:18px;margin:0;">
      <li><strong>965–191</strong> boys model record — <strong>83.5% accuracy</strong>.</li>
      <li><strong>974–184</strong> girls model record — <strong>84.1% accuracy</strong>.</li>
      <li>Combined favorite record over <strong>2,100+ games</strong> statewide.</li>
      <li>Average miss on the spread: <strong>13.2 points MAE</strong>, <strong>17.0 points RMSE</strong>.</li>
    </ul>
  </div>
  <div class="feat-card-footer">
    Full subscribers can explore every game and matchup behind these numbers.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div style="height:12px;"></div>
<div class="feat-card-shell">
  <div class="feat-card-header">
    <span class="feat-card-title">📰 Latest from the Blog</span>
    <span class="feat-card-link">Coming soon</span>
  </div>
  <div class="feat-card-body">
    Deep dives on rankings, tournament paths, and model explainers.
  </div>
  <div style="font-size:11px;color:#e5e7eb;">
    <ul style="padding-left:18px;margin:0;">
      <li>Preseason 2026–27 Power Index sneak peek.</li>
      <li>How the model rated last year's biggest upsets.</li>
      <li>Class A North: early bracket storylines.</li>
    </ul>
  </div>
  <div class="feat-card-footer">
    These will link directly to new posts as they're published.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

_sp(1)

# ─────────────────────────────────────────────
# CAPABILITY EXAMPLES — base64 images inside HTML
# ─────────────────────────────────────────────

st.markdown("### What you unlock during the season")

bracket_b64  = img_to_b64("web/static/home/bracket.png")
themodel_b64 = img_to_b64("web/static/home/themodel.png")
strength_b64 = img_to_b64("web/static/home/strength.png")


def feature_card_html(title: str, subtitle: str, img_b64: str, footer: str) -> str:
    return f"""
<div style="
  background:#020617;
  border-radius:18px;
  border:1px solid rgba(148,163,184,0.45);
  padding:10px;
  box-shadow:0 18px 30px rgba(15,23,42,0.85);
  font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
">
  <div style="
    border-radius:10px;
    border:1px solid rgba(148,163,184,0.55);
    padding:6px 10px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin-bottom:8px;
  ">
    <span style="font-size:10px;font-weight:800;letter-spacing:.14em;
                 text-transform:uppercase;color:#f59e0b;">{title}</span>
    <span style="font-size:10px;color:rgba(148,163,184,0.7);">Example</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:8px;">{subtitle}</div>
  <div style="
    width:100%;
    height:220px;
    border-radius:10px;
    overflow:hidden;
  ">
    <img src="{img_b64}"
         style="width:100%;height:100%;object-fit:cover;object-position:top;display:block;" />
  </div>
  <div style="font-size:9px;color:rgba(148,163,184,0.6);
              border-top:1px solid rgba(255,255,255,0.08);
              padding-top:6px;margin-top:8px;">
    {footer}
  </div>
</div>
"""


ex1, ex2, ex3 = st.columns(3, gap="large")

with ex1:
    st.markdown(feature_card_html(
        title="🏆 BRACKET ENGINE",
        subtitle="Auto-filled brackets with live scores, seeds, and model win chances.",
        img_b64=bracket_b64,
        footer="Subscribers see every round update in real time.",
    ), unsafe_allow_html=True)

with ex2:
    st.markdown(feature_card_html(
        title="📈 MATCHUP BREAKDOWN",
        subtitle="Projected score, win chance, and driver bars for any matchup.",
        img_b64=themodel_b64,
        footer="Use it to prep, preview, or argue with friends.",
    ), unsafe_allow_html=True)

with ex3:
    st.markdown(feature_card_html(
        title="📊 TEAM RESUME",
        subtitle="Strength & resume tools: quality wins, bad losses, and more.",
        img_b64=strength_b64,
        footer="Perfect for seeding debates and preview shows.",
    ), unsafe_allow_html=True)

_sp(1)

# ─────────────────────────────────────────────
# WHO IT'S FOR / BENEFITS
# ─────────────────────────────────────────────

st.markdown("### Who Analytics207 is built for")

left, right = st.columns(2, gap="large")

with left:
    st.markdown(
        """
- Casual fans who just want to know who’s actually good.
- Data nerds who refresh ratings like it’s a hobby.
- Bracket junkies plotting chaos before it happens.
- Fans who want their voice heard through weekly voting.
- Communities tracking school milestones and historic runs.
- Competitors ready to test themselves in the Pick 5 challenge.
"""
    )

with right:
    st.markdown(
        """
- See **true-strength rankings** for every team, not just win–loss.
- Get **projected scores and win chances** for any matchup.
- Explore **bracket paths** and "what-if" scenarios before the tourney.
- Track **team resumes**: quality wins, bad losses, and more.
- Participate in **fan voting** and see how public opinion compares to the model.
- Follow **school milestones** and benchmark seasons against history.
- Compete against others in the **Pick 5 Challenge** and climb the leaderboard.
"""
    )

_sp(1)

_sp(1)

# ─────────────────────────────────────────────
# SIMPLE PRICING STRIP
# ─────────────────────────────────────────────



st.markdown(
    """
<div style="text-align:center;margin-top:8px;">
  <a href="/My_Account" target="_self" style="text-decoration:none;">
    <div class="a207-hero-cta-primary" style="display:inline-flex;margin-top:4px;">
      <span>Choose your plan and lock in 2026–27</span> <span>→</span>
    </div>
  </a>
</div>
""",
    unsafe_allow_html=True,
)

_sp(2)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

if callable(render_footer):
    render_footer()
else:
    st.caption("© 2026 Analytics207")
