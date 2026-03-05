from __future__ import annotations

import base64
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from auth import logout_button
import layout as L
from sidebar_auth import render_sidebar_auth

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Analytics207 | Maine HS Basketball",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar_auth()
logout_button()

render_logo   = getattr(L, "render_logo",   None)
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
# GLOBAL STREAMLIT STYLE OVERRIDES
# (only things that affect Streamlit's own chrome)
# ─────────────────────────────────────────────

st.markdown("""
<style>
.block-container { padding-top: 0.5rem !important; padding-bottom: 0 !important; }
[data-testid="stPlotlyChart"] > div { padding-top: 0 !important; }
.js-plotly-plot .plotly, .js-plotly-plot .plotly div { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER / LOGO
# ─────────────────────────────────────────────

if callable(render_logo):
    render_logo()

# ─────────────────────────────────────────────
# SHARED CSS — injected into every components.html block
# ─────────────────────────────────────────────

SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { background: transparent; font-family: 'Barlow', sans-serif; color: #e2e8f0; }

/* ── TICKER ── */
.a207-ticker {
  background: rgba(15,23,42,0.97);
  border-bottom: 1px solid rgba(251,191,36,0.2);
  padding: 0.5rem 0;
  overflow: hidden;
}
.a207-ticker-inner {
  display: flex;
  gap: 3rem;
  animation: ticker-scroll 32s linear infinite;
  white-space: nowrap;
  width: max-content;
}
.a207-ticker-inner:hover { animation-play-state: paused; }
@keyframes ticker-scroll {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
.a207-ticker-item {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a3b8;
}
.a207-ticker-item strong { color: #fbbf24; }

/* ── HERO ── */
.a207-hero {
  position: relative;
  min-height: 400px;
  border-radius: 24px;
  overflow: hidden;
  margin: 1rem 0 1.5rem 0;
  display: flex;
  align-items: center;
  padding: 2.5rem 3rem;
  background: #020617;
}
.a207-hero-bg {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 0% 0%,   rgba(59,130,246,0.45), transparent),
    radial-gradient(ellipse 60% 50% at 100% 0%,  rgba(244,114,182,0.32), transparent),
    radial-gradient(ellipse 50% 70% at 50% 100%, rgba(34,197,94,0.12),   transparent);
  mix-blend-mode: screen;
}
.a207-hero-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse 80% 80% at 30% 50%, black 40%, transparent 100%);
}
.a207-hero-content { position: relative; z-index: 2; max-width: 560px; }

.a207-eyebrow {
  display: inline-flex; align-items: center; gap: 0.5rem;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.7rem; letter-spacing: 0.22em; text-transform: uppercase;
  color: #7dd3fc; margin-bottom: 0.9rem;
}
.a207-eyebrow-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 0 4px rgba(74,222,128,0.3);
  animation: pulse 2s ease infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(74,222,128,0.3); }
  50%       { box-shadow: 0 0 0 8px rgba(74,222,128,0.1); }
}

.a207-headline {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 3.8rem; font-weight: 900;
  line-height: 0.95; letter-spacing: -0.01em;
  text-transform: uppercase;
  color: #f8fafc; margin-bottom: 1rem;
}
.a207-headline em {
  font-style: normal;
  background: linear-gradient(135deg, #fbbf24, #fb7185);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.a207-sub {
  font-size: 1rem; color: #cbd5e1; line-height: 1.65;
  margin-bottom: 1.3rem; max-width: 450px;
}

.a207-accuracy-strip { display: flex; gap: 0.65rem; flex-wrap: wrap; margin-bottom: 1.4rem; }
.a207-pill {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.32rem 0.85rem; border-radius: 999px;
  background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.32);
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.85rem; font-weight: 700; color: #86efac;
}
.a207-pill .num { font-size: 1.05rem; font-weight: 900; color: #4ade80; }

.a207-cta-row { display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; }
.a207-btn-primary {
  display: inline-flex; align-items: center; gap: 0.5rem;
  padding: 0.62rem 1.5rem; border-radius: 999px;
  background: linear-gradient(135deg, #fb7185, #f97316);
  color: #0f172a; text-decoration: none;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.95rem; font-weight: 800;
  letter-spacing: 0.06em; text-transform: uppercase;
  box-shadow: 0 4px 18px rgba(251,113,133,0.4);
  transition: transform 0.15s, box-shadow 0.15s;
}
.a207-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(251,113,133,0.55);
}
.a207-btn-ghost {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.6rem 1.3rem; border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.3);
  background: rgba(15,23,42,0.5);
  color: #94a3b8; text-decoration: none;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.88rem; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase;
}
.a207-trust { margin-top: 1rem; font-size: 0.73rem; color: #475569; }

/* HERO RIGHT PANEL */
.a207-hero-panel {
  position: absolute; right: 2rem; top: 50%; transform: translateY(-50%);
  z-index: 2; display: flex; flex-direction: column; gap: 0.7rem; width: 250px;
}
.a207-stat-card {
  background: rgba(15,23,42,0.85);
  border: 1px solid rgba(148,163,184,0.13);
  border-radius: 14px; padding: 0.85rem 1rem;
  backdrop-filter: blur(12px);
}
.a207-stat-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.63rem; letter-spacing: 0.18em;
  text-transform: uppercase; color: #64748b; margin-bottom: 0.2rem;
}
.a207-stat-value {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 1.85rem; font-weight: 900; line-height: 1; color: #f8fafc;
}
.a207-stat-sub { font-size: 0.7rem; color: #64748b; margin-top: 0.15rem; }
.accent { color: #4ade80; }
.gold   { color: #fbbf24; }

/* ── RHYTHM STRIP ── */
.a207-rhythm {
  background: rgba(251,191,36,0.05);
  border: 1px solid rgba(251,191,36,0.18);
  border-radius: 16px; padding: 1.1rem 1.4rem;
  display: flex; align-items: center; gap: 1.4rem; flex-wrap: wrap;
  margin-bottom: 1.8rem;
}
.a207-rhythm-icon { font-size: 1.8rem; flex-shrink: 0; }
.a207-rhythm-text { flex: 1; }
.a207-rhythm-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 1rem; font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.06em; color: #fbbf24; margin-bottom: 0.2rem;
}
.a207-rhythm-body { font-size: 0.85rem; color: #94a3b8; line-height: 1.5; }
.a207-rhythm-days { display: flex; gap: 0.35rem; }
.a207-day {
  width: 32px; height: 32px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em;
}
.a207-day.on  { background: rgba(251,191,36,0.18); border: 1px solid rgba(251,191,36,0.45); color: #fbbf24; }
.a207-day.off { background: rgba(15,23,42,0.5);    border: 1px solid rgba(148,163,184,0.08); color: #1e293b; }

/* ── SECTION HEADERS ── */
.sec-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.68rem; letter-spacing: 0.22em; text-transform: uppercase;
  color: #fbbf24; margin-bottom: 0.3rem;
}
.sec-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 1.9rem; font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.02em; color: #f8fafc; margin-bottom: 0.25rem;
}
.sec-sub { font-size: 0.88rem; color: #64748b; margin-bottom: 1.4rem; }

/* ── FEATURE GRID ── */
.feat-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 0.9rem; margin-bottom: 1.8rem;
}
.feat-card {
  background: rgba(15,23,42,0.65);
  border: 1px solid rgba(148,163,184,0.1);
  border-radius: 16px; padding: 1.1rem 1.2rem;
  transition: border-color 0.2s, transform 0.2s;
}
.feat-card:hover { border-color: rgba(251,191,36,0.28); transform: translateY(-3px); }
.feat-icon  { font-size: 1.5rem; margin-bottom: 0.55rem; }
.feat-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.92rem; font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.1em; color: #f8fafc; margin-bottom: 0.3rem;
}
.feat-body  { font-size: 0.8rem; color: #64748b; line-height: 1.55; }
.feat-tier  {
  display: inline-block; margin-top: 0.65rem;
  padding: 0.13rem 0.55rem; border-radius: 999px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.63rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
}
.tier-free    { background: rgba(148,163,184,0.1);  color: #94a3b8; border: 1px solid rgba(148,163,184,0.18); }
.tier-paid    { background: rgba(96,165,250,0.1);   color: #60a5fa; border: 1px solid rgba(96,165,250,0.22); }
.tier-coaches { background: rgba(251,191,36,0.1);   color: #fbbf24; border: 1px solid rgba(251,191,36,0.28); }

/* ── PERSONA CARDS ── */
.persona-card {
  background: rgba(15,23,42,0.5);
  border: 1px solid rgba(148,163,184,0.09);
  border-radius: 13px; padding: 1rem 1.1rem; margin-bottom: 0.7rem;
}
.persona-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.82rem; font-weight: 800; text-transform: uppercase;
  letter-spacing: 0.1em; color: #f8fafc; margin-bottom: 0.2rem;
}
.persona-body { font-size: 0.78rem; color: #64748b; line-height: 1.5; }

/* ── BOTTOM CTA ── */
.bottom-cta {
  background: radial-gradient(ellipse 80% 100% at 50% 0%, rgba(59,130,246,0.18), transparent);
  border: 1px solid rgba(148,163,184,0.12);
  border-radius: 24px; padding: 3rem 2rem;
  text-align: center; margin-top: 0.5rem;
}
.bottom-cta-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 2.6rem; font-weight: 900; text-transform: uppercase;
  letter-spacing: 0.02em; color: #f8fafc; margin-bottom: 0.45rem;
}
.bottom-cta-sub { font-size: 0.9rem; color: #64748b; margin-bottom: 1.4rem; }
.center { display: flex; justify-content: center; }
</style>
"""

# ─────────────────────────────────────────────
# BLOCK 1 — TICKER + HERO + RHYTHM + FEATURES
# ─────────────────────────────────────────────

ticker_items = [
    "🏀 <strong>Boys Model</strong> &nbsp;·&nbsp; 965–191 &nbsp;·&nbsp; <strong>83.5% Accuracy</strong>",
    "🏀 <strong>Girls Model</strong> &nbsp;·&nbsp; 974–184 &nbsp;·&nbsp; <strong>84.1% Accuracy</strong>",
    "📊 <strong>2,100+ Games</strong> Tracked Statewide This Season",
    "⚡ <strong>Updated Mon–Sat</strong> &nbsp;·&nbsp; Every Game. Every Score. Every Shift.",
    "🏆 <strong>Trophy Room</strong> &nbsp;·&nbsp; 20 Live Trophies &nbsp;·&nbsp; Updated Every Night",
    "🎯 <strong>Spread Accuracy</strong> &nbsp;·&nbsp; 13.2 pts MAE &nbsp;·&nbsp; 17.0 pts RMSE",
    "☠️ <strong>Survivor</strong> &nbsp;·&nbsp; Pick One Team Per Week &nbsp;·&nbsp; Don't Repeat",
    "🤖 <strong>Fan vs. The Model</strong> &nbsp;·&nbsp; Can You Outpick the AI?",
]
doubled_ticker = " &nbsp;&nbsp;&nbsp; ".join(ticker_items * 2)

components.html(SHARED_CSS + f"""
<!-- TICKER -->
<div class="a207-ticker">
  <div class="a207-ticker-inner">
    <span class="a207-ticker-item">{doubled_ticker}</span>
  </div>
</div>

<!-- HERO -->
<div class="a207-hero">
  <div class="a207-hero-bg"></div>
  <div class="a207-hero-grid"></div>

  <div class="a207-hero-content">
    <div class="a207-eyebrow">
      <span class="a207-eyebrow-dot"></span>
      <span>2025–26 Season · Maine High School Hoops</span>
    </div>
    <div class="a207-headline">
      Maine's Basketball Model.</em>
    </div>
    <div class="a207-sub">
      Six days a week, every score, every shift in the rankings —
      Analytics207 tracks all of Maine high school basketball so you
      never miss a moment that matters.
    </div>
    <div class="a207-accuracy-strip">
      <div class="a207-pill"><span class="num">83.5%</span> Boys Accuracy</div>
      <div class="a207-pill"><span class="num">84.1%</span> Girls Accuracy</div>
      <div class="a207-pill"><span class="num">2,100+</span> Games</div>
    </div>
    <div class="a207-cta-row">
      <a href="/My_Account" target="_self" class="a207-btn-primary">Create free account →</a>
      <a href="/My_Account" target="_self" class="a207-btn-ghost">View plans</a>
    </div>
    <div class="a207-trust">Free forever · No credit card required · Used by coaches and media across Maine</div>
  </div>

  <div class="a207-hero-panel">
    <div class="a207-stat-card">
      <div class="a207-stat-label">Season Record · Boys</div>
      <div class="a207-stat-value">965<span style="color:#334155;font-size:1.1rem;">–191</span></div>
      <div class="a207-stat-sub"><span class="accent">83.5%</span> prediction accuracy</div>
    </div>
    <div class="a207-stat-card">
      <div class="a207-stat-label">Season Record · Girls</div>
      <div class="a207-stat-value">974<span style="color:#334155;font-size:1.1rem;">–184</span></div>
      <div class="a207-stat-sub"><span class="accent">84.1%</span> prediction accuracy</div>
    </div>
    <div class="a207-stat-card">
      <div class="a207-stat-label">🏆 Trophy Room</div>
      <div class="a207-stat-value gold" style="font-size:1.2rem;">Live Tonight</div>
      <div class="a207-stat-sub">20 trophies · updated every night automatically</div>
    </div>
  </div>
</div>

<!-- RHYTHM STRIP -->
<div class="a207-rhythm">
  <div class="a207-rhythm-icon">📡</div>
  <div class="a207-rhythm-text">
    <div class="a207-rhythm-title">Updated Six Days a Week — All Season Long</div>
    <div class="a207-rhythm-body">
      Every game night, Analytics207 scrapes results, recalculates rankings, updates Heal Points,
      reassigns trophies, and refreshes predictions — automatically. No manual updates. No delays.
      Fresh data every morning.
    </div>
  </div>
  <div class="a207-rhythm-days">
    <div class="a207-day on">MON</div>
    <div class="a207-day on">TUE</div>
    <div class="a207-day on">WED</div>
    <div class="a207-day on">THU</div>
    <div class="a207-day on">FRI</div>
    <div class="a207-day on">SAT</div>
    <div class="a207-day off">SUN</div>
  </div>
</div>

<!-- FEATURE GRID -->
<div class="sec-label">What's Inside</div>
<div class="sec-title">Everything Maine Basketball</div>
<div class="sec-sub">From live Heal Points to bracket simulations — built for fans, media, and coaches.</div>

<div class="feat-grid">
  <div class="feat-card">
    <div class="feat-icon">🤖</div>
    <div class="feat-title">The Model</div>
    <div class="feat-body">Projected scores, win probabilities, spreads, and confidence ratings for every matchup statewide.</div>
    <span class="feat-tier tier-paid">Subscriber</span>
  </div>
  <div class="feat-card">
    <div class="feat-icon">🏆</div>
    <div class="feat-title">Trophy Room</div>
    <div class="feat-body">20 live trophies across 20 metrics. Trophy holders change every night as results come in.</div>
    <span class="feat-tier tier-paid">Subscriber</span>
  </div>
  <div class="feat-card">
    <div class="feat-icon">💊</div>
    <div class="feat-title">Heal Points</div>
    <div class="feat-body">The official MPA ranking metric — tracked, visualized, and updated daily throughout the season.</div>
    <span class="feat-tier tier-free">Free</span>
  </div>
  <div class="feat-card">
    <div class="feat-icon">🏀</div>
    <div class="feat-title">Team Center</div>
    <div class="feat-body">Deep team dashboards — offense, defense, margins, strength of schedule, road records, and more.</div>
    <span class="feat-tier tier-paid">Subscriber</span>
  </div>
  <div class="feat-card">
    <div class="feat-icon">🏆</div>
    <div class="feat-title">Bracketology</div>
    <div class="feat-body">Auto-seeded brackets with live scores and model win chances for every tournament path.</div>
    <span class="feat-tier tier-paid">Subscriber</span>
  </div>
  <div class="feat-card">
    <div class="feat-icon">🔭</div>
    <div class="feat-title">Scouting Report</div>
    <div class="feat-body">Advanced matchup analytics — margin buckets, rest &amp; recovery, opponent tiers, late-season skew, and more.</div>
    <span class="feat-tier tier-coaches">Coaches</span>
  </div>
  <div class="feat-card">
    <div class="feat-icon">☠️</div>
    <div class="feat-title">Survivor</div>
    <div class="feat-body">Pick one team per week. Never repeat. Last fan standing wins bragging rights as Maine's best basketball mind.</div>
    <span class="feat-tier tier-free">Free</span>
  </div>
  <div class="feat-card">
    <div class="feat-icon">🤖</div>
    <div class="feat-title">Fan vs. The Model</div>
    <div class="feat-body">Can you outpick an analytics engine that's right 83% of the time? Compete weekly on the leaderboard.</div>
    <span class="feat-tier tier-free">Free</span>
  </div>
  <div class="feat-card">
    <div class="feat-icon">🚗</div>
    <div class="feat-title">Road Trip</div>
    <div class="feat-body">Track every mile traveled, longest trips, road records, and bus hours logged across the season.</div>
    <span class="feat-tier tier-free">Free</span>
  </div>
</div>
""", height=1400, scrolling=False)

# ─────────────────────────────────────────────
# BLOCK 2 — PRICING SECTION HEADER
# ─────────────────────────────────────────────

components.html(SHARED_CSS + """
<div class="sec-label">Pricing</div>
<div class="sec-title">Plans &amp; Pricing</div>
<div class="sec-sub">Start free. Upgrade when you're ready. No credit card required for the free tier.</div>
""", height=100, scrolling=False)

# ─────────────────────────────────────────────
# BLOCK 3 — DOT MATRIX CHART (Plotly — stays as st)
# ─────────────────────────────────────────────

_features = [
    ("🏟️ Fan Hub",                True,  True,  True,  True),
    ("🤖 Fan vs. The Model",       True,  True,  True,  True),
    ("☠️ Survivor",                True,  True,  True,  True),
    ("🧠 Stump The Model",         True,  True,  True,  True),
    ("💎 Pick 5 Challenge",        True,  True,  True,  True),
    ("📋 The Slate",               True,  True,  True,  True),
    ("💊 Heal Points",             True,  True,  True,  True),
    ("🏅 Milestones & Records",    True,  True,  True,  True),
    ("📈 Insights & Trends",       True,  True,  True,  True),
    ("🚗 Road Trip Planner",       True,  True,  True,  True),
    ("⚡ Power Index Rankings",    False, True,  True,  True),
    ("🤖 The Model – Predictions", False, True,  True,  True),
    ("📊 The Aftermath",           False, True,  True,  True),
    ("🏀 Team Center",             False, True,  True,  True),
    ("🏆 Bracketology",            False, True,  True,  True),
    ("📋 Report Card",             False, True,  True,  True),
    ("🥇 Trophy Room",             False, True,  True,  True),
    ("🗳️ Team of the Week",       False, True,  True,  True),
    ("📉 The Mover Board",         False, True,  True,  True),
    ("⭐ All-State Analytics",     False, True,  True,  True),
    ("📰 The Press Box",           False, True,  True,  True),
    ("🔭 Scouting Report",         False, False, False, False),
]

feat_names = [f[0] for f in _features]
feat_data  = [f[1:] for f in _features]
feat_rev   = list(reversed(feat_names))
data_rev   = list(reversed(feat_data))

_plan_colors = [
    "rgba(148,163,184,0.85)",
    "rgba(96,165,250,0.95)",
    "rgba(251,191,36,0.95)",
    "rgba(167,139,250,0.95)",
]
_plan_names = ["Free", "Monthly", "Season Pass", "Annual Pass"]

dot_fig = go.Figure()
for pi in range(4):
    xf, yf, xe, ye = [], [], [], []
    for fi, row in enumerate(data_rev):
        if row[pi]: xf.append(pi); yf.append(fi)
        else:       xe.append(pi); ye.append(fi)
    if xf:
        dot_fig.add_trace(go.Scatter(
            x=xf, y=yf, mode="markers",
            marker=dict(size=13, color=_plan_colors[pi],
                        line=dict(width=1, color="rgba(255,255,255,0.2)")),
            name=_plan_names[pi],
            hovertemplate=f"<b>{_plan_names[pi]}</b><br>%{{customdata}}<extra></extra>",
            customdata=[feat_rev[i] for i in yf],
        ))
    if xe:
        dot_fig.add_trace(go.Scatter(
            x=xe, y=ye, mode="markers",
            marker=dict(size=13, color="rgba(15,23,42,0.9)",
                        line=dict(width=1, color="rgba(148,163,184,0.08)")),
            hovertemplate="<b>Not included</b><br>%{customdata}<extra></extra>",
            customdata=[feat_rev[i] for i in ye],
            showlegend=False,
        ))

dot_fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="'Barlow Condensed', ui-sans-serif, sans-serif", color="#cbd5e1", size=13),
    xaxis=dict(
        tickvals=list(range(4)),
        ticktext=[
            "<b>Free</b><br><span style='font-size:11px;color:#94a3b8;'>account req.</span>",
            "<b>Monthly</b><br><span style='font-size:11px;color:#86efac;'>$6.99/mo</span>",
            "<b>Season Pass</b><br><span style='font-size:11px;color:#86efac;'>$19.99 · 28% off</span>",
            "<b>Annual Pass</b><br><span style='font-size:11px;color:#86efac;'>$49.99 · 40% off</span>",
        ],
        side="top", showgrid=False, zeroline=False,
        tickfont=dict(size=13), title_text="", fixedrange=True,
        range=[-0.6, 3.6],
    ),
    yaxis=dict(
        tickvals=list(range(len(feat_names))),
        ticktext=feat_rev,
        showgrid=True, gridcolor="rgba(255,255,255,0.04)",
        zeroline=False, tickfont=dict(size=12),
        title_text="", autorange=True, fixedrange=True,
    ),
    legend=dict(
        orientation="h", yanchor="top", y=-0.02,
        xanchor="center", x=0.5,
        font=dict(size=12), bgcolor="rgba(0,0,0,0)",
        itemsizing="constant",
    ),
    margin=dict(l=185, r=20, t=80, b=50),
    height=620,
    dragmode=False,
)

