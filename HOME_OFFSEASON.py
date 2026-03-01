from __future__ import annotations

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

# Layout helpers
render_logo = getattr(L, "render_logo", None)
render_footer = getattr(L, "render_footer", None)

def _sp(n: int = 1) -> None:
    for _ in range(max(0, int(n))):
        st.write("")

# ─────────────────────────────────────────────
# OFFSEASON STYLES
# ─────────────────────────────────────────────

st.markdown(
    """
<style>
.block-container { padding-top: 0.7rem; }

/* HERO */
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

/* Generic cards reused for examples */
.feat-card {
  background:#0f1e35; border:1px solid rgba(255,255,255,0.14);
  border-radius:14px; padding:12px 14px;
  display:flex; flex-direction:column; gap:8px;
  font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
  height:100%;
}
.feat-card:hover { border-color:rgba(245,158,11,0.55); }
.feat-card-header {
  display:flex; justify-content:space-between; align-items:center;
}
.feat-card-title {
  font-size:10px; font-weight:800; letter-spacing:.14em;
  text-transform:uppercase; color:#f59e0b;
}
.feat-card-link { font-size:10px; color:rgba(148,163,184,0.55); }
.feat-footer {
  font-size:9px; color:rgba(148,163,184,0.50);
  border-top:1px solid rgba(255,255,255,0.08);
  padding-top:6px; margin-top:2px;
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

season_start = pd.Timestamp(year=2026, month=12, day=1)  # adjust as needed
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
    # Offseason “season recap” summary
    st.markdown(
        """
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">📋 2025–26 Season Report Card</span>
    <span class="feat-card-link">Sample stats</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">
    A look at how the model performed last season across the state.
  </div>
  <div style="font-size:11px;color:#e5e7eb;">
    <ul style="padding-left:18px;margin:0;">
      <li>Hit rate of <strong>68%</strong> across 800+ games.</li>
      <li>Correctly projected <strong>11 of 14</strong> regional champions.</li>
      <li>Flagged <strong>4 double-digit seed upsets</strong> before they happened.</li>
    </ul>
  </div>
  <div class="feat-footer">
    Subscribers can deep dive into every game, bracket, and team from 2025–26.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

_sp(1)

# ─────────────────────────────────────────────
# CAPABILITY EXAMPLES (STATIC / SMALL)
# ─────────────────────────────────────────────

st.markdown("### What you unlock during the season")

ex1, ex2, ex3 = st.columns(3, gap="large")

with ex1:
    # Bracket engine example
    st.markdown(
        """
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">🏆 Bracket Engine</span>
    <span class="feat-card-link">Example</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">
    Auto-filled brackets with live scores, seeds, and model win chances.
  </div>
  <div style="height:120px;background:#020617;border-radius:10px;
              border:1px solid rgba(148,163,184,0.35);display:flex;
              align-items:center;justify-content:center;
              font-size:11px;color:rgba(148,163,184,0.7);">
    Bracket preview
  </div>
  <div class="feat-footer">Subscribers see every round update in real time.</div>
</div>
""",
        unsafe_allow_html=True,
    )

with ex2:
    # Matchup breakdown example
    st.markdown(
        """
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">📈 Matchup Breakdown</span>
    <span class="feat-card-link">Example</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">
    Projected score, win chance, and driver bars for any matchup.
  </div>
  <div style="height:120px;background:#020617;border-radius:10px;
              border:1px solid rgba(148,163,184,0.35);padding:8px;font-size:10px;">
    <div style="font-weight:800;color:#e5e7eb;margin-bottom:4px;">
      Central Aroostook vs Ashland (example)
    </div>
    <div style="font-size:10px;color:#fbbf24;margin-bottom:4px;">
      Model edge +12.5 · Win chance 78% · High confidence
    </div>
    <div style="height:6px;background:#111827;border-radius:999px;
                overflow:hidden;margin-bottom:4px;">
      <div style="width:78%;height:100%;background:#f97316;border-radius:999px;"></div>
    </div>
    <div style="font-size:9px;color:#9ca3af;">
      Driver bars for PIR, net efficiency, and recent form.
    </div>
  </div>
  <div class="feat-footer">Use it to prep, preview, or argue with friends.</div>
</div>
""",
        unsafe_allow_html=True,
    )

with ex3:
    # Team resume example
    st.markdown(
        """
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">📊 Team Resume</span>
    <span class="feat-card-link">Example</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">
    Strength-of-schedule, quality wins, and bad-loss filters on one page.
  </div>
  <div style="height:120px;background:#020617;border-radius:10px;
              border:1px solid rgba(148,163,184,0.35);padding:8px;font-size:10px;">
    <div style="display:flex;gap:6px;flex-wrap:wrap;">
      <div style="flex:1;min-width:90px;">
        <div style="font-size:9px;color:#9ca3af;">Top TI</div>
        <div style="font-size:16px;font-weight:900;color:#e5e7eb;">178.5</div>
        <div style="font-size:9px;color:#9ca3af;">Cony (example)</div>
      </div>
      <div style="flex:1;min-width:90px;">
        <div style="font-size:9px;color:#9ca3af;">Best win</div>
        <div style="font-size:16px;font-weight:900;color:#e5e7eb;">94.4%</div>
        <div style="font-size:9px;color:#9ca3af;">Camden Hills (example)</div>
      </div>
    </div>
  </div>
  <div class="feat-footer">Perfect for seeding debates and preview shows.</div>
</div>
""",
        unsafe_allow_html=True,
    )

_sp(1)

# ─────────────────────────────────────────────
# WHO IT'S FOR / BENEFITS
# ─────────────────────────────────────────────

st.markdown("### Who Analytics207 is built for")

left, right = st.columns(2, gap="large")

with left:
    st.markdown(
        """
- **Coaches** who want a fast read on opponents and bracket paths.
- **Media** who need clean numbers and storylines.
- **Hardcore fans** who live on the tournament pages all February.
"""
    )

with right:
    st.markdown(
        """
- See **true-strength rankings** for every team, not just win–loss.
- Get **projected scores and win chances** for any matchup.
- Explore **bracket paths** and “what-if” scenarios before the tourney.
- Track **team resumes**: quality wins, bad losses, and more.
"""
    )

_sp(1)

# ─────────────────────────────────────────────
# SIMPLE PRICING STRIP
# ─────────────────────────────────────────────

st.markdown("### Plans for the 2026–27 season")

p1, p2, p3 = st.columns(3, gap="large")

with p1:
    st.markdown(
        """
<div class="feat-card" style="border-color:rgba(245,158,11,0.6);box-shadow:0 0 0 1px rgba(245,158,11,0.35);">
  <div class="feat-card-header">
    <span class="feat-card-title">🏆 Season Pass</span>
    <span class="feat-card-link">$19.99</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">
    One-time payment for full 2026–27 access: rankings, projections, brackets, and all tools.
  </div>
  <div class="feat-footer">Best value for dedicated fans and staff.</div>
</div>
""",
        unsafe_allow_html=True,
    )

with p2:
    st.markdown(
        """
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">📅 Monthly</span>
    <span class="feat-card-link">$6.99/mo</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">
    Full access during the months you need it most. Cancel anytime.
  </div>
  <div class="feat-footer">Great for trying the platform mid-season.</div>
</div>
""",
        unsafe_allow_html=True,
    )

with p3:
    st.markdown(
        """
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">🆓 Free</span>
    <span class="feat-card-link">$0</span>
  </div>
  <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">
    Home dashboard, model record, and sample top-5 rankings so you can get a feel for the site.
  </div>
  <div class="feat-footer">Upgrade anytime from your account page.</div>
</div>
""",
        unsafe_allow_html=True,
    )

_sp(1)

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
