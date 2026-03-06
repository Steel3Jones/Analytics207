# The Report Card
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)
from auth import login_gate, logout_button, is_subscribed

# ----------------------------
# PAGE CONFIG
# ----------------------------

from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

st.set_page_config(
    page_title="🚀 The Report Card – Analytics207.com",
    page_icon="🚀",
    layout="wide",
)
apply_global_layout_tweaks()
login_gate(required=False)
logout_button()
render_logo()
render_page_header(
    title="🚀 The Report Card",
    definition="Report Card (n.): how The Model behaves under pressure—accuracy, calibration, and misses.",
    subtitle="Every prediction vs every final score. How sharp are the picks, how honest are the percentages, and where did things go sideways?",
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
    The Report Card — Subscriber Only
  </div>
  <div style="font-size:0.85rem;color:#94a3b8;max-width:420px;margin:0 auto;">
    Subscribe to unlock full model performance analytics,
    calibration data, and biggest-miss breakdowns.
  </div>
</div>
""", height=160, scrolling=False)
    render_footer()
    st.stop()

# ----------------------------
# DATA PATHS (bundle)
# ----------------------------
DATA_DIR = os.environ.get("DATA_DIR", "data")

V50 = {
    "label": "v50",
    "summary":     f"{DATA_DIR}/calibration/performance_summary_v50.parquet",
    "games":       f"{DATA_DIR}/calibration/performance_games_v50.parquet",
    "calibration": f"{DATA_DIR}/calibration/performance_calibration_v50.parquet",
    "spread":      f"{DATA_DIR}/calibration/performance_by_spread_v50.parquet",
}

@st.cache_data(ttl=300, show_spinner=False)
def load_performance_data():
    try:
        s = pd.read_parquet(V50["summary"])
        if s is None or s.empty:
            st.error("Performance summary parquet is empty.")
            st.stop()

        summary     = s.iloc[0].to_dict()
        games       = pd.read_parquet(V50["games"])
        calibration = pd.read_parquet(V50["calibration"])
        spread_perf = pd.read_parquet(V50["spread"])
        return summary, games, calibration, spread_perf

    except FileNotFoundError:
        st.error(
            "v50 performance data not found.\n\n"
            "Expected files:\n"
            f"- {V50['summary']}\n"
            f"- {V50['games']}\n"
            f"- {V50['calibration']}\n"
            f"- {V50['spread']}\n"
        )
        render_footer()
        st.stop()

def _coerce_datetime(df: pd.DataFrame, col: str) -> None:
    if df is not None and not df.empty and col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

def _ensure_fav_prob_pct(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    if "FavProbPct" in out.columns:
        nonnull = pd.to_numeric(out["FavProbPct"], errors="coerce").notna().sum()
        if nonnull > 0:
            return out
    if "FavProb" in out.columns:
        out["FavProbPct"] = pd.to_numeric(out["FavProb"], errors="coerce") * 100.0
        return out
    out["FavProbPct"] = np.nan
    return out

summary_metrics, played, calibration_data, spread_performance = load_performance_data()
st.caption(f"Data source: {V50['label']} performance bundle")

# ----------------------------
# NORMALIZE TYPES
# ----------------------------
_coerce_datetime(played, "Date")
played = _ensure_fav_prob_pct(played)

# ----------------------------
# SUMMARY METRICS
# ----------------------------
total_games   = int(summary_metrics.get("TotalGames", 0) or 0)
correct_games = int(summary_metrics.get("CorrectGames", 0) or 0)
overall_pct   = float(summary_metrics.get("OverallAccuracy", np.nan))
upset_rate    = float(summary_metrics.get("UpsetRate", np.nan))

mae      = float(summary_metrics.get("MAE", np.nan))
rmse     = float(summary_metrics.get("RMSE", np.nan))
within5  = float(summary_metrics.get("Within5Pts", np.nan))
within10 = float(summary_metrics.get("Within10Pts", np.nan))

overall_brier = float(summary_metrics.get("BrierScore", np.nan))

def gender_record(df: pd.DataFrame, gender_value: str) -> tuple[int, int, float]:
    if df is None or df.empty:
        return 0, 0, 0.0
    needed = {"Gender", "ModelCorrect"}
    if not needed.issubset(df.columns):
        return 0, 0, 0.0
    g     = df[df["Gender"] == gender_value]
    games = int(len(g))
    if games == 0:
        return 0, 0, 0.0
    wins = int(pd.to_numeric(g["ModelCorrect"], errors="coerce").fillna(0).astype(int).sum())
    acc  = 100.0 * wins / games
    return wins, games, acc

def fav_home_away_record(df: pd.DataFrame):
    if df is None or df.empty:
        return 0, 0, 0, 0
    needed = {"Favorite", "Home", "Away", "ModelCorrect"}
    if not needed.issubset(df.columns):
        return 0, 0, 0, 0
    home_fav = df[df["Favorite"] == df["Home"]]
    hf_games = int(len(home_fav))
    hf_wins  = int(pd.to_numeric(home_fav["ModelCorrect"], errors="coerce").fillna(0).astype(int).sum())
    away_fav = df[df["Favorite"] == df["Away"]]
    af_games = int(len(away_fav))
    af_wins  = int(pd.to_numeric(away_fav["ModelCorrect"], errors="coerce").fillna(0).astype(int).sum())
    return hf_wins, hf_games, af_wins, af_games

boys_wins,  boys_games,  boys_acc  = gender_record(played, "Boys")
girls_wins, girls_games, girls_acc = gender_record(played, "Girls")
home_fav_wins, home_fav_games, away_fav_wins, away_fav_games = fav_home_away_record(played)

def gender_mae(df: pd.DataFrame, gender_value: str) -> float:
    if df is None or df.empty:
        return float("nan")
    needed = {"Gender", "PredMargin", "ActualMargin"}
    if not needed.issubset(df.columns):
        return float("nan")
    g = df[df["Gender"] == gender_value].dropna(subset=["PredMargin", "ActualMargin"])
    if g.empty:
        return float("nan")
    return float(
        (pd.to_numeric(g["PredMargin"], errors="coerce") - pd.to_numeric(g["ActualMargin"], errors="coerce"))
        .abs()
        .mean()
    )

boys_mae  = gender_mae(played, "Boys")
girls_mae = gender_mae(played, "Girls")

# ----------------------------
# HINDSIGHT baselines (TI & WinPct)
# ----------------------------
@st.cache_data(ttl=300, show_spinner=False)
def compute_hindsight_baselines(perf_games: pd.DataFrame) -> dict:
    result = {
        "ti_hit": float("nan"), "ti_games": 0,
        "rec_hit": float("nan"), "rec_games": 0,
    }

    if perf_games is None or perf_games.empty:
        return result

    core_path = f"{DATA_DIR}/core/teams_team_season_core_v50.parquet"
    try:
        core = pd.read_parquet(core_path)
    except FileNotFoundError:
        return result

    needed_core = {"Team", "Gender", "Season", "TI", "WinPct"}
    if not needed_core.issubset(core.columns):
        return result

    perf = perf_games.copy()
    perf["HomeScore"] = pd.to_numeric(perf["HomeScore"], errors="coerce")
    perf["AwayScore"] = pd.to_numeric(perf["AwayScore"], errors="coerce")
    perf = perf.dropna(subset=["HomeScore", "AwayScore"])

    perf["Winner"] = np.where(
        perf["HomeScore"] > perf["AwayScore"],
        perf["Home"],
        np.where(perf["AwayScore"] > perf["HomeScore"], perf["Away"], None),
    )
    perf = perf[perf["Winner"].notna()].copy()
    if perf.empty:
        return result

    if "Season" not in perf.columns:
        perf["Season"] = "2025-26"

    core_local = core[["Team", "Gender", "Season", "TI", "WinPct"]].copy()
    home_stats = core_local.rename(columns={"Team": "Home", "TI": "HomeTI", "WinPct": "HomeWinPct"})
    away_stats = core_local.rename(columns={"Team": "Away", "TI": "AwayTI", "WinPct": "AwayWinPct"})

    merged = perf.merge(
        home_stats, on=["Home", "Gender"], how="left", suffixes=("", "_hcore"),
    ).merge(
        away_stats, on=["Away", "Gender"], how="left", suffixes=("", "_acore"),
    )

    for dropcol in ["Season_hcore", "Season_acore"]:
        if dropcol in merged.columns:
            merged.drop(columns=[dropcol], inplace=True)

    merged["HomeTI"] = pd.to_numeric(merged["HomeTI"], errors="coerce")
    merged["AwayTI"] = pd.to_numeric(merged["AwayTI"], errors="coerce")
    ti_valid = merged.dropna(subset=["HomeTI", "AwayTI"]).copy()

    if not ti_valid.empty:
        ti_valid["TI_Fav"] = np.where(
            ti_valid["HomeTI"] > ti_valid["AwayTI"],
            ti_valid["Home"],
            np.where(ti_valid["AwayTI"] > ti_valid["HomeTI"], ti_valid["Away"], None),
        )
        ti_valid = ti_valid[ti_valid["TI_Fav"].notna()].copy()
        if not ti_valid.empty:
            result["ti_hit"] = float((ti_valid["TI_Fav"] == ti_valid["Winner"]).mean()) * 100.0
            result["ti_games"] = len(ti_valid)

    merged["HomeWinPct"] = pd.to_numeric(merged["HomeWinPct"], errors="coerce")
    merged["AwayWinPct"] = pd.to_numeric(merged["AwayWinPct"], errors="coerce")
    rec_valid = merged.dropna(subset=["HomeWinPct", "AwayWinPct"]).copy()

    if not rec_valid.empty:
        rec_valid["Rec_Fav"] = np.where(
            rec_valid["HomeWinPct"] > rec_valid["AwayWinPct"],
            rec_valid["Home"],
            np.where(rec_valid["AwayWinPct"] > rec_valid["HomeWinPct"], rec_valid["Away"], None),
        )
        rec_valid = rec_valid[rec_valid["Rec_Fav"].notna()].copy()
        if not rec_valid.empty:
            result["rec_hit"] = float((rec_valid["Rec_Fav"] == rec_valid["Winner"]).mean()) * 100.0
            result["rec_games"] = len(rec_valid)

    return result

baselines = compute_hindsight_baselines(played)
ti_hit    = baselines["ti_hit"]
ti_games  = baselines["ti_games"]
rec_hit   = baselines["rec_hit"]
rec_games = baselines["rec_games"]

# ══════════════════════════════════════════════════════════════════════════
#  VISUAL HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _inject_rc_css() -> None:
    st.markdown("""<style>
/* ── Section pill header ─────────────────────────────────────────── */
.rc-section-head {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    border-radius: 999px;
    border: 1px solid rgba(96,165,250,0.35);
    background: rgba(96,165,250,0.07);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #93c5fd;
    margin: 18px 0 12px;
}

/* ── Hero banner ─────────────────────────────────────────────────── */
.rc-hero-banner {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.20);
    border-radius: 16px;
    padding: 28px 32px;
    display: flex;
    flex-wrap: wrap;
    gap: 28px;
    align-items: center;
    margin: 0 0 20px;
}
.rc-hero-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 90px;
}
.rc-hero-val {
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.rc-hero-lbl {
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-top: 5px;
    text-align: center;
}
.rc-hero-divider {
    width: 1px;
    height: 52px;
    background: rgba(255,255,255,0.08);
}

/* ── Stat grid cards ─────────────────────────────────────────────── */
.rc-stat-grid {
    display: grid;
    gap: 10px;
    margin: 8px 0 16px;
}
.rc-stat-grid-2 { grid-template-columns: repeat(2, 1fr); }
.rc-stat-grid-3 { grid-template-columns: repeat(3, 1fr); }
.rc-stat-grid-4 { grid-template-columns: repeat(4, 1fr); }
.rc-stat-card {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.18);
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.rc-stat-card .rc-sc-lbl {
    font-size: 0.63rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #94a3b8;
}
.rc-stat-card .rc-sc-val {
    font-size: 1.55rem;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.rc-stat-card .rc-sc-sub {
    font-size: 0.76rem;
    color: #94a3b8;
    margin-top: 2px;
}

/* ── Dark table ──────────────────────────────────────────────────── */
.rc-table-wrap {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.15);
    border-radius: 12px;
    overflow-x: auto;
    margin: 6px 0 16px;
}

/* ── Callout box ─────────────────────────────────────────────────── */
.rc-callout {
    border-radius: 10px;
    padding: 12px 16px;
    margin: 8px 0 14px;
    font-size: 0.83rem;
    line-height: 1.55;
}
.rc-callout-amber {
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.28);
    color: #fde68a;
}
.rc-callout-blue {
    background: rgba(96,165,250,0.07);
    border: 1px solid rgba(96,165,250,0.25);
    color: #bfdbfe;
}
.rc-callout-green {
    background: rgba(74,222,128,0.07);
    border: 1px solid rgba(74,222,128,0.25);
    color: #bbf7d0;
}

