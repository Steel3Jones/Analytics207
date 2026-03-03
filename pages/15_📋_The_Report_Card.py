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

# ----------------------------
# INTRO + GREEN PILLS
# ----------------------------
st.markdown("### 📚 How to read this page")
st.markdown(
    """
    This is the **report card** for the prediction model:
    - **Accuracy** – how often the favorite actually wins.
    - **Margin error** – how close the projected margin is to the final score.
    - **Calibration** – when the model says 70%, does it win about 7 out of 10?
    """
)
st.info(
    "All numbers below use *completed* regular-season games. "
    "Playoffs, scrimmage & exhibitions are not included."
)

overall_text  = f"{overall_pct:.1f}%" if np.isfinite(overall_pct) else "—"
upset_count   = max(0, total_games - correct_games)
upset_text    = f"{upset_rate:.1f}%" if np.isfinite(upset_rate) else "—"
mae_text      = f"{mae:.2f}" if np.isfinite(mae) else "—"
within5_text  = f"{within5:.1f}%" if np.isfinite(within5) else "—"

hero_html = f"""
<div style="
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin:10px 0 24px;
  font-family:system-ui,-apple-system,Segoe UI,sans-serif;
">
  <div style="
      padding:6px 12px;
      border-radius:999px;
      background:#022c22;
      border:1px solid #16a34a33;
      color:#bbf7d0;
      font-size:12px;
      font-weight:600;
  ">
    Overall accuracy: <span style="color:#4ade80;font-weight:700;">{overall_text}</span>
  </div>
  <div style="
      padding:6px 12px;
      border-radius:999px;
      background:#022c22;
      border:1px solid #16a34a33;
      color:#bbf7d0;
      font-size:12px;
      font-weight:600;
  ">
    Upsets so far: <span style="color:#facc15;font-weight:700;">{upset_count}</span> games ({upset_text})
  </div>
  <div style="
      padding:6px 12px;
      border-radius:999px;
      background:#022c22;
      border:1px solid #16a34a33;
      color:#bbf7d0;
      font-size:12px;
      font-weight:600;
  ">
    Avg margin error: <span style="color:#38bdf8;font-weight:700;">{mae_text} pts</span>
  </div>
  <div style="
      padding:6px 12px;
      border-radius:999px;
      background:#022c22;
      border:1px solid #16a34a33;
      color:#bbf7d0;
      font-size:12px;
      font-weight:600;
  ">
    Within 5 points: <span style="color:#4ade80;font-weight:700;">{within5_text}</span> of games
  </div>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

st.divider()

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
    st.markdown("#### Model record by group")

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "Boys model record",
            f"{boys_wins}-{max(0, boys_games - boys_wins)}" if boys_games > 0 else "—",
            f"{boys_acc:.1f}% accuracy" if boys_games > 0 else "no boys games yet",
        )
        st.metric(
            "Girls model record",
            f"{girls_wins}-{max(0, girls_games - girls_wins)}" if girls_games > 0 else "—",
            f"{girls_acc:.1f}% accuracy" if girls_games > 0 else "no girls games yet",
        )

    with c2:
        if home_fav_games > 0:
            home_acc = 100.0 * home_fav_wins / home_fav_games
            st.metric("When favorite is home", f"{home_fav_wins}-{home_fav_games - home_fav_wins}", f"{home_acc:.1f}%")
        else:
            st.metric("When favorite is home", "—", "no home favorites yet")

        if away_fav_games > 0:
            away_acc = 100.0 * away_fav_wins / away_fav_games
            st.metric("When favorite is away", f"{away_fav_wins}-{away_fav_games - away_fav_wins}", f"{away_acc:.1f}%")
        else:
            st.metric("When favorite is away", "—", "no away favorites yet")

    st.markdown("#### 📏 Margin accuracy (spread quality)")

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("MAE (points)",  f"{mae:.2f}"       if np.isfinite(mae)      else "—")
    with mc2:
        st.metric("RMSE (points)", f"{rmse:.2f}"      if np.isfinite(rmse)     else "—")
    with mc3:
        st.metric("Within 5 pts",  f"{within5:.1f}%"  if np.isfinite(within5)  else "—")
    with mc4:
        st.metric("Within 10 pts", f"{within10:.1f}%" if np.isfinite(within10) else "—")

    st.caption(
        "Think of MAE as: on average, the predicted margin is this many points off the final score. "
        "Within 5 / 10 pts shows how often the spread was basically on the money."
    )

    st.markdown("#### How hard is it to pick winners?")

    model_hit = overall_pct
    home_hit = np.nan

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
        '<p style="margin-bottom:2px;font-size:0.85rem;color:#4ade80;font-weight:600;">'
        '📡 REAL‑TIME — picks made before tipoff, zero future information</p>',
        unsafe_allow_html=True,
    )
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.metric("Model favorite wins", f"{model_hit:.1f}%" if np.isfinite(model_hit) else "—")
    with r1c2:
        st.metric(
            "Always pick home team",
            f"{home_hit:.1f}%" if np.isfinite(home_hit) else "—",
        )
    with r1c3:
        st.metric("Coin flip", "50.0%", "reference only")

    st.markdown(
        '<p style="margin-bottom:2px;font-size:0.85rem;color:#f59e0b;font-weight:600;">'
        '🔮 HINDSIGHT — these strategies use end‑of‑season data the model never had</p>',
        unsafe_allow_html=True,
    )
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.metric(
            "Higher TI (Heal) with hindsight",
            f"{ti_hit:.1f}%" if np.isfinite(ti_hit) else "needs TI data",
            f"{ti_games:,} games • uses final TI" if ti_games > 0 else None,
        )
    with r2c2:
        st.metric(
            "Better record with hindsight",
            f"{rec_hit:.1f}%" if np.isfinite(rec_hit) else "needs record data",
            f"{rec_games:,} games • uses final record" if rec_games > 0 else None,
        )

    st.markdown(
        """
        <div style="
            margin:12px 0 20px;
            padding:12px 16px;
            border-radius:8px;
            background:rgba(245,158,11,0.08);
            border:1px solid rgba(245,158,11,0.25);
            font-size:0.82rem;
            color:#fde68a;
            line-height:1.55;
        ">
            <strong>💡 Why this matters:</strong> The hindsight strategies get to cheat —
            they use each team's <em>final</em> Heal points and win–loss record,
            information that didn't exist when the games were actually played.
            Our model made every single pick <strong>before tipoff</strong>,
            using only what was known at that moment — and still hit the mid‑80s.
            That's nearly as good as reading tomorrow's newspaper.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 📅 Season-over-season scoreboard")

    season_rows = [
        {
            "Season":   "Current",
            "Games":    total_games,
            "Accuracy": f"{overall_pct:.1f}%"    if np.isfinite(overall_pct)    else "—",
            "Brier":    f"{overall_brier:.3f}"   if np.isfinite(overall_brier) else "—",
            "MAE":      f"{mae:.2f}"             if np.isfinite(mae)           else "—",
            "Note":     "Updates from latest loaded bundle.",
        },
    ]
    st.dataframe(pd.DataFrame(season_rows), hide_index=True, use_container_width=True)

    st.markdown("#### Which teams are easiest (and hardest) to predict?")

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

        gp = team_long.groupby("Team").agg(
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
                team_long.groupby("Team")["AbsError"]
                .mean()
                .rename("MAE")
                .reset_index()
            )
            gp = gp.merge(mae_by_team, on="Team", how="left")
        else:
            gp["MAE"] = np.nan

        gp["HitRate"] = 100.0 * gp["ModelWins"] / gp["Games"].replace(0, np.nan)

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
            most_predictable = gp_filt.sort_values(
                ["HitRate", "MAE"], ascending=[False, True]
            ).head(10)
            chaos = gp_filt.sort_values(
                ["HitRate", "MAE"], ascending=[True, False]
            ).head(10)

            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("Most predictable teams")
                st.dataframe(
                    most_predictable[["Team", "Games", "HitRate", "MAE"]]
                    .rename(columns={
                        "HitRate": "Model hit %",
                        "MAE": "Avg margin error",
                    }),
                    hide_index=True,
                    use_container_width=True,
                )
            with c_right:
                st.markdown("Chaos teams (hardest to model)")
                st.dataframe(
                    chaos[["Team", "Games", "HitRate", "MAE"]]
                    .rename(columns={
                        "HitRate": "Model hit %",
                        "MAE": "Avg margin error",
                    }),
                    hide_index=True,
                    use_container_width=True,
                )

            st.caption(
                "High hit rate and low margin error → the model 'gets' that team. "
                "Low hit rate or big errors → they're volatile, streaky, or just weird."
            )

