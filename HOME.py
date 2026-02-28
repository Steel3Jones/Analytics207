from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from auth import login_gate, logout_button, is_subscribed

import layout as L
from components.home_card import inject_home_card_css

from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="🏀 ANALYTICS207 | Home",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_ROOT = Path(__file__).resolve().parent

DATA_DIR = APP_ROOT / "data"

inject_home_card_css()

# ── SIDEBAR AUTH — top of sidebar, above page nav ──
with st.sidebar:
    if "user" in st.session_state and st.session_state["user"]:
        profile = st.session_state.get("profile", {}) or {}
        name = profile.get("display_name", "User")
        st.markdown(f"👤 **{name}**")
        if st.button("Log Out", key="sidebar_logout_top"):
            from auth import get_supabase
            try:
                get_supabase().auth.sign_out()
            except Exception:
                pass
            for k in ["user", "session", "profile"]:
                st.session_state[k] = None
            st.rerun()
    else:
        login_gate(required=False)

# ─────────────────────────────────────────────
# TEAM KEY PARSER
# ─────────────────────────────────────────────

_KEY_RE = re.compile(r"^(.+?)(Boys|Girls)(A|B|C|D|S)(North|South)$")

def parse_team_key(key: str) -> dict:
    m = _KEY_RE.match(str(key).strip())
    if m:
        return dict(name=m.group(1).strip(), gender=m.group(2), cls=m.group(3), region=m.group(4))
    return dict(name=str(key).strip(), gender="", cls="", region="")


# ─────────────────────────────────────────────
# LAYOUT HELPERS
# ─────────────────────────────────────────────

def _pick(*names: str) -> Optional[Callable]:
    for n in names:
        fn = getattr(L, n, None)
        if callable(fn):
            return fn
    return None

render_logo   = _pick("render_logo",        "renderlogo")
render_header = _pick("render_page_header", "renderpageheader")
render_footer = _pick("render_footer",      "renderfooter")
spacer        = _pick("spacer",             "spacerlines")

def _sp(n: int = 1) -> None:
    if callable(spacer):
        try:
            spacer(n)
            return
        except Exception:
            pass
    for _ in range(max(0, int(n))):
        st.write("")


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def load_all():
    def safe(path):
        try:
            return pd.read_parquet(path) if Path(path).exists() else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    teams = safe(DATA_DIR / "core"        / "teams_team_season_analytics_v50.parquet")
    games = safe(DATA_DIR / "public"      / "games_public_v50.parquet")
    preds = safe(DATA_DIR / "predictions" / "games_predictions_current.parquet")
    pir   = safe(DATA_DIR / "core"        / "teams_power_index_v50.parquet")

    for col in ["Team", "Gender", "Class", "Region", "TeamKey"]:
        if col in teams.columns:
            teams[col] = teams[col].astype(str).str.strip()
    if "Gender" in teams.columns:
        teams["Gender"] = teams["Gender"].str.title()
    if "Class" in teams.columns:
        teams["Class"] = teams["Class"].str.upper().str.replace("CLASS", "", regex=False).str.strip()
    if "Region" in teams.columns:
        teams["Region"] = teams["Region"].str.title()
    for col in ["TI", "NetEff", "PPG", "OPPG", "MarginPG", "WinPct", "Wins", "Losses"]:
        if col in teams.columns:
            teams[col] = pd.to_numeric(teams[col], errors="coerce")
    if {"Wins", "Losses"}.issubset(teams.columns) and "Record" not in teams.columns:
        teams["Record"] = (
            teams["Wins"].fillna(0).astype(int).astype(str) + "-" +
            teams["Losses"].fillna(0).astype(int).astype(str)
        )

    if not games.empty:
        games["Date"]   = pd.to_datetime(games["Date"], errors="coerce")
        games["Played"] = games.get("Played", False).fillna(False).astype(bool)
        for col in ["HomeKey", "AwayKey", "Home", "Away", "Gender"]:
            if col in games.columns:
                games[col] = games[col].astype(str).str.strip()
        for col in ["HomeScore", "AwayScore"]:
            if col in games.columns:
                games[col] = pd.to_numeric(games[col], errors="coerce")

    if not preds.empty:
        for col in ["HomeKey", "AwayKey"]:
            if col in preds.columns:
                preds[col] = preds[col].astype(str).str.strip()
        for col in ["PredHomeWinProb", "PredHomeScore", "PredAwayScore", "PredMargin", "GameID"]:
            if col in preds.columns:
                preds[col] = pd.to_numeric(preds[col], errors="coerce")

    if not pir.empty:
        for col in ["TeamKey", "Gender"]:
            if col in pir.columns:
                pir[col] = pir[col].astype(str).str.strip()
        if "Gender" in pir.columns:
            pir["Gender"] = pir["Gender"].str.title()
        if "PowerIndex_Display" in pir.columns:
            pir["PowerIndex_Display"] = pd.to_numeric(pir["PowerIndex_Display"], errors="coerce")
        parsed = pir["TeamKey"].apply(lambda k: pd.Series(parse_team_key(k)))
        pir["Team"]   = parsed["name"]
        pir["Class"]  = parsed["cls"]
        pir["Region"] = parsed["region"]

    return teams, games, preds, pir