/* ── Spotlight game cards ────────────────────────────────────────── */
.rc-spotlight {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border-radius: 12px;
    padding: 16px 18px;
    border: 1px solid rgba(96,165,250,0.18);
    margin: 6px 0 10px;
    min-height: 110px;
}
.rc-spotlight-badge {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 8px;
}
.rc-spotlight-game {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 6px;
}
.rc-spotlight-detail {
    font-size: 0.82rem;
    color: #94a3b8;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)


def _rc_section(icon: str, label: str) -> None:
    st.markdown(f'<div class="rc-section-head">{icon} {label}</div>', unsafe_allow_html=True)


def _rc_stat_card(label: str, value: str, sub: str = "", color: str = "#60a5fa") -> str:
    sub_html = f'<div class="rc-sc-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="rc-stat-card">'
        f'<div class="rc-sc-lbl">{label}</div>'
        f'<div class="rc-sc-val" style="color:{color};">{value}</div>'
        f'{sub_html}'
        f'</div>'
    )


def _rc_df_html(df: pd.DataFrame, max_rows: int = 30) -> str:
    th_s = (
        "padding:0.28rem 0.6rem;font-size:0.65rem;text-transform:uppercase;"
        "letter-spacing:0.10em;color:#60a5fa;background:rgba(9,14,28,0.9);"
        "border-bottom:2px solid rgba(96,165,250,0.20);white-space:nowrap;"
        "font-weight:700;text-align:left;"
    )
    td_s = (
        "padding:0.30rem 0.6rem;font-size:0.82rem;color:#e2e8f0;"
        "border-bottom:1px solid rgba(255,255,255,0.04);white-space:nowrap;"
    )
    thead = "".join(f'<th style="{th_s}">{c}</th>' for c in df.columns)
    rows = ""
    for _, row in df.head(max_rows).iterrows():
        cells = "".join(f'<td style="{td_s}">{v}</td>' for v in row.values)
        rows += f'<tr>{cells}</tr>'
    return (
        f'<div class="rc-table-wrap">'
        f'<table style="width:100%;border-collapse:collapse;min-width:360px;">'
        f'<thead><tr>{thead}</tr></thead><tbody>{rows}</tbody></table></div>'
    )