# ----------------------------
# TAB 2 — CONFIDENCE & CALIBRATION
# ----------------------------
with tab_conf:
    st.markdown("#### How honest are the percentages?")

    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        st.metric("Overall Brier score", f"{overall_brier:.3f}" if np.isfinite(overall_brier) else "—")
    with bc2:
        st.metric("Boys MAE (points)",   f"{boys_mae:.2f}"       if np.isfinite(boys_mae)       else "—")
    with bc3:
        st.metric("Girls MAE (points)",  f"{girls_mae:.2f}"      if np.isfinite(girls_mae)      else "—")

    st.caption(
        "Lower Brier is better. 0.00 would be perfect; ~0.25 is like always predicting a 50/50 coin flip."
    )

    st.markdown("#### Accuracy by confidence band")
    if calibration_data is None or calibration_data.empty:
        st.info("Calibration table not available in this bundle.")
    else:
        st.dataframe(
            calibration_data.rename(columns={
                "ConfBucket": "Confidence band",
                "Games":      "Games",
                "Correct":    "Model wins",
                "HitRate":    "Actual win %",
                "AvgProb":    "Avg predicted %",
            }),
            hide_index=True,
            use_container_width=True,
        )
        st.markdown(
            """
            - If **Actual win %** is higher than **Avg predicted %** in a band, the model is *under‑confident* there.
            - If it's lower, the model is *over‑confident* in that range.
            """
        )

        delta_df = calibration_data.copy()
        delta_df["Delta (actual - predicted)"] = (
            pd.to_numeric(delta_df["HitRate"], errors="coerce")
            - pd.to_numeric(delta_df["AvgProb"], errors="coerce")
        )

        st.markdown("#### Where is the model over or under-confident?")
        st.dataframe(
            delta_df[["ConfBucket", "Games", "AvgProb", "HitRate", "Delta (actual - predicted)"]]
            .rename(columns={
                "ConfBucket": "Confidence band",
                "AvgProb": "Avg predicted %",
                "HitRate": "Actual win %",
            }),
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            "Positive delta = favorites win more often than predicted (model is under‑confident). "
            "Negative delta = favorites win less often (model is over‑confident)."
        )

    st.markdown("#### Record by spread size")
    if spread_performance is None or spread_performance.empty:
        st.info("Spread table not available in this bundle.")
    else:
        st.dataframe(
            spread_performance.rename(columns={
                "SpreadBucket": "Spread band",
                "Games":        "Games",
                "Correct":      "Model wins",
                "HitRate":      "Win %",
                "AvgSpread":    "Avg spread",
                "MAE":          "Avg margin error",
            }),
            hide_index=True,
            use_container_width=True,
        )