teams_df, games_df, preds_df, pir_df = load_all()


# ─────────────────────────────────────────────
# TEAM NAME CLEANER
# ─────────────────────────────────────────────

_key_to_name: dict[str, str] = {}
if not teams_df.empty and {"TeamKey", "Team"}.issubset(teams_df.columns):
    _key_to_name = dict(zip(
        teams_df["TeamKey"].astype(str).str.strip(),
        teams_df["Team"].astype(str).str.strip(),
    ))

def clean_name(row: pd.Series) -> str:
    key = str(row.get("TeamKey", "")).strip()
    if key and key in _key_to_name:
        return _key_to_name[key]
    return parse_team_key(key)["name"]


# ─────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────

def tonight_games() -> pd.DataFrame:
    if games_df.empty:
        return pd.DataFrame()
    today = pd.Timestamp.now().normalize()
    mask  = (games_df["Date"] == today) & (~games_df["Played"])
    return games_df[mask].copy()

def get_pred(home_key: str, away_key: str) -> Optional[pd.Series]:
    if preds_df.empty:
        return None
    rows = preds_df[
        ((preds_df["HomeKey"] == home_key) & (preds_df["AwayKey"] == away_key)) |
        ((preds_df["HomeKey"] == away_key) & (preds_df["AwayKey"] == home_key))
    ].sort_values("GameID", ascending=False)
    return rows.iloc[0] if not rows.empty else None

def last_night_record() -> tuple[int, int]:
    if games_df.empty:
        return 0, 0
    yesterday = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)
    played    = games_df[(games_df["Date"] == yesterday) & (games_df["Played"])].copy()
    if played.empty:
        return 0, 0
    correct, total = 0, 0
    for _, g in played.iterrows():
        hk = str(g.get("HomeKey", ""))
        ak = str(g.get("AwayKey", ""))
        p  = get_pred(hk, ak)
        if p is None:
            continue
        hs  = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
        as_ = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
        if pd.isna(hs) or pd.isna(as_):
            continue
        stored_home_is_hk = (str(p.get("HomeKey", "")) == hk)
        prob_home = float(p.get("PredHomeWinProb", 0.5))
        if not stored_home_is_hk:
            prob_home = 1.0 - prob_home
        pred_home_wins   = prob_home >= 0.5
        actual_home_wins = float(hs) > float(as_)
        total   += 1
        correct += int(pred_home_wins == actual_home_wins)
    return correct, total

def top_pir_teams(gender: str, n: int = 5) -> pd.DataFrame:
    if pir_df.empty or "PowerIndex_Display" not in pir_df.columns:
        return pd.DataFrame()
    sub = pir_df[pir_df["Gender"] == gender.title()].copy()
    sub = sub.sort_values("PowerIndex_Display", ascending=False).head(n).reset_index(drop=True)
    sub["_DisplayName"] = sub["Team"].astype(str).str.strip()
    return sub

def top_ti_teams(gender: str, n: int = 5) -> pd.DataFrame:
    if teams_df.empty or "TI" not in teams_df.columns:
        return pd.DataFrame()
    sub = teams_df[teams_df["Gender"] == gender.title()].copy()
    sub = sub.sort_values("TI", ascending=False).head(n).reset_index(drop=True)
    sub["_DisplayName"] = sub["Team"].astype(str).str.strip()
    return sub

def featured_game() -> Optional[dict]:
    tonight = tonight_games()
    if tonight.empty:
        return None
    best_game, best_diff = None, 999.0
    for _, g in tonight.iterrows():
        hk = str(g.get("HomeKey", ""))
        ak = str(g.get("AwayKey", ""))
        p  = get_pred(hk, ak)
        if p is None:
            continue
        stored_home_is_hk = (str(p.get("HomeKey", "")) == hk)
        prob = float(p.get("PredHomeWinProb", 0.5))
        prob_home = prob if stored_home_is_hk else 1.0 - prob
        diff = abs(prob_home - 0.5)
        if diff < best_diff:
            best_diff = diff
            sh = float(p.get("PredHomeScore", np.nan))
            sa = float(p.get("PredAwayScore", np.nan))
            mg = float(p.get("PredMargin",    np.nan))
            if not stored_home_is_hk:
                sh, sa = sa, sh
                mg = -mg if pd.notna(mg) else mg
            best_game = dict(
                home=str(g.get("Home", hk)), away=str(g.get("Away", ak)),
                prob_home=prob_home, prob_away=1.0 - prob_home,
                score_h=sh, score_a=sa, margin=mg,
                gender=str(g.get("Gender", "")),
            )
    return best_game

