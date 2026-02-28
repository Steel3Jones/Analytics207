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

import os


# ---------- PREDICTION HELPERS ----------

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
    page_title="🧠 THE MODEL – Analytics207.com",
    page_icon="🧠",
    layout="wide",
)

apply_global_layout_tweaks()
render_logo()
render_page_header(
    title="🧠 THE MODEL",
    definition="Model (n.): A calibrated predictive engine built to forecast outcomes statewide.",
    subtitle="Statewide matchup forecasts driven by a world class calibrated analytics engine.",
)


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


    # ── Build TeamKey from components if blank ────────────────────────────
    if "TeamKey" not in teams.columns or teams["TeamKey"].eq("").all():
        teams["TeamKey"] = (
            teams["Team"].str.replace(r"\s+", "", regex=True).str.strip()
            + teams["Gender"].str.strip()
            + teams["Class"].str.strip()
            + teams["Region"].str.strip()
        )
    # ─────────────────────────────────────────────────────────────────────

    # ── Merge PIR (PowerIndex_Display) from power index parquet ──────────
    pir_raw = read_parquet_safe(PIR_FILE)
    if not pir_raw.empty and "PowerIndex_Display" in pir_raw.columns:
        pir_small = pir_raw[["TeamKey", "Gender", "PowerIndex_Display"]].copy()
        pir_small["Gender"] = pir_small["Gender"].astype(str).str.title().str.strip()
        pir_small["Team"]   = pir_small["TeamKey"].str.replace(r"(Boys|Girls).*$", "", regex=True).str.strip()
        pir_small = pir_small.rename(columns={"PowerIndex_Display": "PIR"})
        teams = teams.merge(pir_small[["Team", "Gender", "PIR"]], on=["Team", "Gender"], how="left")
    else:
        teams["PIR"] = np.nan

    # Rating column = PIR (our model), fallback to TI, then PI
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
        # ── Normalize HomeKey / AwayKey to match teams_df TeamKey format ──
        if "HomeKey" in games.columns:
            games["HomeKey"] = games["HomeKey"].astype(str).str.replace(r"\s+", "", regex=True).str.strip()
        if "AwayKey" in games.columns:
            games["AwayKey"] = games["AwayKey"].astype(str).str.replace(r"\s+", "", regex=True).str.strip()
        # ──────────────────────────────────────────────────────────────────
        games = _ensure_pred_cols(games)
        games = _compute_actuals(games)


    return teams, games


teams_df, games_df = load_v50_data()

# ── TEMPORARY DEBUG ───────────────────────────────────────────────────────
with st.expander("🔧 Debug: TeamKey check", expanded=False):
    st.write("**teams_df TeamKey samples:**")
    st.write(teams_df["TeamKey"].dropna().head(20).tolist())

    st.write("**games_df HomeKey / AwayKey samples:**")
    if "HomeKey" in games_df.columns:
        st.write(games_df[["Home","Away","HomeKey","AwayKey"]].head(20))
    else:
        st.write("NO HomeKey column in games_df!")

    st.write("**Bangor Christian row:**")
    st.write(teams_df[teams_df["Team"].str.contains("Bangor Christian", case=False, na=False)][["Team","TeamKey","Gender","Class","Region"]].to_dict("records"))

    st.write("**Hodgdon HS row:**")
    st.write(teams_df[teams_df["Team"].str.contains("Hodgdon", case=False, na=False)][["Team","TeamKey","Gender","Class","Region"]].to_dict("records"))

    st.write("**games_df rows involving Bangor Christian or Hodgdon:**")
    if "HomeKey" in games_df.columns:
        mask = (
            games_df["Home"].str.contains("Bangor Christian", case=False, na=False) |
            games_df["Away"].str.contains("Bangor Christian", case=False, na=False) |
            games_df["Home"].str.contains("Hodgdon", case=False, na=False) |
            games_df["Away"].str.contains("Hodgdon", case=False, na=False)
        )
        st.write(games_df[mask][["Home","Away","HomeKey","AwayKey","PredHomeWinProb"]].to_dict("records"))
