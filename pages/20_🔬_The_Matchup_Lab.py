# pages/06__The_Model.py – THE MODEL (Single-Page Vegas Dashboard, v50 Core)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)
from auth import login_gate, logout_button, is_subscribed

import os


# ---------- PREDICTION HELPERS ----------



from sidebar_auth import render_sidebar_auth

render_sidebar_auth()



@dataclass
class WalkForwardConfig:
    min_games_before_scoring: int = 25
    rolling_window: int = 200


def _safe_to_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def _ensure_pred_cols(g: pd.DataFrame) -> pd.DataFrame:
    out = g.copy()
    for c in ["PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore", "PredTotalPoints"]:
        if c not in out.columns:
            out[c] = np.nan
    return out


def _compute_actuals(g: pd.DataFrame) -> pd.DataFrame:
    out = g.copy()
    out["PlayedBool"] = out.get("Played", False).fillna(False).astype(bool)
    hs = pd.to_numeric(out.get("HomeScore", np.nan), errors="coerce")
    aw = pd.to_numeric(out.get("AwayScore", np.nan), errors="coerce")
    out["ActualMargin"] = np.where(out["PlayedBool"], hs - aw, np.nan)
    out["ActualHomeWin"] = np.where(
        out["PlayedBool"],
        np.where(hs > aw, 1.0, np.where(hs < aw, 0.0, 0.5)),
        np.nan,
    )
    return out


def _brier(p: np.ndarray, y: np.ndarray) -> float:
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() == 0:
        return float("nan")
    return float(np.mean((p[ok] - y[ok]) ** 2))


def _mae(pred: np.ndarray, actual: np.ndarray) -> float:
    ok = np.isfinite(pred) & np.isfinite(actual)
    if ok.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs(pred[ok] - actual[ok])))


def _rmse(pred: np.ndarray, actual: np.ndarray) -> float:
    ok = np.isfinite(pred) & np.isfinite(actual)
    if ok.sum() == 0:
        return float("nan")
    return float(np.sqrt(np.mean((pred[ok] - actual[ok]) ** 2)))


def build_predictions_walkforward(
    games_core: pd.DataFrame,
    cfg: WalkForwardConfig | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    cfg = cfg or WalkForwardConfig()
    g = games_core.copy()
    g = _ensure_pred_cols(g)
    g["Date"] = _safe_to_datetime(g.get("Date", pd.Series([pd.NaT] * len(g))))
    g = _compute_actuals(g)

    keep_cols = [
        "GameID", "Date", "Season", "Gender", "Home", "Away", "HomeKey", "AwayKey",
        "IsNeutral", "HomeScore", "AwayScore", "PlayedBool",
        "PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore", "PredTotalPoints",
        "ActualHomeWin", "ActualMargin",
    ]
    keep_cols = [c for c in keep_cols if c in g.columns]
    pred_games = g[keep_cols].copy()
    pred_games = pred_games.sort_values(["Date", "GameID"], na_position="last").reset_index(drop=True)

    played = pred_games[pred_games["PlayedBool"]].copy()
    if played.empty:
        eval_df = pd.DataFrame([{
            "AsOfDate": pd.NaT, "GamesScored": 0, "RollingWindow": 0,
            "WinAccuracyPct": np.nan, "Brier": np.nan, "MAE_Margin": np.nan, "RMSE_Margin": np.nan,
        }])
        return pred_games, eval_df

    ph = pd.to_numeric(played["PredHomeWinProb"], errors="coerce").to_numpy(dtype=float)
    y  = pd.to_numeric(played["ActualHomeWin"],   errors="coerce").to_numpy(dtype=float)
    pm = pd.to_numeric(played["PredMargin"],       errors="coerce").to_numpy(dtype=float)
    am = pd.to_numeric(played["ActualMargin"],     errors="coerce").to_numpy(dtype=float)

    pred_home_win   = ph >= 0.5
    actual_home_win = y  >= 0.5
    correct = (pred_home_win == actual_home_win) & np.isfinite(ph) & np.isfinite(y)
    dates   = played["Date"].to_numpy()

    rows = []
    for i in range(len(played)):
        if i + 1 < cfg.min_games_before_scoring:
            continue
        start      = max(0, (i + 1) - cfg.rolling_window)
        idx        = slice(start, i + 1)
        window_len = i + 1 - start
        correct_rate = float(np.mean(correct[idx])) if window_len > 0 else float("nan")
        rows.append({
            "AsOfDate":       pd.to_datetime(dates[i]),
            "GamesScored":    int(i + 1),
            "RollingWindow":  int(window_len),
            "WinAccuracyPct": 100.0 * correct_rate if correct_rate == correct_rate else np.nan,
            "Brier":          _brier(ph[idx], y[idx]),
            "MAE_Margin":     _mae(pm[idx], am[idx]),
            "RMSE_Margin":    _rmse(pm[idx], am[idx]),
        })

    eval_df = pd.DataFrame(rows)
    if eval_df.empty:
        eval_df = pd.DataFrame([{
            "AsOfDate":       played["Date"].max(),
            "GamesScored":    int(len(played)),
            "RollingWindow":  int(min(len(played), cfg.rolling_window)),
            "WinAccuracyPct": 100.0 * float(np.mean(correct)) if len(played) else np.nan,
            "Brier":          _brier(ph, y),
            "MAE_Margin":     _mae(pm, am),
            "RMSE_Margin":    _rmse(pm, am),
        }])

    for c in ["WinAccuracyPct", "Brier", "MAE_Margin", "RMSE_Margin"]:
        if c in eval_df.columns:
            eval_df[c] = pd.to_numeric(eval_df[c], errors="coerce").round(4)

    return pred_games, eval_df


# ---------- PAGE CONFIG ----------

st.set_page_config(
    page_title="🔬 The Matchup Lab – Analytics207.com",
    page_icon="🔬",
    layout="wide",
)

apply_global_layout_tweaks()
login_gate(required=False)
logout_button()
render_logo()
render_page_header(
    title="🔬 THE MATCHUP LAB",
    definition="Matchup Lab (n.): A coach-grade analytics workspace built to dissect, compare, and forecast game outcomes.",
    subtitle="Coach-grade matchup intelligence — scouting reports, schedule analysis, and calibrated game forecasts.",
)

# ══════════════════════════════════════════════════════════════════════════
#  🔒 SUBSCRIBER GATE — entire page is locked
# ══════════════════════════════════════════════════════════════════════════
if not is_subscribed():
    components.html("""
<style>* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: transparent; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; color: #f1f5f9; }</style>
<div style="background:linear-gradient(135deg,#0f172a,#1a1a2e);
            border:1px solid rgba(245,158,11,0.3);border-radius:14px;
            padding:32px 28px;text-align:center;">
  <div style="font-size:2.5rem;margin-bottom:10px;">🔒</div>
  <div style="font-size:1.1rem;font-weight:800;color:#fbbf24;margin-bottom:6px;">
    THE MATCHUP LAB — Premium Subscribers Only
  </div>
  <div style="font-size:0.85rem;color:#94a3b8;max-width:460px;margin:0 auto;">
    Subscribe to unlock coach-grade matchup intelligence: calibrated game forecasts,
    full scouting reports, strength of schedule deep-dives, form &amp; momentum analysis,
    and the complete metrics breakdown — the tools serious coaches rely on.
  </div>
</div>
""", height=200, scrolling=False)
    render_footer()
    st.stop()


# ---------- GLOBAL CSS ----------

st.markdown("""
<style>
.vegas-card {
    background: radial-gradient(circle at top left, #0b1120, #020617 55%);
    border: 1px solid #1f2937;
    border-radius: 20px;
    padding: 16px 20px;
    box-shadow: 0 18px 45px rgba(0,0,0,0.85);
    margin-bottom: 18px;
}
.vegas-title { font-size:0.78rem; text-transform:uppercase; letter-spacing:0.10em; color:#9ca3af; }
.vegas-subtitle { font-size:1.25rem; font-weight:800; color:#e5e7eb; margin-top:6px; }
.vegas-body { font-size:0.9rem; color:#d1d5db; margin-top:8px; line-height:1.35; }
.vegas-section-label { margin-top:14px; margin-bottom:6px; font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.12em; color:#f97316; }
.vegas-row { margin-top:10px; }
.chip { display:inline-flex; align-items:center; padding:3px 11px; border-radius:999px; font-size:0.74rem; font-weight:750; letter-spacing:0.04em; border:1px solid rgba(148,163,184,0.22); }
.chip-green { background:rgba(34,197,94,0.14); color:#4ade80; border-color:rgba(34,197,94,0.40); }
.chip-red   { background:rgba(239,68,68,0.14);  color:#fca5a5; border-color:rgba(239,68,68,0.40); }
.chip-gold  { background:rgba(234,179,8,0.14);  color:#facc15; border-color:rgba(234,179,8,0.40); }
.chip-blue  { background:rgba(59,130,246,0.14); color:#93c5fd; border-color:rgba(59,130,246,0.40); }
.chip-gray  { background:rgba(148,163,184,0.10);color:#e5e7eb; border-color:rgba(148,163,184,0.30); }
.win-bar-bg { background-color:#111827; height:10px; border-radius:999px; overflow:hidden; }
.small-note { color:#9ca3af; font-size:0.78rem; }
</style>
""", unsafe_allow_html=True)


# ---------- HTML HELPERS ----------

def render_stat_card(title: str, subtitle: str, lines, accent: str = "#22c55e"):
    body_html = "<br>".join(lines)
    st.markdown(f"""
<div class="vegas-card">
  <div class="vegas-title">{title}</div>
  <div class="vegas-subtitle" style="color:{accent};">{subtitle}</div>
  <div class="vegas-body">{body_html}</div>
</div>
""", unsafe_allow_html=True)


def conf_chip(win_pct: float) -> str:
    if win_pct >= 75:
        return '<span class="chip chip-green">🔥 HIGH CONFIDENCE</span>'
    if win_pct >= 60:
        return '<span class="chip chip-gold">⚠️ MEDIUM CONFIDENCE</span>'
    return '<span class="chip chip-blue">🧊 LOW CONFIDENCE</span>'


# ---------- DATA LOADING (v50) ----------

ROOT     = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

TEAMS_FILE = DATA_DIR / "core" / "teams_team_season_analytics_v50.parquet"
GAMES_FILE = DATA_DIR / "public" / "games_public_v50.parquet"
PIR_FILE   = DATA_DIR / "core" / "teams_power_index_v50.parquet"


@st.cache_data(ttl=600, show_spinner=False)
def read_parquet_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path).copy()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def load_v50_data():
    teams = read_parquet_safe(TEAMS_FILE)
    games = read_parquet_safe(GAMES_FILE)

    if "Team" in teams.columns:
        teams["Team"] = teams["Team"].astype(str).str.strip()
    if "Gender" in teams.columns:
        teams["Gender"] = teams["Gender"].astype(str).str.title().str.strip()
    if "Class" in teams.columns:
        teams["Class"] = teams["Class"].astype(str).str.upper().str.strip()
    if "Region" in teams.columns:
        teams["Region"] = teams["Region"].astype(str).str.title().str.strip()
    if "TeamKey" in teams.columns:
        teams["TeamKey"] = teams["TeamKey"].astype(str).str.replace(r"\s+", "", regex=True).str.strip()

    if "TeamKey" not in teams.columns or teams["TeamKey"].eq("").all():
        teams["TeamKey"] = (
            teams["Team"].str.replace(r"\s+", "", regex=True).str.strip()
            + teams["Gender"].str.strip()
            + teams["Class"].str.strip()
            + teams["Region"].str.strip()
        )

    pir_raw = read_parquet_safe(PIR_FILE)
    if not pir_raw.empty and "PowerIndex_Display" in pir_raw.columns:
        pir_small = pir_raw[["TeamKey", "Gender", "PowerIndex_Display"]].copy()
        pir_small["Gender"] = pir_small["Gender"].astype(str).str.title().str.strip()
        pir_small["Team"]   = pir_small["TeamKey"].str.replace(r"(Boys|Girls).*$", "", regex=True).str.strip()
        pir_small = pir_small.rename(columns={"PowerIndex_Display": "PIR"})
        teams = teams.merge(pir_small[["Team", "Gender", "PIR"]], on=["Team", "Gender"], how="left")
    else:
        teams["PIR"] = np.nan

    if "PIR" in teams.columns and pd.to_numeric(teams["PIR"], errors="coerce").notna().any():
        teams["Rating"] = pd.to_numeric(teams["PIR"], errors="coerce")
    elif "TI" in teams.columns:
        teams["Rating"] = pd.to_numeric(teams["TI"], errors="coerce")
    elif "PI" in teams.columns:
        teams["Rating"] = pd.to_numeric(teams["PI"], errors="coerce")
    else:
        teams["Rating"] = np.nan

    if not games.empty:
        if "Date" in games.columns:
            games["Date"] = pd.to_datetime(games["Date"], errors="coerce")
        if "HomeKey" in games.columns:
            games["HomeKey"] = games["HomeKey"].astype(str).str.replace(r"\s+", "", regex=True).str.strip()
        if "AwayKey" in games.columns:
            games["AwayKey"] = games["AwayKey"].astype(str).str.replace(r"\s+", "", regex=True).str.strip()
        games = _ensure_pred_cols(games)
        games = _compute_actuals(games)

    return teams, games


