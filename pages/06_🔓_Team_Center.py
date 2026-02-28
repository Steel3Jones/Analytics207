# 06__Team_Center.py  –  Team Center v4.2 (Subscriber Lock)
# Analytics207.com  |  Primary source: teams_team_season_analytics_v50.parquet
from __future__ import annotations
import re
from pathlib import Path
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from layout import apply_global_layout_tweaks, render_logo, render_page_header, render_footer
from components.cards import inject_card_css
from components.cards_team_center import inject_team_center_card_css
from auth import login_gate, logout_button, is_subscribed


from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

st.set_page_config(page_title="🏫 Team Center – Analytics207.com", page_icon="🏫", layout="wide")
apply_global_layout_tweaks()
inject_card_css()
inject_team_center_card_css()

user = login_gate(required=False)
logout_button()

render_logo()
render_page_header(
    title="🏫 Team Center",
    definition="Team Center (n.): The complete story of any Maine program, on one page.",
    subtitle="Search any school — records, model grades, tournament outlook, milestones, and more.",
)

# ══════════════════════════════════════════════════════════════════════════
#  LOCK WALL
# ══════════════════════════════════════════════════════════════════════════
_BASE_CSS = """
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: transparent;
  font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
  color: #f1f5f9;
}
</style>
"""

def _render_lock_wall(section_name: str) -> None:
    components.html(f"""{_BASE_CSS}
<div style="background:linear-gradient(135deg,#0f172a,#1a1a2e);
            border:1px solid rgba(245,158,11,0.3);border-radius:14px;
            padding:32px 28px;text-align:center;">
  <div style="font-size:2.5rem;margin-bottom:10px;">🔒</div>
  <div style="font-size:1.1rem;font-weight:800;color:#fbbf24;margin-bottom:6px;">
    {section_name} — Subscriber Only
  </div>
  <div style="font-size:0.85rem;color:#94a3b8;max-width:420px;margin:0 auto;">
    Subscribe to unlock full analytics, model rankings, spreads,
    tournament simulations, and more.
  </div>
</div>
""", height=160, scrolling=False)

# ══════════════════════════════════════════════════════════════════════════
#  FILE PATHS
# ══════════════════════════════════════════════════════════════════════════
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
CORE_DIR = DATA_DIR / "core"

ANALYTICS_FILE   = CORE_DIR  / "teams_team_season_analytics_v50.parquet"
GAMES_FILE       = CORE_DIR  / "games_analytics_v50.parquet"
POWER_FILE       = CORE_DIR  / "teams_power_index_v50.parquet"
PREDICTIONS_FILE = DATA_DIR  / "predictions" / "games_predictions_current.parquet"
SIM_PATH         = CORE_DIR  / "tournament_sim_v50.parquet"
MILESTONE_FILE   = DATA_DIR  / "milestone_claims.csv"

# ══════════════════════════════════════════════════════════════════════════
#  BRACKET SIZES  (mirrors heal_points.py)
# ══════════════════════════════════════════════════════════════════════════
BRACKET_SIZES: dict[tuple[str, str, str], int] = {
    ("Boys",  "A", "North"): 8,  ("Boys",  "A", "South"): 11,
    ("Boys",  "B", "North"): 9,  ("Boys",  "B", "South"): 10,
    ("Boys",  "C", "North"): 10, ("Boys",  "C", "South"): 10,
    ("Boys",  "D", "North"): 10, ("Boys",  "D", "South"): 8,
    ("Boys",  "S", "North"): 8,  ("Boys",  "S", "South"): 8,
    ("Girls", "A", "North"): 8,  ("Girls", "A", "South"): 11,
    ("Girls", "B", "North"): 9,  ("Girls", "B", "South"): 10,
    ("Girls", "C", "North"): 10, ("Girls", "C", "South"): 10,
    ("Girls", "D", "North"): 10, ("Girls", "D", "South"): 8,
    ("Girls", "S", "North"): 8,  ("Girls", "S", "South"): 8,
}

def is_qualified(rank_n: float, gender_label: str, cls: str, reg: str) -> int:
    if np.isnan(rank_n): return 0
    cut = BRACKET_SIZES.get((gender_label, str(cls).strip().upper(), str(reg).strip().title()), 10)
    return 1 if int(rank_n) <= cut else 0