def upset_watch() -> list[dict]:
    tonight = tonight_games()
    upsets  = []
    for _, g in tonight.iterrows():
        hk = str(g.get("HomeKey", ""))
        ak = str(g.get("AwayKey", ""))
        p  = get_pred(hk, ak)
        if p is None:
            continue
        stored_home_is_hk = (str(p.get("HomeKey", "")) == hk)
        prob = float(p.get("PredHomeWinProb", 0.5))
        prob_home = prob if stored_home_is_hk else 1.0 - prob
        dog_prob  = min(prob_home, 1.0 - prob_home)
        if dog_prob >= 0.35:
            upsets.append(dict(
                home=str(g.get("Home", hk)), away=str(g.get("Away", ak)),
                dog_prob=dog_prob,
            ))
    return sorted(upsets, key=lambda x: -x["dog_prob"])[:4]

def top_tonight_games(n: int = 10) -> list[dict]:
    tonight = tonight_games()
    results = []
    for _, g in tonight.iterrows():
        hk   = str(g.get("HomeKey", ""))
        ak   = str(g.get("AwayKey", ""))
        home = str(g.get("Home", hk))
        away = str(g.get("Away", ak))
        p    = get_pred(hk, ak)
        if p is None:
            continue
        stored_home_is_hk = (str(p.get("HomeKey", "")) == hk)
        prob = float(p.get("PredHomeWinProb", 0.5))
        prob_home = prob if stored_home_is_hk else 1.0 - prob
        sh = float(p.get("PredHomeScore", np.nan))
        sa = float(p.get("PredAwayScore", np.nan))
        if not stored_home_is_hk:
            sh, sa = sa, sh
        fav_prob = max(prob_home, 1.0 - prob_home)
        diff     = abs(prob_home - 0.5)
        results.append(dict(
            home=home, away=away,
            prob_home=prob_home, prob_away=1.0 - prob_home,
            fav_prob=fav_prob, diff=diff,
            score_h=sh, score_a=sa,
            gender=str(g.get("Gender", "")),
            cls=str(g.get("HomeClass", g.get("AwayClass", ""))),
        ))
    results.sort(key=lambda x: x["diff"])
    return results[:n]


# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
.block-container { padding-top: 0.7rem; }
/* AAU sidebar separator */
[data-testid="stSidebarNav"] ul li:nth-last-child(3)::before {
    content: "🏀  AAU (BETA)";
    display: block;
    font-size: 10px;
    font-weight: 800;
    color: rgba(245,158,11,0.7);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 14px 0 6px 12px;
    margin-top: 6px;
    border-top: 1px solid rgba(245,158,11,0.25);
    pointer-events: none;
}
/* ── MOVE auth expander ABOVE page nav ── */
[data-testid="stSidebarContent"] {
    display: flex;
    flex-direction: column;
}
[data-testid="stSidebarContent"] [data-testid="stSidebarNav"] {
    order: 2;
}
[data-testid="stSidebarContent"] > div:not([data-testid="stSidebarNav"]) {
    order: 1;
}

/* ── HERO ── */
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