teams_df, games_df = load_v50_data()



if teams_df.empty or games_df.empty:
    st.info("THE MODEL data is not available yet.")
    render_footer()
    st.stop()


# ---------- FILTERS ----------

st.markdown("#### 🔍 Game Filters (Head-to-Head Analysis)")
col_g, col_c, col_r = st.columns([1, 1, 1])

with col_g:
    selected_gender = st.selectbox("Gender", ["Boys", "Girls"], index=0, key="model_v50_gender")
with col_c:
    selected_class  = st.selectbox("Class",  ["All Classes", "A", "B", "C", "D", "S"], key="model_v50_class")
with col_r:
    selected_region = st.selectbox("Region", ["All Regions", "North", "South"], key="model_v50_region")


def filter_teams(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Gender" in out.columns and selected_gender:
        out = out[out["Gender"] == selected_gender]
    if "Class" in out.columns and selected_class and selected_class != "All Classes":
        out = out[out["Class"] == selected_class]
    if "Region" in out.columns and selected_region and selected_region != "All Regions":
        out = out[out["Region"] == selected_region]
    return out


teams_filtered = filter_teams(teams_df)

if "Team" not in teams_filtered.columns:
    st.error("teams_team_season_analytics_v50.parquet does not expose a Team column.")
    render_footer()
    st.stop()


# ---------- MATCHUP CHOOSER (scheduled opponents only) ----------

lab_teams = teams_filtered["Team"].dropna().sort_values().unique().tolist()
if len(lab_teams) < 2:
    st.warning("Not enough teams available in this filter to build a matchup. Try widening filters.")
    render_footer()
    st.stop()

name_to_key = dict(zip(teams_filtered["Team"], teams_filtered["TeamKey"]))
key_to_name = dict(zip(teams_filtered["TeamKey"], teams_filtered["Team"]))

col_h, col_a = st.columns(2)
with col_h:
    home_team = st.selectbox("Home Team (Team 1)", lab_teams, key="lab_v50_home")

home_key = name_to_key.get(home_team, "")
gdf_gender = games_df[games_df["Gender"] == selected_gender] if "Gender" in games_df.columns else games_df

scheduled_opponent_keys: set = set()
if home_key and "HomeKey" in gdf_gender.columns:
    scheduled_opponent_keys.update(
        gdf_gender.loc[gdf_gender["HomeKey"] == home_key, "AwayKey"].dropna().tolist()
    )
    scheduled_opponent_keys.update(
        gdf_gender.loc[gdf_gender["AwayKey"] == home_key, "HomeKey"].dropna().tolist()
    )

away_options = sorted([
    key_to_name[k] for k in scheduled_opponent_keys
    if k in key_to_name and key_to_name[k] in lab_teams and key_to_name[k] != home_team
])

if not away_options:
    away_options = [t for t in lab_teams if t != home_team]

with col_a:
    away_team = st.selectbox("Away Team (Team 2)", away_options, index=0, key="lab_v50_away")


# ---------- GET TEAM ROWS ----------

def get_team_row(team_name: str) -> pd.Series:
    sub = teams_filtered[teams_filtered["Team"] == team_name]
    return sub.iloc[0] if not sub.empty else pd.Series(dtype=object)


h_row = get_team_row(home_team)
a_row = get_team_row(away_team)


# ---------- PREDICTION LOOKUP (parquet only — no fallback math) ----------

def _safe_float(x, default=None):
    try:    return float(x)
    except: return default


def _edge(fav_val, dog_val, default=0.0):
    fv = _safe_float(fav_val, None)
    dv = _safe_float(dog_val, None)
    if fv is None or dv is None: return default
    return fv - dv


def _is_nan(x):   return isinstance(x, float) and np.isnan(x)
def fmt0(x):      return "—" if x is None or _is_nan(x) else f"{float(x):.0f}"
def fmt1(x):      return "—" if x is None or _is_nan(x) else f"{float(x):.1f}"


def lookup_prediction(home_row: pd.Series, away_row: pd.Series):
    hk = home_row.get("TeamKey")
    ak = away_row.get("TeamKey")
    if not hk or not ak or "HomeKey" not in games_df.columns:
        return None

    sub = games_df[(games_df["HomeKey"] == hk) & (games_df["AwayKey"] == ak)].copy()
    flipped = False
    if sub.empty:
        sub = games_df[(games_df["HomeKey"] == ak) & (games_df["AwayKey"] == hk)].copy()
        flipped = True
    if sub.empty:
        return None

    row = sub.sort_values(["Date", "GameID"], ascending=False).iloc[0]
    p_home  = float(row.get("PredHomeWinProb", np.nan))
    margin  = float(row.get("PredMargin",      np.nan))
    score_h = float(row.get("PredHomeScore",   np.nan))
    score_a = float(row.get("PredAwayScore",   np.nan))
    total   = float(row.get("PredTotalPoints", np.nan))

    if flipped:
        p_home  = 1.0 - p_home if np.isfinite(p_home) else p_home
        margin  = -margin      if np.isfinite(margin)  else margin
        score_h, score_a = score_a, score_h

    return {
        "PredHomeWinProb": p_home,
        "PredMargin":      margin,
        "PredHomeScore":   score_h,
        "PredAwayScore":   score_a,
        "PredTotalPoints": total,
    }


# ---------- HEAD-TO-HEAD & RECENT FORM HELPERS ----------

def head_to_head_games(games: pd.DataFrame, key_a: str, key_b: str) -> pd.DataFrame:
    if not {"HomeKey", "AwayKey"}.issubset(games.columns):
        return pd.DataFrame()
    played_col = "Played" if "Played" in games.columns else "PlayedBool"
    played = games[games[played_col]].copy()
    mask = (
        ((played["HomeKey"] == key_a) & (played["AwayKey"] == key_b)) |
        ((played["HomeKey"] == key_b) & (played["AwayKey"] == key_a))
    )
    return played[mask].sort_values("Date", ascending=False).head(10)


def recent_form_games(games: pd.DataFrame, team_key: str, n: int = 5) -> pd.DataFrame:
    if not {"HomeKey", "AwayKey"}.issubset(games.columns):
        return pd.DataFrame()
    played_col = "Played" if "Played" in games.columns else "PlayedBool"
    played = games[games[played_col]].copy()
    mask = (played["HomeKey"] == team_key) | (played["AwayKey"] == team_key)
    return played[mask].sort_values("Date", ascending=False).head(n)


pred = lookup_prediction(h_row, a_row)

if pred is None or not np.isfinite(pred.get("PredHomeWinProb", np.nan)):
    st.warning(
        f"⚠️ No prediction found for **{away_team} at {home_team}**. "
        "This matchup is not on the schedule or has not been built yet. "
        "Select a scheduled opponent from the Away Team dropdown."
    )
    render_footer()
    st.stop()

win_prob = pred["PredHomeWinProb"]
margin   = pred["PredMargin"]
total    = pred["PredTotalPoints"]
score_h  = pred["PredHomeScore"]
score_a  = pred["PredAwayScore"]

score_h = round(float(score_h))
score_a = round(float(score_a))

fav_is_home  = win_prob >= 0.5
margin_edge  = float(margin)
fav_team     = home_team if fav_is_home else away_team
fav_row      = h_row     if fav_is_home else a_row
dog_row      = a_row     if fav_is_home else h_row
dog_team     = away_team if fav_is_home else home_team

pir_fav  = _safe_float(fav_row.get("PIR"), None)
pir_dog  = _safe_float(dog_row.get("PIR"), None)
pir_edge = (pir_fav - pir_dog) if (pir_fav is not None and pir_dog is not None) else np.nan

net_fav  = _safe_float(fav_row.get("MarginPG"), None)
net_dog  = _safe_float(dog_row.get("MarginPG"), None)
net_edge = (net_fav - net_dog) if (net_fav is not None and net_dog is not None) else np.nan

l5_fav   = _safe_float(fav_row.get("L5MarginPG"), None)
l5_dog   = _safe_float(dog_row.get("L5MarginPG"), None)
l5_edge  = (l5_fav - l5_dog) if (l5_fav is not None and l5_dog is not None) else np.nan

r_edge          = _edge(fav_row.get("PIR"),        dog_row.get("PIR"),        default=0.0)
ppg_edge        = _edge(fav_row.get("PPG"),        dog_row.get("PPG"),        default=0.0)
def_edge        = _edge(dog_row.get("OPPG"),       fav_row.get("OPPG"),       default=0.0)
r_edge_display  = f"{r_edge:+.1f}" if abs(r_edge) > 1e-9 else "0.0"
l5_edge_val     = _edge(fav_row.get("L5MarginPG"), dog_row.get("L5MarginPG"), default=0.0)
l5_edge_display = f"{l5_edge_val:+.1f}" if abs(l5_edge_val) > 1e-9 else "0.0"
net_edge_val    = _edge(fav_row.get("MarginPG"),   dog_row.get("MarginPG"),   default=0.0)
net_edge_display= f"{net_edge_val:+.1f}" if abs(net_edge_val) > 1e-9 else "0.0"

home_win_pct = win_prob * 100.0
away_win_pct = 100.0 - home_win_pct
fav_win_pct  = max(home_win_pct, away_win_pct)
spread       = -abs(margin_edge)

if fav_win_pct >= 75:
    conf_text = "HIGH CONFIDENCE";   conf_cls = "pill pill-green"
elif fav_win_pct >= 60:
    conf_text = "MEDIUM CONFIDENCE"; conf_cls = "pill pill-gold"
else:
    conf_text = "LOW CONFIDENCE";    conf_cls = "pill pill-blue"


# ---------- METRIC CONFIG ----------

metrics_core = [
    ("RATING",    "PIR",    True,  1, "Power Index Rating (PIR scale)."),
    ("HEAL POINTS","TI",    True,  1, "Tournament Index (Heal Points)."),
    ("WINS",      "Wins",   True,  0, "Total wins this season."),
    ("LOSSES",    "Losses", False, 0, "Total losses this season."),
    ("WIN %",     "WinPct", True,  1, "Season win percentage."),
]
metrics_scoring = [
    ("OFFENSE PPG",    "PPG",          True,  1, "Average points scored per game."),
    ("DEFENSE OPP",    "OPPG",         False, 1, "Opponent points per game (lower better)."),
    ("NET MARGIN PPG", "MarginPG",     True,  1, "Average scoring margin."),
    ("MARGIN VOL",     "MarginStd",    False, 1, "Std dev of all margins."),
    ("RECENT VOL L10", "MarginStdL10", False, 1, "Std dev last 10 margins."),
    ("L5 PPG",         "L5PPG",        True,  1, "Points per game over last 5."),
    ("L5 MARGIN",      "L5MarginPG",   True,  1, "Margin per game over last 5."),
]
metrics_home_road = [
    ("HOME GAMES",    "HomeGames",    True,  0, "Games played at home."),
    ("HOME WIN %",    "HomeWinPct",   True,  3, "Win% at home."),
    ("HOME MARGIN",   "HomeMarginPG", True,  1, "Avg margin at home."),
    ("ROAD GAMES",    "RoadGames",    True,  0, "Games played on the road."),
    ("ROAD WIN %",    "RoadWinPct",   True,  3, "Win% on the road."),
    ("ROAD MARGIN",   "RoadMarginPG", True,  1, "Avg margin on the road."),
    ("HOME/ROAD DIFF","HomeRoadDiff", True,  1, "Home minus road margin."),
]
metrics_close_blowout = [
    ("CLOSE GAMES",        "CloseGames",       True,  0, "Games decided by few points."),
    ("CLOSE WINS",         "CloseWins",        True,  0, "Wins in close games."),
    ("CLOSE LOSSES",       "CloseLosses",      False, 0, "Losses in close games."),
    ("CLOSE WIN %",        "CloseWinPct",      True,  3, "Win% in close games."),
    ("CLOSE GAME RATE",    "CloseGameRate",    True,  3, "Share of games that are close."),
    ("ONE POSSESSION RATE","OnePossessionRate",True,  3, "Share decided by 1–3 pts."),
    ("BLOWOUT GAMES",      "BlowoutGames",     True,  0, "Games that were blowouts."),
    ("BLOWOUT RATE",       "BlowoutRate",      True,  3, "Share of games that are blowouts."),
    ("BLOWOUT MARGIN",     "BlowoutMarginPG",  True,  1, "Avg margin in blowouts."),
]
metrics_margin_buckets = [
    ("GMS 0–3",    "GamesMargin0to3",    True,  0, "Games decided by 0–3 points."),
    ("WIN % 0–3",  "WinPctMargin0to3",   True,  1, "Win% in 0–3 pt games."),
    ("GMS 4–10",   "GamesMargin4to10",   True,  0, "Games decided by 4–10 points."),
    ("WIN % 4–10", "WinPctMargin4to10",  True,  1, "Win% in 4–10 pt games."),
    ("GMS 11–20",  "GamesMargin11to20",  True,  0, "Games decided by 11–20 points."),
    ("WIN % 11–20","WinPctMargin11to20", True,  1, "Win% in 11–20 pt games."),
    ("GMS 21+",    "GamesMargin21plus",  True,  0, "Games decided by 21+ points."),
    ("WIN % 21+",  "WinPctMargin21plus", True,  1, "Win% in 21+ pt games."),
]
metrics_early_late = [
    ("EARLY GAMES",    "EarlyGames",    True,  0, "Games in early season segment."),
    ("EARLY WINS",     "EarlyWins",     True,  0, "Wins early season."),
    ("EARLY MARGIN",   "EarlyMarginPG", True,  1, "Avg margin early season."),
    ("LATE GAMES",     "LateGames",     True,  0, "Games in late season segment."),
    ("LATE WINS",      "LateWins",      True,  0, "Wins late season."),
    ("LATE MARGIN",    "LateMarginPG",  True,  1, "Avg margin late season."),
    ("LATE SKEW FLAG", "IsLateSkew",    True,  0, "1 if team skews late season."),
]
metrics_rest = [
    ("AVG REST (DAYS)",  "AvgRestDays",    True,  1, "Average rest days between games."),
    ("SHORT REST G",     "ShortRestGames", True,  0, "Games on short rest."),
    ("SHORT REST SHARE", "ShortRestShare", True,  1, "Share of games on short rest."),
    ("LONG REST G",      "LongRestGames",  True,  0, "Games on long rest."),
    ("LONG REST SHARE",  "LongRestShare",  True,  1, "Share of games on long rest."),
]
metrics_sos_quality = [
    ("EXPECTED WINS",  "ExpectedWins",    True,  1, "Modeled wins from scoring."),
    ("SOS (EWP)",      "SOS_EWP",         True,  1, "Strength of schedule via expected wins."),
    ("SCHED ADJ WINS", "ScheduleAdjWins", True,  1, "Wins adjusted for schedule."),
    ("LUCK Z",         "LuckZ",           False, 2, "Luck vs expectation (Z-score)."),
    ("QUALITY WINS",   "QualityWins",     True,  0, "High-quality wins."),
    ("BAD LOSSES",     "BadLosses",       False, 0, "Losses to weaker teams."),
    ("TOP-25 WINS",    "Top25Wins",       True,  0, "Wins vs statewide top-25."),
    ("TOP-25 LOSSES",  "Top25Losses",     False, 0, "Losses vs top-25."),
]
metrics_vs_bands = [
    ("GMS VS TOP",       "GamesVsTop",     True,  0, "Games vs top tier."),
    ("WIN % VS TOP",     "WinPctVsTop",    True,  1, "Win% vs top tier."),
    ("MARGIN VS TOP",    "MarginVsTop",    True,  1, "Margin vs top tier."),
    ("GMS VS MID",       "GamesVsMiddle",  True,  0, "Games vs middle tier."),
    ("WIN % VS MID",     "WinPctVsMiddle", True,  1, "Win% vs middle tier."),
    ("MARGIN VS MID",    "MarginVsMiddle", True,  1, "Margin vs middle tier."),
    ("GMS VS BOTTOM",    "GamesVsBottom",  True,  0, "Games vs bottom tier."),
    ("WIN % VS BOTTOM",  "WinPctVsBottom", True,  1, "Win% vs bottom tier."),
    ("MARGIN VS BOTTOM", "MarginVsBottom", True,  1, "Margin vs bottom tier."),
    ("GMS VS TOP25",     "GamesVsTop25",   True,  0, "Games vs statewide top-25."),
    ("WIN % VS TOP25",   "WinPctVsTop25",  True,  1, "Win% vs top-25."),
    ("MARGIN VS TOP25",  "MarginVsTop25",  True,  1, "Margin vs top-25."),
]

metric_groups = [
    ("Core power & record",           metrics_core),
    ("Scoring & efficiency",          metrics_scoring),
    ("Home / road profile",           metrics_home_road),
    ("Close & blowouts",              metrics_close_blowout),
    ("Margin buckets",                metrics_margin_buckets),
    ("Early / late & skew",           metrics_early_late),
    ("Rest & recovery",               metrics_rest),
    ("Strength of schedule & quality",metrics_sos_quality),
    ("Performance by opponent tier",  metrics_vs_bands),
]

PERCENT_KEYS = {
    "WinPct", "HomeWinPct", "RoadWinPct", "CloseWinPct", "BlowoutRate",
    "ShortRestShare", "LongRestShare", "CloseGameRate", "OnePossessionRate",
    "WinPctMargin0to3", "WinPctMargin4to10", "WinPctMargin11to20", "WinPctMargin21plus",
    "WinPctVsTop", "WinPctVsMiddle", "WinPctVsBottom", "WinPctVsTop25",
}

SECTION_EMOJI = {
    "CORE POWER & RECORD":"💪","SCORING & EFFICIENCY":"🔥","HOME / ROAD PROFILE":"🏠",
    "CLOSE & BLOWOUTS":"⚖️","MARGIN BUCKETS":"🧮","EARLY / LATE & SKEW":"⏱️",
    "REST & RECOVERY":"🛌","STRENGTH OF SCHEDULE & QUALITY":"🧭","PERFORMANCE BY OPPONENT TIER":"🆚",
}


# ---------- METRIC BOX HELPERS ----------

def get_float(row, key, default=0.0):
    try:
        v = row.get(key, default)
        return float(v) if v is not None else float(default)
    except: return float(default)


def _isnan_num(x): return isinstance(x, float) and np.isnan(x)


def barsplit(edge, base=50.0, scale=1.0, cap=18.0):
    if edge is None or _isnan_num(edge): return 50.0
    try:    shift = float(edge) * float(scale)
    except: return 50.0
    shift = max(-cap, min(cap, shift))
    return float(base + shift)


bar_split = barsplit


def fmt_num_metric(val, places):
    try:
        if val is None: return "—"
        v = float(val)
        if np.isnan(v): return "—"
        return f"{v:.{places}f}"
    except: return "—"


def fmt_driver(x, places=1):
    try:
        v = float(x)
        if np.isnan(v): return "—"
        return f"{v:.{places}f}"
    except: return "—"


def metric_box_html(label, key, higher_better, places, note, home_team, away_team):
    hv = get_float(h_row, key, np.nan)
    av = get_float(a_row, key, np.nan)
    if key in PERCENT_KEYS:
        if not _isnan_num(hv): hv = hv * 100.0
        if not _isnan_num(av): av = av * 100.0
    diff   = hv - av
    edge   = diff if higher_better else -diff
    p_left = barsplit(edge, scale=2.0, cap=18)
    hv_txt = fmt_num_metric(hv, places)
    av_txt = fmt_num_metric(av, places)
    return f"""
<div class="mbox">
  <div class="mlabel">{label}</div>
  <div class="mnote">{note}</div>
  <div class="splitbar splitbar-sm"
       style="margin-top:10px; --pLeft:{p_left:.1f}; --leftColor:#22c55e; --rightColor:#f97316;">
    <div class="lbl left">{home_team} {hv_txt}</div>
    <div class="lbl right">{av_txt} {away_team}</div>
  </div>
</div>
"""


# ---------- MINI-BAR DRIVER VALUES ----------

pir_home = _safe_float(h_row.get("PIR"),        np.nan)
pir_away = _safe_float(a_row.get("PIR"),        np.nan)
net_home = _safe_float(h_row.get("MarginPG"),   np.nan)
net_away = _safe_float(a_row.get("MarginPG"),   np.nan)
l5_home  = _safe_float(h_row.get("L5MarginPG"), np.nan)
l5_away  = _safe_float(a_row.get("L5MarginPG"), np.nan)

pir_edge_ha = (pir_home - pir_away) if (np.isfinite(pir_home) and np.isfinite(pir_away)) else 0.0
net_edge_ha = (net_home - net_away) if (np.isfinite(net_home) and np.isfinite(net_away)) else 0.0
l5_edge_ha  = (l5_home  - l5_away)  if (np.isfinite(l5_home)  and np.isfinite(l5_away))  else 0.0

pir_p_left = bar_split(pir_edge_ha, scale=1.5, cap=18)
net_p_left = bar_split(net_edge_ha, scale=2.0, cap=18)
l5_p_left  = bar_split(l5_edge_ha,  scale=2.0, cap=18)

pir_left_lbl  = f"{home_team} {fmt_driver(pir_home, 1)}"
pir_right_lbl = f"{fmt_driver(pir_away, 1)} {away_team}"
net_left_lbl  = f"{home_team} {fmt_driver(net_home, 1)}"
net_right_lbl = f"{fmt_driver(net_away, 1)} {away_team}"
l5_left_lbl   = f"{home_team} {fmt_driver(l5_home, 1)}"
l5_right_lbl  = f"{fmt_driver(l5_away, 1)} {away_team}"

source_chip = f"<span class='pill pill-gray' style='margin-left:6px'>LIVE</span>"

# Team records for hero display
h_wins_n  = int(_safe_float(h_row.get("Wins",   0), 0) or 0)
h_losses_n = int(_safe_float(h_row.get("Losses", 0), 0) or 0)
a_wins_n  = int(_safe_float(a_row.get("Wins",   0), 0) or 0)
a_losses_n = int(_safe_float(a_row.get("Losses", 0), 0) or 0)
h_record  = f"{h_wins_n}–{h_losses_n}"
a_record  = f"{a_wins_n}–{a_losses_n}"


# ---------- HERO HTML (Forecast Card) ----------

hero_html = f"""
<style>
  body {{
    margin:0; background:transparent;
    font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;
    color:#e5e7eb;
  }}
  .card {{
    background:radial-gradient(circle at top left,#142040,#060c1a);
    border:1px solid rgba(96,165,250,0.55); border-radius:22px;
    padding:24px 24px 24px; box-shadow:0 28px 60px rgba(15,23,42,0.95);
  }}
  .pill {{ display:inline-flex; align-items:center; padding:2px 10px; border-radius:999px;
           font-size:10px; font-weight:800; letter-spacing:0.12em; text-transform:uppercase;
           background:#020617; border:1px solid rgba(55,65,81,0.9); white-space:nowrap; }}
  .pill-green {{ color:#22c55e; border-color:#22c55e; }}
  .pill-gold  {{ color:#facc15; border-color:#facc15; }}
  .pill-blue  {{ color:#60a5fa; border-color:#60a5fa; }}
  .pill-gray  {{ color:#e5e7eb; border-color:#374151; }}
  .splitbar {{
    --pLeft:50; --leftColor:#22c55e; --rightColor:#f97316;
    position:relative; border-radius:999px; overflow:hidden;
    border:1px solid transparent; box-shadow:inset 0 0 0 1px rgba(255,255,255,.10);
    background:
      linear-gradient(#0000,#0000) padding-box,
      linear-gradient(90deg,
        var(--leftColor) 0%,
        var(--leftColor) calc(var(--pLeft)*1%),
        var(--rightColor) calc(var(--pLeft)*1%),
        var(--rightColor) 100%) border-box;
  }}
  .splitbar::after {{
    content:""; position:absolute; left:50%; top:2px; bottom:2px; width:2px;
    background:rgba(255,255,255,.60); box-shadow:0 0 8px rgba(255,255,255,.35);
    pointer-events:none; z-index:30;
  }}
  .splitbar .lbl {{
    position:absolute; top:50%; transform:translateY(-50%);
    font-weight:950; color:rgba(255,255,255,.95);
    text-shadow:0 1px 2px rgba(0,0,0,.55); white-space:nowrap; z-index:20;
    padding:1px 6px; border-radius:999px;
    background:rgba(2,6,23,.22); backdrop-filter:blur(1px);
  }}
  .splitbar .lbl.left  {{ left:10px; }}
  .splitbar .lbl.right {{ right:10px; }}
  .splitbar-lg {{ height:36px; }} .splitbar-md {{ height:20px; }}
  .splitbar-lg .lbl {{ font-size:13px; }} .splitbar-md .lbl {{ font-size:10px; }}
  .minibar-wrap {{ width:min(580px,100%); margin:6px auto 0; display:grid; gap:8px; }}
  .minibar-cap  {{ font-size:12px; color:#9ca3af; text-align:center; margin-top:-2px; }}
  .stat-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:20px; }}
  .stat-box {{ background:rgba(15,23,42,0.65); border:1px solid rgba(148,163,184,0.14);
               border-radius:14px; padding:14px; text-align:center; }}
  .stat-label {{ font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#9ca3af; }}
  .stat-val {{ font-size:22px; font-weight:950; margin-top:4px; }}
  .stat-sub {{ font-size:11px; color:#9ca3af; margin-top:2px; }}
</style>

<div class="card">
  <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px;">
    <div>
      <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.13em; color:#9ca3af;">
        🔬 THE MATCHUP LAB {source_chip}
      </div>
      <div style="margin-top:6px; font-size:22px; font-weight:950; color:#ffffff; line-height:1.1;">
        {away_team} at {home_team}
      </div>
      <div style="margin-top:5px; font-size:13px; color:#9ca3af;">
        <span style="color:#f97316; font-weight:800;">{a_record}</span>
        &nbsp;<span style="color:#6b7280;">away</span>&nbsp;&nbsp;&middot;&nbsp;&nbsp;
        <span style="color:#22c55e; font-weight:800;">{h_record}</span>
        &nbsp;<span style="color:#6b7280;">home</span>
      </div>
      <div style="margin-top:4px; font-size:11px; color:#6b7280;">
        Calibrated model forecast &nbsp;·&nbsp; coach-grade matchup intelligence
      </div>
    </div>
    <div style="text-align:right; flex-shrink:0;">
      <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.13em; color:#9ca3af;">
        Confidence
      </div>
      <div style="margin-top:6px;">
        <span class="{conf_cls}">{conf_text}</span>
      </div>
      <div style="margin-top:4px; font-size:12px; color:#9ca3af;">
        Edge {margin_edge:+.1f} pts
      </div>
    </div>
  </div>

  <div style="margin-top:22px; text-align:center;">
    <div style="font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#9ca3af; margin-bottom:8px;">
      Projected Final Score
    </div>
    <div style="font-size:34px; font-weight:950; color:#ffffff; letter-spacing:-0.02em;">
      {home_team}&nbsp;<span style="color:#22c55e">{score_h}</span>
      &nbsp;&ndash;&nbsp;
      <span style="color:#f97316">{score_a}</span>&nbsp;{away_team}
    </div>
    <div style="margin-top:6px; font-size:13px;">
      <span style="color:#22c55e; font-weight:800;">{h_record}</span>
      <span style="color:#6b7280;">&nbsp;home&nbsp;&nbsp;&middot;&nbsp;&nbsp;</span>
      <span style="color:#f97316; font-weight:800;">{a_record}</span>
      <span style="color:#6b7280;">&nbsp;away</span>
    </div>
    <div style="margin-top:6px; font-size:13px; color:#9ca3af;">
      {fav_team} favored by {abs(spread):.1f} &nbsp;&middot;&nbsp; O/U {total:.0f}
    </div>
  </div>

  <div style="margin-top:18px; display:flex; justify-content:center;">
    <div class="splitbar splitbar-lg"
         style="width:min(760px,100%); --pLeft:{home_win_pct:.0f}; --leftColor:#22c55e; --rightColor:#f97316;">
      <div class="lbl left">{home_team} {home_win_pct:.0f}%</div>
      <div class="lbl right">{away_win_pct:.0f}% {away_team}</div>
    </div>
  </div>

  <div class="stat-grid">
    <div class="stat-box">
      <div class="stat-label">Win Probability</div>
      <div class="stat-val" style="color:#22c55e">{fav_win_pct:.0f}%</div>
      <div class="stat-sub">{fav_team}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Model Edge</div>
      <div class="stat-val" style="color:#facc15">{abs(margin_edge):.1f}</div>
      <div class="stat-sub">predicted margin</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">O / U Total</div>
      <div class="stat-val" style="color:#c7d2fe">{total:.0f}</div>
      <div class="stat-sub">combined pts</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">PIR Edge</div>
      <div class="stat-val" style="color:{'#22c55e' if pir_edge_ha >= 0 else '#f97316'}">{pir_edge_ha:+.1f}</div>
      <div class="stat-sub">{'home' if pir_edge_ha >= 0 else 'away'} adv</div>
    </div>
  </div>

  <div style="margin-top:22px;">
    <div style="font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#9ca3af; text-align:center; margin-bottom:12px;">
      Key Driver Bars &mdash; bigger side = advantage
    </div>
    <div class="minibar-wrap">
      <div class="splitbar splitbar-md"
           style="--pLeft:{pir_p_left:.0f}; --leftColor:#22c55e; --rightColor:#f97316;">
        <div class="lbl left">{pir_left_lbl}</div>
        <div class="lbl right">{pir_right_lbl}</div>
      </div>
      <div class="minibar-cap">PIR RATING EDGE {pir_edge_ha:+.1f}</div>

      <div class="splitbar splitbar-md"
           style="--pLeft:{net_p_left:.0f}; --leftColor:#22c55e; --rightColor:#f97316;">
        <div class="lbl left">{net_left_lbl}</div>
        <div class="lbl right">{net_right_lbl}</div>
      </div>
      <div class="minibar-cap">NET MARGIN EDGE {net_edge_ha:+.1f}</div>

      <div class="splitbar splitbar-md"
           style="--pLeft:{l5_p_left:.0f}; --leftColor:#22c55e; --rightColor:#f97316;">
        <div class="lbl left">{l5_left_lbl}</div>
        <div class="lbl right">{l5_right_lbl}</div>
      </div>
      <div class="minibar-cap">LAST 5 FORM EDGE {l5_edge_ha:+.1f}</div>
    </div>
  </div>
</div>
"""

# ---------- MATCHUP TABS ----------

home_key = str(h_row.get("TeamKey", "")).strip()
away_key = str(a_row.get("TeamKey", "")).strip()

tab_forecast, tab_scout, tab_h2h, tab_momentum, tab_sos, tab_breakdown = st.tabs([
    "🎯 Forecast",
    "📋 Scouting Report",
    "🔄 Series History",
    "📈 Form & Momentum",
    "🏆 Schedule Analysis",
    "⚔️ Tale of the Tape",
])


# ── TAB 1: FORECAST ──────────────────────────────────────────────────

with tab_forecast:
    components.html(hero_html, height=660, scrolling=False)

    st.markdown("---")
    st.markdown("##### 🧠 What the Model Sees")

    edge_factors = []

    if abs(pir_edge_ha) > 5:
        leader = home_team if pir_edge_ha > 0 else away_team
        edge_factors.append(
            f"**Power Index advantage** — {leader} holds a {abs(pir_edge_ha):.1f} PIR edge, "
            "indicating a meaningful talent gap that the model weighs heavily."
        )

    if abs(net_edge_ha) > 3:
        leader = home_team if net_edge_ha > 0 else away_team
        edge_factors.append(
            f"**Scoring margin edge** — {leader} outscores opponents by {abs(net_edge_ha):.1f} "
            "pts/game more than the other team across the full season."
        )

    if abs(l5_edge_ha) > 3:
        leader = home_team if l5_edge_ha > 0 else away_team
        edge_factors.append(
            f"**Recent momentum** — {leader} has been {abs(l5_edge_ha):.1f} pts/game better "
            "over the last 5 games, suggesting current form favors them."
        )

    sos_h_v = _safe_float(h_row.get("SOS_EWP"), None)
    sos_a_v = _safe_float(a_row.get("SOS_EWP"), None)
    if sos_h_v is not None and sos_a_v is not None:
        sos_diff = sos_h_v - sos_a_v
        if abs(sos_diff) > 0.5:
            harder = home_team if sos_diff < 0 else away_team
            edge_factors.append(
                f"**Schedule context** — {harder} has faced a notably tougher schedule "
                f"(SOS gap: {abs(sos_diff):.2f}), which the model adjusts for in its projection."
            )

    qw_h_v = _safe_float(h_row.get("QualityWins"), 0)
    qw_a_v = _safe_float(a_row.get("QualityWins"), 0)
    if qw_h_v != qw_a_v:
        leader = home_team if qw_h_v > qw_a_v else away_team
        edge_factors.append(
            f"**Quality résumé** — {leader} has more quality wins "
            f"({max(qw_h_v, qw_a_v):.0f} vs {min(qw_h_v, qw_a_v):.0f}), "
            "proving their record against strong competition."
        )

    if not edge_factors:
        edge_factors.append(
            "This is a tightly matched game — the model sees minimal statistical edge in either direction."
        )

    col_factors, col_type = st.columns([2, 1])
    with col_factors:
        for i, factor in enumerate(edge_factors[:4], 1):
            st.markdown(f"{i}. {factor}")
    with col_type:
        close_h_r = _safe_float(h_row.get("CloseGameRate"), None)
        close_a_r = _safe_float(a_row.get("CloseGameRate"), None)
        if close_h_r is not None and close_a_r is not None:
            avg_close = (close_h_r + close_a_r) / 2
            if avg_close > 0.40:
                game_type = "Classic — expect a close, contested game"
                gt_icon = "🔥"
            elif abs(margin_edge) > 15:
                game_type = "Mismatch — one side has clear statistical dominance"
                gt_icon = "📊"
            else:
                game_type = "Competitive — model favors one side but it's winnable"
                gt_icon = "⚖️"
            st.info(f"**{gt_icon} Game Type**\n\n{game_type}")


# ── TAB 2: SCOUTING REPORT ────────────────────────────────────────────

with tab_scout:
    st.markdown(f"#### 📋 Full Scouting Report — {away_team} at {home_team}")
    st.caption(
        "Each section breaks down both teams across the full metrics catalog. "
        "🟢 = Home team advantage  ·  🟠 = Away team advantage  ·  ➖ = Even"
    )

    section_descriptions = {
        "Core power & record": (
            "The foundation of any scouting report. PIR is our single best predictor of future "
            "performance — it captures overall team quality adjusted for schedule. Win % and "
            "record give context but PIR tells you who is actually better."
        ),
        "Scoring & efficiency": (
            "Offensive output and defensive resistance. Net margin per game is the most predictive "
            "scoring stat — teams that consistently outscore opponents win. Watch for a large "
            "defensive gap (OPPG) as that often predicts lopsided games."
        ),
        "Home / road profile": (
            "Home court is real in high school basketball. A team with a large Home/Road "
            "differential may underperform expectations on the road. Road Win % below 0.400 "
            "combined with a high Home Win % signals heavy home-court dependency."
        ),
        "Close & blowouts": (
            "Clutch vs. dominant profile. High close-game win % signals a battle-tested team "
            "that competes late. High blowout rate reveals a team that physically outmatches "
            "opponents. In playoff settings, both matter — know which type you're facing."
        ),
        "Margin buckets": (
            "Win/loss records sorted by victory margin. Coaches use this to identify if a team "
            "wins ugly (lots of 0–3 pt wins) or routinely dominates (21+ pt margins). "
            "A high 0–3 pt win rate with a low 21+ rate may indicate a team that relies on luck."
        ),
        "Early / late & skew": (
            "Seasonal trajectory. A team flagged with late-season skew has improved significantly "
            "from early to late in the season — they may be peaking at playoff time. "
            "Compare early vs. late margin to see if a team is trending up or fading."
        ),
        "Rest & recovery": (
            "Schedule density and fatigue. Teams on short rest (0–1 days between games) often "
            "underperform their averages. If one team in this matchup has a meaningful rest "
            "advantage, the model factors that in — and so should you."
        ),
        "Strength of schedule & quality": (
            "Schedule difficulty and résumé quality. Expected Wins vs. Actual Wins reveals "
            "over/underperformance. Quality Wins and Bad Losses are the two most important "
            "résumé factors for tournament seeding. Schedule-Adj Wins normalizes for who they played."
        ),
        "Performance by opponent tier": (
            "The most coaching-relevant section. How does each team actually perform against "
            "top-tier, middle-tier, and bottom-tier competition? A team with a great overall "
            "record built against weak competition (high Win% vs Bottom, low Win% vs Top) "
            "is very different from a team that beats everybody."
        ),
    }

    for section_title, metrics in metric_groups:
        desc = section_descriptions.get(section_title, "")
        key_upper = section_title.strip().upper()
        emoji = SECTION_EMOJI.get(key_upper, "📊")
        is_first = (section_title == "Core power & record")

        with st.expander(f"{emoji} {section_title.title()}", expanded=is_first):
            if desc:
                st.caption(f"*{desc}*")

            header_cols = st.columns([3, 1, 1, 1, 3])
            header_cols[0].markdown("<small style='color:#6b7280'>METRIC</small>", unsafe_allow_html=True)
            header_cols[1].markdown(f"<small style='color:#22c55e'>{home_team}</small>", unsafe_allow_html=True)
            header_cols[2].markdown("<small style='color:#6b7280'>ADV</small>", unsafe_allow_html=True)
            header_cols[3].markdown(f"<small style='color:#f97316'>{away_team}</small>", unsafe_allow_html=True)
            header_cols[4].markdown("<small style='color:#6b7280'>WHAT IT MEANS</small>", unsafe_allow_html=True)
            st.divider()

            for label, col_key, higher_better, places, note in metrics:
                hv = get_float(h_row, col_key, np.nan)
                av = get_float(a_row, col_key, np.nan)
                if col_key in PERCENT_KEYS:
                    if not _isnan_num(hv): hv = hv * 100.0
                    if not _isnan_num(av): av = av * 100.0
                hv_txt = fmt_num_metric(hv, places)
                av_txt = fmt_num_metric(av, places)
                diff = (hv - av) if (not _isnan_num(hv) and not _isnan_num(av)) else np.nan
                edge = diff if higher_better else -diff
                if not _isnan_num(edge) and edge > 0.01:
                    adv = "🟢"
                elif not _isnan_num(edge) and edge < -0.01:
                    adv = "🟠"
                else:
                    adv = "➖"

                row_cols = st.columns([3, 1, 1, 1, 3])
                row_cols[0].markdown(
                    f"<span style='font-size:13px; font-weight:700; color:#e5e7eb'>{label}</span>",
                    unsafe_allow_html=True
                )
                row_cols[1].markdown(f"**{hv_txt}**")
                row_cols[2].markdown(
                    f"<div style='text-align:center; font-size:14px'>{adv}</div>",
                    unsafe_allow_html=True
                )
                row_cols[3].markdown(f"**{av_txt}**")
                row_cols[4].markdown(
                    f"<small style='color:#6b7280'>{note}</small>",
                    unsafe_allow_html=True
                )


# ── TAB 3: SERIES HISTORY ──────────────────────────────────────────────

with tab_h2h:
    st.write("")

    h2h_df = head_to_head_games(games_df, home_key, away_key)

    if h2h_df.empty:
        st.info(f"No head-to-head games found between {home_team} and {away_team} this season.")
    else:
        h_wins = 0
        a_wins_count = 0
        margin_trend = []
        game_cards_html = ""

        for _, g in h2h_df.iterrows():
            hs  = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
            as_ = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
            home_name = str(g.get("Home", ""))
            away_name = str(g.get("Away", ""))
            date_str  = str(g.get("Date", ""))[:10]

            if pd.notna(hs) and pd.notna(as_):
                home_team_is_home = (home_name == home_team)
                margin_from_home  = (hs - as_) if home_team_is_home else (as_ - hs)
                margin_trend.append((date_str, float(margin_from_home)))

                home_won = hs > as_
                winner   = home_name if home_won else away_name
                w_score  = int(max(hs, as_))
                l_score  = int(min(hs, as_))

                if winner == home_team:
                    h_wins += 1
                    w_color, l_color = "#22c55e", "#f97316"
                    w_name, l_name   = home_team, away_team
                else:
                    a_wins_count += 1
                    w_color, l_color = "#f97316", "#22c55e"
                    w_name, l_name   = away_team, home_team

                m_sign = "+" if margin_from_home > 0 else ""
                game_cards_html += f"""
<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
            border-radius:14px;margin-bottom:6px;
            background:rgba(15,23,42,0.40);
            border:1px solid rgba(148,163,184,0.14);
            font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;">
  <span style="color:#9ca3af;font-size:11px;min-width:80px;letter-spacing:0.04em;">{date_str}</span>
  <span style="color:{w_color};font-size:13px;font-weight:900;flex:1;">&#10003; {w_name}</span>
  <span style="color:#facc15;font-size:14px;font-weight:950;">{w_score}&ndash;{l_score}</span>
  <span style="color:rgba(148,163,184,0.55);font-size:11px;padding:0 6px;">
    {m_sign}{margin_from_home:.0f} {home_team}
  </span>
  <span style="color:{l_color};font-size:13px;flex:1;text-align:right;">{l_name}</span>
</div>"""

        tally_html = f"""
<div style="display:flex;gap:16px;margin-top:16px;
            font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;">
  <div style="flex:1;background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.30);
              border-radius:14px;padding:16px;text-align:center;">
    <div style="font-size:42px;font-weight:950;color:#22c55e;">{h_wins}</div>
    <div style="font-size:12px;color:#e5e7eb;font-weight:800;margin-top:4px;">{home_team}</div>
    <div style="font-size:11px;color:#9ca3af;margin-top:2px;">season series wins</div>
  </div>
  <div style="flex:1;background:rgba(249,115,22,0.08);border:1px solid rgba(249,115,22,0.30);
              border-radius:14px;padding:16px;text-align:center;">
    <div style="font-size:42px;font-weight:950;color:#f97316;">{a_wins_count}</div>
    <div style="font-size:12px;color:#e5e7eb;font-weight:800;margin-top:4px;">{away_team}</div>
    <div style="font-size:11px;color:#9ca3af;margin-top:2px;">season series wins</div>
  </div>
</div>"""

        full_h2h_html = f"""
<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;
             font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;
             color:#e5e7eb;">
<div style="background:radial-gradient(circle at top left,#142040,#060c1a);
            border:1px solid rgba(96,165,250,0.25);border-radius:22px;
            padding:22px 24px;box-shadow:0 18px 45px rgba(0,0,0,0.85);">
  <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.13em;color:#9ca3af;">
    Season Series
  </div>
  <div style="margin-top:6px;font-size:20px;font-weight:950;color:#ffffff;">
    {home_team} vs {away_team}
  </div>
  <div style="margin-top:4px;font-size:12px;color:#9ca3af;">
    All matchups this season &middot; most recent first &middot; margin shown from {home_team} perspective
  </div>
  <div style="margin-top:16px;">
    {game_cards_html}
  </div>
  {tally_html}
</div>
</body></html>"""

        h2h_height = min(140 + len(h2h_df) * 52 + 120, 680)
        components.html(full_h2h_html, height=h2h_height, scrolling=True)

        if len(margin_trend) >= 2:
            st.markdown(f"##### Margin Trend — from {home_team} perspective")
            mt_df = pd.DataFrame(sorted(margin_trend), columns=["Date", "Margin"])
            mt_df["Winner"] = mt_df["Margin"].apply(lambda x: home_team if x > 0 else away_team)
            fig_h2h = px.bar(
                mt_df, x="Date", y="Margin",
                color="Winner",
                color_discrete_map={home_team: "#22c55e", away_team: "#f97316"},
                labels={"Margin": "Score Margin", "color": "Winner"},
            )
            fig_h2h.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e5e7eb"), showlegend=True,
                yaxis=dict(gridcolor="rgba(148,163,184,0.1)"),
                xaxis=dict(showgrid=False),
                margin=dict(t=20, b=20, l=20, r=20), height=260,
            )
            fig_h2h.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_dash="dash")
            st.plotly_chart(fig_h2h, use_container_width=True)
            st.caption(
                f"Bars above zero = {home_team} win · Below zero = {away_team} win · "
                "Bar height = margin of victory"
            )