price_left, price_right = st.columns([1.6, 1.0], gap="large")

with price_left:
    st.plotly_chart(dot_fig, use_container_width=True, config={
        "displayModeBar": False,
        "staticPlot": False,
    })

with price_right:
    components.html(SHARED_CSS + """
<style>
.plan-box {
  background: rgba(15,23,42,0.85);
  border: 1px solid rgba(148,163,184,0.13);
  border-radius: 20px; padding: 20px 18px;
  margin-top: 60px;
}
.plan-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.63rem; font-weight: 800;
  letter-spacing: 0.2em; text-transform: uppercase;
  color: #fbbf24; margin-bottom: 14px;
}
.plan-btn {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.44rem 1rem; border-radius: 999px; margin-bottom: 8px;
  text-decoration: none; font-size: 0.82rem; font-weight: 600;
  font-family: 'Barlow', sans-serif;
}
.plan-btn.free    { background: rgba(148,163,184,0.08); border: 1px solid rgba(148,163,184,0.2);  color: #94a3b8; }
.plan-btn.monthly { background: rgba(59,130,246,0.1);   border: 1px solid rgba(59,130,246,0.3);   color: #60a5fa; }
.plan-btn.season  { background: rgba(251,191,36,0.1);   border: 1px solid rgba(251,191,36,0.32);  color: #fbbf24; }
.plan-btn.annual  {
  background: linear-gradient(135deg,#fb7185,#f97316); border: none;
  color: #0f172a;
  font-family: 'Barlow Condensed', sans-serif; font-size: 0.88rem;
  font-weight: 800; letter-spacing: 0.04em; text-transform: uppercase;
  box-shadow: 0 4px 14px rgba(251,113,133,0.35); margin-bottom: 14px;
}
.plan-fine {
  font-size: 10px; color: #475569; line-height: 1.9;
  border-top: 1px solid rgba(255,255,255,0.06); padding-top: 11px;
}
</style>
<div class="plan-box">
  <div class="plan-label">🌟 Choose Your Plan</div>
  <a href="/My_Account" target="_self" class="plan-btn free">
    <span>Free Pass</span><span style="font-size:.74rem;opacity:.7;">$0 · always free</span>
  </a>
  <a href="/My_Account" target="_self" class="plan-btn monthly">
    <span>Monthly Pass</span><span style="font-size:.74rem;">$6.99/mo</span>
  </a>
  <a href="/My_Account" target="_self" class="plan-btn season">
    <span>🏆 Season Pass</span><span style="font-size:.74rem;">$19.99 · 28% off</span>
  </a>
  <a href="/My_Account" target="_self" class="plan-btn annual">
    <span>🌟 Annual — Best Value</span><span style="font-size:.76rem;">$49.99 · 40% off</span>
  </a>
  <div class="plan-fine">
    ✓ Every feature unlocked on any paid plan<br>
    ✓ No recurring billing on Season &amp; Annual<br>
    ✓ Early feature access on Annual<br>
    ✓ Free tier never requires a credit card
  </div>
</div>
""", height=380, scrolling=False)