_inject_rc_css()

# ══════════════════════════════════════════════════════════════════════════
#  HERO BANNER
# ══════════════════════════════════════════════════════════════════════════
overall_text = f"{overall_pct:.1f}%" if np.isfinite(overall_pct) else "—"
upset_count  = max(0, total_games - correct_games)
upset_text   = f"{upset_rate:.1f}%" if np.isfinite(upset_rate) else "—"
mae_text     = f"{mae:.2f}" if np.isfinite(mae) else "—"
within5_text = f"{within5:.1f}%" if np.isfinite(within5) else "—"

st.markdown(f"""
<div class="rc-hero-banner">
  <div class="rc-hero-stat">
    <div class="rc-hero-val" style="color:#4ade80;">{overall_text}</div>
    <div class="rc-hero-lbl">Overall Accuracy</div>
  </div>
  <div class="rc-hero-divider"></div>
  <div class="rc-hero-stat">
    <div class="rc-hero-val" style="color:#60a5fa;">{mae_text}</div>
    <div class="rc-hero-lbl">Avg Margin Error (pts)</div>
  </div>
  <div class="rc-hero-divider"></div>
  <div class="rc-hero-stat">
    <div class="rc-hero-val" style="color:#38bdf8;">{within5_text}</div>
    <div class="rc-hero-lbl">Within 5 Points</div>
  </div>
  <div class="rc-hero-divider"></div>
  <div class="rc-hero-stat">
    <div class="rc-hero-val" style="color:#facc15;">{upset_count}</div>
    <div class="rc-hero-lbl">Upsets ({upset_text})</div>
  </div>
  <div class="rc-hero-divider"></div>
  <div class="rc-hero-stat">
    <div class="rc-hero-val" style="color:#a78bfa;">{total_games:,}</div>
    <div class="rc-hero-lbl">Games Analyzed</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="rc-callout rc-callout-blue">'
    '<strong>How to read this page —</strong> '
    '<strong>Accuracy</strong>: how often the favorite actually wins. '
    '<strong>Margin error</strong>: how close the projected spread is to the final score. '
    '<strong>Calibration</strong>: when the model says 70%, does it win ~7 out of 10? '
    'All numbers use <em>completed regular-season games only</em> — playoffs, scrimmages, and exhibitions excluded.'
    '</div>',
    unsafe_allow_html=True,
)

# ----------------------------
# TABS
# ----------------------------
tab_overview, tab_conf, tab_misses = st.tabs(
    ["📊 Overview", "🎯 Confidence & calibration", "⚡ Biggest misses"]
)

# ----------------------------
# TAB 1 — OVERVIEW
# ----------------------------
with tab_overview:
    _rc_section("🏆", "Model Record by Group")

    boys_val  = f"{boys_wins}-{max(0, boys_games - boys_wins)}"   if boys_games  > 0 else "—"
    boys_sub  = f"{boys_acc:.1f}% accuracy"                       if boys_games  > 0 else "no boys games"
    girls_val = f"{girls_wins}-{max(0, girls_games - girls_wins)}" if girls_games > 0 else "—"
    girls_sub = f"{girls_acc:.1f}% accuracy"                      if girls_games > 0 else "no girls games"

    if home_fav_games > 0:
        home_acc = 100.0 * home_fav_wins / home_fav_games
        hf_val   = f"{home_fav_wins}-{home_fav_games - home_fav_wins}"
        hf_sub   = f"{home_acc:.1f}% accuracy"
    else:
        hf_val, hf_sub = "—", "no home favorites"

    if away_fav_games > 0:
        away_acc = 100.0 * away_fav_wins / away_fav_games
        af_val   = f"{away_fav_wins}-{away_fav_games - away_fav_wins}"
        af_sub   = f"{away_acc:.1f}% accuracy"
    else:
        af_val, af_sub = "—", "no away favorites"

    st.markdown(
        '<div class="rc-stat-grid rc-stat-grid-4">'
        + _rc_stat_card("Boys Record",    boys_val,  boys_sub,  "#4ade80")
        + _rc_stat_card("Girls Record",   girls_val, girls_sub, "#f472b6")
        + _rc_stat_card("Home Favorite",  hf_val,    hf_sub,    "#60a5fa")
        + _rc_stat_card("Away Favorite",  af_val,    af_sub,    "#38bdf8")
        + '</div>',
        unsafe_allow_html=True,
    )

    _rc_section("📏", "Margin Accuracy — Spread Quality")

    st.markdown(
        '<div class="rc-stat-grid rc-stat-grid-4">'
        + _rc_stat_card("MAE (points)",   f"{mae:.2f}"       if np.isfinite(mae)      else "—", "avg margin error",         "#60a5fa")
        + _rc_stat_card("RMSE (points)",  f"{rmse:.2f}"      if np.isfinite(rmse)     else "—", "root mean sq. error",      "#a78bfa")
        + _rc_stat_card("Within 5 pts",   f"{within5:.1f}%"  if np.isfinite(within5)  else "—", "basically on the money",   "#4ade80")
        + _rc_stat_card("Within 10 pts",  f"{within10:.1f}%" if np.isfinite(within10) else "—", "within two possessions",   "#34d399")
        + '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="rc-callout rc-callout-blue" style="margin-top:0;">'
        'MAE = on average, the predicted margin is this many points off the final score. '
        'Within 5/10 pts shows how often the spread was basically right.'
        '</div>',
        unsafe_allow_html=True,
    )

    _rc_section("📡", "How Hard Is It to Pick Winners?")

    model_hit = overall_pct
    home_hit  = np.nan

    if played is not None and not played.empty:
        scores_ok = played[["Home", "Away", "HomeScore", "AwayScore"]].copy()
        scores_ok["HomeScore"] = pd.to_numeric(scores_ok["HomeScore"], errors="coerce")
        scores_ok["AwayScore"] = pd.to_numeric(scores_ok["AwayScore"], errors="coerce")
        scores_ok = scores_ok.dropna(subset=["HomeScore", "AwayScore"])

        if not scores_ok.empty:
            winner = np.where(
                scores_ok["HomeScore"] > scores_ok["AwayScore"],
                scores_ok["Home"],
                np.where(scores_ok["AwayScore"] > scores_ok["HomeScore"], scores_ok["Away"], None),
            )
            scores_ok["Winner"] = winner
            base = played.join(scores_ok[["Winner"]], how="left")
            mask_winner = base["Winner"].notna()
            if mask_winner.any():
                home_hit = float((base.loc[mask_winner, "Home"] == base.loc[mask_winner, "Winner"]).mean()) * 100.0

    st.markdown(
        '<div class="rc-callout rc-callout-green" style="margin-bottom:8px;">'
        '📡 <strong>REAL-TIME</strong> — picks made before tipoff, using zero future information'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="rc-stat-grid rc-stat-grid-3">'
        + _rc_stat_card("Model Favorite Wins", f"{model_hit:.1f}%" if np.isfinite(model_hit) else "—", "pre-tipoff picks only",       "#4ade80")
        + _rc_stat_card("Always Pick Home",    f"{home_hit:.1f}%"  if np.isfinite(home_hit)  else "—", "naive home-team baseline",    "#60a5fa")
        + _rc_stat_card("Coin Flip",           "50.0%",                                                  "reference baseline",          "#94a3b8")
        + '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="rc-callout rc-callout-amber" style="margin-top:4px;">'
        '🔮 <strong>HINDSIGHT</strong> — these strategies use end-of-season data the model never had'
        '</div>',
        unsafe_allow_html=True,
    )

    ti_val  = f"{ti_hit:.1f}%"  if np.isfinite(ti_hit)  else "needs TI data"
    ti_sub  = f"{ti_games:,} games · final TI" if ti_games > 0 else ""
    rec_val = f"{rec_hit:.1f}%" if np.isfinite(rec_hit) else "needs record data"
    rec_sub = f"{rec_games:,} games · final record" if rec_games > 0 else ""

    st.markdown(
        '<div class="rc-stat-grid rc-stat-grid-2">'
        + _rc_stat_card("Higher TI (Heal) w/ Hindsight", ti_val,  ti_sub,  "#f59e0b")
        + _rc_stat_card("Better Record w/ Hindsight",    rec_val, rec_sub, "#f59e0b")
        + '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="rc-callout rc-callout-amber">'
        '<strong>💡 Why this matters:</strong> The hindsight strategies get to cheat — '
        'they use each team\'s <em>final</em> Heal points and win-loss record, '
        'information that didn\'t exist when the games were actually played. '
        'Our model made every single pick <strong>before tipoff</strong>, '
        'using only what was known at that moment — and still hit the mid-80s. '
        'That\'s nearly as good as reading tomorrow\'s newspaper.'
        '</div>',
        unsafe_allow_html=True,
    )

    _rc_section("📅", "Season-over-Season Scoreboard")

    season_rows = [
        {
            "Season":   "Current",
            "Games":    total_games,
            "Accuracy": f"{overall_pct:.1f}%"   if np.isfinite(overall_pct)   else "—",
            "Brier":    f"{overall_brier:.3f}"  if np.isfinite(overall_brier) else "—",
            "MAE":      f"{mae:.2f}"            if np.isfinite(mae)           else "—",
            "Note":     "Updates from latest loaded bundle.",
        },
    ]
    st.markdown(_rc_df_html(pd.DataFrame(season_rows)), unsafe_allow_html=True)

    _rc_section("🎲", "Which Teams Are Easiest (and Hardest) to Predict?")

    if played is None or played.empty:
        st.info("Team predictability will appear once per-game performance data is available.")
    else:
        tmp = played.copy()
        tmp["HomeScore"] = pd.to_numeric(tmp["HomeScore"], errors="coerce")
        tmp["AwayScore"] = pd.to_numeric(tmp["AwayScore"], errors="coerce")
        tmp = tmp.dropna(subset=["HomeScore", "AwayScore"])

        home_rows = tmp[["Date", "Gender", "Home", "ModelCorrect", "PredMargin", "ActualMargin"]].copy()
        home_rows = home_rows.rename(columns={"Home": "Team"})
        away_rows = tmp[["Date", "Gender", "Away", "ModelCorrect", "PredMargin", "ActualMargin"]].copy()
        away_rows = away_rows.rename(columns={"Away": "Team"})
        team_long = pd.concat([home_rows, away_rows], ignore_index=True)

        team_long["Team"] = team_long["Team"].astype(str)
        team_long = team_long[team_long["Team"].str.len() > 0]

        gp = team_long.groupby(["Team", "Gender"]).agg(
            Games=("Team", "size"),
            ModelWins=("ModelCorrect", lambda s: int(pd.to_numeric(s, errors="coerce").fillna(0).sum())),
        ).reset_index()

        if {"PredMargin", "ActualMargin"}.issubset(team_long.columns):
            diffs = (
                pd.to_numeric(team_long["PredMargin"], errors="coerce")
                - pd.to_numeric(team_long["ActualMargin"], errors="coerce")
            ).abs()
            team_long["AbsError"] = diffs
            mae_by_team = (
                team_long.groupby(["Team", "Gender"])["AbsError"]
                .mean()
                .rename("MAE")
                .reset_index()
            )
            gp = gp.merge(mae_by_team, on=["Team", "Gender"], how="left")
        else:
            gp["MAE"] = np.nan

        gp["HitRate"] = 100.0 * gp["ModelWins"] / gp["Games"].replace(0, np.nan)
        gp["HitRate"] = gp["HitRate"].round(1)
        gp["MAE"]     = gp["MAE"].round(2)

        min_games = st.slider(
            "Minimum games to include a team in this view",
            min_value=5,
            max_value=25,
            value=10,
            step=1,
        )
        gp_filt = gp[gp["Games"] >= min_games].copy()

        if gp_filt.empty:
            st.info("No teams meet the minimum-games threshold yet.")
        else:
            most_predictable = gp_filt.sort_values(["HitRate", "MAE"], ascending=[False, True]).head(10)
            chaos            = gp_filt.sort_values(["HitRate", "MAE"], ascending=[True, False]).head(10)

            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown(
                    '<div class="rc-section-head" style="font-size:0.68rem;padding:4px 12px;">🎯 Most Predictable</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    _rc_df_html(
                        most_predictable[["Team", "Gender", "Games", "HitRate", "MAE"]]
                        .rename(columns={"HitRate": "Model hit %", "MAE": "Avg margin error"})
                    ),
                    unsafe_allow_html=True,
                )
            with c_right:
                st.markdown(
                    '<div class="rc-section-head" style="font-size:0.68rem;padding:4px 12px;'
                    'border-color:rgba(250,204,21,0.35);background:rgba(250,204,21,0.07);color:#fde68a;">💥 Chaos Teams</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    _rc_df_html(
                        chaos[["Team", "Gender", "Games", "HitRate", "MAE"]]
                        .rename(columns={"HitRate": "Model hit %", "MAE": "Avg margin error"})
                    ),
                    unsafe_allow_html=True,
                )

            st.markdown(
                '<div class="rc-callout rc-callout-blue">'
                'High hit rate + low margin error → the model "gets" that team. '
                'Low hit rate or big errors → they\'re volatile, streaky, or just weird.'
                '</div>',
                unsafe_allow_html=True,
            )

# ----------------------------
# TAB 2 — CONFIDENCE & CALIBRATION
# ----------------------------
with tab_conf:
    _rc_section("🎯", "How Honest Are the Percentages?")

    st.markdown(
        '<div class="rc-stat-grid rc-stat-grid-3">'
        + _rc_stat_card("Overall Brier Score",   f"{overall_brier:.3f}" if np.isfinite(overall_brier) else "—", "lower is better · 0.25 = coin flip", "#a78bfa")
        + _rc_stat_card("Boys MAE (points)",     f"{boys_mae:.2f}"      if np.isfinite(boys_mae)      else "—", "avg margin error · boys games",       "#60a5fa")
        + _rc_stat_card("Girls MAE (points)",    f"{girls_mae:.2f}"     if np.isfinite(girls_mae)     else "—", "avg margin error · girls games",      "#f472b6")
        + '</div>',
        unsafe_allow_html=True,
    )

    _rc_section("📊", "Accuracy by Confidence Band")

    if calibration_data is None or calibration_data.empty:
        st.info("Calibration table not available in this bundle.")
    else:
        cal_display = calibration_data.rename(columns={
            "ConfBucket": "Confidence band",
            "Games":      "Games",
            "Correct":    "Model wins",
            "HitRate":    "Actual win %",
            "AvgProb":    "Avg predicted %",
        })
        st.markdown(_rc_df_html(cal_display), unsafe_allow_html=True)
        st.markdown(
            '<div class="rc-callout rc-callout-blue">'
            'If <strong>Actual win %</strong> &gt; <strong>Avg predicted %</strong> in a band → model is <em>under-confident</em>. '
            'If lower → model is <em>over-confident</em> in that range.'
            '</div>',
            unsafe_allow_html=True,
        )

        delta_df = calibration_data.copy()
        delta_df["Delta (actual - predicted)"] = (
            pd.to_numeric(delta_df["HitRate"], errors="coerce")
            - pd.to_numeric(delta_df["AvgProb"], errors="coerce")
        )

        _rc_section("⚖️", "Where Is the Model Over or Under-Confident?")
        delta_display = delta_df[["ConfBucket", "Games", "AvgProb", "HitRate", "Delta (actual - predicted)"]].rename(columns={
            "ConfBucket": "Confidence band",
            "AvgProb":    "Avg predicted %",
            "HitRate":    "Actual win %",
        })
        st.markdown(_rc_df_html(delta_display), unsafe_allow_html=True)
        st.markdown(
            '<div class="rc-callout rc-callout-green">'
            'Positive delta = favorites win more than predicted (model is under-confident). '
            'Negative delta = favorites win less (model is over-confident).'
            '</div>',
            unsafe_allow_html=True,
        )

    _rc_section("📐", "Record by Spread Size")

    if spread_performance is None or spread_performance.empty:
        st.info("Spread table not available in this bundle.")
    else:
        spread_display = spread_performance.rename(columns={
            "SpreadBucket": "Spread band",
            "Games":        "Games",
            "Correct":      "Model wins",
            "HitRate":      "Win %",
            "AvgSpread":    "Avg spread",
            "MAE":          "Avg margin error",
        })
        st.markdown(_rc_df_html(spread_display), unsafe_allow_html=True)

# ----------------------------
# TAB 3 — BIGGEST MISSES
# ----------------------------
with tab_misses:
    _rc_section("💥", "When Big Favorites Lose")

    if played is None or played.empty or "ModelCorrect" not in played.columns:
        st.info("Favorite-loss analysis will appear once per-game performance data is available.")
    else:
        min_conf = st.slider(
            "Minimum confidence to count as a favorite loss",
            min_value=50,
            max_value=95,
            value=60,
            step=5,
            help="Filters out low-confidence coin flips so favorite losses reflect real surprises.",
        )

        show_band_split  = st.toggle("Show confidence-band split", value=True)
        show_true_shocks = st.toggle("Show true shocks (90%+ favorites only)", value=True)

        d = played.copy()

        needed = {"ModelCorrect", "FavProbPct", "Date", "Home", "Away", "Favorite", "HomeScore", "AwayScore"}
        if not needed.issubset(d.columns):
            st.info("Favorite-loss analysis needs columns: " + ", ".join(sorted(needed)))
        else:
            d["ModelCorrect"] = pd.to_numeric(d["ModelCorrect"], errors="coerce").fillna(0).astype(int).astype(bool)
            d["FavProbPct"]   = pd.to_numeric(d["FavProbPct"],   errors="coerce")

            fav_losses      = d[~d["ModelCorrect"]].sort_values("FavProbPct", ascending=False).copy()
            fav_losses_filt = fav_losses[fav_losses["FavProbPct"] >= float(min_conf)].copy()

            loss_ct   = int(len(fav_losses_filt))
            denom     = int(len(d)) if len(d) else 0
            loss_rate = (100.0 * loss_ct / denom) if denom else 0.0

            true_shocks    = fav_losses[fav_losses["FavProbPct"] >= 90].copy()
            true_shocks_ct = int(len(true_shocks))

            st.markdown(
                '<div class="rc-stat-grid rc-stat-grid-3">'
                + _rc_stat_card("Favorite Losses",     str(loss_ct),       f"{loss_rate:.1f}% of completed games",         "#f87171")
                + _rc_stat_card("Min Confidence",      f"{min_conf}%",     "applied filter",                               "#60a5fa")
                + _rc_stat_card("True Shocks (90%+)",  str(true_shocks_ct), "unfiltered · high-confidence losses",         "#facc15")
                + '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="rc-callout rc-callout-blue">'
                'Raising the minimum confidence hides coin-flip games and focuses on spots where the model really stuck its neck out.'
                '</div>',
                unsafe_allow_html=True,
            )

            if fav_losses_filt.empty:
                st.info("No favorite losses at this confidence threshold yet.")
            else:
                show = fav_losses_filt.head(10).copy()
                show["DateStr"]  = pd.to_datetime(show["Date"], errors="coerce").dt.strftime("%b %d")
                show["ScoreStr"] = (
                    pd.to_numeric(show["HomeScore"], errors="coerce").fillna(0).astype(int).astype(str)
                    + "-"
                    + pd.to_numeric(show["AwayScore"], errors="coerce").fillna(0).astype(int).astype(str)
                )
                view = show[["DateStr", "Home", "Away", "Favorite", "FavProbPct", "ScoreStr"]].rename(columns={
                    "DateStr":    "Date",
                    "FavProbPct": "Model conf. %",
                    "ScoreStr":   "Final score",
                })
                st.markdown("**Biggest misses (favorite lost):**")
                st.markdown(_rc_df_html(view), unsafe_allow_html=True)

            if show_band_split and not d.empty:
                bins   = [50, 60, 70, 80, 90, 101]
                labels = ["50-59%", "60-69%", "70-79%", "80-89%", "90-100%"]
                band_df = d.copy()
                band_df["ConfBand"] = pd.cut(band_df["FavProbPct"], bins=bins, labels=labels, right=False)

                band = (
                    band_df.groupby("ConfBand", dropna=True)
                    .agg(
                        Games=("ConfBand", "size"),
                        FavoriteLosses=("ModelCorrect", lambda s: int((~pd.Series(s).astype(bool)).sum())),
                    )
                    .reset_index()
                )
                band["Favorite loss %"] = 100.0 * band["FavoriteLosses"] / band["Games"].replace(0, np.nan)

                _rc_section("📊", "Confidence Bands — How Often Favorites Lose")
                st.markdown(
                    _rc_df_html(band.rename(columns={"ConfBand": "Confidence band"})),
                    unsafe_allow_html=True,
                )

            _rc_section("🔦", "Spotlight Games")

            sharp_game = None
            if {"PredMargin", "ActualMargin"}.issubset(d.columns):
                temp = d.copy()
                temp["PredMargin"]   = pd.to_numeric(temp["PredMargin"], errors="coerce")
                temp["ActualMargin"] = pd.to_numeric(temp["ActualMargin"], errors="coerce")
                temp["AbsError"]     = (temp["PredMargin"] - temp["ActualMargin"]).abs()
                mid = temp[(temp["ModelCorrect"]) & (temp["FavProbPct"].between(55, 75))]
                if not mid.empty:
                    sharp_game = mid.sort_values("AbsError").head(1).iloc[0]

            miss_game = fav_losses.head(1).iloc[0] if not fav_losses.empty else None

            sc1, sc2 = st.columns(2)
            with sc1:
                if sharp_game is None:
                    st.markdown(
                        '<div class="rc-spotlight">'
                        '<div class="rc-spotlight-badge">🎯 Sharpest Call So Far</div>'
                        '<div class="rc-spotlight-detail">Waiting on enough completed games.</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    date_str = pd.to_datetime(sharp_game["Date"], errors="coerce").strftime("%b %d")
                    home = sharp_game["Home"]
                    away = sharp_game["Away"]
                    conf = sharp_game["FavProbPct"]
                    pm   = sharp_game["PredMargin"]
                    am   = sharp_game["ActualMargin"]
                    st.markdown(
                        f'<div class="rc-spotlight" style="border-color:rgba(74,222,128,0.35);">'
                        f'<div class="rc-spotlight-badge" style="color:#4ade80;">🎯 SHARPEST CALL SO FAR</div>'
                        f'<div class="rc-spotlight-game">{home} vs {away}</div>'
                        f'<div class="rc-spotlight-detail">'
                        f'{date_str} &nbsp;·&nbsp; {conf:.0f}% favorite &nbsp;·&nbsp; spread {pm:+.1f}<br>'
                        f'Final margin: <strong style="color:#4ade80;">{am:+.1f}</strong> — nearly perfect projection'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

            with sc2:
                if miss_game is None:
                    st.markdown(
                        '<div class="rc-spotlight">'
                        '<div class="rc-spotlight-badge">💥 Biggest Miss</div>'
                        '<div class="rc-spotlight-detail">No completed games yet.</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    date_str = pd.to_datetime(miss_game["Date"], errors="coerce").strftime("%b %d")
                    home = miss_game["Home"]
                    away = miss_game["Away"]
                    conf = miss_game["FavProbPct"]
                    hs   = pd.to_numeric(miss_game["HomeScore"], errors="coerce")
                    as_  = pd.to_numeric(miss_game["AwayScore"], errors="coerce")
                    if np.isnan(hs) or np.isnan(as_):
                        score_detail = "score unavailable"
                    else:
                        am = hs - as_
                        score_detail = f"{int(hs)}-{int(as_)} (margin {am:+.1f})"
                    st.markdown(
                        f'<div class="rc-spotlight" style="border-color:rgba(248,113,113,0.35);">'
                        f'<div class="rc-spotlight-badge" style="color:#f87171;">💥 BIGGEST MISS</div>'
                        f'<div class="rc-spotlight-game">{home} vs {away}</div>'
                        f'<div class="rc-spotlight-detail">'
                        f'{date_str} &nbsp;·&nbsp; {conf:.0f}% confident &nbsp;·&nbsp; favorite still lost<br>'
                        f'Final score: <strong style="color:#f87171;">{score_detail}</strong>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

            if show_true_shocks:
                if true_shocks.empty:
                    st.info("No true shocks yet (90%+ favorites).")
                else:
                    shock = true_shocks.head(10).copy()
                    shock["DateStr"]  = pd.to_datetime(shock["Date"], errors="coerce").dt.strftime("%b %d")
                    shock["ScoreStr"] = (
                        pd.to_numeric(shock["HomeScore"], errors="coerce").fillna(0).astype(int).astype(str)
                        + "-"
                        + pd.to_numeric(shock["AwayScore"], errors="coerce").fillna(0).astype(int).astype(str)
                    )
                    shock_view = shock[["DateStr", "Home", "Away", "Favorite", "FavProbPct", "ScoreStr"]].rename(columns={
                        "DateStr":    "Date",
                        "FavProbPct": "Model conf. %",
                        "ScoreStr":   "Final score",
                    })
                    _rc_section("⚡", "True Shocks — 90%+ Favorites That Lost")
                    st.markdown(_rc_df_html(shock_view), unsafe_allow_html=True)

st.divider()
st.caption("Data loaded from v50 performance parquets.")
render_footer()