# ─────────────────────────────────────────────────────────────────────────

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
    with st.expander("Debug: teams_df columns", expanded=False):
        st.write(list(teams_df.columns))
    render_footer()
    st.stop()


# ---------- MATCHUP CHOOSER (scheduled opponents only) ----------

lab_teams = teams_filtered["Team"].dropna().sort_values().unique().tolist()
if len(lab_teams) < 2:
    st.warning("Not enough teams available in this filter to build a matchup. Try widening filters.")
    render_footer()
    st.stop()

# Build TeamKey lookup
name_to_key = dict(zip(teams_filtered["Team"], teams_filtered["TeamKey"]))
key_to_name = dict(zip(teams_filtered["TeamKey"], teams_filtered["Team"]))

col_h, col_a = st.columns(2)
with col_h:
    home_team = st.selectbox("Home Team (Team 1)", lab_teams, key="lab_v50_home")

# Resolve home TeamKey and find scheduled opponents from games_df
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

# Map opponent keys back to display names, keep only those in current filter
away_options = sorted([
    key_to_name[k] for k in scheduled_opponent_keys
    if k in key_to_name and key_to_name[k] in lab_teams and key_to_name[k] != home_team
])

# Safety fallback: if no scheduled opponents found, show all filtered teams
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

    # Try home=hk / away=ak first, then flipped
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

    # Flip perspective if teams were stored in reverse order
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
    """Return up to 10 most recent played games between two teams."""
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
    """Return the last n played games for a team."""
    if not {"HomeKey", "AwayKey"}.issubset(games.columns):
        return pd.DataFrame()
    played_col = "Played" if "Played" in games.columns else "PlayedBool"
    played = games[games[played_col]].copy()
    mask = (played["HomeKey"] == team_key) | (played["AwayKey"] == team_key)
    return played[mask].sort_values("Date", ascending=False).head(n)


pred = lookup_prediction(h_row, a_row)

# Hard stop — no math fallback, only real predictions
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

# ── PIR edge from our model rating ───────────────────────────────────────
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


# ---------- BUILD METRIC SECTION HTML ----------

section_blocks = []
for section_title, metrics in metric_groups:
    rows = []
    for i in range(0, len(metrics), 4):
        chunk    = metrics[i: i + 4]
        row_html = "".join(metric_box_html(*m, home_team, away_team) for m in chunk)
        rows.append(f"<div class='mrow'>{row_html}</div>")
    key     = str(section_title).strip().upper()
    emoji   = SECTION_EMOJI.get(key, "")
    prefix  = f"{emoji} " if emoji else ""
    section_blocks.append(f"<div class='section'>{prefix}{section_title}</div>" + "".join(rows))

metric_rows_html = "".join(section_blocks)


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