# ── TAB 4: FORM & MOMENTUM ────────────────────────────────────────────

with tab_momentum:
    st.markdown(f"#### Form & Momentum — Last 10 Games")
    st.caption(
        "Extended recent form window. **Momentum score** = sum of recent game margins "
        "(positive = winning big, negative = losing ground). Updated each night."
    )

    col_home_form, col_away_form = st.columns(2)

    for col, team_name, team_key, accent, accent_rgb in [
        (col_home_form, home_team, home_key, "#22c55e", "34,197,94"),
        (col_away_form, away_team, away_key, "#f97316", "249,115,22"),
    ]:
        with col:
            recent = recent_form_games(games_df, team_key, n=10)
            st.markdown(f"**{team_name}**")

            if recent.empty:
                st.info("No recent games found.")
                continue

            margins_list = []
            results_list = []
            for _, g in recent.iterrows():
                hs  = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
                as_ = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
                is_home = (str(g.get("HomeKey", "")) == team_key)
                if pd.notna(hs) and pd.notna(as_):
                    tm_s = float(hs) if is_home else float(as_)
                    op_s = float(as_) if is_home else float(hs)
                    margins_list.append(tm_s - op_s)
                    results_list.append("W" if tm_s > op_s else "L")

            if margins_list:
                momentum_score = sum(margins_list)
                win_streak = 0
                for r in results_list:
                    if r == "W":
                        win_streak += 1
                    else:
                        break
                loss_streak = 0
                for r in results_list:
                    if r == "L":
                        loss_streak += 1
                    else:
                        break

                m_color = "#22c55e" if momentum_score > 0 else "#ef4444"
                st.markdown(
                    f"<span style='font-size:24px;font-weight:900;color:{m_color}'>"
                    f"{'▲' if momentum_score > 0 else '▼'} {abs(momentum_score):.0f}</span>"
                    f"&nbsp;<span style='font-size:12px;color:#9ca3af'>momentum score</span>",
                    unsafe_allow_html=True
                )
                if win_streak >= 2:
                    st.success(f"🔥 {win_streak}-game win streak")
                elif loss_streak >= 2:
                    st.error(f"❄️ {loss_streak}-game losing streak")

            game_rows_html = ""
            for _, g in recent.iterrows():
                hs  = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
                as_ = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
                g_home  = str(g.get("Home", ""))
                g_away  = str(g.get("Away", ""))
                date    = str(g.get("Date", ""))[:10]
                is_home = (str(g.get("HomeKey", "")) == team_key)
                opp     = g_away if is_home else g_home

                if pd.notna(hs) and pd.notna(as_):
                    tm_score    = int(hs) if is_home else int(as_)
                    op_score    = int(as_) if is_home else int(hs)
                    won         = tm_score > op_score
                    res_label   = "W" if won else "L"
                    res_color   = "#22c55e" if won else "#ef4444"
                    res_bg      = "rgba(34,197,94,0.08)" if won else "rgba(239,68,68,0.08)"
                    venue       = "Home" if is_home else "Away"
                    game_margin = tm_score - op_score
                    m_sign      = "+" if game_margin > 0 else ""
                    m_col       = "#22c55e" if game_margin > 0 else "#ef4444"

                    game_rows_html += f"""
<div style="display:flex;align-items:center;gap:8px;padding:7px 10px;
            border-radius:10px;margin-bottom:4px;
            background:{res_bg};border:1px solid {res_color}22;
            font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;">
  <span style="background:{res_color};color:#0f172a;font-size:10px;font-weight:900;
               padding:2px 7px;border-radius:999px;text-align:center;">{res_label}</span>
  <span style="color:#e5e7eb;font-size:12px;font-weight:800;flex:1;">vs {opp}</span>
  <span style="color:#facc15;font-size:12px;font-weight:950;">{tm_score}&ndash;{op_score}</span>
  <span style="color:{m_col};font-size:10px;font-weight:800">{m_sign}{game_margin}</span>
  <span style="color:#9ca3af;font-size:9px;">{venue}&middot;{date}</span>
</div>"""

            form_card_html = f"""
<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;color:#e5e7eb;
             font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;">
<div style="background:radial-gradient(circle at top left,#142040,#060c1a);
            border:1px solid rgba({accent_rgb},0.35);border-radius:18px;
            padding:16px 18px;box-shadow:0 18px 45px rgba(0,0,0,0.85);">
  {game_rows_html}
</div>
</body></html>"""

            components.html(form_card_html, height=500, scrolling=True)

            if margins_list:
                fig_form = go.Figure()
                game_nums   = list(range(len(margins_list), 0, -1))
                bar_colors  = ["#22c55e" if m > 0 else "#ef4444" for m in margins_list]
                fig_form.add_trace(go.Bar(
                    x=game_nums, y=margins_list,
                    marker_color=bar_colors,
                    name="Margin",
                ))
                fig_form.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e5e7eb"), showlegend=False,
                    xaxis=dict(
                        title="Games ago (1 = most recent)",
                        tickvals=game_nums, showgrid=False,
                    ),
                    yaxis=dict(title="Margin", gridcolor="rgba(148,163,184,0.1)"),
                    margin=dict(t=10, b=30, l=30, r=10), height=170,
                )
                fig_form.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_dash="dash")
                st.plotly_chart(fig_form, use_container_width=True)
                st.caption("Game margin trend — green bars = wins, red = losses.")