# ----------------------------
# TAB 3 — BIGGEST MISSES
# ----------------------------
with tab_misses:
    st.markdown("#### When big favorites lose")

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

            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Favorite losses",      f"{loss_ct}",       f"{loss_rate:.1f}% of completed games")
            with k2:
                st.metric("Min confidence",       f"{min_conf}%",     "applied")
            with k3:
                st.metric("True shocks (90%+)",   f"{true_shocks_ct}", "unfiltered count")

            st.caption(
                "Raising the minimum confidence hides coin‑flip games and focuses on spots where the model really stuck its neck out."
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
                st.markdown("Biggest misses (favorite lost):")
                st.dataframe(view, hide_index=True, use_container_width=True)

            if show_band_split and not d.empty:
                bins   = [50, 60, 70, 80, 90, 101]
                labels = ["50–59%", "60–69%", "70–79%", "80–89%", "90–100%"]
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

                st.markdown("Confidence bands (how often favorites lose):")
                st.dataframe(
                    band.rename(columns={"ConfBand": "Confidence band"}),
                    hide_index=True,
                    use_container_width=True,
                )

            st.markdown("#### Spotlight games")

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
                st.markdown("**Sharpest call so far**")
                if sharp_game is None:
                    st.write("Waiting on enough completed games.")
                else:
                    date_str = pd.to_datetime(sharp_game["Date"], errors="coerce").strftime("%b %d")
                    home = sharp_game["Home"]
                    away = sharp_game["Away"]
                    conf = sharp_game["FavProbPct"]
                    pm   = sharp_game["PredMargin"]
                    am   = sharp_game["ActualMargin"]
                    st.markdown(
                        f"{date_str}: **{home} vs {away}**  \n"
                        f"Model edge: {conf:.0f}% favorite, spread {pm:+.1f}  \n"
                        f"Final margin: {am:+.1f} (very close to the projection)."
                    )

            with sc2:
                st.markdown("**Biggest miss by the model**")
                if miss_game is None:
                    st.write("No completed games yet.")
                else:
                    date_str = pd.to_datetime(miss_game["Date"], errors="coerce").strftime("%b %d")
                    home = miss_game["Home"]
                    away = miss_game["Away"]
                    conf = miss_game["FavProbPct"]
                    hs   = pd.to_numeric(miss_game["HomeScore"], errors="coerce")
                    as_  = pd.to_numeric(miss_game["AwayScore"], errors="coerce")
                    if np.isnan(hs) or np.isnan(as_):
                        margin_str = "margin N/A"
                        score_str = "score unavailable"
                    else:
                        am   = hs - as_
                        margin_str = f"margin {am:+.1f}"
                        score_str = f"{int(hs)}–{int(as_)}"
                    st.markdown(
                        f"{date_str}: **{home} vs {away}**  \n"
                        f"Model was {conf:.0f}% confident and the favorite still lost.  \n"
                        f"Final score: {score_str} ({margin_str})."
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
                    st.markdown("True shocks (90%+ favorites only):")
                    st.dataframe(shock_view, hide_index=True, use_container_width=True)

st.divider()
st.caption("Data loaded from v50 performance parquets.")
render_footer()