/* ── FEATURED GAME ── */
.featured-game {
    background:linear-gradient(135deg,rgba(245,158,11,0.14),rgba(59,130,246,0.14));
    border:1px solid rgba(245,158,11,0.45); border-radius:16px;
    padding:16px 18px; height:100%;
    font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
}
.featured-eyebrow {
    font-size:10px; font-weight:800; letter-spacing:.18em;
    text-transform:uppercase; color:#f59e0b; margin-bottom:10px;
}
.featured-teams { font-size:20px; font-weight:900; color:#ffffff; margin-bottom:4px; }
.featured-score { font-size:26px; font-weight:900; color:#fde047; margin-bottom:6px; }
.featured-bar-wrap {
    height:8px; border-radius:999px; overflow:hidden;
    background:rgba(239,68,68,0.30); margin-bottom:4px;
}
.featured-bar-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#60a5fa,#3b82f6); }

/* ── FEAT CARDS ── */
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
.feat-row {
    display:flex; align-items:center; gap:8px;
    padding:5px 6px; border-radius:8px; margin-bottom:2px;
    background:rgba(255,255,255,0.04);
    border:1px solid rgba(255,255,255,0.06);
}
.feat-rank { color:#fbbf24; font-size:10px; font-weight:800; min-width:18px; }
.feat-name { color:#ffffff; font-size:12px; font-weight:700; flex:1;
             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.feat-val  { color:#fde047; font-size:11px; font-weight:800; }
.feat-sub  { color:rgba(203,213,225,0.55); font-size:10px; }
.feat-badge {
    font-size:8px; font-weight:800; letter-spacing:.10em; text-transform:uppercase;
    padding:2px 6px; border-radius:999px;
    background:rgba(148,163,184,0.12); color:rgba(203,213,225,0.6);
    border:1px solid rgba(148,163,184,0.2);
}
.feat-footer {
    font-size:9px; color:rgba(148,163,184,0.50);
    border-top:1px solid rgba(255,255,255,0.08);
    padding-top:6px; margin-top:2px;
}

/* ── TONIGHT BOARD (top 10) ── */
.tonight-board {
    background:#0b1526; border:1px solid rgba(255,255,255,0.10);
    border-radius:20px; padding:18px 20px; margin-bottom:20px;
    font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
}
.tonight-header {
    display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;
}
.tonight-title {
    font-size:12px; font-weight:800; letter-spacing:.14em;
    text-transform:uppercase; color:#f59e0b;
}
.tonight-game {
    border-radius:12px; padding:10px 14px; margin-bottom:8px;
    border-left:4px solid transparent;
    font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
}
.tonight-game-tossup  { background:rgba(168,85,247,0.12); border-left-color:#a855f7; }
.tonight-game-close   { background:rgba(245,158,11,0.10); border-left-color:#f59e0b; }
.tonight-game-leaning { background:rgba(59,130,246,0.10); border-left-color:#3b82f6; }
.tonight-game-lock    { background:rgba(34,197,94,0.08);  border-left-color:#22c55e; }
.tonight-matchup { font-size:13px; font-weight:800; color:#ffffff; margin-bottom:6px; }
.tonight-meta    { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.tonight-fav     { font-size:11px; font-weight:700; color:#fde68a; }
.tonight-score   { font-size:11px; color:rgba(203,213,225,0.55); }
.tonight-badge {
    font-size:8px; font-weight:800; letter-spacing:.12em; text-transform:uppercase;
    padding:2px 8px; border-radius:999px;
}
.badge-tossup  { background:rgba(168,85,247,0.25); color:#d8b4fe; border:1px solid rgba(168,85,247,0.5); }
.badge-close   { background:rgba(245,158,11,0.25); color:#fde68a; border:1px solid rgba(245,158,11,0.5); }
.badge-leaning { background:rgba(59,130,246,0.25); color:#93c5fd; border:1px solid rgba(59,130,246,0.5); }
.badge-lock    { background:rgba(34,197,94,0.25);  color:#86efac; border:1px solid rgba(34,197,94,0.5); }

/* ── BAR inside board ── */
.prob-bar-wrap {
    height:5px; border-radius:999px; overflow:hidden;
    background:rgba(239,68,68,0.25); margin-top:6px;
}
.prob-bar-fill { height:100%; border-radius:999px; }
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

correct, total = last_night_record()
last_night_s   = f"{correct}-{total - correct}" if total > 0 else "—"
last_night_pct = f"{correct / total * 100:.0f}%" if total > 0 else "—"
feat           = featured_game()

col_left, col_right = st.columns([1.2, 1.6], gap="large")

with col_left:
    st.markdown(f"""
<div style="position:relative;z-index:1;">
  <div class="a207-hero-tag">
    <span class="a207-hero-tag-dot"></span>
    <span>LIVE SEASON 2025–26 · RATINGS. PREDICTIONS. EDGES.</span>
  </div>
  <div class="a207-hero-title">
    Every game, every edge,<br>🧠 The model for the entire state.
  </div>
  <div class="a207-hero-sub">
    True Strength ratings, projected scores, and calculated spreads
    driven by real data — updated every single night.
  </div>
  <div class="a207-hero-highlight">
    <span class="a207-hero-highlight-badge">LAST NIGHT</span>
    <span>Model went <strong>{last_night_s}</strong> &nbsp;·&nbsp; {last_night_pct} accuracy</span>
  </div>
  <div class="a207-hero-pricing-row">
  <div>
    <div class="a207-hero-price-main">Free Beta · 2025–26 season</div>
    <div class="a207-hero-price-sub">
      Live test launch — features may evolve as we tune the models.
    </div>
  </div>
</div>
<div class="a207-hero-cta-row">
  <div class="a207-hero-cta-primary">
    <span>Free Beta · 2025–26 season</span> <span></span>
  </div>
  <div class="a207-hero-cta-secondary">
    Brackets, rankings, and projections — updated nightly during the beta.
  </div>
</div>

  <div class="a207-hero-social-proof">
    Trusted by coaches, media, and hoops sickos across Maine.
  </div>
</div>
""", unsafe_allow_html=True)

with col_right:
    if feat:
        prob_h  = feat["prob_home"]
        prob_a  = feat["prob_away"]
        score_s = (f"{feat['score_h']:.0f} – {feat['score_a']:.0f}"
                   if pd.notna(feat["score_h"]) and pd.notna(feat["score_a"]) else "—")
        bar_w   = f"{prob_h * 100:.1f}%"
        fav     = feat["home"] if prob_h >= 0.5 else feat["away"]
        fav_pct = f"{max(prob_h, prob_a) * 100:.0f}%"
        conf    = ("HIGH CONFIDENCE"   if max(prob_h, prob_a) >= 0.75 else
                   "MEDIUM CONFIDENCE" if max(prob_h, prob_a) >= 0.60 else "TOSS-UP")
        conf_color = "#22c55e" if "HIGH" in conf else ("#f59e0b" if "MEDIUM" in conf else "#a855f7")

        st.markdown(f"""
<div class="featured-game">
  <div class="featured-eyebrow">🔥 FEATURED MATCHUP TONIGHT · CLOSEST GAME ON THE BOARD</div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
    <div>
      <div class="featured-teams">{feat['away']} at {feat['home']}</div>
      <div style="font-size:11px;color:rgba(203,213,225,0.5);margin-bottom:10px;">
        {feat.get('gender','')} · Model: <strong style="color:#fde68a;">{fav} wins {fav_pct}</strong>
      </div>
    </div>
    <div style="text-align:right;">
      <div class="featured-score">{score_s}</div>
      <div style="font-size:9px;color:rgba(148,163,184,0.4);">projected final</div>
    </div>
  </div>
  <div class="featured-bar-wrap">
    <div class="featured-bar-fill" style="width:{bar_w};"></div>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:9px;
              color:rgba(148,163,184,0.4);margin-bottom:10px;">
    <span>{feat['home']} {prob_h * 100:.0f}%</span>
    <span>{feat['away']} {prob_a * 100:.0f}%</span>
  </div>
  <span style="background:{conf_color}22;border:1px solid {conf_color}66;
               color:{conf_color};font-size:9px;font-weight:800;letter-spacing:.12em;
               text-transform:uppercase;padding:3px 10px;border-radius:999px;">
    {conf}
  </span>
  <span style="font-size:9px;color:rgba(148,163,184,0.3);margin-left:10px;">
    🤖 Prediction Engine
  </span>
</div>
</body></html>
""", height=320, scrolling=False)

    else:
        # Pull some quick stats for the graphic
        total_teams = len(teams_df) if not teams_df.empty else 0
        total_games = len(games_df[games_df["Played"] == True]) if not games_df.empty else 0
        top_boy  = top_ti_teams("Boys",  1)
        top_girl = top_ti_teams("Girls", 1)
        top_boy_name  = str(top_boy.iloc[0]["_DisplayName"])  if not top_boy.empty  else "—"
        top_girl_name = str(top_girl.iloc[0]["_DisplayName"]) if not top_girl.empty else "—"
        top_boy_ti    = f'{top_boy.iloc[0]["TI"]:.2f}'        if not top_boy.empty  else "—"
        top_girl_ti   = f'{top_girl.iloc[0]["TI"]:.2f}'       if not top_girl.empty else "—"

        components.html(f"""<!DOCTYPE html><html><head><meta charset="utf-8"/></head><body style="margin:0;background:transparent;">
<div style="
  background:linear-gradient(135deg,rgba(15,23,42,0.95),rgba(9,18,34,0.98));
  border:1px solid rgba(255,255,255,0.09); border-radius:16px;
  padding:20px 22px; height:100%;
  font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
  position:relative; overflow:hidden;
">
  <!-- background glow -->
  <div style="position:absolute;inset:0;pointer-events:none;
    background:radial-gradient(ellipse at 20% 50%,rgba(59,130,246,0.12),transparent 60%),
               radial-gradient(ellipse at 80% 50%,rgba(245,158,11,0.10),transparent 60%);"></div>

  <div style="position:relative;z-index:1;">
    <div style="font-size:10px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;
                color:rgba(245,158,11,0.8);margin-bottom:14px;">
      📊 Season At A Glance
    </div>

    <!-- Big stat row -->
    <div style="display:flex;gap:12px;margin-bottom:16px;">
      <div style="flex:1;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                  border-radius:10px;padding:10px 12px;text-align:center;">
        <div style="font-size:28px;font-weight:900;color:#60a5fa;">{total_teams}</div>
        <div style="font-size:9px;color:rgba(148,163,184,0.5);text-transform:uppercase;letter-spacing:.1em;margin-top:2px;">Teams</div>
      </div>
      <div style="flex:1;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                  border-radius:10px;padding:10px 12px;text-align:center;">
        <div style="font-size:28px;font-weight:900;color:#34d399;">{total_games}</div>
        <div style="font-size:9px;color:rgba(148,163,184,0.5);text-transform:uppercase;letter-spacing:.1em;margin-top:2px;">Games Played</div>
      </div>
      <div style="flex:1;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                  border-radius:10px;padding:10px 12px;text-align:center;">
        <div style="font-size:28px;font-weight:900;color:#f59e0b;">5</div>
        <div style="font-size:9px;color:rgba(148,163,184,0.5);text-transform:uppercase;letter-spacing:.1em;margin-top:2px;">Classes</div>
      </div>
    </div>

    <!-- Top ranked teams -->
    <div style="font-size:9px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;
                color:rgba(148,163,184,0.4);margin-bottom:8px;">Current #1 Ranked Teams</div>

    <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);
                border-radius:10px;padding:10px 12px;margin-bottom:6px;
                display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-size:9px;color:rgba(245,158,11,0.6);font-weight:700;letter-spacing:.1em;text-transform:uppercase;">🏀 Boys #1</div>
        <div style="font-size:14px;font-weight:800;color:#f1f5f9;margin-top:2px;">{top_boy_name}</div>
      </div>
      <div style="font-size:18px;font-weight:900;color:#fde68a;">{top_boy_ti}</div>
    </div>

    <div style="background:rgba(168,85,247,0.08);border:1px solid rgba(168,85,247,0.2);
                border-radius:10px;padding:10px 12px;
                display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-size:9px;color:rgba(168,85,247,0.7);font-weight:700;letter-spacing:.1em;text-transform:uppercase;">🏀 Girls #1</div>
        <div style="font-size:14px;font-weight:800;color:#f1f5f9;margin-top:2px;">{top_girl_name}</div>
      </div>
      <div style="font-size:18px;font-weight:900;color:#d8b4fe;">{top_girl_ti}</div>
    </div>

    <div style="margin-top:12px;font-size:9px;color:rgba(148,163,184,0.3);text-align:center;">
      No games tonight · Check back tomorrow for predictions
    </div>
  </div>
</div>
</body></html>
""", height=320, scrolling=False)

_sp(1)

# ─────────────────────────────────────────────
# TONIGHT'S TOP 10 BOARD


top_games = top_tonight_games(10)

board_col, chart_col = st.columns([1.1, 1.0], gap="large")

with board_col:
    st.markdown(f"""
<div class="tonight-board" style="padding-bottom:4px;">
  <div class="tonight-header">
    <span class="tonight-title">🗓️ Tonight's Top 10 Matchups</span>
    <span style="font-size:10px;color:rgba(148,163,184,0.4);">
      Ranked by game closeness · 🧠 Model picks
    </span>
  </div>
""", unsafe_allow_html=True)

    if not top_games:
        st.markdown("""
  <div style="color:rgba(148,163,184,0.4);font-size:12px;padding:10px 0 14px;">
    No games scheduled tonight.
  </div>
""", unsafe_allow_html=True)
    else:
        cards_html = ""
        for g in top_games:
            prob_h   = g["prob_home"]
            fav_prob = g["fav_prob"]
            sh, sa   = g["score_h"], g["score_a"]
            score_s  = f"{sh:.0f}–{sa:.0f}" if pd.notna(sh) and pd.notna(sa) else "—"
            fav_name = g["home"] if prob_h >= 0.5 else g["away"]
            fav_pct  = f"{fav_prob * 100:.0f}%"
            bar_w    = f"{prob_h * 100:.1f}%"

            if fav_prob < 0.57:
                game_cls, badge_cls, badge_lbl = "tonight-game-tossup",  "badge-tossup",  "TOSS-UP"
            elif fav_prob < 0.67:
                game_cls, badge_cls, badge_lbl = "tonight-game-close",   "badge-close",   "CLOSE GAME"
            elif fav_prob < 0.80:
                game_cls, badge_cls, badge_lbl = "tonight-game-leaning", "badge-leaning", "LEANING"
            else:
                game_cls, badge_cls, badge_lbl = "tonight-game-lock",    "badge-lock",    "LOCK 🔒"

            bar_color = (
                "linear-gradient(90deg,#a855f7,#7c3aed)" if fav_prob < 0.57 else
                "linear-gradient(90deg,#f59e0b,#d97706)" if fav_prob < 0.67 else
                "linear-gradient(90deg,#3b82f6,#1d4ed8)" if fav_prob < 0.80 else
                "linear-gradient(90deg,#22c55e,#15803d)"
            )

            meta_tag = ""
            if g["gender"] or g["cls"]:
                parts = [x for x in [g["gender"], f"Class {g['cls']}" if g["cls"] else ""] if x]
                meta_tag = f'<span style="font-size:10px;color:rgba(148,163,184,0.4);">{" · ".join(parts)}</span>'

            cards_html += f"""
<div class="tonight-game {game_cls}">
  <div class="tonight-matchup">{g['away']} <span style="color:rgba(148,163,184,0.4);font-weight:400;">at</span> {g['home']}</div>
  <div class="tonight-meta">
    <span class="tonight-fav">{fav_name} {fav_pct}</span>
    <span class="tonight-score">proj {score_s}</span>
    <span class="tonight-badge {badge_cls}">{badge_lbl}</span>
    {meta_tag}
  </div>
  <div class="prob-bar-wrap">
    <div class="prob-bar-fill" style="width:{bar_w};background:{bar_color};"></div>
  </div>
</div>"""

        st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

with chart_col:
    st.markdown("""
<div style="font-size:12px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;
            color:#f59e0b;margin-bottom:10px;">
  📊 Win Probability Chart — Tonight
</div>
""", unsafe_allow_html=True)

    if top_games:
        labels     = [f"{g['away'][:13]} vs {g['home'][:13]}" for g in top_games]
        home_probs = [round(g["prob_home"] * 100, 1) for g in top_games]
        away_probs = [round(g["prob_away"] * 100, 1) for g in top_games]

        def bar_color_fn(p: float) -> str:
            if p >= 80: return "#22c55e"
            if p >= 67: return "#3b82f6"
            if p >= 57: return "#f59e0b"
            return "#a855f7"

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Home Win%",
            y=labels,
            x=home_probs,
            orientation="h",
            marker=dict(color=[bar_color_fn(p) for p in home_probs], opacity=0.9),
            text=[f"{p:.0f}%" for p in home_probs],
            textposition="inside",
            textfont=dict(color="white", size=11, family="ui-sans-serif"),
        ))
        fig.add_trace(go.Bar(
            name="Away Win%",
            y=labels,
            x=[-p for p in away_probs],
            orientation="h",
            marker=dict(color=[bar_color_fn(p) for p in away_probs], opacity=0.45),
            text=[f"{p:.0f}%" for p in away_probs],
            textposition="inside",
            textfont=dict(color="white", size=11, family="ui-sans-serif"),
        ))
        fig.update_layout(
            barmode="overlay",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0", family="ui-sans-serif, system-ui", size=11),
            xaxis=dict(
                showgrid=False, zeroline=True,
                zerolinecolor="rgba(148,163,184,0.3)", zerolinewidth=1,
                tickvals=[-100, -75, -50, -25, 0, 25, 50, 75, 100],
                ticktext=["100%","75%","50%","25%","0","25%","50%","75%","100%"],
                range=[-105, 105],
                tickfont=dict(size=9, color="rgba(148,163,184,0.5)"),
            ),
            yaxis=dict(
                showgrid=False,
                tickfont=dict(size=10, color="#e2e8f0"),
                automargin=True,
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(size=9, color="rgba(148,163,184,0.6)"),
                bgcolor="rgba(0,0,0,0)",
            ),
            margin=dict(l=0, r=10, t=30, b=10),
            height=380,
            annotations=[dict(
                x=0, y=-0.08, xref="paper", yref="paper",
                text="← Away favored  |  Home favored →",
                showarrow=False,
                font=dict(size=9, color="rgba(148,163,184,0.35)"),
                xanchor="center",
            )],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown("""
<div style="text-align:center;padding:60px 20px;color:rgba(148,163,184,0.4);font-size:12px;">
  No game data to chart tonight.
</div>
""", unsafe_allow_html=True)

_sp(1)

# ─────────────────────────────────────────────
# ROW 1 — Power Index Rating Boys / Girls / Model Report Card
# ─────────────────────────────────────────────

c1, c2, c3 = st.columns(3, gap="small")

with c1:
    boys_pir  = top_pir_teams("Boys", 5)
    rows_html = ""
    if not boys_pir.empty:
        for i, (_, r) in enumerate(boys_pir.iterrows()):
            name  = str(r.get("_DisplayName", r.get("Team", "—")))
            val   = r.get("PowerIndex_Display", np.nan)
            cls   = str(r.get("Class", ""))
            val_s = f"{val:.1f}" if pd.notna(val) else "—"
            rows_html += f"""
<div class="feat-row">
  <span class="feat-rank">#{i+1}</span>
  <span class="feat-name">{name}</span>
  <span class="feat-badge">{cls}</span>
  <span class="feat-val">{val_s}</span>
</div>"""
    else:
        rows_html = '<div class="feat-sub" style="padding:6px;">No data.</div>'
    st.markdown(f"""
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">📊 Power Index Rating — Boys</span>
    <span class="feat-card-link">→ PIR page</span>
  </div>
  <div>{rows_html}</div>
  <div class="feat-footer">Updated nightly · All classes combined</div>
</div>""", unsafe_allow_html=True)

with c2:
    girls_pir = top_pir_teams("Girls", 5)
    rows_html = ""
    if not girls_pir.empty:
        for i, (_, r) in enumerate(girls_pir.iterrows()):
            name  = str(r.get("_DisplayName", r.get("Team", "—")))
            val   = r.get("PowerIndex_Display", np.nan)
            cls   = str(r.get("Class", ""))
            val_s = f"{val:.1f}" if pd.notna(val) else "—"
            rows_html += f"""
<div class="feat-row">
  <span class="feat-rank">#{i+1}</span>
  <span class="feat-name">{name}</span>
  <span class="feat-badge">{cls}</span>
  <span class="feat-val">{val_s}</span>
</div>"""
    else:
        rows_html = '<div class="feat-sub" style="padding:6px;">No data.</div>'
    st.markdown(f"""
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">📊 Power Index Rating — Girls</span>
    <span class="feat-card-link">→ PIR page</span>
  </div>
  <div>{rows_html}</div>
  <div class="feat-footer">Updated nightly · All classes combined</div>
</div>""", unsafe_allow_html=True)

with c3:
    yesterday   = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)
    yesterday_s = yesterday.strftime("%A, %b %#d")
    wrong       = total - correct
    rc_color    = ("#22c55e" if total > 0 and correct / total >= 0.70 else
                   "#f59e0b" if total > 0 and correct / total >= 0.55 else "#ef4444")
    if total > 0:
        pct      = correct / total * 100
        rc_inner = f"""
<div style="text-align:center;padding:8px 0;">
  <div style="font-size:38px;font-weight:900;color:{rc_color};">{correct}-{wrong}</div>
  <div style="font-size:10px;color:rgba(148,163,184,0.5);margin-top:2px;">
    {pct:.0f}% on {total} predictions
  </div>
  <div style="margin-top:8px;height:5px;border-radius:999px;
              background:rgba(148,163,184,0.1);overflow:hidden;">
    <div style="height:100%;width:{pct:.1f}%;background:{rc_color};border-radius:999px;"></div>
  </div>
</div>"""
    else:
        rc_inner = """
<div style="text-align:center;padding:16px 0;">
  <div style="font-size:24px;margin-bottom:6px;">📭</div>
  <div style="color:rgba(148,163,184,0.4);font-size:11px;">No results yet.</div>
</div>"""
    st.markdown(f"""
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">📋 Model Report Card</span>
    <span class="feat-card-link">{yesterday_s}</span>
  </div>
  {rc_inner}
  <div class="feat-footer">Last night's prediction W-L record</div>
</div>""", unsafe_allow_html=True)

_sp(1)

# ─────────────────────────────────────────────
# ROW 2 — Heal Point Rating Boys / Girls / Upset Watch
# ─────────────────────────────────────────────

c4, c5, c6 = st.columns(3, gap="small")

with c4:
    boys_ti   = top_ti_teams("Boys", 5)
    rows_html = ""
    if not boys_ti.empty:
        for i, (_, r) in enumerate(boys_ti.iterrows()):
            name  = str(r.get("_DisplayName", r.get("Team", "—")))
            ti    = r.get("TI", np.nan)
            rec   = str(r.get("Record", ""))
            cls   = str(r.get("Class", ""))
            ti_s  = f"{ti:.2f}" if pd.notna(ti) else "—"
            rows_html += f"""
<div class="feat-row">
  <span class="feat-rank">#{i+1}</span>
  <span class="feat-name">{name}</span>
  <span class="feat-badge">{cls}</span>
  <span class="feat-sub" style="margin-right:4px;">{rec}</span>
  <span class="feat-val">{ti_s}</span>
</div>"""
    else:
        rows_html = '<div class="feat-sub" style="padding:6px;">No data.</div>'
    st.markdown(f"""
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">🏅 Heal Point Rating — Boys</span>
    <span class="feat-card-link">→ Rankings</span>
  </div>
  <div>{rows_html}</div>
  <div class="feat-footer">TI = Tournament Index · Bracket seeding · All classes</div>
</div>""", unsafe_allow_html=True)

with c5:
    girls_ti  = top_ti_teams("Girls", 5)
    rows_html = ""
    if not girls_ti.empty:
        for i, (_, r) in enumerate(girls_ti.iterrows()):
            name  = str(r.get("_DisplayName", r.get("Team", "—")))
            ti    = r.get("TI", np.nan)
            rec   = str(r.get("Record", ""))
            cls   = str(r.get("Class", ""))
            ti_s  = f"{ti:.2f}" if pd.notna(ti) else "—"
            rows_html += f"""
<div class="feat-row">
  <span class="feat-rank">#{i+1}</span>
  <span class="feat-name">{name}</span>
  <span class="feat-badge">{cls}</span>
  <span class="feat-sub" style="margin-right:4px;">{rec}</span>
  <span class="feat-val">{ti_s}</span>
</div>"""
    else:
        rows_html = '<div class="feat-sub" style="padding:6px;">No data.</div>'
    st.markdown(f"""
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">🏅 Heal Point Rating — Girls</span>
    <span class="feat-card-link">→ Rankings</span>
  </div>
  <div>{rows_html}</div>
  <div class="feat-footer">TI = Tournament Index · Bracket seeding · All classes</div>
</div>""", unsafe_allow_html=True)

with c6:
    upsets    = upset_watch()
    rows_html = ""
    if upsets:
        for u in upsets:
            dog_pct = f"{u['dog_prob'] * 100:.0f}%"
            rows_html += f"""
<div class="feat-row">
  <span style="font-size:13px;">⚡</span>
  <div style="flex:1;min-width:0;">
    <div class="feat-name">{u['away']} at {u['home']}</div>
    <div class="feat-sub">Upset chance: <strong style="color:#fca5a5;">{dog_pct}</strong></div>
  </div>
</div>"""
    else:
        rows_html = """
<div style="text-align:center;padding:16px 0;">
  <div style="font-size:11px;color:rgba(148,163,184,0.4);">No upset candidates tonight.</div>
</div>"""
    st.markdown(f"""
<div class="feat-card">
  <div class="feat-card-header">
    <span class="feat-card-title">⚡ Upset Watch Tonight</span>
    <span class="feat-card-link">→ The Model</span>
  </div>
  <div>{rows_html}</div>
  <div class="feat-footer">Teams with ≥35% upset probability</div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

_sp(2)
if callable(render_footer):
    render_footer()
else:
    st.caption("© 2026 Analytics207")
