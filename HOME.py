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
    page_title="🏀 ANALYTICS207 | Maine HS Hoops",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar_auth()
logout_button()

render_logo  = getattr(L, "render_logo",  None)
render_footer = getattr(L, "render_footer", None)

def _sp(n: int = 1) -> None:
    for _ in range(max(0, int(n))):
        st.write("")

def img_to_b64(path: str) -> str:
    data = Path(path).read_bytes()
    ext  = Path(path).suffix.lstrip(".")
    b64  = base64.b64encode(data).decode()
    return f"data:image/{ext};base64,{b64}"

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────

st.markdown("""
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

/* ── Pricing Cards ── */
.pricing-grid {
  display:grid; grid-template-columns:repeat(4,1fr); gap:16px;
  margin:24px 0;
}
.pricing-card {
  border-radius:18px; padding:24px 20px;
  font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
  position:relative; overflow:hidden;
}
.pricing-card-free     { background:rgba(15,23,42,0.6);   border:1px solid rgba(148,163,184,0.2); }
.pricing-card-monthly  { background:rgba(37,99,235,0.10); border:1px solid rgba(59,130,246,0.35); }
.pricing-card-season   { background:rgba(180,83,9,0.12);  border:1px solid rgba(245,158,11,0.45); }
.pricing-card-annual   { background:rgba(79,70,229,0.12); border:1px solid rgba(99,102,241,0.45); }
.pricing-badge {
  display:inline-block; padding:3px 10px; border-radius:999px;
  font-size:10px; font-weight:800; text-transform:uppercase;
  letter-spacing:.1em; margin-bottom:12px;
}
.badge-free    { background:rgba(148,163,184,0.15); color:#94a3b8; }
.badge-monthly { background:rgba(59,130,246,0.2);  color:#60a5fa; }
.badge-season  { background:rgba(245,158,11,0.2);  color:#fbbf24; }
.badge-annual  { background:rgba(99,102,241,0.2);  color:#a78bfa; }
.pricing-price {
  font-size:2rem; font-weight:900; line-height:1; margin-bottom:4px;
}
.pricing-period { font-size:12px; color:#64748b; margin-bottom:8px; }
.pricing-savings {
  font-size:11px; font-weight:700; color:#86efac;
  margin-bottom:14px; min-height:16px;
}
.pricing-features {
  font-size:12px; color:#94a3b8; line-height:1.8;
  border-top:1px solid rgba(255,255,255,0.07);
  padding-top:12px; margin-top:4px;
}
.pricing-features li { list-style:none; padding:0; }
.pricing-features li::before { content:"✓ "; color:#22c55e; font-weight:700; }
.pricing-cta {
  display:block; text-align:center; margin-top:16px;
  padding:8px 0; border-radius:999px;
  font-size:13px; font-weight:700; text-decoration:none;
}
.cta-free    { background:rgba(148,163,184,0.1); color:#94a3b8; border:1px solid rgba(148,163,184,0.2); }
.cta-monthly { background:rgba(59,130,246,0.2);  color:#93c5fd; border:1px solid rgba(59,130,246,0.4); }
.cta-season  { background:rgba(245,158,11,0.2);  color:#fcd34d; border:1px solid rgba(245,158,11,0.4); }
.cta-annual  { background:linear-gradient(135deg,#fb7185,#f97316); color:#111827; border:none; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

if callable(render_logo):
    render_logo()
_sp(1)

# ─────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────

season_start   = pd.Timestamp(year=2026, month=12, day=1)
days_to_tip    = max(0, (season_start.normalize() - pd.Timestamp.now().normalize()).days)

col_left, col_right = st.columns([1.4, 1.0], gap="large")

with col_left:
    st.markdown(f"""
<div class="a207-hero-card" style="position:relative;z-index:1;">
  <div class="a207-hero-tag">
    <span class="a207-hero-tag-dot"></span>
    <span>LIVE NOW · 2025–26 SEASON · MAINE HIGH SCHOOL HOOPS</span>
  </div>
  <div class="a207-hero-title">
    The model for Maine<br>high school basketball.
  </div>
  <div class="a207-hero-sub">
    Season-long ratings, matchup projections, bracket simulations, fan games,
    and team resume tools — built for coaches, media, and hardcore fans.
  </div>
  <div class="a207-hero-highlight">
    <span class="a207-hero-highlight-badge">FREE</span>
    <span>Fan Hub, Survivor, Stump The Model &amp; more — no account needed</span>
  </div>
  <div class="a207-hero-cta-row">
    <a href="/My_Account" target="_self" style="text-decoration:none;">
      <div class="a207-hero-cta-primary">
        <span>View plans &amp; pricing</span> <span>→</span>
      </div>
    </a>
    <div class="a207-hero-cta-secondary">
      Free forever · No credit card required
    </div>
  </div>
  <div class="a207-hero-social-proof">
    Used by coaches, media, and hoops diehards across Maine all season long.
  </div>
</div>
""", unsafe_allow_html=True)

with col_right:
    st.markdown("""
<div class="feat-card-shell">
  <div class="feat-card-header">
    <span class="feat-card-title">📋 2025–26 Season Report Card</span>
    <span class="feat-card-link">Model performance</span>
  </div>
  <div class="feat-card-body">
    How the prediction engine performed across all boys and girls games this season.
  </div>
  <div style="font-size:11px;color:#e5e7eb;">
    <ul style="padding-left:18px;margin:0;">
      <li><strong>965–191</strong> boys model record — <strong>83.5% accuracy</strong>.</li>
      <li><strong>974–184</strong> girls model record — <strong>84.1% accuracy</strong>.</li>
      <li>Combined favorite record over <strong>2,100+ games</strong> statewide.</li>
      <li>Average miss on the spread: <strong>13.2 pts MAE</strong>, <strong>17.0 pts RMSE</strong>.</li>
    </ul>
  </div>
  <div class="feat-card-footer">
    Full subscribers can explore every game and matchup behind these numbers.
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="height:12px;"></div>
<div class="feat-card-shell">
  <div class="feat-card-header">
    <span class="feat-card-title">🏟️ Fan Games — Free to Play</span>
    <span class="feat-card-link">No account needed</span>
  </div>
  <div class="feat-card-body">
    Jump in and compete with the community right now.
  </div>
  <div style="font-size:11px;color:#e5e7eb;">
    <ul style="padding-left:18px;margin:0;">
      <li>☠️ <strong>Survivor</strong> — pick one team per week, don't repeat.</li>
      <li>🤖 <strong>Fan vs. The Model</strong> — can you outpick the AI?</li>
      <li>🧠 <strong>Stump The Model</strong> — find the upsets it missed.</li>
      <li>💎 <strong>Pick 5 Challenge</strong> — weekly 5-team roster picks.</li>
    </ul>
  </div>
  <div class="feat-card-footer">
    All fan games are free — sign up for a leaderboard spot.
  </div>
</div>
""", unsafe_allow_html=True)

_sp(1)

# ─────────────────────────────────────────────
# PRICING STRIP
# ─────────────────────────────────────────────

st.markdown("### Plans & Pricing")

st.markdown("""
<div class="pricing-grid">

  <!-- FREE -->
  <div class="pricing-card pricing-card-free">
    <span class="pricing-badge badge-free">Free</span>
    <div class="pricing-price" style="color:#94a3b8;">$0</div>
    <div class="pricing-period">forever free</div>
    <div class="pricing-savings">&nbsp;</div>
    <ul class="pricing-features">
      <li>Fan Hub &amp; Community</li>
      <li>Fan vs. The Model</li>
      <li>Survivor</li>
      <li>Stump The Model</li>
      <li>Pick 5 Challenge</li>
      <li>Milestones &amp; Records</li>
      <li>Home Dashboard</li>
      <li>The Slate</li>
      <li>Heal Points</li>
      <li>Road Trip Planner</li>
      <li>Insights &amp; Trends</li>
    </ul>
    <a href="/My_Account" target="_self" class="pricing-cta cta-free">Create Free Account</a>
  </div>

  <!-- MONTHLY -->
  <div class="pricing-card pricing-card-monthly">
    <span class="pricing-badge badge-monthly">Monthly</span>
    <div class="pricing-price" style="color:#60a5fa;">$6.99</div>
    <div class="pricing-period">per month · cancel anytime</div>
    <div class="pricing-savings">&nbsp;</div>
    <ul class="pricing-features">
      <li>Everything in Free</li>
      <li>Full Power Index Rankings</li>
      <li>The Model — Predictions</li>
      <li>Bracketology</li>
      <li>Team Center</li>
      <li>The Aftermath</li>
      <li>The Projector</li>
      <li>The Press Box</li>
      <li>Trophy Room</li>
      <li>The Mover Board</li>
      <li>All-State Analytics</li>
    </ul>
    <a href="/My_Account" target="_self" class="pricing-cta cta-monthly">Subscribe Monthly</a>
  </div>

  <!-- SEASON PASS -->
  <div class="pricing-card pricing-card-season">
    <span class="pricing-badge badge-season">Season Pass</span>
    <div class="pricing-price" style="color:#fbbf24;">$19.99</div>
    <div class="pricing-period">one-time · December–March</div>
    <div class="pricing-savings">28.5% Savings vs Monthly!</div>
    <ul class="pricing-features">
      <li>Everything in Monthly</li>
      <li>Full season locked in</li>
      <li>No recurring billing</li>
      <li>Priority support</li>
    </ul>
    <a href="/My_Account" target="_self" class="pricing-cta cta-season">Buy Season Pass</a>
  </div>

  <!-- ANNUAL PASS -->
  <div class="pricing-card pricing-card-annual">
    <span class="pricing-badge badge-annual">Annual Pass</span>
    <div class="pricing-price" style="color:#a78bfa;">$49.99</div>
    <div class="pricing-period">one-time · full year access</div>
    <div class="pricing-savings">40.4% Savings vs Monthly!</div>
    <ul class="pricing-features">
      <li>Everything in Season Pass</li>
      <li>Full year locked in</li>
      <li>No recurring billing</li>
      <li>Priority support</li>
      <li>Early feature access</li>
    </ul>
    <a href="/My_Account" target="_self" class="pricing-cta cta-annual">Buy Annual Pass →</a>
  </div>

</div>
""", unsafe_allow_html=True)

_sp(1)

# ─────────────────────────────────────────────
# CAPABILITY EXAMPLES
# ─────────────────────────────────────────────

st.markdown("### What you unlock with a paid plan")

bracket_b64  = img_to_b64("web/static/home/bracket.png")
themodel_b64 = img_to_b64("web/static/home/themodel.png")
strength_b64 = img_to_b64("web/static/home/strength.png")

def feature_card_html(title: str, subtitle: str, img_b64: str, footer: str) -> str:
    return f"""
<div style="
  background:#020617; border-radius:18px;
  border:1px solid rgba(148,163,184,0.45); padding:10px;
  box-shadow:0 18px 30px rgba(15,23,42,0.85);
  font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
">
  <div style="
    border-radius:10px; border:1px solid rgba(148,163,184,0.55);
    padding:6px 10px; display:flex; align-items:center;
    justify-content:space-between; margin-bottom:8px;
  ">
    <span style="font-size:10px;font-weight:800;letter-spacing:.14em;
                 text-transform:uppercase;color:#f59e0b;">{title}</span>
    <span style="font-size:10px;color:rgba(148,163,184,0.7);">Example</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:8px;">{subtitle}</div>
  <div style="width:100%;height:220px;border-radius:10px;overflow:hidden;">
    <img src="{img_b64}" style="width:100%;height:100%;object-fit:cover;object-position:top;display:block;" />
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
# WHO IT'S FOR
# ─────────────────────────────────────────────

st.markdown("### Who Analytics207 is built for")

left, right = st.columns(2, gap="large")

with left:
    st.markdown("""
- Casual fans who just want to know who's actually good.
- Data nerds who refresh ratings like it's a hobby.
- Bracket junkies plotting chaos before it happens.
- Fans who want their voice heard through weekly voting.
- Communities tracking school milestones and historic runs.
- Competitors ready to test themselves in the Pick 5 challenge.
""")

with right:
    st.markdown("""
- See **true-strength rankings** for every team, not just win–loss.
- Get **projected scores and win chances** for any matchup.
- Explore **bracket paths** and "what-if" scenarios before the tourney.
- Track **team resumes**: quality wins, bad losses, and more.
- Participate in **fan voting** and see how public opinion compares to the model.
- Follow **school milestones** and benchmark seasons against history.
- Compete against others in the **Pick 5 Challenge** and climb the leaderboard.
""")

_sp(1)

# ─────────────────────────────────────────────
# BOTTOM CTA
# ─────────────────────────────────────────────

st.markdown("""
<div style="text-align:center;margin-top:8px;">
  <a href="/My_Account" target="_self" style="text-decoration:none;">
    <div class="a207-hero-cta-primary" style="display:inline-flex;margin-top:4px;">
      <span>Choose your plan and get started</span> <span>→</span>
    </div>
  </a>
</div>
""", unsafe_allow_html=True)

_sp(2)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

if callable(render_footer):
    render_footer()
else:
    st.caption("© 2026 Analytics207")
