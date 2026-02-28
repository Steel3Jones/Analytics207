from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)

st.set_page_config(
    page_title="⚔️ The Matchup Lab | Analytics207",
    page_icon="⚔️",
    layout="wide",
)
apply_global_layout_tweaks()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEAMS_PATH   = PROJECT_ROOT / "data" / "core" / "teams_team_season_core_v50.parquet"
GAMES_PATH   = PROJECT_ROOT / "data" / "core" / "games_game_core_v50.parquet"
PRED_PATH    = PROJECT_ROOT / "data" / "predictions" / "games_predictions_current.parquet"

# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_teams() -> pd.DataFrame:
    df = pd.read_parquet(TEAMS_PATH)
    for col in ["TeamKey", "Team", "Gender", "Class", "Region"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Class" in df.columns:
        df["Class"] = (
            df["Class"].str.upper()
            .str.replace("CLASS", "", regex=False)
            .str.strip()
        )
    for col in ["TI", "Wins", "Losses", "WinPct", "NetEff",
                "PPG", "OPPG", "MarginPG", "LuckZ", "QualityWins", "BadLosses"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if {"Wins", "Losses"}.issubset(df.columns) and "Record" not in df.columns:
        df["Record"] = (
            df["Wins"].fillna(0).astype(int).astype(str) + "-" +
            df["Losses"].fillna(0).astype(int).astype(str)
        )
    return df


@st.cache_data(ttl=3600)
def load_games() -> pd.DataFrame:
    df = pd.read_parquet(GAMES_PATH)
    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df["Played"] = df["Played"].fillna(False).astype(bool)
    for col in ["Home", "Away", "HomeKey", "AwayKey", "Gender"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    for col in ["HomeScore", "AwayScore"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=3600)
def load_predictions() -> pd.DataFrame:
    if not PRED_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(PRED_PATH)
    for col in ["HomeKey", "AwayKey", "PredWinnerKey"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    for col in ["PredHomeWinProb", "PredHomeScore", "PredAwayScore",
                "PredMargin", "PredTotalPoints", "PredWinnerProb",
                "PredWinnerProbPct", "PredSpreadAbs"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


teams_df = load_teams()
games_df = load_games()
pred_df  = load_predictions()


# ─────────────────────────────────────────────
# PREDICTION LOOKUP — no math, parquet only
# ─────────────────────────────────────────────

def get_prediction(key_a: str, key_b: str) -> dict | None:
    """
    Look up the prediction for key_a vs key_b from the predictions parquet.
    Prefers the most recent unplayed game, falls back to most recent overall.
    Returns None if no prediction exists.
    """
    if pred_df.empty:
        return None

    rows = pred_df[
        ((pred_df["HomeKey"] == key_a) & (pred_df["AwayKey"] == key_b)) |
        ((pred_df["HomeKey"] == key_b) & (pred_df["AwayKey"] == key_a))
    ].copy()

    if rows.empty:
        return None

    # Prefer unplayed, then most recent GameID
    unplayed = rows[rows["ResultHomeWin"].isna() | (rows["ResultHomeWin"] == 0.0)]
    best = (unplayed if not unplayed.empty else rows)
    best = best.sort_values("GameID", ascending=False).iloc[0]

    home_is_a = best["HomeKey"] == key_a

    prob_a  = float(best["PredHomeWinProb"]) if home_is_a else 1.0 - float(best["PredHomeWinProb"])
    score_a = float(best["PredHomeScore"])   if home_is_a else float(best["PredAwayScore"])
    score_b = float(best["PredAwayScore"])   if home_is_a else float(best["PredHomeScore"])
    margin  = float(best["PredMargin"])      if home_is_a else -float(best["PredMargin"])
    spread  = float(best["PredSpreadAbs"])

    fav_prob = max(prob_a, 1 - prob_a)
    if fav_prob >= 0.85:   confidence = "Very High"
    elif fav_prob >= 0.70: confidence = "High"
    elif fav_prob >= 0.58: confidence = "Medium"
    else:                  confidence = "Toss-Up"

    return dict(
        prob_a=prob_a,
        prob_b=1.0 - prob_a,
        score_a=score_a,
        score_b=score_b,
        margin=margin,
        spread=spread,
        confidence=confidence,
        game_id=best["GameID"],
    )


def head_to_head(games: pd.DataFrame, key_a: str, key_b: str) -> pd.DataFrame:
    if not {"HomeKey", "AwayKey"}.issubset(games.columns):
        return pd.DataFrame()
    played = games[games["Played"]].copy()
    mask = (
        ((played["HomeKey"] == key_a) & (played["AwayKey"] == key_b)) |
        ((played["HomeKey"] == key_b) & (played["AwayKey"] == key_a))
    )
    return played[mask].sort_values("Date", ascending=False).head(10)


def recent_games(games: pd.DataFrame, team_key: str, n: int = 5) -> pd.DataFrame:
    if not {"HomeKey", "AwayKey"}.issubset(games.columns):
        return pd.DataFrame()
    played = games[games["Played"]].copy()
    mask = (played["HomeKey"] == team_key) | (played["AwayKey"] == team_key)
    return played[mask].sort_values("Date", ascending=False).head(n)


# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────

render_logo()
render_page_header(
    title="⚔️ The Matchup Lab",
    definition="The Matchup Lab (n.): Put any two teams head-to-head. The model does the rest.",
    subtitle="Win probability, projected score, stat comparison, head-to-head history, and recent form — all in one place.",
)
st.write("")

# ─────────────────────────────────────────────
# TEAM SELECTOR
# ─────────────────────────────────────────────

sel_gender = st.radio("Gender", ["Boys", "Girls"], horizontal=True, key="lab_gender")
gender_teams = teams_df[teams_df["Gender"] == sel_gender].copy()
team_options = sorted(gender_teams["Team"].dropna().unique().tolist())

if len(team_options) < 2:
    st.error("Not enough teams loaded.")
    st.stop()

col_a, col_vs, col_b = st.columns([5, 1, 5])
with col_a:
    team_a_name = st.selectbox("🔵 Team A", team_options, index=0, key="lab_a")
with col_vs:
    st.markdown(
        "<div style='text-align:center;padding-top:28px;font-size:18px;"
        "font-weight:900;color:rgba(148,163,184,0.5);'>VS</div>",
        unsafe_allow_html=True,
    )
with col_b:
    team_b_name = st.selectbox("🔴 Team B", team_options,
                                index=min(1, len(team_options) - 1), key="lab_b")

if team_a_name == team_b_name:
    st.warning("Please select two different teams.")
    st.stop()

row_a = gender_teams[gender_teams["Team"] == team_a_name].iloc[0]
row_b = gender_teams[gender_teams["Team"] == team_b_name].iloc[0]
key_a = str(row_a.get("TeamKey", "")).strip()
key_b = str(row_b.get("TeamKey", "")).strip()

prediction = get_prediction(key_a, key_b)

st.write("")

if prediction is None:
    st.warning(
        f"No prediction found for **{team_a_name}** vs **{team_b_name}**. "
        "This matchup may not be scheduled or the prediction engine hasn't run yet."
    )
    st.stop()

# ─────────────────────────────────────────────
# HERO MATCHUP CARD
# ─────────────────────────────────────────────

def render_hero_matchup(a: pd.Series, b: pd.Series, pred: dict) -> None:
    name_a = str(a.get("Team",   ""))
    name_b = str(b.get("Team",   ""))
    rec_a  = str(a.get("Record", ""))
    rec_b  = str(b.get("Record", ""))
    cls_a  = str(a.get("Class",  ""))
    cls_b  = str(b.get("Class",  ""))
    reg_a  = str(a.get("Region", ""))
    reg_b  = str(b.get("Region", ""))

    prob_a = pred["prob_a"]
    prob_b = pred["prob_b"]
    sc_a   = pred["score_a"]
    sc_b   = pred["score_b"]
    conf   = pred["confidence"]
    bar_a  = f"{prob_a * 100:.1f}%"

    score_s = f"{sc_a:.0f} – {sc_b:.0f}" if pd.notna(sc_a) and pd.notna(sc_b) else "—"

    conf_color = {
        "Very High": "#22c55e",
        "High":      "#3b82f6",
        "Medium":    "#f59e0b",
        "Toss-Up":   "#a855f7",
    }.get(conf, "#64748b")

    html = f"""
<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;
             font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
<div style="background:#0d1626;border:1px solid rgba(255,255,255,0.09);
            border-radius:18px;padding:24px 28px;">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;
              margin-bottom:20px;">
    <div style="flex:1;text-align:left;">
      <div style="font-size:22px;font-weight:900;color:#f1f5f9;">{name_a}</div>
      <div style="font-size:12px;color:rgba(203,213,225,0.6);margin-top:2px;">
        {rec_a} · Class {cls_a} {reg_a}
      </div>
      <div style="font-size:28px;font-weight:900;color:#3b82f6;margin-top:8px;">
        {prob_a*100:.1f}%
      </div>
      <div style="font-size:10px;color:rgba(148,163,184,0.5);">win probability</div>
    </div>
    <div style="text-align:center;padding:0 16px;">
      <div style="font-size:13px;color:rgba(148,163,184,0.4);font-weight:700;
                  margin-bottom:6px;">PROJECTED</div>
      <div style="font-size:24px;font-weight:900;color:#fde68a;">{score_s}</div>
      <div style="font-size:10px;color:rgba(148,163,184,0.4);margin-top:4px;">final score</div>
      <div style="margin-top:10px;background:{conf_color};color:#0f172a;
                  font-size:9px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;
                  padding:4px 12px;border-radius:999px;display:inline-block;">{conf}</div>
      <div style="font-size:9px;color:rgba(148,163,184,0.35);margin-top:6px;">
        🤖 Prediction Engine
      </div>
    </div>
    <div style="flex:1;text-align:right;">
      <div style="font-size:22px;font-weight:900;color:#f1f5f9;">{name_b}</div>
      <div style="font-size:12px;color:rgba(203,213,225,0.6);margin-top:2px;">
        {rec_b} · Class {cls_b} {reg_b}
      </div>
      <div style="font-size:28px;font-weight:900;color:#ef4444;margin-top:8px;">
        {prob_b*100:.1f}%
      </div>
      <div style="font-size:10px;color:rgba(148,163,184,0.5);">win probability</div>
    </div>
  </div>
  <div style="height:8px;border-radius:999px;overflow:hidden;
              background:rgba(239,68,68,0.3);position:relative;">
    <div style="position:absolute;left:0;top:0;height:100%;width:{bar_a};
                background:linear-gradient(90deg,#3b82f6,#2563eb);
                border-radius:999px;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:4px;">
    <span style="font-size:10px;color:rgba(59,130,246,0.7);">{name_a}</span>
    <span style="font-size:10px;color:rgba(239,68,68,0.7);">{name_b}</span>
  </div>
</div>
</body></html>"""
    components.html(html, height=250, scrolling=False)


render_hero_matchup(row_a, row_b, prediction)
st.write("")

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab_stats, tab_h2h, tab_form, tab_radar = st.tabs([
    "📊 Stat Comparison",
    "📜 Head-to-Head History",
    "📅 Recent Form",
    "🕸️ Radar Chart",
])

# ── STAT COMPARISON ───────────────────────────────────────────────────

with tab_stats:
    st.markdown("### 📊 Side-by-Side Stats")
    st.write("")

    stat_map = {
        "TI (Heal Point Index)": "TI",
        "Net Efficiency":        "NetEff",
        "Points Per Game":       "PPG",
        "Opp Points Per Game":   "OPPG",
        "Margin Per Game":       "MarginPG",
        "Win Pct":               "WinPct",
        "Luck Z-Score":          "LuckZ",
        "Quality Wins":          "QualityWins",
        "Bad Losses":            "BadLosses",
    }

    rows = []
    for label, col in stat_map.items():
        val_a = pd.to_numeric(row_a.get(col, np.nan), errors="coerce")
        val_b = pd.to_numeric(row_b.get(col, np.nan), errors="coerce")
        if pd.isna(val_a) and pd.isna(val_b):
            continue
        lower_is_better = col in ["OPPG", "BadLosses"]
        if pd.notna(val_a) and pd.notna(val_b):
            a_wins = (val_a < val_b) if lower_is_better else (val_a > val_b)
            edge = team_a_name if a_wins else team_b_name
        else:
            edge = "—"
        rows.append({
            "Stat":      label,
            team_a_name: f"{val_a:.3f}" if pd.notna(val_a) else "—",
            team_b_name: f"{val_b:.3f}" if pd.notna(val_b) else "—",
            "Edge":      edge,
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.write("")
        a_edges = sum(1 for r in rows if r["Edge"] == team_a_name)
        b_edges = sum(1 for r in rows if r["Edge"] == team_b_name)
        tally_html = f"""
<div style="display:flex;gap:16px;font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="flex:1;background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);
              border-radius:12px;padding:14px;text-align:center;">
    <div style="font-size:28px;font-weight:900;color:#3b82f6;">{a_edges}</div>
    <div style="font-size:11px;color:rgba(203,213,225,0.6);">stat advantages</div>
    <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-top:4px;">{team_a_name}</div>
  </div>
  <div style="flex:1;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
              border-radius:12px;padding:14px;text-align:center;">
    <div style="font-size:28px;font-weight:900;color:#ef4444;">{b_edges}</div>
    <div style="font-size:11px;color:rgba(203,213,225,0.6);">stat advantages</div>
    <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-top:4px;">{team_b_name}</div>
  </div>
</div>"""
        components.html(tally_html, height=100, scrolling=False)

# ── HEAD-TO-HEAD ──────────────────────────────────────────────────────

with tab_h2h:
    st.markdown(f"### 📜 {team_a_name} vs {team_b_name} — All-Time This Season")
    st.write("")

    h2h_df = head_to_head(games_df, key_a, key_b)

    if h2h_df.empty:
        st.info(f"No games found between {team_a_name} and {team_b_name} this season.")
    else:
        a_wins = 0
        b_wins = 0

        for _, g in h2h_df.iterrows():
            hs  = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
            as_ = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
            home = str(g.get("Home", ""))
            away = str(g.get("Away", ""))
            date = str(g.get("Date", ""))[:10]

            if pd.notna(hs) and pd.notna(as_):
                home_won = hs > as_
                winner   = home if home_won else away
                w_score  = int(max(hs, as_))
                l_score  = int(min(hs, as_))

                if winner == team_a_name:
                    a_wins += 1
                    w_color, l_color = "#3b82f6", "#ef4444"
                    w_name, l_name   = team_a_name, team_b_name
                else:
                    b_wins += 1
                    w_color, l_color = "#ef4444", "#3b82f6"
                    w_name, l_name   = team_b_name, team_a_name

                html = f"""
<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
            border-radius:10px;margin-bottom:6px;
            background:rgba(255,255,255,0.02);
            border:1px solid rgba(255,255,255,0.07);
            font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <span style="color:rgba(148,163,184,0.4);font-size:11px;min-width:80px;">{date}</span>
  <span style="color:{w_color};font-size:13px;font-weight:800;flex:1;">✓ {w_name}</span>
  <span style="color:#fde68a;font-size:14px;font-weight:900;">{w_score}–{l_score}</span>
  <span style="color:{l_color};font-size:13px;flex:1;text-align:right;">{l_name}</span>
  <span style="color:rgba(148,163,184,0.4);font-size:10px;min-width:60px;text-align:right;">
    {away} @ {home}
  </span>
</div>"""
                components.html(html, height=50, scrolling=False)

        st.write("")
        components.html(f"""
<div style="display:flex;gap:16px;font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="flex:1;background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);
              border-radius:12px;padding:12px;text-align:center;">
    <div style="font-size:32px;font-weight:900;color:#3b82f6;">{a_wins}</div>
    <div style="font-size:12px;color:#f1f5f9;font-weight:700;">{team_a_name}</div>
  </div>
  <div style="flex:1;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
              border-radius:12px;padding:12px;text-align:center;">
    <div style="font-size:32px;font-weight:900;color:#ef4444;">{b_wins}</div>
    <div style="font-size:12px;color:#f1f5f9;font-weight:700;">{team_b_name}</div>
  </div>
</div>""", height=90, scrolling=False)

# ── RECENT FORM ───────────────────────────────────────────────────────

with tab_form:
    st.markdown("### 📅 Recent Form — Last 5 Games Each")
    st.write("")

    col_a_form, col_b_form = st.columns(2)

    for col, team_name, team_key, color in [
        (col_a_form, team_a_name, key_a, "#3b82f6"),
        (col_b_form, team_b_name, key_b, "#ef4444"),
    ]:
        with col:
            st.markdown(f"#### {team_name}")
            recent = recent_games(games_df, team_key, n=5)

            if recent.empty:
                st.info("No recent games found.")
                continue

            for _, g in recent.iterrows():
                hs   = pd.to_numeric(g.get("HomeScore", np.nan), errors="coerce")
                as_  = pd.to_numeric(g.get("AwayScore", np.nan), errors="coerce")
                home = str(g.get("Home", ""))
                away = str(g.get("Away", ""))
                date = str(g.get("Date", ""))[:10]

                is_home  = (str(g.get("HomeKey", "")) == team_key)
                opp      = away if is_home else home
                tm_score = int(hs) if is_home and pd.notna(hs) else (int(as_) if pd.notna(as_) else 0)
                op_score = int(as_) if is_home and pd.notna(as_) else (int(hs) if pd.notna(hs) else 0)

                if pd.notna(hs) and pd.notna(as_):
                    won       = tm_score > op_score
                    res_label = "W" if won else "L"
                    res_color = "#22c55e" if won else "#ef4444"
                    res_bg    = "rgba(34,197,94,0.08)" if won else "rgba(239,68,68,0.08)"
                    venue     = "Home" if is_home else "Away"

                    components.html(f"""
<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
            border-radius:9px;margin-bottom:5px;
            background:{res_bg};border:1px solid {res_color}33;
            font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <span style="background:{res_color};color:#0f172a;font-size:11px;font-weight:900;
               padding:2px 8px;border-radius:999px;min-width:16px;text-align:center;">
    {res_label}
  </span>
  <span style="color:#f1f5f9;font-size:12px;font-weight:700;flex:1;">vs {opp}</span>
  <span style="color:#fde68a;font-size:13px;font-weight:800;">{tm_score}–{op_score}</span>
  <span style="color:rgba(148,163,184,0.4);font-size:10px;">{venue} · {date}</span>
</div>""", height=48, scrolling=False)

# ── RADAR CHART ───────────────────────────────────────────────────────

with tab_radar:
    st.markdown("### 🕸️ Stat Radar")
    st.caption("Normalized comparison across key metrics. Larger area = better overall profile.")
    st.write("")

    radar_stats = {
        "Offense (PPG)":  "PPG",
        "Defense (OPPG)": "OPPG",
        "Efficiency":     "NetEff",
        "Win Rate":       "WinPct",
        "Margin/Game":    "MarginPG",
        "TI Rating":      "TI",
    }
    invert = {"Defense (OPPG)"}

    labels, vals_a, vals_b = [], [], []

    for label, col in radar_stats.items():
        va = pd.to_numeric(row_a.get(col, np.nan), errors="coerce")
        vb = pd.to_numeric(row_b.get(col, np.nan), errors="coerce")
        if pd.isna(va) or pd.isna(vb):
            continue
        lo, hi = min(float(va), float(vb)), max(float(va), float(vb))
        rng = hi - lo
        if rng == 0:
            na, nb = 0.5, 0.5
        else:
            na = (float(va) - lo) / rng
            nb = (float(vb) - lo) / rng
            if label in invert:
                na, nb = 1 - na, 1 - nb
        labels.append(label)
        vals_a.append(round(na, 3))
        vals_b.append(round(nb, 3))

    if len(labels) >= 3:
        fig = go.Figure()
        for vals, name, color, fill in [
            (vals_a, team_a_name, "#3b82f6", "rgba(59,130,246,0.15)"),
            (vals_b, team_b_name, "#ef4444", "rgba(239,68,68,0.15)"),
        ]:
            fig.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name=name,
                line=dict(color=color, width=2),
                fillcolor=fill,
                opacity=0.8,
            ))
        fig.update_layout(
            polar=dict(
                bgcolor="#0d1626",
                radialaxis=dict(
                    visible=True, range=[0, 1],
                    showticklabels=False,
                    gridcolor="rgba(148,163,184,0.15)",
                    linecolor="rgba(148,163,184,0.15)",
                ),
                angularaxis=dict(
                    gridcolor="rgba(148,163,184,0.15)",
                    linecolor="rgba(148,163,184,0.15)",
                    tickfont=dict(color="#94a3b8", size=11),
                ),
            ),
            paper_bgcolor="#060d1a",
            font=dict(color="#94a3b8"),
            legend=dict(font=dict(color="#f1f5f9", size=12), bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=40, b=40, l=60, r=60),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough stat data to render radar chart.")

render_footer()