# ---------- HERO HTML ----------

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
    padding:22px 22px 18px; box-shadow:0 28px 60px rgba(15,23,42,0.95);
  }}
  .top {{ display:flex; align-items:flex-start; justify-content:space-between; gap:18px; }}
  .kicker {{ font-size:11px; text-transform:uppercase; letter-spacing:0.13em; color:#9ca3af; }}
  .title  {{ margin-top:6px; font-size:24px; font-weight:950; color:#ffffff; line-height:1.1; }}
  .sub    {{ margin-top:6px; font-size:12px; color:#9ca3af; }}
  .pill {{ display:inline-flex; align-items:center; padding:2px 10px; border-radius:999px;
           font-size:10px; font-weight:800; letter-spacing:0.12em; text-transform:uppercase;
           background:#020617; border:1px solid rgba(55,65,81,0.9); white-space:nowrap; }}
  .pill-green {{ color:#22c55e; border-color:#22c55e; }}
  .pill-red   {{ color:#ef4444; border-color:#ef4444; }}
  .pill-gold  {{ color:#facc15; border-color:#facc15; }}
  .pill-blue  {{ color:#60a5fa; border-color:#60a5fa; }}
  .pill-gray  {{ color:#e5e7eb; border-color:#374151; }}
  .hero-main {{ margin-top:18px; display:grid; grid-template-columns:1fr; gap:18px; align-items:stretch; }}
  .hero-left {{ background:rgba(18,30,55,0.90); border-radius:18px;
                border:1px solid rgba(96,165,250,0.30); padding:18px 20px 16px; }}
  .hero-label    {{ font-size:11px; text-transform:uppercase; letter-spacing:0.14em; color:#9ca3af; }}
  .hero-scoreline{{ margin-top:8px; font-size:26px; font-weight:950; color:#ffffff; }}
  .hero-subline  {{ margin-top:6px; font-size:20px; color:#c7d2fe; }}
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
  .splitbar-lg {{ height:34px; }} .splitbar-md {{ height:18px; }} .splitbar-sm {{ height:14px; }}
  .splitbar-lg .lbl {{ font-size:12px; }} .splitbar-md .lbl {{ font-size:10px; }} .splitbar-sm .lbl {{ font-size:9px; }}
  .minibar-wrap {{ width:min(560px,100%); margin:6px auto 0; display:grid; gap:8px; }}
  .minibar-cap  {{ font-size:12px; color:#9ca3af; text-align:center; margin-top:-2px; }}
  .divider {{ margin-top:18px; border-top:1px solid rgba(148,163,184,0.16); padding-top:12px; }}
  .section {{ margin-top:14px; margin-bottom:8px; font-size:1.15rem; font-weight:900;
              letter-spacing:0.06em; color:#ffffff; text-transform:uppercase; }}
  .mrow {{ margin-top:10px; display:grid; grid-template-columns:repeat(4,minmax(0,1fr));
           gap:12px; align-items:stretch; width:100%; }}
  .mbox {{ background:rgba(15,23,42,0.40); border:1px solid rgba(148,163,184,0.14);
           border-radius:14px; padding:12px 12px; min-width:0; }}
  .mlabel {{ font-size:12px; font-weight:950; letter-spacing:0.08em; color:#e5e7eb; }}
  .mnote  {{ margin-top:4px; font-size:11px; color:#9ca3af; }}
</style>

<div class="card">
  <div class="top">
    <div style="min-width:0">
      <div class="kicker">🧠 THE MODEL {source_chip}</div>
      <div class="title">{away_team} at {home_team}</div>
      <div class="sub">Featured projection with a clear pick, score, and the metrics behind it</div>
    </div>
    <div style="text-align:right">
      <div class="kicker">Snapshot</div>
      <div class="title" style="font-size:18px">
        <span class="{conf_cls}">{conf_text}</span>
        &nbsp;Edge {margin_edge:.0f}
      </div>
      <div class="sub">Projected final: {home_team} {score_h} – {away_team} {score_a}</div>
    </div>
  </div>

  <div class="hero-main">
    <div class="hero-left" style="padding:18px 20px 16px">
      <div style="text-align:center">
        <div class="hero-label" style="margin-bottom:6px">Matchup</div>
        <div class="hero-scoreline" style="font-size:30px">{away_team} vs {home_team}</div>
        <div class="hero-subline" style="color:#e5e7eb">
          Projected: {home_team} {score_h} – {away_team} {score_a} &nbsp;·&nbsp;
          {fav_team} favored by {abs(spread):.1f}
        </div>
      </div>

      <div style="margin-top:12px; display:flex; justify-content:center; gap:12px; flex-wrap:wrap">
        <span style="padding:4px 10px; border-radius:999px; border:1px solid rgba(148,163,184,0.18); background:rgba(2,6,23,0.35)">
          <span style="color:#e5e7eb; font-weight:900">Model edge</span>&nbsp;
          <span style="color:#facc15; font-weight:950">{margin_edge:.1f}</span>
        </span>
        <span style="padding:4px 10px; border-radius:999px; border:1px solid rgba(148,163,184,0.18); background:rgba(2,6,23,0.35)">
          <span style="color:#e5e7eb; font-weight:900">Win chance</span>&nbsp;
          <span style="color:#22c55e; font-weight:950">{fav_win_pct:.0f}%</span>
        </span>
        <span style="padding:4px 10px; border-radius:999px; border:1px solid rgba(148,163,184,0.18); background:rgba(2,6,23,0.35)">
          <span style="color:#e5e7eb; font-weight:900">{conf_text}</span>
        </span>
      </div>

      <div style="margin-top:12px; display:flex; justify-content:center;">
        <div class="splitbar splitbar-lg" style="width:min(760px,100%); --pLeft:{home_win_pct:.0f}; --leftColor:#22c55e; --rightColor:#f97316;">
          <div class="lbl left">{home_team} <span>{home_win_pct:.0f}%</span></div>
          <div class="lbl right"><span>{away_win_pct:.0f}%</span> {away_team}</div>
        </div>
      </div>

      <div class="hero-subline" style="margin-top:10px; color:#9ca3af; text-align:center">
        Driver bars — bigger side = advantage
      </div>
      <div class="minibar-wrap">
        <div class="splitbar splitbar-md" style="--pLeft:{pir_p_left:.0f}; --leftColor:#22c55e; --rightColor:#f97316;">
          <div class="lbl left">{pir_left_lbl}</div>
          <div class="lbl right">{pir_right_lbl}</div>
        </div>
        <div class="minibar-cap">PIR EDGE {pir_edge_ha:.1f}</div>

        <div class="splitbar splitbar-md" style="--pLeft:{net_p_left:.0f}; --leftColor:#22c55e; --rightColor:#f97316;">
          <div class="lbl left">{net_left_lbl}</div>
          <div class="lbl right">{net_right_lbl}</div>
        </div>
        <div class="minibar-cap">NET EDGE {net_edge_ha:.1f}</div>

        <div class="splitbar splitbar-md" style="--pLeft:{l5_p_left:.0f}; --leftColor:#22c55e; --rightColor:#f97316;">
          <div class="lbl left">{l5_left_lbl}</div>
          <div class="lbl right">{l5_right_lbl}</div>
        </div>
        <div class="minibar-cap">L5 EDGE {l5_edge_ha:.1f}</div>
      </div>

      <div class="divider"></div>
      {metric_rows_html}
    </div>
  </div>
</div>
"""

# ---------- MATCHUP TABS ----------

home_key = str(h_row.get("TeamKey", "")).strip()
away_key = str(a_row.get("TeamKey", "")).strip()

tab_model, tab_h2h, tab_form, tab_compare = st.tabs([
    "🧠 Model Breakdown",
    "📜 Head-to-Head History",
    "📅 Recent Form",
    "⚔️ Tale of the Tape",
])

with tab_model:
    components.html(hero_html, height=5600, scrolling=True)

with tab_h2h:
    st.write("")

    h2h_df = head_to_head_games(games_df, home_key, away_key)

    if h2h_df.empty:
        st.info(f"No games found between {home_team} and {away_team} this season.")
    else:
        h_wins = 0
        a_wins_count = 0
        game_cards_html = ""

        for _, g in h2h_df.iterrows():
            hs  = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
            as_ = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
            home_name = str(g.get("Home", ""))
            away_name = str(g.get("Away", ""))
            date = str(g.get("Date", ""))[:10]

            if pd.notna(hs) and pd.notna(as_):
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

                game_cards_html += f"""
<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
            border-radius:14px;margin-bottom:6px;
            background:rgba(15,23,42,0.40);
            border:1px solid rgba(148,163,184,0.14);
            font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;">
  <span style="color:#9ca3af;font-size:11px;min-width:80px;letter-spacing:0.04em;">{date}</span>
  <span style="color:{w_color};font-size:13px;font-weight:900;flex:1;">✓ {w_name}</span>
  <span style="color:#facc15;font-size:14px;font-weight:950;">{w_score}–{l_score}</span>
  <span style="color:{l_color};font-size:13px;flex:1;text-align:right;">{l_name}</span>
  <span style="color:rgba(148,163,184,0.4);font-size:10px;min-width:60px;text-align:right;">
    {away_name} @ {home_name}
  </span>
</div>"""

        # Tally card
        tally_html = f"""
<div style="display:flex;gap:16px;margin-top:12px;
            font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;">
  <div style="flex:1;background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.30);
              border-radius:14px;padding:14px;text-align:center;">
    <div style="font-size:32px;font-weight:950;color:#22c55e;">{h_wins}</div>
    <div style="font-size:12px;color:#e5e7eb;font-weight:800;margin-top:2px;">{home_team}</div>
  </div>
  <div style="flex:1;background:rgba(249,115,22,0.08);border:1px solid rgba(249,115,22,0.30);
              border-radius:14px;padding:14px;text-align:center;">
    <div style="font-size:32px;font-weight:950;color:#f97316;">{a_wins_count}</div>
    <div style="font-size:12px;color:#e5e7eb;font-weight:800;margin-top:2px;">{away_team}</div>
  </div>
</div>"""

        full_h2h_html = f"""
<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;
             font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;color:#e5e7eb;">
<div style="background:radial-gradient(circle at top left,#142040,#060c1a);
            border:1px solid rgba(96,165,250,0.25);border-radius:22px;
            padding:22px 24px;box-shadow:0 18px 45px rgba(0,0,0,0.85);">
  <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.13em;color:#9ca3af;">
    📜 Season Series
  </div>
  <div style="margin-top:6px;font-size:20px;font-weight:950;color:#ffffff;">
    {home_team} vs {away_team}
  </div>
  <div style="margin-top:4px;font-size:12px;color:#9ca3af;">
    All matchups this season — most recent first
  </div>
  <div style="margin-top:16px;">
    {game_cards_html}
  </div>
  {tally_html}
</div>
</body></html>"""

        components.html(full_h2h_html, height=520, scrolling=True)


# ── RECENT FORM ──────────────────────────────────────────────────────

with tab_form:
    st.write("")

    col_home_form, col_away_form = st.columns(2)

    for col, team_name, team_key, accent in [
        (col_home_form, home_team, home_key, "#22c55e"),
        (col_away_form, away_team, away_key, "#f97316"),
    ]:
        with col:
            recent = recent_form_games(games_df, team_key, n=5)

            game_rows_html = ""
            if recent.empty:
                game_rows_html = '<div style="color:#9ca3af;font-size:13px;padding:12px;">No recent games found.</div>'
            else:
                for _, g in recent.iterrows():
                    hs   = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
                    as_  = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
                    g_home = str(g.get("Home", ""))
                    g_away = str(g.get("Away", ""))
                    date = str(g.get("Date", ""))[:10]

                    is_home  = (str(g.get("HomeKey", "")) == team_key)
                    opp      = g_away if is_home else g_home
                    tm_score = int(hs) if is_home and pd.notna(hs) else (int(as_) if pd.notna(as_) else 0)
                    op_score = int(as_) if is_home and pd.notna(as_) else (int(hs) if pd.notna(hs) else 0)

                    if pd.notna(hs) and pd.notna(as_):
                        won       = tm_score > op_score
                        res_label = "W" if won else "L"
                        res_color = "#22c55e" if won else "#ef4444"
                        res_bg    = "rgba(34,197,94,0.08)" if won else "rgba(239,68,68,0.08)"
                        venue     = "Home" if is_home else "Away"

                        game_rows_html += f"""
<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
            border-radius:12px;margin-bottom:5px;
            background:{res_bg};border:1px solid {res_color}22;
            font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;">
  <span style="background:{res_color};color:#0f172a;font-size:11px;font-weight:900;
               padding:2px 8px;border-radius:999px;min-width:16px;text-align:center;">
    {res_label}
  </span>
  <span style="color:#e5e7eb;font-size:12px;font-weight:800;flex:1;">vs {opp}</span>
  <span style="color:#facc15;font-size:13px;font-weight:950;">{tm_score}–{op_score}</span>
  <span style="color:#9ca3af;font-size:10px;">{venue} · {date}</span>
</div>"""

            form_card_html = f"""
<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;
             font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;color:#e5e7eb;">
<div style="background:radial-gradient(circle at top left,#142040,#060c1a);
            border:1px solid rgba(148,163,184,0.18);border-radius:22px;
            padding:20px 22px;box-shadow:0 18px 45px rgba(0,0,0,0.85);">
  <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.13em;color:#9ca3af;">
    📅 Last 5 Games
  </div>
  <div style="margin-top:6px;font-size:18px;font-weight:950;color:{accent};">
    {team_name}
  </div>
  <div style="margin-top:12px;">
    {game_rows_html}
  </div>
</div>
</body></html>"""

            components.html(form_card_html, height=340, scrolling=False)


# ── RADAR CHART ──────────────────────────────────────────────────────

with tab_compare:
    st.write("")

    tape_metrics = [
        ("PIR Rating",      "PIR",          True,  1),
        ("Win %",           "WinPct",       True,  1),
        ("Offense PPG",     "PPG",          True,  1),
        ("Defense OPPG",    "OPPG",         False, 1),
        ("Net Margin",      "MarginPG",     True,  1),
        ("L5 Margin",       "L5MarginPG",   True,  1),
        ("SOS (EWP)",       "SOS_EWP",      True,  3),
        ("Expected Wins",   "ExpectedWins", True,  1),
        ("Close Win %",     "CloseWinPct",  True,  1),
        ("Quality Wins",    "QualityWins",  True,  0),
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
            marker=dict(
                color="rgba(34,197,94,0.85)",
                line=dict(color="#4ade80", width=1),
            ),
            text=[f"{abs(v):.{places_list[i]}f}" for i, v in enumerate(home_vals_t)],
            textposition="inside",
            textfont=dict(color="#ffffff", size=13,
                          family="ui-sans-serif,system-ui,sans-serif"),
            insidetextanchor="middle",
            hovertemplate="%{y}: %{text}<extra>" + home_team + "</extra>",
        ))

        fig.add_trace(go.Bar(
            y=labels_t,
            x=[abs(v) for v in away_vals_t],
            orientation="h",
            name=away_team,
            marker=dict(
                color="rgba(249,115,22,0.85)",
                line=dict(color="#fb923c", width=1),
            ),
            text=[f"{abs(v):.{places_list[i]}f}" for i, v in enumerate(away_vals_t)],
            textposition="inside",
            textfont=dict(color="#ffffff", size=13,
                          family="ui-sans-serif,system-ui,sans-serif"),
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
                showticklabels=False,
                showgrid=False,
                zeroline=True,
                zerolinecolor="rgba(255,255,255,0.25)",
                zerolinewidth=2,
            ),
            yaxis=dict(
                autorange="reversed",
                tickfont=dict(color="#e5e7eb", size=13,
                              family="ui-sans-serif,system-ui,sans-serif"),
                gridcolor="rgba(148,163,184,0.06)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb",
                      family="ui-sans-serif,system-ui,sans-serif"),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="center", x=0.5,
                font=dict(color="#e5e7eb", size=14),
                bgcolor="rgba(0,0,0,0)",
            ),
            margin=dict(t=60, b=30, l=120, r=30),
            height=480,
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"\u2190 {home_team} bars extend left \u00b7 "
            f"{away_team} bars extend right \u2192  |  "
            "Longer bar = higher raw value."
        )
    else:
        st.info("Not enough stat data to render comparison chart.")


render_footer()