# ─────────────────────────────────────────────
# BLOCK 4 — WHO IT'S FOR + BOTTOM CTA
# ─────────────────────────────────────────────

components.html(SHARED_CSS + """
<div class="sec-label">Audience</div>
<div class="sec-title">Built for Everyone in the 207</div>
<div class="sec-sub">Whether you're a die-hard fan, a coach hunting an edge, or a parent tracking your kid's school.</div>

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.9rem;margin-bottom:2rem;">

  <div>
    <div class="persona-card">
      <div class="persona-title">🏀 The Die-Hard Fan</div>
      <div class="persona-body">You refresh rankings like it's a hobby. You have opinions about every Class C North seed. Analytics207 was built for you.</div>
    </div>
    <div class="persona-card">
      <div class="persona-title">👨‍👩‍👧 The Hoops Parent</div>
      <div class="persona-body">Follow your kid's school all season. Track every game, every Heal Point update, every milestone. Free to sign up.</div>
    </div>
  </div>

  <div>
    <div class="persona-card">
      <div class="persona-title">🏆 The Bracket Junkie</div>
      <div class="persona-body">You're plotting chaos before seedings drop. Our Bracketology engine runs simulations all season so you're always ready.</div>
    </div>
    <div class="persona-card">
      <div class="persona-title">🎮 The Competitor</div>
      <div class="persona-body">Survivor, Fan vs. The Model, Pick 5 — if there's a leaderboard, you want to be on it. All free with an account.</div>
    </div>
  </div>

  <div>
    <div class="persona-card">
      <div class="persona-title">📋 The Coach</div>
      <div class="persona-body">See how your team stacks up statewide. Strength of schedule, opponent tier performance, Heal Point trajectory — your edge.</div>
    </div>
    <div class="persona-card">
      <div class="persona-title">📰 Media &amp; Press</div>
      <div class="persona-body">Power rankings, model predictions, rivalry data — everything you need to tell the story of Maine basketball all season long.</div>
    </div>
  </div>

</div>

<!-- BOTTOM CTA -->
<div class="bottom-cta">
  <div class="bottom-cta-title">Ready for next season?</div>
  <div class="bottom-cta-sub">Free forever · No credit card required · The 207's home for Maine basketball analytics</div>
  <div class="center">
    <a href="/My_Account" target="_self" class="a207-btn-primary">Create your free account →</a>
  </div>
</div>
""", height=620, scrolling=False)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

_sp(1)
if callable(render_footer):
    render_footer()
else:
    st.caption("© 2026 Analytics207")