# ── TAB 5: SCHEDULE ANALYSIS ──────────────────────────────────────────

with tab_sos:
    st.markdown("#### Schedule Analysis — Strength of Schedule Deep Dive")
    st.caption(
        "**SOS EWP** = the win percentage an average team would be expected to have against "
        "this schedule. Higher = harder schedule. **Schedule-Adj Wins** normalizes the win "
        "total for who they actually played. **Luck Z** = how much they over/underperformed "
        "statistical expectations (z-score; >1.5 = lucky, <−1.5 = unlucky)."
    )

    sos_h_val  = _safe_float(h_row.get("SOS_EWP"),         None)
    sos_a_val  = _safe_float(a_row.get("SOS_EWP"),         None)
    exp_h      = _safe_float(h_row.get("ExpectedWins"),     None)
    exp_a      = _safe_float(a_row.get("ExpectedWins"),     None)
    act_h      = _safe_float(h_row.get("Wins"),             None)
    act_a      = _safe_float(a_row.get("Wins"),             None)
    luck_h     = _safe_float(h_row.get("LuckZ"),            None)
    luck_a     = _safe_float(a_row.get("LuckZ"),            None)
    sadj_h     = _safe_float(h_row.get("ScheduleAdjWins"),  None)
    sadj_a     = _safe_float(a_row.get("ScheduleAdjWins"),  None)
    qw_h2      = _safe_float(h_row.get("QualityWins"),      0)
    qw_a2      = _safe_float(a_row.get("QualityWins"),      0)
    bl_h       = _safe_float(h_row.get("BadLosses"),        0)
    bl_a       = _safe_float(a_row.get("BadLosses"),        0)
    t25w_h     = _safe_float(h_row.get("Top25Wins"),        0)
    t25w_a     = _safe_float(a_row.get("Top25Wins"),        0)
    t25l_h     = _safe_float(h_row.get("Top25Losses"),      0)
    t25l_a     = _safe_float(a_row.get("Top25Losses"),      0)

    # SOS summary side-by-side
    sos_cols = st.columns(2)
    for i, (team, sos_val, exp, act, luck, sadj, qw, bl, t25w, t25l, color) in enumerate([
        (home_team, sos_h_val, exp_h, act_h, luck_h, sadj_h, qw_h2, bl_h, t25w_h, t25l_h, "#22c55e"),
        (away_team, sos_a_val, exp_a, act_a, luck_a, sadj_a, qw_a2, bl_a, t25w_a, t25l_a, "#f97316"),
    ]):
        with sos_cols[i]:
            st.markdown(f"<span style='font-size:16px;font-weight:900;color:{color}'>{team}</span>", unsafe_allow_html=True)
            sos_pct = f"{sos_val:.3f}" if sos_val is not None else "—"
            exp_str = f"{exp:.1f}"     if exp  is not None else "—"
            act_str = f"{int(act)}"    if act  is not None else "—"
            ovr_str = ""
            if exp is not None and act is not None:
                diff    = act - exp
                ovr_str = f"({'+' if diff >= 0 else ''}{diff:.1f} vs expected)"
            luck_str = f"{luck:+.2f}"   if luck  is not None else "—"
            sadj_str = f"{sadj:.1f}"    if sadj  is not None else "—"

            luck_flag = ""
            if luck is not None:
                if luck > 1.5:   luck_flag = " 🍀 lucky"
                elif luck < -1.5: luck_flag = " 💔 unlucky"

            st.markdown(f"""
| Metric | Value |
|---|---|
| SOS (EWP) | **{sos_pct}** |
| Expected Wins | {exp_str} |
| Actual Wins | **{act_str}** {ovr_str} |
| Schedule-Adj Wins | {sadj_str} |
| Luck Z-Score | {luck_str}{luck_flag} |
| Quality Wins | **{int(qw) if qw is not None else '—'}** |
| Bad Losses | **{int(bl) if bl is not None else '—'}** |
| Top-25 Wins | {int(t25w) if t25w is not None else '—'} |
| Top-25 Losses | {int(t25l) if t25l is not None else '—'} |
""")

    st.markdown("---")

    # Opponent tier breakdown
    st.markdown("##### Opponent Tier Performance")
    st.caption(
        "Win% and scoring margin broken down by the quality of opponent. "
        "**Top Tier** is the most important column for evaluating playoff readiness."
    )

    tiers = [
        ("vs Top Tier",    "GamesVsTop",    "WinPctVsTop",    "MarginVsTop"),
        ("vs Middle Tier", "GamesVsMiddle", "WinPctVsMiddle", "MarginVsMiddle"),
        ("vs Bottom Tier", "GamesVsBottom", "WinPctVsBottom", "MarginVsBottom"),
        ("vs Top 25",      "GamesVsTop25",  "WinPctVsTop25",  "MarginVsTop25"),
    ]

    tier_rows = []
    for tier_label, g_key, wp_key, m_key in tiers:
        for team, row in [(home_team, h_row), (away_team, a_row)]:
            games_n = _safe_float(row.get(g_key), None)
            wp      = _safe_float(row.get(wp_key), None)
            margin  = _safe_float(row.get(m_key),  None)
            if games_n is not None and games_n > 0:
                tier_rows.append({
                    "Team": team, "Tier": tier_label,
                    "Games": games_n,
                    "Win%": (wp * 100 if wp is not None else None),
                    "Margin": margin,
                })

    if tier_rows:
        tier_df = pd.DataFrame(tier_rows)

        fig_tier = px.bar(
            tier_df[tier_df["Win%"].notna()],
            x="Tier", y="Win%", color="Team", barmode="group",
            color_discrete_map={home_team: "#22c55e", away_team: "#f97316"},
            labels={"Win%": "Win %", "Tier": "Opponent Tier"},
            text="Win%",
        )
        fig_tier.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
        fig_tier.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb"), legend=dict(bgcolor="rgba(0,0,0,0)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.1)", range=[0, 115], title="Win %"),
            xaxis=dict(showgrid=False),
            margin=dict(t=30, b=20, l=20, r=20), height=320,
        )
        st.plotly_chart(fig_tier, use_container_width=True)
        st.caption("Win % vs each opponent tier. Focus on 'vs Top Tier' — that's where seedings are decided.")

        fig_margin = px.bar(
            tier_df[tier_df["Margin"].notna()],
            x="Tier", y="Margin", color="Team", barmode="group",
            color_discrete_map={home_team: "#22c55e", away_team: "#f97316"},
            labels={"Margin": "Avg Margin", "Tier": "Opponent Tier"},
            text="Margin",
        )
        fig_margin.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_margin.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb"), legend=dict(bgcolor="rgba(0,0,0,0)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.1)", title="Avg Margin"),
            xaxis=dict(showgrid=False),
            margin=dict(t=30, b=20, l=20, r=20), height=300,
        )
        fig_margin.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_dash="dash")
        st.plotly_chart(fig_margin, use_container_width=True)
        st.caption(
            "Avg scoring margin vs each tier. A negative margin vs top tier is still informative — "
            "close losses vs elite teams is very different from blowout losses."
        )
    else:
        st.info("Opponent tier data not available for this matchup.")

    # Expected vs Actual Wins
    st.markdown("---")
    st.markdown("##### Expected vs Actual Wins")
    st.caption(
        "Teams winning more than expected may be clutch or benefiting from schedule luck. "
        "Teams below expectation may be underperforming their talent. "
        "Both extremes are meaningful for tournament projection."
    )

    exp_act_data = []
    for team, exp, act in [(home_team, exp_h, act_h), (away_team, exp_a, act_a)]:
        if exp is not None and act is not None:
            exp_act_data.append({"Team": team, "Type": "Expected", "Wins": round(exp, 1)})
            exp_act_data.append({"Team": team, "Type": "Actual",   "Wins": float(act)})

    if exp_act_data:
        exp_act_df = pd.DataFrame(exp_act_data)
        fig_expact = px.bar(
            exp_act_df, x="Team", y="Wins", color="Type", barmode="group",
            color_discrete_map={"Expected": "rgba(148,163,184,0.55)", "Actual": "#facc15"},
            text="Wins",
        )
        fig_expact.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_expact.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb"), legend=dict(bgcolor="rgba(0,0,0,0)"),
            yaxis=dict(gridcolor="rgba(148,163,184,0.1)", title="Wins"),
            xaxis=dict(showgrid=False),
            margin=dict(t=30, b=20, l=20, r=20), height=280,
        )
        st.plotly_chart(fig_expact, use_container_width=True)