# ══════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
.hero-box {
    background: linear-gradient(135deg,#0f172a,#1e293b);
    border: 1px solid #334155; border-radius:14px;
    padding: 22px 26px 18px;
}
.hero-school { font-size:2.2rem; font-weight:800; color:#f8fafc; margin-bottom:10px; }
.hero-phase  { background:#0f766e; color:#99f6e4; border-radius:6px;
    padding:3px 10px; font-size:0.75rem; font-weight:600; display:inline-block; }
.badge-boys  { background:#1d4ed8; color:#ffffff; border-radius:8px;
    padding:6px 18px; font-size:0.95rem; font-weight:800; display:inline-block;
    letter-spacing:0.04em; text-transform:uppercase; }
.badge-girls { background:#9333ea; color:#ffffff; border-radius:8px;
    padding:6px 18px; font-size:0.95rem; font-weight:800; display:inline-block;
    letter-spacing:0.04em; text-transform:uppercase; }
.badge-qualified { background:#14532d; color:#86efac; border-radius:6px;
    padding:2px 10px; font-size:0.74rem; font-weight:700; display:inline-block; margin-left:6px; }
.badge-bubble { background:#1c1917; color:#a8a29e; border-radius:6px;
    padding:2px 10px; font-size:0.74rem; font-weight:700; display:inline-block; margin-left:6px; }

.card { background:#1e293b; border:1px solid #334155; border-radius:10px;
    padding:18px 20px; margin-bottom:6px; }
.lbl  { font-size:0.68rem; color:#64748b; text-transform:uppercase;
    letter-spacing:.06em; margin-bottom:2px; }
.val  { font-size:1.5rem; font-weight:700; color:#f1f5f9; line-height:1.15; }
.sub  { font-size:0.78rem; color:#64748b; margin-top:2px; }
.sm   { font-size:1.0rem; font-weight:700; color:#f1f5f9; }

.stat-row   { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:10px; }
.stat-block { min-width:72px; }

.divider { border:none; border-top:1px solid #1e293b; margin:10px 0; }

.badge-hot  { background:#7f1d1d; color:#fca5a5; border-radius:6px;
    padding:2px 8px; font-size:0.74rem; font-weight:700; }
.badge-cold { background:#1e3a5f; color:#93c5fd; border-radius:6px;
    padding:2px 8px; font-size:0.74rem; font-weight:700; }
.badge-even { background:#1e2a1e; color:#86efac; border-radius:6px;
    padding:2px 8px; font-size:0.74rem; font-weight:700; }

.section-head { font-size:1.0rem; font-weight:700; color:#38bdf8;
    border-bottom:1px solid #334155; padding-bottom:6px;
    margin:22px 0 12px; letter-spacing:.04em; text-transform:uppercase; }

.gender-div-boys  { border-left:4px solid #3b82f6; padding-left:12px;
    margin:16px 0 8px; font-size:1.0rem; font-weight:700; color:#93c5fd; }
.gender-div-girls { border-left:4px solid #d946ef; padding-left:12px;
    margin:16px 0 8px; font-size:1.0rem; font-weight:700; color:#f0abfc; }

.game-row { display:flex; align-items:center; gap:8px; padding:7px 12px;
    border-radius:8px; margin-bottom:4px; background:#1e293b;
    border:1px solid #2d3748; }
.game-row-w { border-left:4px solid #22c55e; }
.game-row-l { border-left:4px solid #ef4444; }
.game-opp   { flex:1; font-size:0.88rem; color:#cbd5e1; font-weight:600; }
.game-score { font-size:0.88rem; color:#f1f5f9; min-width:56px; text-align:right; }
.game-margin{ font-size:0.76rem; color:#94a3b8; min-width:42px; text-align:right; }

.upcoming-row { display:flex; align-items:center; gap:8px; padding:7px 12px;
    border-radius:8px; margin-bottom:4px; background:#0f172a;
    border:1px solid #334155; }
.upcoming-opp  { flex:1; font-size:0.88rem; color:#cbd5e1; font-weight:600; }
.upcoming-date { font-size:0.74rem; color:#64748b; min-width:52px; }

.tourn-card { background:#0c1a0c; border:1px solid #166534; border-radius:10px;
    padding:18px 22px; margin-bottom:8px; }

.ms-row { background:#1a2035; border:1px solid #2d3748; border-radius:8px;
    padding:10px 14px; margin-bottom:6px; }
.ms-status-verified  { color:#22c55e; font-weight:700; font-size:0.76rem; }
.ms-status-contested { color:#eab308; font-weight:700; font-size:0.76rem; }
.ms-status-pending   { color:#94a3b8; font-weight:700; font-size:0.76rem; }
.ms-text { font-size:0.88rem; color:#e2e8f0; margin-top:3px; }

.roadtrip-stub { background:#161625; border:2px dashed #334155; border-radius:10px;
    padding:22px; text-align:center; color:#475569; font-size:0.88rem; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════
def sf(val, default=0.0):
    try:
        if pd.isna(val): return default
    except Exception: pass
    try: return float(val)
    except Exception: return default

def get(row, *keys, default="—"):
    if row is None: return default
    for k in keys:
        try:
            v = row.get(k, pd.NA)
        except Exception: continue
        if pd.notna(v) and str(v).strip() not in ("","nan","None","N/A","—"):
            return str(v).strip()
    return default

def _latest(df):
    if df is None or df.empty or "Season" not in df.columns: return df
    s = pd.to_numeric(df["Season"].astype(str).str[:4], errors="coerce")
    if s.dropna().empty: return df
    return df.loc[s == int(s.dropna().max())].copy()

_SUFFIX_RE = re.compile(
    r"(Boys|Girls)(A|B|C|D|S)?(North|South|East|West|DNorth|DSouth|DEast|DWest)?\s*$",
    re.IGNORECASE,
)
def clean(raw):
    if not raw or raw in ("nan","None",""): return raw
    return _SUFFIX_RE.sub("", str(raw)).strip()

def win_bar(pct):
    c = "#22c55e" if pct >= 0.7 else ("#eab308" if pct >= 0.5 else "#ef4444")
    return (
        f'<div style="background:#0f172a;border-radius:4px;height:8px;width:130px;'
        f'display:inline-block;vertical-align:middle;margin-right:6px;">'
        f'<div style="background:{c};width:{int(pct*100)}%;height:100%;'
        f'border-radius:4px;"></div></div>'
    )

def heat(lz):
    v = sf(lz, 0.0)
    if v > 1.5:  return '<span class="badge-hot">&#x1F525; HOT</span>'
    if v < -1.5: return '<span class="badge-cold">&#x2744; COLD</span>'
    return '<span class="badge-even">&#x25CF; EVEN</span>'

def phase():
    import datetime
    m = datetime.date.today().month
    if m in (11,12,1,2): return "&#x1F3C0; Regular Season"
    if m == 3:           return "&#x1F3C6; Tournament"
    return "&#x2600; Offseason"

def fmt(v, spec=".1f", na="—"):
    if isinstance(v, float) and np.isnan(v): return na
    try: return format(float(v), spec)
    except: return na

def cval(v, spec=".1f", good_pos=True, prefix=""):
    if isinstance(v, float) and np.isnan(v): return "—"
    try: fv = float(v)
    except: return "—"
    c = ("#22c55e" if fv >= 0 else "#ef4444") if good_pos else ("#ef4444" if fv >= 0 else "#22c55e")
    sign = "+" if fv >= 0 else ""
    return f'<span style="color:{c};font-weight:700;">{prefix}{sign}{fv:{spec}}</span>'

def _gdiv(label):
    css = "gender-div-boys" if label == "Boys" else "gender-div-girls"
    icon = "&#x1F535;" if label == "Boys" else "&#x1F7E3;"
    st.markdown(f'<div class="{css}">{icon} {label}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
#  TEAM KEY HELPERS
# ══════════════════════════════════════════════════════════════════════════
def build_team_key(team: str, gender: str, cls: str, reg: str) -> str:
    t = (team   or "").strip()
    g = (gender or "").strip()
    c = (cls    or "").strip()
    r = (reg    or "").strip()
    if t in ("","—","nan","None"): return ""
    g = "" if g in ("—","nan","None") else g
    c = "" if c in ("—","nan","None") else c
    r = "" if r in ("—","nan","None") else r
    return f"{t}{g}{c}{r}"

def resolve_key(stored: str, team: str, gender: str, cls: str, reg: str) -> str:
    if stored and stored not in ("","—","nan","None"):
        return stored
    return build_team_key(team, gender, cls, reg)

# ══════════════════════════════════════════════════════════════════════════
#  DATA LOADERS
# ══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False, ttl=3600)
def load_analytics():
    return pd.read_parquet(ANALYTICS_FILE) if ANALYTICS_FILE.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=3600)
def load_games():
    return pd.read_parquet(GAMES_FILE) if GAMES_FILE.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=3600)
def load_power():
    return pd.read_parquet(POWER_FILE) if POWER_FILE.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=3600)
def load_predictions():
    return pd.read_parquet(PREDICTIONS_FILE) if PREDICTIONS_FILE.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=3600)
def load_sim():
    return pd.read_parquet(SIM_PATH) if SIM_PATH.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=3600)
def load_ms():
    try: return pd.read_csv(MILESTONE_FILE) if MILESTONE_FILE.exists() else pd.DataFrame()
    except: return pd.DataFrame()

with st.spinner("Loading program data…"):
    ana_df   = load_analytics()
    games_df = load_games()
    power_df = load_power()
    pred_df  = load_predictions()
    sim_df   = load_sim()
    ms_df    = load_ms()

if ana_df.empty:
    st.error("Analytics data not found — run your nightly build.")
    st.stop()

ana_latest  = _latest(ana_df)
phase_badge = phase()

# ══════════════════════════════════════════════════════════════════════════
#  SCHOOL DROPDOWN  (FREE — always visible)
# ══════════════════════════════════════════════════════════════════════════
all_schools = sorted(ana_latest["Team"].dropna().unique().tolist())
_qp      = st.query_params.get("school", "")
_default = (_qp[0] if isinstance(_qp, list) else _qp) or ""

sc_col, _ = st.columns([3, 4])
with sc_col:
    selected = st.selectbox(
        "&#x1F50D; Search for a school",
        [""] + all_schools,
        index=([""] + all_schools).index(_default) if _default in all_schools else 0,
        key="school_selector",
    )

if not selected:
    st.info("Search for a school above to load their Team Center profile.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
#  PULL BOTH GENDER ROWS
# ══════════════════════════════════════════════════════════════════════════
school_rows = ana_latest[ana_latest["Team"] == selected]

def grow(gender_str):
    r = school_rows[school_rows["Gender"].astype(str).str.strip() == gender_str]
    return r.iloc[0] if not r.empty else None

boys_row  = grow("Boys")
girls_row = grow("Girls")

def meta(row, fb=None):
    cls = get(row, "Class", "Classification")
    reg = get(row, "Region", "RegionName")
    div = get(row, "Division")
    if cls == "—" and fb is not None: cls = get(fb, "Class", "Classification")
    if reg == "—" and fb is not None: reg = get(fb, "Region", "RegionName")
    if div == "—" and fb is not None: div = get(fb, "Division")
    return cls, reg, div

boys_cls,  boys_reg,  boys_div  = meta(boys_row,  girls_row)
girls_cls, girls_reg, girls_div = meta(girls_row, boys_row)

boys_key  = resolve_key(get(boys_row,  "TeamKey"), selected, "Boys",  boys_cls,  boys_reg)
girls_key = resolve_key(get(girls_row, "TeamKey"), selected, "Girls", girls_cls, girls_reg)

# ══════════════════════════════════════════════════════════════════════════
#  POWER INDEX LOOKUP
# ══════════════════════════════════════════════════════════════════════════
def pi_lookup(team_key):
    if power_df.empty or not team_key or team_key == "—": return None
    r = power_df[power_df["TeamKey"].astype(str) == team_key]
    return r.iloc[0] if not r.empty else None

boys_pi  = pi_lookup(boys_key)
girls_pi = pi_lookup(girls_key)

# ══════════════════════════════════════════════════════════════════════════
#  GAME + ATS HELPERS
# ══════════════════════════════════════════════════════════════════════════
def games_for(team_key: str, gender: str) -> pd.DataFrame:
    if games_df.empty or not team_key or team_key == "—":
        return pd.DataFrame()
    g = _latest(games_df.copy())
    g = g[g["Gender"].astype(str).str.strip() == gender]
    g = g[(g["HomeKey"] == team_key) | (g["AwayKey"] == team_key)].copy()
    if "Played" in g.columns:
        g["Played"] = g["Played"].fillna(False).astype(bool)
    if "Date" in g.columns:
        g["Date"] = pd.to_datetime(g["Date"], errors="coerce")

    if not pred_df.empty and "GameID" in g.columns and "GameID" in pred_df.columns:
        want  = [
            "GameID","PredMargin","PredHomeWinProb",
            "PredHomeScore","PredAwayScore","PredTotalPoints",
            "PredWinnerKey","PredSpreadAbs","BlowoutMode","SecondMeeting",
        ]
        avail = [c for c in want if c in pred_df.columns]
        g["GameID"] = g["GameID"].astype(str)
        p = pred_df[avail].copy()
        p["GameID"] = p["GameID"].astype(str)
        g = g.merge(p, on="GameID", how="left")

    return g


def perspective(g: pd.DataFrame, team_key: str) -> pd.DataFrame:
    if g.empty: return g
    out = g.copy()
    out["IsHome"]     = out["HomeKey"] == team_key
    out["TeamPts"]    = np.where(out["IsHome"], out["HomeScore"], out["AwayScore"])
    out["OppPts"]     = np.where(out["IsHome"], out["AwayScore"], out["HomeScore"])
    out["TeamMargin"] = (
        pd.to_numeric(out["TeamPts"], errors="coerce")
        - pd.to_numeric(out["OppPts"], errors="coerce")
    )
    out["OppName"] = np.where(
        out["IsHome"],
        out["Away"] if "Away" in out.columns else "",
        out["Home"] if "Home" in out.columns else "",
    )
    out["OppRank"] = np.where(
        out["IsHome"],
        pd.to_numeric(out.get("AwayRank", np.nan), errors="coerce"),
        pd.to_numeric(out.get("HomeRank", np.nan), errors="coerce"),
    )

    if "PredMargin" in out.columns:
        pred_m = pd.to_numeric(out["PredMargin"], errors="coerce")
        out["TeamSpread"]  = np.where(out["IsHome"],  pred_m, -pred_m)
        out["ATSMargin"]   = out["TeamMargin"] - out["TeamSpread"]
        played_mask = out.get("Played", pd.Series(True, index=out.index)).fillna(False).astype(bool)
        has_spread  = out["TeamSpread"].notna() & out["ATSMargin"].notna()
        lined       = played_mask & has_spread
        out["ATSResult"] = np.select(
            [lined & (out["ATSMargin"] > 0),
             lined & (out["ATSMargin"] == 0),
             lined & (out["ATSMargin"] < 0)],
            ["COVER","PUSH","NO_COVER"],
            default=pd.NA,
        )
        home_wp = pd.to_numeric(out.get("PredHomeWinProb", np.nan), errors="coerce")
        out["TeamWinProb"] = np.where(out["IsHome"], home_wp, 1.0 - home_wp)
    else:
        out["ATSResult"]   = pd.NA
        out["TeamWinProb"] = np.nan
        out["TeamSpread"]  = np.nan
        out["ATSMargin"]   = np.nan

    return out


def ats_summary(team_key: str, gender: str):
    if not team_key or team_key == "—" or games_df.empty:
        return None
    g = games_for(team_key, gender)
    if g.empty: return None
    g = perspective(g, team_key)
    played = g[g["Played"] == True].copy() if "Played" in g.columns else g.copy()
    if "ATSResult" not in played.columns: return None
    x = played[played["ATSResult"].astype(str).isin(["COVER","NO_COVER","PUSH"])]
    if x.empty: return None
    covers   = int((x["ATSResult"] == "COVER").sum())
    no_cover = int((x["ATSResult"] == "NO_COVER").sum())
    pushes   = int((x["ATSResult"] == "PUSH").sum())
    denom    = covers + no_cover
    if denom == 0: return None
    pct   = covers / denom
    avg_m = x["ATSMargin"].dropna().mean() if "ATSMargin" in x.columns else np.nan
    return covers, no_cover, pushes, pct, avg_m

# ══════════════════════════════════════════════════════════════════════════
#  SECTION 1 – HERO CARDS  (FREE — always visible)
# ══════════════════════════════════════════════════════════════════════════
def hero_card(gender_label, row, cls, reg, pi_row):
    if row is None:
        badge = "badge-boys" if gender_label == "Boys" else "badge-girls"
        st.markdown(
            f'<div class="hero-box"><span class="{badge}">{gender_label}</span>'
            '<div style="color:#475569;margin-top:14px;font-size:0.88rem;">No data this season</div></div>',
            unsafe_allow_html=True,
        )
        return

    record  = get(row, "Record")
    seed    = sf(row.get("ProjectedSeed", np.nan), np.nan)
    rank_n  = sf(row.get("Rank",          np.nan), np.nan)
    qual    = is_qualified(rank_n, gender_label, cls, reg)
    ti      = sf(row.get("TI",            np.nan), np.nan)
    pi_disp = sf(pi_row["PowerIndex_Display"], np.nan) if pi_row is not None else np.nan
    off_r   = sf(pi_row["OffRating_Ridge"],    np.nan) if pi_row is not None else np.nan
    def_r   = sf(pi_row["DefRating_Ridge"],    np.nan) if pi_row is not None else np.nan

    badge_cls = "badge-boys" if gender_label == "Boys" else "badge-girls"
    acc       = "#93c5fd"    if gender_label == "Boys" else "#f0abfc"

    qual_badge = '<span class="badge-qualified">&#x2705; QUALIFIED</span>' if qual \
        else '<span class="badge-bubble">Bubble</span>'

    seed_s = f"#{int(seed)}"   if not np.isnan(seed)   else "?"
    rank_s = f"#{int(rank_n)}" if not np.isnan(rank_n) else "—"

    st.markdown(f"""
<div class="hero-box">
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    <span class="{badge_cls}">{gender_label}</span>
    <span class="hero-phase">{phase_badge}</span>
    {qual_badge}
  </div>
  <div style="margin-top:8px;font-size:0.84rem;color:{acc};font-weight:600;">
    {cls} &middot; {reg} &middot; Rank {rank_s}
  </div>
  <div style="margin-top:10px;">
    <div class="lbl">Season Record</div>
    <div style="font-size:2.2rem;font-weight:800;color:#f1f5f9;line-height:1.1;">{record}</div>
  </div>
  <div style="margin-top:12px;display:flex;gap:20px;flex-wrap:wrap;">
    <div>
      <div class="lbl">Proj Seed</div>
      <div style="font-size:1.5rem;font-weight:800;color:#4ade80;">{seed_s}</div>
    </div>
    <div>
      <div class="lbl">TI Score</div>
      <div style="font-size:1.1rem;font-weight:700;color:#a78bfa;">{fmt(ti,".2f")}</div>
    </div>
    <div>
      <div class="lbl">Power Index</div>
      <div style="font-size:1.1rem;font-weight:700;color:#38bdf8;">{fmt(pi_disp,".1f")}</div>
    </div>
    <div>
      <div class="lbl">Off Rating</div>
      <div style="font-size:1.0rem;">{cval(off_r,".2f") if not np.isnan(off_r) else "—"}</div>
    </div>
    <div>
      <div class="lbl">Def Rating</div>
      <div style="font-size:1.0rem;">{cval(def_r,".2f",False) if not np.isnan(def_r) else "—"}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


st.markdown(f'<div class="hero-school">{selected}</div>', unsafe_allow_html=True)
h1, h2 = st.columns(2)
with h1: hero_card("Boys",  boys_row,  boys_cls,  boys_reg,  boys_pi)
with h2: hero_card("Girls", girls_row, girls_cls, girls_reg, girls_pi)

# ══════════════════════════════════════════════════════════════════════════
#  🔒  SUBSCRIBER GATE — everything below hero cards requires subscription
# ══════════════════════════════════════════════════════════════════════════
_subscribed = is_subscribed()

# ══════════════════════════════════════════════════════════════════════════
#  SECTION 2 – RICH SNAPSHOT  (🔒 LOCKED)
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-head">&#x1F4CA; Program Snapshot</div>', unsafe_allow_html=True)

if not _subscribed:
    _render_lock_wall("Program Snapshot")
else:
    def snap_block(row, gender_label, cls, reg, pi_row, team_key):
        if row is None:
            st.markdown(
                f'<div class="card"><div class="lbl">{gender_label}</div>'
                '<div style="color:#475569;font-size:0.85rem;margin-top:6px;">No data this season</div></div>',
                unsafe_allow_html=True,
            )
            return

        wpct       = sf(row.get("WinPct",         0.0))
        record     = get(row, "Record")
        g_rem      = int(sf(row.get("GamesRemaining", 0)))
        ppg        = sf(row.get("PPG",            np.nan), np.nan)
        oppg       = sf(row.get("OPPG",           np.nan), np.nan)
        mpg        = sf(row.get("MarginPG",       np.nan), np.nan)
        l5mpg      = sf(row.get("L5MarginPG",     np.nan), np.nan)
        l10mpg     = sf(row.get("Last10MarginPG", np.nan), np.nan)
        hi_score   = sf(row.get("HighestScore",   np.nan), np.nan)
        lo_score   = sf(row.get("LowestScore",    np.nan), np.nan)

        off_eff    = sf(row.get("OffEff",  np.nan), np.nan)
        def_eff    = sf(row.get("DefEff",  np.nan), np.nan)
        net_eff    = sf(row.get("NetEff",  np.nan), np.nan)
        off_ridge  = sf(pi_row["OffRating_Ridge"],    np.nan) if pi_row is not None else np.nan
        def_ridge  = sf(pi_row["DefRating_Ridge"],    np.nan) if pi_row is not None else np.nan
        pi_display = sf(pi_row["PowerIndex_Display"], np.nan) if pi_row is not None else np.nan

        ti         = sf(row.get("TI",        np.nan), np.nan)
        rpi        = sf(row.get("RPI",       np.nan), np.nan)
        sos        = sf(row.get("SOS_EWP",   np.nan), np.nan)
        luckz      = sf(row.get("LuckZ",     np.nan), np.nan)
        exp_w      = sf(row.get("ExpectedWins",    np.nan), np.nan)
        sadj_w     = sf(row.get("ScheduleAdjWins", np.nan), np.nan)
        proj_seed  = sf(row.get("ProjectedSeed",   np.nan), np.nan)
        rank_n     = sf(row.get("Rank",            np.nan), np.nan)

        streak_lbl = get(row, "StreakLabel", default="—")

        h_w   = int(sf(row.get("HomeWins",   0))); h_l  = int(sf(row.get("HomeLosses",  0)))
        h_mpg = sf(row.get("HomeMarginPG",   np.nan), np.nan)
        r_w   = int(sf(row.get("RoadWins",   0))); r_l  = int(sf(row.get("RoadLosses",  0)))
        r_mpg = sf(row.get("RoadMarginPG",   np.nan), np.nan)

        cl_w  = int(sf(row.get("CloseWins",  0))); cl_l = int(sf(row.get("CloseLosses", 0)))
        cl_wp = sf(row.get("CloseWinPct",    np.nan), np.nan)

        q1w = int(sf(row.get("Q1_Wins",0))); q1l = int(sf(row.get("Q1_Losses",0)))
        q2w = int(sf(row.get("Q2_Wins",0))); q2l = int(sf(row.get("Q2_Losses",0)))
        q3w = int(sf(row.get("Q3_Wins",0))); q3l = int(sf(row.get("Q3_Losses",0)))
        q4w = int(sf(row.get("Q4_Wins",0))); q4l = int(sf(row.get("Q4_Losses",0)))
        q_wins  = int(sf(row.get("QualityWins", 0)))
        bad_l   = int(sf(row.get("BadLosses",   0)))
        top25_w = int(sf(row.get("Top25Wins",   0)))

        best_win   = get(row, "BestWin",   default="")
        best_mar   = sf(row.get("BestWinMargin",   np.nan), np.nan)
        worst_loss = get(row, "WorstLoss", default="")
        worst_mar  = sf(row.get("WorstLossMargin", np.nan), np.nan)

        in_div_w = int(sf(row.get("InDivisionWins",    0)))
        xdiv_w   = int(sf(row.get("CrossDivisionWins", 0)))

        ats_info = ats_summary(team_key, gender_label) if team_key else None
        if ats_info:
            covers, no_cover, pushes, pct_val, avg_m = ats_info
            ats_clr = "#22c55e" if pct_val >= 0.5 else "#ef4444"
            avg_clr = "#22c55e" if (not np.isnan(avg_m) and avg_m >= 0) else "#ef4444"
            ats_rec = f'<span style="color:{ats_clr};font-weight:700;">{covers}-{no_cover}-{pushes}</span>'
            ats_pct = f'<span style="color:{ats_clr};font-weight:700;">{pct_val:.0%}</span>'
            ats_avg = (f'<span style="color:{avg_clr};font-weight:700;">{avg_m:+.1f}</span>'
                       if not np.isnan(avg_m) else "—")
        else:
            ats_rec = ats_pct = ats_avg = "—"

        bar       = win_bar(wpct)
        ht        = heat(luckz)
        seed_s    = f"#{int(proj_seed)}" if not np.isnan(proj_seed) else "?"
        cl_wp_c   = "#22c55e" if (not np.isnan(cl_wp) and cl_wp >= 0.5) else "#ef4444"
        cl_wp_s   = f"{cl_wp:.0%}" if not np.isnan(cl_wp) else "—"
        best_m_s  = f" <span style='color:#22c55e;'>+{best_mar:.0f}</span>" if not np.isnan(best_mar)  else ""
        worst_m_s = f" <span style='color:#ef4444;'>{worst_mar:.0f}</span>" if not np.isnan(worst_mar) else ""

        st.markdown(f"""
<div class="card">

  <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:12px;">
    <div>
      <div class="lbl">{gender_label} &#x1F3C0;</div>
      <div class="val">{record}</div>
    </div>
    <div style="display:flex;align-items:center;gap:6px;margin-top:4px;">
      {bar}<span style="color:#94a3b8;font-size:0.88rem;">{wpct:.0%}</span>
    </div>
    <div style="margin-top:4px;">{ht}</div>
    <div style="margin-top:4px;">
      <div class="lbl">Streak</div>
      <div class="sm">{streak_lbl}</div>
    </div>
    <div style="margin-top:4px;">
      <div class="lbl">Games Left</div>
      <div class="sm">{g_rem}</div>
    </div>
    <div style="margin-top:4px;">
      <div class="lbl">Proj Seed</div>
      <div style="font-size:1.2rem;font-weight:800;color:#4ade80;">{seed_s}</div>
    </div>
  </div>

  <hr class="divider">

  <div class="stat-row">
    <div class="stat-block">
      <div class="lbl">PPG / OPPG</div>
      <div class="sm">{fmt(ppg)} / {fmt(oppg)}
        <span style="font-size:0.8rem;">{cval(mpg)}</span>
      </div>
    </div>
    <div class="stat-block"><div class="lbl">L5 Margin</div><div class="sm">{cval(l5mpg)}</div></div>
    <div class="stat-block"><div class="lbl">L10 Margin</div><div class="sm">{cval(l10mpg)}</div></div>
    <div class="stat-block">
      <div class="lbl">Hi / Lo Score</div>
      <div class="sm">{fmt(hi_score,".0f")} / {fmt(lo_score,".0f")}</div>
    </div>
  </div>

  <div class="stat-row">
    <div class="stat-block"><div class="lbl">Off Eff</div>
      <div class="sm" style="color:#38bdf8;">{fmt(off_eff)}</div></div>
    <div class="stat-block"><div class="lbl">Def Eff</div>
      <div class="sm">{fmt(def_eff)}</div></div>
    <div class="stat-block"><div class="lbl">Net Eff</div>
      <div class="sm">{cval(net_eff)}</div></div>
    <div class="stat-block"><div class="lbl">Off Rating</div>
      <div class="sm">{cval(off_ridge,".2f") if not np.isnan(off_ridge) else "—"}</div></div>
    <div class="stat-block"><div class="lbl">Def Rating</div>
      <div class="sm">{cval(def_ridge,".2f",False) if not np.isnan(def_ridge) else "—"}</div></div>
  </div>

  <hr class="divider">

  <div class="stat-row">
    <div class="stat-block"><div class="lbl">TI Score</div>
      <div class="sm" style="color:#a78bfa;">{fmt(ti,".2f")}</div></div>
    <div class="stat-block"><div class="lbl">Power Index</div>
      <div class="sm" style="color:#38bdf8;">{fmt(pi_display,".1f")}</div></div>
    <div class="stat-block"><div class="lbl">RPI</div>
      <div class="sm">{fmt(rpi,".4f")}</div></div>
    <div class="stat-block"><div class="lbl">SOS</div>
      <div class="sm">{fmt(sos,".4f")}</div></div>
    <div class="stat-block"><div class="lbl">Luck Z</div>
      <div class="sm">{cval(luckz,".2f")}</div></div>
    <div class="stat-block"><div class="lbl">Exp W</div>
      <div class="sm">{fmt(exp_w)}</div></div>
    <div class="stat-block"><div class="lbl">Sched Adj</div>
      <div class="sm">{cval(sadj_w)}</div></div>
  </div>

  <div class="stat-row">
    <div class="stat-block"><div class="lbl">ATS Record</div>
      <div class="sm">{ats_rec}</div></div>
    <div class="stat-block"><div class="lbl">Cover %</div>
      <div class="sm">{ats_pct}</div></div>
    <div class="stat-block"><div class="lbl">Avg ATS Margin</div>
      <div class="sm">{ats_avg}</div></div>
  </div>

  <hr class="divider">

  <div class="stat-row">
    <div class="stat-block"><div class="lbl">Home</div>
      <div class="sm">{h_w}-{h_l}
        <span style="font-size:0.78rem;color:#64748b;">{cval(h_mpg)}</span>
      </div></div>
    <div class="stat-block"><div class="lbl">Road</div>
      <div class="sm">{r_w}-{r_l}
        <span style="font-size:0.78rem;color:#64748b;">{cval(r_mpg)}</span>
      </div></div>
    <div class="stat-block"><div class="lbl">Clutch (1-pos)</div>
      <div class="sm" style="color:{cl_wp_c};">{cl_w}-{cl_l} ({cl_wp_s})</div></div>
  </div>

  <div class="stat-row">
    <div class="stat-block"><div class="lbl">Q1</div><div class="sm">{q1w}-{q1l}</div></div>
    <div class="stat-block"><div class="lbl">Q2</div><div class="sm">{q2w}-{q2l}</div></div>
    <div class="stat-block"><div class="lbl">Q3</div><div class="sm">{q3w}-{q3l}</div></div>
    <div class="stat-block"><div class="lbl">Q4</div><div class="sm">{q4w}-{q4l}</div></div>
    <div class="stat-block"><div class="lbl">Qual Wins</div>
      <div class="sm" style="color:#22c55e;">{q_wins}</div></div>
    <div class="stat-block"><div class="lbl">Bad Losses</div>
      <div class="sm" style="color:#ef4444;">{bad_l}</div></div>
    <div class="stat-block"><div class="lbl">Top-25 W</div><div class="sm">{top25_w}</div></div>
  </div>

  <div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:4px;">
    <div>
      <div class="lbl">Best Win</div>
      <div style="font-size:0.86rem;color:#86efac;">{best_win or "—"}{best_m_s}</div>
    </div>
    <div>
      <div class="lbl">Worst Loss</div>
      <div style="font-size:0.86rem;color:#fca5a5;">{worst_loss or "—"}{worst_m_s}</div>
    </div>
    <div>
      <div class="lbl">Div W (In / Cross)</div>
      <div style="font-size:0.86rem;color:#e2e8f0;">{in_div_w} / {xdiv_w}</div>
    </div>
  </div>

</div>
""", unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    with sc1: snap_block(boys_row,  "Boys",  boys_cls,  boys_reg,  boys_pi,  boys_key)
    with sc2: snap_block(girls_row, "Girls", girls_cls, girls_reg, girls_pi, girls_key)

# ══════════════════════════════════════════════════════════════════════════
#  SECTION 3 – RECENT GAMES + NEXT UP  (🔒 LOCKED)
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-head">&#x1F5D3; Recent Games &amp; Next Up</div>', unsafe_allow_html=True)

if not _subscribed:
    _render_lock_wall("Recent Games & Next Up")
else:
    def games_block(team_key: str, gender_label: str):
        if not team_key or games_df.empty:
            st.markdown(f"*No schedule data for {gender_label}.*"); return

        g = games_for(team_key, gender_label)
        if g.empty:
            st.markdown(f"*No games found for {gender_label}.*"); return
        g = perspective(g, team_key)

        played   = g[g["Played"] == True].copy()  if "Played" in g.columns else pd.DataFrame()
        upcoming = g[g["Played"] == False].copy() if "Played" in g.columns else pd.DataFrame()
        if "Date" in played.columns:   played   = played.sort_values("Date", ascending=False)
        if "Date" in upcoming.columns: upcoming = upcoming.sort_values("Date", ascending=True)

        st.markdown(f"**{gender_label} — Last 5 Results**")
        if played.empty:
            st.markdown("*No completed games yet.*")
        else:
            for _, row in played.head(5).iterrows():
                tm    = sf(row.get("TeamMargin", np.nan), np.nan)
                rc    = "game-row-w" if tm > 0 else "game-row-l"
                icon  = "✅" if tm > 10 else ("💚" if tm > 0 else ("🧡" if tm > -10 else "❌"))
                opp   = str(row.get("OppName","Opponent"))
                dv    = pd.to_datetime(row.get("Date", pd.NaT))
                ds    = dv.strftime("%b %d") if pd.notna(dv) else ""
                tp    = sf(row.get("TeamPts", np.nan), np.nan)
                op_   = sf(row.get("OppPts",  np.nan), np.nan)
                sc_s  = f"{int(tp)}-{int(op_)}" if not (np.isnan(tp) or np.isnan(op_)) else "—"
                mar_s = f"{tm:+.0f}" if not np.isnan(tm) else "—"

                ats_r  = str(row.get("ATSResult",""))
                ats_m  = sf(row.get("ATSMargin",  np.nan), np.nan)
                spread = sf(row.get("TeamSpread", np.nan), np.nan)
                if ats_r in ("COVER","NO_COVER","PUSH"):
                    ac  = "#22c55e" if ats_r == "COVER" else ("#ef4444" if ats_r == "NO_COVER" else "#eab308")
                    al  = "COV" if ats_r == "COVER" else ("NO" if ats_r == "NO_COVER" else "PSH")
                    am_s = f"{ats_m:+.1f}" if not np.isnan(ats_m) else ""
                    sp_s = f"sprd {spread:+.1f}" if not np.isnan(spread) else ""
                    ats_html = (
                        f'<div style="min-width:80px;text-align:right;">'
                        f'<div style="color:{ac};font-weight:700;font-size:0.78rem;">{al} {am_s}</div>'
                        f'<div style="font-size:0.66rem;color:#475569;">{sp_s}</div>'
                        f'</div>'
                    )
                else:
                    ats_html = '<div style="min-width:80px;"></div>'

                opp_rank  = sf(row.get("OppRank", np.nan), np.nan)
                rank_tag  = f'<span style="color:#64748b;font-size:0.68rem;margin-left:4px;">#{int(opp_rank)}</span>' if not np.isnan(opp_rank) else ""
                close_tag = '<span style="color:#eab308;font-size:0.66rem;margin-left:4px;">CLOSE</span>' if str(row.get("IsClose","")) == "1" else ""
                blow_tag  = '<span style="color:#64748b;font-size:0.66rem;margin-left:4px;">BLW</span>'   if str(row.get("IsBlowout","")) == "1" else ""

                st.markdown(f"""
<div class="game-row {rc}">
  <div style="font-size:1.0rem;min-width:20px;">{icon}</div>
  <div class="game-opp">{opp}{rank_tag}{close_tag}{blow_tag}
    <span style="font-size:0.66rem;color:#475569;margin-left:6px;">{ds}</span>
  </div>
  <div class="game-score">{sc_s}</div>
  <div class="game-margin">{mar_s}</div>
  {ats_html}
</div>
""", unsafe_allow_html=True)

        st.markdown(f"**{gender_label} — Next 3 Games**")
        if upcoming.empty:
            st.markdown("*No upcoming games scheduled.*")
        else:
            for _, row in upcoming.head(3).iterrows():
                opp    = str(row.get("OppName","Opponent"))
                dv     = pd.to_datetime(row.get("Date", pd.NaT))
                ds     = dv.strftime("%b %d") if pd.notna(dv) else "TBD"
                loc    = "vs" if row.get("IsHome", True) else "@"
                wp     = sf(row.get("TeamWinProb", np.nan), np.nan)
                spread = sf(row.get("TeamSpread",  np.nan), np.nan)
                wp_s   = f"{wp:.0%}"      if not np.isnan(wp)     else "—"
                wp_c   = "#22c55e"        if (not np.isnan(wp) and wp >= 0.5) else "#f97316"
                sp_s   = f"{spread:+.1f}" if not np.isnan(spread) else ""
                opp_r  = sf(row.get("OppRank", np.nan), np.nan)
                rank_s = f'<span style="color:#64748b;font-size:0.70rem;margin-left:4px;">#{int(opp_r)}</span>' if not np.isnan(opp_r) else ""
                blow_w  = " 💥" if str(row.get("BlowoutMode",""))   == "True" else ""
                rematch = ' <span style="color:#eab308;font-size:0.68rem;">REMATCH</span>' if str(row.get("SecondMeeting","")) == "True" else ""

                st.markdown(f"""
<div class="upcoming-row">
  <div class="upcoming-date">{ds}</div>
  <div class="upcoming-opp">{loc} {opp}{blow_w}{rematch}{rank_s}</div>
  <div style="text-align:right;min-width:90px;">
    <div style="font-size:0.88rem;font-weight:700;color:{wp_c};">{wp_s}</div>
    <div style="font-size:0.68rem;color:#64748b;">{sp_s}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    gc1, gc2 = st.columns(2)
    with gc1: games_block(boys_key,  "Boys")
    with gc2: games_block(girls_key, "Girls")

# ══════════════════════════════════════════════════════════════════════════
#  SECTION 4 – TOURNAMENT OUTLOOK  (🔒 LOCKED)
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-head">&#x1F3C6; Tournament Outlook</div>', unsafe_allow_html=True)

if not _subscribed:
    _render_lock_wall("Tournament Outlook")
else:
    def tourn_block(row, team_key, gender_label, cls, reg, pi_row):
        if row is None:
            st.markdown(f"*No tournament data for {gender_label}.*"); return

        ti      = sf(row.get("TI",           np.nan), np.nan)
        pi_disp = sf(pi_row["PowerIndex_Display"], np.nan) if pi_row is not None else np.nan
        seed    = sf(row.get("ProjectedSeed", np.nan), np.nan)
        rank_n  = sf(row.get("Rank",          np.nan), np.nan)
        qual    = is_qualified(rank_n, gender_label, cls, reg)
        rpi     = sf(row.get("RPI",           np.nan), np.nan)
        sos     = sf(row.get("SOS_EWP",       np.nan), np.nan)
        q1w = int(sf(row.get("Q1_Wins",0))); q1l = int(sf(row.get("Q1_Losses",0)))
        q2w = int(sf(row.get("Q2_Wins",0))); q2l = int(sf(row.get("Q2_Losses",0)))
        q_wins  = int(sf(row.get("QualityWins", 0)))
        bad_l   = int(sf(row.get("BadLosses",   0)))
        l5mpg   = sf(row.get("L5MarginPG",   np.nan), np.nan)
        best_w  = get(row, "BestWin", default="")
        best_m  = sf(row.get("BestWinMargin", np.nan), np.nan)

        champ_pct = np.nan; r1_opp = "—"; r1_wp = np.nan
        if not sim_df.empty and team_key:
            kc = next((c for c in sim_df.columns if "key" in c.lower()), None)
            if kc:
                sr = sim_df[sim_df[kc].astype(str) == team_key]
                if not sr.empty:
                    s0        = sr.iloc[0]
                    champ_pct = sf(s0.get("SimChampPct", np.nan), np.nan) / 100.0
                    r1_opp    = get(s0, "R1Opponent", "Round1Opp", "FirstRoundOpp")
                    r1_wp     = sf(s0.get("R1WinProb", s0.get("Round1WinProb", np.nan)), np.nan)

        qual_badge = '<span class="badge-qualified">&#x2705; QUALIFIED</span>' if qual \
            else '<span class="badge-bubble">Bubble</span>'
        seed_s   = f"#{int(seed)}"    if not np.isnan(seed)       else "?"
        rank_s   = f"#{int(rank_n)}"  if not np.isnan(rank_n)     else "—"
        champ_s  = f"{champ_pct:.1%}" if not np.isnan(champ_pct)  else "—"
        r1_wp_s  = f"{r1_wp:.0%}"     if not np.isnan(r1_wp)      else "—"
        r1_clr   = "#22c55e" if (not np.isnan(r1_wp) and r1_wp >= 0.5) else "#f97316"
        best_m_s = f" (+{best_m:.0f})" if not np.isnan(best_m)    else ""

        r1_line = (
            f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #166534;'
            f'font-size:0.88rem;color:#d1fae5;">'
            f'If season ended today &rarr; Round 1 vs <b>{r1_opp}</b>'
            f' &nbsp; <span style="color:{r1_clr};font-weight:700;">Win prob: {r1_wp_s}</span></div>'
        ) if not np.isnan(r1_wp) else ""

        st.markdown(f"""
<div class="tourn-card">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
    <span style="font-size:0.70rem;color:#86efac;text-transform:uppercase;letter-spacing:.05em;">
      {gender_label} &middot; {cls} &middot; {reg}
    </span>
    {qual_badge}
  </div>
  <div style="display:flex;gap:22px;flex-wrap:wrap;align-items:flex-start;">
    <div>
      <div class="lbl" style="color:#86efac;">Projected Seed</div>
      <div style="font-size:2rem;font-weight:800;color:#4ade80;">{seed_s}</div>
      <div style="font-size:0.78rem;color:#86efac;margin-top:2px;">Rank {rank_s} in {cls} {reg}</div>
    </div>
    <div>
      <div class="lbl" style="color:#86efac;">Ranking Metrics</div>
      <div style="font-size:0.86rem;color:#d1fae5;margin-top:4px;line-height:1.7;">
        TI: <b>{fmt(ti,".2f")}</b> &nbsp;|&nbsp;
        PI: <b>{fmt(pi_disp,".1f")}</b> &nbsp;|&nbsp;
        RPI: <b>{fmt(rpi,".4f")}</b><br>
        SOS: <b>{fmt(sos,".4f")}</b> &nbsp;|&nbsp;
        Q1: <b>{q1w}-{q1l}</b> &nbsp;|&nbsp;
        Q2: <b>{q2w}-{q2l}</b><br>
        Qual Wins: <b style="color:#4ade80;">{q_wins}</b>
        &nbsp;|&nbsp;
        Bad Losses: <b style="color:#f87171;">{bad_l}</b>
        &nbsp;|&nbsp;
        L5: <b>{cval(l5mpg) if not np.isnan(l5mpg) else "—"}</b>
      </div>
    </div>
    <div>
      <div class="lbl" style="color:#86efac;">Best Win</div>
      <div style="font-size:0.86rem;color:#86efac;margin-top:4px;">
        {best_w or "—"}{best_m_s}
      </div>
      <div style="margin-top:10px;">
        <div class="lbl" style="color:#86efac;">Sim Champ %</div>
        <div style="font-size:1.3rem;font-weight:700;color:#fbbf24;">{champ_s}</div>
      </div>
    </div>
  </div>
  {r1_line}
</div>
""", unsafe_allow_html=True)

    col_b, col_g = st.columns(2)
    with col_b:
        tourn_block(boys_row,  boys_key,  "Boys",  boys_cls,  boys_reg,  boys_pi)
    with col_g:
        tourn_block(girls_row, girls_key, "Girls", girls_cls, girls_reg, girls_pi)

# ══════════════════════════════════════════════════════════════════════════
#  SECTION 5 – SCHOOL RECORD BOOK  (FREE — community content)
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-head">&#x1F4D6; School Record Book</div>', unsafe_allow_html=True)

if ms_df.empty:
    st.info("No milestone data loaded.")
else:
    scol      = next((c for c in ms_df.columns if "school" in c.lower()), ms_df.columns[0])
    school_ms = ms_df[ms_df[scol].astype(str).str.strip().str.lower() == selected.lower().strip()]
    if school_ms.empty:
        st.info(f"No milestones on record for {selected} yet.")
    else:
        st_col = next((c for c in school_ms.columns if "status"  in c.lower()), None)
        cl_col = next((c for c in school_ms.columns if any(k in c.lower() for k in
                       ["claim","milestone","description","text","title"])), None)
        yr_col = next((c for c in school_ms.columns if "year" in c.lower() or "season" in c.lower()), None)
        gn_col = next((c for c in school_ms.columns if "gender" in c.lower()), None)
        for _, mr in school_ms.iterrows():
            status = str(mr[st_col]).strip().lower() if st_col else "pending"
            claim  = str(mr[cl_col]).strip()         if cl_col else "—"
            yr     = str(mr[yr_col]).strip()         if yr_col else ""
            gn     = str(mr[gn_col]).strip()         if gn_col else ""
            if "verified" in status:   sc, si = "ms-status-verified",  "✅ Verified"
            elif "contest" in status:  sc, si = "ms-status-contested", "⚠️ Contested"
            else:                      sc, si = "ms-status-pending",   "🕐 Pending"
            meta_s = " · ".join(b for b in [gn, yr] if b and b not in ("nan",""))
            st.markdown(f"""
<div class="ms-row">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <span class="{sc}">{si}</span>
    <span style="font-size:0.72rem;color:#475569;">{meta_s}</span>
  </div>
  <div class="ms-text">{claim}</div>
</div>
""", unsafe_allow_html=True)

    enc = selected.replace(" ", "+")
    st.markdown(
        f'<a href="/Milestones?school={enc}" target="_self" style="display:inline-block;'
        f'margin-top:8px;background:#1d4ed8;color:#fff;padding:7px 16px;border-radius:8px;'
        f'font-size:0.82rem;font-weight:600;text-decoration:none;">'
        f'&#x2795; Add a milestone for {selected}</a>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════
#  SECTION 6 – ROAD TRIP  (🔒 LOCKED)
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-head">&#x1F68C; Road Trip</div>', unsafe_allow_html=True)

if not _subscribed:
    _render_lock_wall("Road Trip")
else:
    @st.cache_data(show_spinner=False, ttl=3600)
    def load_travel():
        tp = DATA_DIR / "travel_core_v50.parquet"
        return pd.read_parquet(tp) if tp.exists() else pd.DataFrame()

    travel_df = load_travel()

    def travel_block(team_key: str, gender_label: str):
        if travel_df.empty or not team_key:
            st.markdown(f"*No travel data for {gender_label}.*")
            return

        away_games = travel_df[travel_df["AwayKey"] == team_key].copy()
        if away_games.empty:
            st.markdown(f"*No away games found for {gender_label}.*")
            return

        total_miles = away_games["MilesRoundTrip"].sum()
        total_hours = away_games["BusHours"].sum()
        avg_miles = away_games["MilesRoundTrip"].mean()
        longest = away_games["MilesOneWay"].max()
        trips = len(away_games)

        played = away_games[away_games["Played"].fillna(False)]
        road_w = (played["WinnerTeam"] == played["Away"]).sum()
        road_l = len(played) - road_w

        st.markdown(f"""
<div class="card">
  <div class="lbl">{gender_label} Travel Summary</div>
  <div class="stat-row" style="margin-top:8px;">
    <div class="stat-block">
      <div class="lbl">Season Miles</div>
      <div class="sm">{total_miles:,.0f} mi</div>
    </div>
    <div class="stat-block">
      <div class="lbl">Bus Hours</div>
      <div class="sm">{total_hours:,.1f} hrs</div>
    </div>
    <div class="stat-block">
      <div class="lbl">Avg/Trip</div>
      <div class="sm">{avg_miles:,.0f} mi</div>
    </div>
    <div class="stat-block">
      <div class="lbl">Longest Trip</div>
      <div class="sm">{longest:,.0f} mi</div>
    </div>
    <div class="stat-block">
      <div class="lbl">Road Record</div>
      <div class="sm">{road_w}-{road_l}</div>
    </div>
  </div>

  <div style="margin-top:12px;">
    <div class="lbl">Last 5 Road Trips</div>
""", unsafe_allow_html=True)

        recent = played.sort_values("Date", ascending=False).head(5)
        for _, row in recent.iterrows():
            opp = row.get("Home", "Opponent")
            miles = row["MilesRoundTrip"]
            result = "W" if row["WinnerTeam"] == row["Away"] else "L"
            margin = row.get("AwayScore", 0) - row.get("HomeScore", 0)
            date_str = pd.to_datetime(row["Date"]).strftime("%b %d")

            color = "#22c55e" if result == "W" else "#ef4444"

            st.markdown(f"""
<div style="display:flex;gap:8px;padding:6px 0;font-size:0.82rem;border-bottom:1px solid #1e293b;">
  <div style="min-width:48px;color:#64748b;">{date_str}</div>
  <div style="flex:1;color:#cbd5e1;">{opp}</div>
  <div style="min-width:60px;text-align:right;color:#94a3b8;">{miles:.0f} mi</div>
  <div style="min-width:28px;text-align:center;color:{color};font-weight:700;">{result}</div>
  <div style="min-width:36px;text-align:right;color:{color};">{margin:+.0f}</div>
</div>
""", unsafe_allow_html=True)

        enc = selected.replace(" ", "+")
        st.markdown(f"""
  </div>
  <div style="margin-top:12px;text-align:center;">
    <a href="/Road_Trips" target="_self" style="color:#38bdf8;font-size:0.82rem;font-weight:600;text-decoration:none;">
      → View full travel analysis in Road Trips
    </a>
  </div>
</div>
""", unsafe_allow_html=True)

    col_b, col_g = st.columns(2)
    with col_b: travel_block(boys_key, "Boys")
    with col_g: travel_block(girls_key, "Girls")


render_footer()