# ── TAB 6: TALE OF THE TAPE ────────────────────────────────────────────

with tab_breakdown:
    st.write("")

    tape_metrics = [
        ("PIR Rating",    "PIR",          True,  1),
        ("Win %",         "WinPct",       True,  1),
        ("Offense PPG",   "PPG",          True,  1),
        ("Defense OPPG",  "OPPG",         False, 1),
        ("Net Margin",    "MarginPG",     True,  1),
        ("L5 Margin",     "L5MarginPG",   True,  1),
        ("SOS (EWP)",     "SOS_EWP",      True,  3),
        ("Expected Wins", "ExpectedWins", True,  1),
        ("Close Win %",   "CloseWinPct",  True,  1),
        ("Quality Wins",  "QualityWins",  True,  0),
        ("Home Win %",    "HomeWinPct",   True,  1),
        ("Road Win %",    "RoadWinPct",   True,  1),
    ]

    labels_t, home_vals_t, away_vals_t, places_list = [], [], [], []

    for label, col, higher_better, places in tape_metrics:
        vh = pd.to_numeric(h_row.get(col, np.nan), errors="coerce")
        va = pd.to_numeric(a_row.get(col, np.nan), errors="coerce")
        if pd.isna(vh) or pd.isna(va):
            continue
        vh, va = float(vh), float(va)
        if col in PERCENT_KEYS:
            vh, va = vh * 100, va * 100
        labels_t.append(label)
        home_vals_t.append(vh)
        away_vals_t.append(va)
        places_list.append(places)

    if len(labels_t) >= 3:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=labels_t,
            x=[-abs(v) for v in home_vals_t],
            orientation="h",
            name=home_team,
            marker=dict(color="rgba(34,197,94,0.85)", line=dict(color="#4ade80", width=1)),
            text=[f"{abs(v):.{places_list[i]}f}" for i, v in enumerate(home_vals_t)],
            textposition="inside",
            textfont=dict(color="#ffffff", size=13, family="ui-sans-serif,system-ui,sans-serif"),
            insidetextanchor="middle",
            hovertemplate="%{y}: %{text}<extra>" + home_team + "</extra>",
        ))

        fig.add_trace(go.Bar(
            y=labels_t,
            x=[abs(v) for v in away_vals_t],
            orientation="h",
            name=away_team,
            marker=dict(color="rgba(249,115,22,0.85)", line=dict(color="#fb923c", width=1)),
            text=[f"{abs(v):.{places_list[i]}f}" for i, v in enumerate(away_vals_t)],
            textposition="inside",
            textfont=dict(color="#ffffff", size=13, family="ui-sans-serif,system-ui,sans-serif"),
            insidetextanchor="middle",
            hovertemplate="%{y}: %{text}<extra>" + away_team + "</extra>",
        ))

        max_val = max(
            max(abs(v) for v in home_vals_t),
            max(abs(v) for v in away_vals_t),
        ) * 1.20

        fig.update_layout(
            barmode="relative",
            bargap=0.25,
            xaxis=dict(
                range=[-max_val, max_val],
                showticklabels=False, showgrid=False,
                zeroline=True, zerolinecolor="rgba(255,255,255,0.25)", zerolinewidth=2,
            ),
            yaxis=dict(
                autorange="reversed",
                tickfont=dict(color="#e5e7eb", size=13, family="ui-sans-serif,system-ui,sans-serif"),
                gridcolor="rgba(148,163,184,0.06)",
            ),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb", family="ui-sans-serif,system-ui,sans-serif"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="center", x=0.5,
                font=dict(color="#e5e7eb", size=14), bgcolor="rgba(0,0,0,0)",
            ),
            margin=dict(t=60, b=30, l=120, r=30),
            height=520,
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"\u2190 {home_team} bars extend left  ·  "
            f"{away_team} bars extend right \u2192  |  "
            "Longer bar = higher raw value. Defense OPPG: lower is better (bar reflects inverted rank)."
        )

        # Coaching edge insights
        st.markdown("---")
        st.markdown("##### Coaching Edge — Key Matchup Factors")
        st.caption(
            "Auto-generated insights based on each team's statistical profile. "
            "These are the factors most likely to influence how this specific game unfolds."
        )

        insights = []

        home_road_h = _safe_float(h_row.get("HomeRoadDiff"), None)
        home_road_a = _safe_float(a_row.get("HomeRoadDiff"), None)
        if home_road_h is not None and home_road_h > 3:
            insights.append(
                f"**{home_team} home court is real** — they are +{home_road_h:.1f} pts/game "
                "better at home vs on the road. Visiting teams have struggled here all season."
            )
        if home_road_a is not None and home_road_a < 1.5:
            insights.append(
                f"**{away_team} travels well** — home/road differential of only {home_road_a:.1f} "
                "suggests they compete equally well in hostile environments."
            )

        close_h_rate = _safe_float(h_row.get("CloseGameRate"), None)
        close_wp_h   = _safe_float(h_row.get("CloseWinPct"),   None)
        close_a_rate = _safe_float(a_row.get("CloseGameRate"), None)
        close_wp_a   = _safe_float(a_row.get("CloseWinPct"),   None)
        if close_wp_h is not None and close_h_rate is not None and close_h_rate > 0.30 and close_wp_h > 0.60:
            insights.append(
                f"**{home_team} is clutch** — {close_wp_h*100:.0f}% win rate in close games "
                f"with {close_h_rate*100:.0f}% of their games decided late. They know how to finish."
            )
        if close_wp_a is not None and close_a_rate is not None and close_a_rate > 0.30 and close_wp_a > 0.60:
            insights.append(
                f"**{away_team} clutch factor** — {close_wp_a*100:.0f}% close-game win rate. "
                "Do not count on them folding in the fourth quarter."
            )

        bl_h2 = _safe_float(h_row.get("BadLosses"), 0)
        bl_a2 = _safe_float(a_row.get("BadLosses"), 0)
        if bl_h2 and bl_h2 > 0:
            insights.append(
                f"**{home_team} vulnerability** — {int(bl_h2)} bad loss(es) this season indicate "
                "they can be beaten by lower-rated teams. A trap game risk exists here."
            )
        if bl_a2 and bl_a2 > 0:
            insights.append(
                f"**{away_team} vulnerability** — {int(bl_a2)} bad loss(es). "
                "Tendency to underperform vs weaker competition; consistency is a question mark."
            )

        late_h = _safe_float(h_row.get("IsLateSkew"), None)
        late_a = _safe_float(a_row.get("IsLateSkew"), None)
        if late_h and late_h == 1:
            insights.append(
                f"**{home_team} is peaking** — late-season skew flag is set. "
                "Their recent form is significantly better than early-season numbers suggest. "
                "Full-season stats may underrate them right now."
            )
        if late_a and late_a == 1:
            insights.append(
                f"**{away_team} is trending up** — late skew flag active. "
                "This team has been improving and may be better than their season line shows."
            )

        luck_h_v = _safe_float(h_row.get("LuckZ"), None)
        luck_a_v = _safe_float(a_row.get("LuckZ"), None)
        if luck_h_v is not None and luck_h_v > 1.8:
            insights.append(
                f"**{home_team} regression risk** — Luck Z of {luck_h_v:.2f} means they have "
                "significantly outperformed statistical expectations. Expect some mean reversion."
            )
        if luck_a_v is not None and luck_a_v < -1.8:
            insights.append(
                f"**{away_team} due for a bounce-back** — Luck Z of {luck_a_v:.2f} means they "
                "have underperformed their underlying metrics. They may be better than their record."
            )

        if not insights:
            insights.append(
                "No standout coaching-edge factors detected beyond the primary model output. "
                "Both teams appear consistent with their statistical profiles."
            )

        for insight in insights:
            st.markdown(f"- {insight}")

    else:
        st.info("Not enough stat data to render comparison chart.")


render_footer()
