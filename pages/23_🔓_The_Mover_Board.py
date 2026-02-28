from __future__ import annotations

from pathlib import Path
import datetime as dt
import os

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
    page_title="📈 The Mover Board | Analytics207",
    page_icon="📈",
    layout="wide",
)
apply_global_layout_tweaks()

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR      = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
TEAMS_PATH    = DATA_DIR / "core" / "teams_team_season_core_v50.parquet"
GAMES_PATH    = DATA_DIR / "core" / "games_game_core_v50.parquet"
ANALYTICS_PATH = DATA_DIR / "core" / "teams_team_season_analytics_v50.parquet"

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
    for col in ["TI", "Wins", "Losses", "WinPct", "NetEff", "PPG", "OPPG", "MarginPG"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if {"Wins", "Losses"}.issubset(df.columns) and "Record" not in df.columns:
        df["Record"] = (
            df["Wins"].fillna(0).astype(int).astype(str) + "-" +
            df["Losses"].fillna(0).astype(int).astype(str)
        )
    return df

@st.cache_data(ttl=3600)
def load_analytics_ti() -> pd.DataFrame:
    df = pd.read_parquet(ANALYTICS_PATH)
    keep = [c for c in ["TeamKey", "TI"] if c in df.columns]
    df = df[keep].copy()
    if "TeamKey" in df.columns:
        df["TeamKey"] = df["TeamKey"].astype(str).str.strip()
    if "TI" in df.columns:
        df["TI"] = pd.to_numeric(df["TI"], errors="coerce")
    return df

@st.cache_data(ttl=3600)
def load_games() -> pd.DataFrame:
    df = pd.read_parquet(GAMES_PATH)
    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce")
    df["Played"] = df["Played"].fillna(False).astype(bool)
    for col in ["Home", "Away", "HomeKey", "AwayKey", "Gender", "HomeClass", "HomeRegion"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    for col in ["HomeScore", "AwayScore"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

teams_df = load_teams()
games_df = load_games()
ti_ana   = load_analytics_ti()

# Attach analytics TI by TeamKey only
if not ti_ana.empty:
    ti_src = ti_ana.dropna(subset=["TeamKey"]).copy()
    teams_df["TeamKey"] = teams_df["TeamKey"].astype(str).str.strip()
    teams_df = teams_df.merge(
        ti_src,
        on="TeamKey",
        how="left",
        suffixes=("", "_ana"),
    )
    if "TI_ana" in teams_df.columns:
        # Use analytics TI when present, otherwise keep existing TI
        teams_df["TI"] = teams_df["TI_ana"].where(
            teams_df["TI_ana"].notna(), teams_df.get("TI")
        )
        teams_df = teams_df.drop(columns=["TI_ana"])

# ─────────────────────────────────────────────
# RECENT FORM ENGINE
# ─────────────────────────────────────────────

def compute_recent_form(games: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    played = games[games["Played"]].copy()
    if not {"HomeKey", "AwayKey", "HomeScore", "AwayScore"}.issubset(played.columns):
        return pd.DataFrame()

    home_view = played[["Date", "HomeKey", "HomeScore", "AwayScore", "Gender"]].rename(
        columns={"HomeKey": "TeamKey", "HomeScore": "TeamScore", "AwayScore": "OppScore"}
    )
    away_view = played[["Date", "AwayKey", "AwayScore", "HomeScore", "Gender"]].rename(
        columns={"AwayKey": "TeamKey", "AwayScore": "TeamScore", "HomeScore": "OppScore"}
    )

    all_games = pd.concat([home_view, away_view]).sort_values("Date")
    rows = []

    for key, grp in all_games.groupby("TeamKey"):
        grp = grp.sort_values("Date")
        recent = grp.tail(n)
        recent = recent[recent["TeamScore"].notna() & recent["OppScore"].notna()]
        if recent.empty:
            continue

        margins = (recent["TeamScore"] - recent["OppScore"]).tolist()
        wins    = sum(m > 0 for m in margins)
        losses  = sum(m < 0 for m in margins)

        # Current streak
        streak_count = 0
        streak_dir   = ""
        for m in reversed(margins):
            direction = "W" if m > 0 else "L"
            if streak_dir == "":
                streak_dir = direction
                streak_count = 1
            elif direction == streak_dir:
                streak_count += 1
            else:
                break

        # Last 5 as W/L string e.g. "W W L W W"
        last5 = " ".join("W" if m > 0 else "L" for m in margins[-5:])

        rows.append({
            "TeamKey":        key,
            "RecentWins":     wins,
            "RecentLosses":   losses,
            "RecentGames":    len(recent),
            "AvgMarginRecent": float(np.mean(margins)),
            "LastMargins":    margins,
            "Streak":         f"{streak_dir}{streak_count}",
            "StreakDir":      streak_dir,
            "StreakN":        streak_count,
            "Last5":          last5,
        })

    return pd.DataFrame(rows)

form_df = compute_recent_form(games_df, n=5)
merged  = teams_df.merge(form_df, on="TeamKey", how="left")

# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────

render_logo()
render_page_header(
    title="📈 The Mover Board",
    definition="The Mover Board (n.): Who's rising, who's falling, and who's on fire right now.",
    subtitle="Teams ranked by momentum — last 5 games, current streak, and TI trajectory. Updated nightly.",
)
st.write("")

# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────

fc1, fc2, fc3 = st.columns(3)
with fc1:
    sel_gender = st.selectbox("Gender", ["All", "Boys", "Girls"])
with fc2:
    sel_class  = st.selectbox("Class",  ["All", "A", "B", "C", "D", "S"])
with fc3:
    sel_region = st.selectbox("Region", ["All", "North", "South"])

view = merged.copy()
if sel_gender != "All":
    view = view[view["Gender"] == sel_gender]
if sel_class != "All":
    view = view[view["Class"] == sel_class]
if sel_region != "All":
    view = view[view["Region"] == sel_region]

st.write("")

# ─────────────────────────────────────────────
# HERO SUMMARY CARDS
# ─────────────────────────────────────────────

def render_mover_hero(df: pd.DataFrame) -> None:
    hot   = df[df["StreakDir"] == "W"].sort_values("StreakN", ascending=False)
    cold  = df[df["StreakDir"] == "L"].sort_values("StreakN", ascending=False)
    hot_name  = str(hot.iloc[0]["Team"])   if not hot.empty else "—"
    hot_str   = str(hot.iloc[0]["Streak"]) if not hot.empty else "—"
    cold_name = str(cold.iloc[0]["Team"])  if not cold.empty else "—"
    cold_str  = str(cold.iloc[0]["Streak"]) if not cold.empty else "—"

    rising = df[df["AvgMarginRecent"].notna()].sort_values("AvgMarginRecent", ascending=False)
    rise_name   = str(rising.iloc[0]["Team"]) if not rising.empty else "—"
    rise_margin = f"+{rising.iloc[0]['AvgMarginRecent']:.1f}" if not rising.empty else "—"

    n_win_streak = (df["StreakDir"] == "W").sum()

    cards = [
        ("🔥", "Hottest Team",         hot_name,   hot_str + " streak",   "#f59e0b"),
        ("❄️", "Coldest Team",         cold_name,  cold_str + " streak",  "#3b82f6"),
        ("📈", "Best Avg Margin (L5)", rise_name,  rise_margin + " pts",  "#10b981"),
        ("✅", "Teams on Win Streak",  str(int(n_win_streak)), "in this view", "#8b5cf6"),
    ]
    card_html = ""
    for icon, label, val, sub, color in cards:
        card_html += f"""
        <div style="flex:1;min-width:160px;background:#0d1626;
                    border:1px solid rgba(255,255,255,0.09);
                    border-top:3px solid {color};border-radius:14px;
                    padding:16px 18px 14px;">
            <div style="font-size:20px;margin-bottom:6px;">{icon}</div>
            <div style="font-size:20px;font-weight:900;color:#f1f5f9;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{val}</div>
            <div style="font-size:10px;color:#fde68a;font-weight:700;margin-top:2px;">{sub}</div>
            <div style="font-size:10px;color:rgba(148,163,184,0.5);margin-top:2px;">{label}</div>
        </div>"""

    html = f"""<!doctype html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;background:transparent;
             font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="display:flex;gap:14px;flex-wrap:wrap;padding:4px 0 8px;">{card_html}</div>
</body></html>"""
    components.html(html, height=130, scrolling=False)

render_mover_hero(view)
st.write("")

# ─────────────────────────────────────────────
# STREAK BADGE
# ─────────────────────────────────────────────

def streak_badge(streak: str, direction: str, n: int) -> str:
    if direction == "W":
        color = "#16a34a" if n >= 4 else "#22c55e"
        bg    = "rgba(34,197,94,0.15)"
    else:
        color = "#dc2626" if n >= 4 else "#ef4444"
        bg    = "rgba(239,68,68,0.15)"
    return (
        f"<span style='background:{bg};color:{color};border:1px solid {color};"
        f"font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px;"
        f"white-space:nowrap;'>{streak}</span>"
    )

def last5_html(last5: str) -> str:
    if not isinstance(last5, str):
        return ""
    parts = last5.strip().split()
    dots  = []
    for p in parts[-5:]:
        c = "#22c55e" if p == "W" else "#ef4444"
        dots.append(
            f"<span style='display:inline-block;width:12px;height:12px;"
            f"border-radius:50%;background:{c};margin:0 2px;'></span>"
        )
    return "".join(dots)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab_risers, tab_fallers, tab_streaks, tab_all = st.tabs([
    "📈 Risers",
    "📉 Fallers",
    "🔥 Streak Leaders",
    "📊 Full Board",
])

# ── RISERS ────────────────────────────────────────────────────────────

with tab_risers:
    st.markdown("### 📈 Teams Trending Up")
    st.caption("Best average margin over their last 5 games — these teams are peaking.")
    st.write("")

    risers = (
        view[view["AvgMarginRecent"].notna() & (view["StreakDir"] == "W")]
        .sort_values("AvgMarginRecent", ascending=False)
        .head(20)
    )

    if risers.empty:
        st.info("No rising teams in this view.")
    else:
        for rank, (_, row) in enumerate(risers.iterrows(), 1):
            name   = str(row.get("Team",   ""))
            rec    = str(row.get("Record", ""))
            cls    = str(row.get("Class",  ""))
            region = str(row.get("Region", ""))
            gender = str(row.get("Gender", ""))
            ti     = row.get("TI",  np.nan)
            net    = row.get("NetEff", np.nan)
            avg_m  = row.get("AvgMarginRecent", np.nan)
            streak = str(row.get("Streak", ""))
            sdir   = str(row.get("StreakDir", "W"))
            sn     = int(row.get("StreakN", 0))
            last5  = str(row.get("Last5",  ""))

            ti_s   = f"{ti:.4f}"   if pd.notna(ti)  else "—"
            net_s  = f"{net:+.2f}" if pd.notna(net) else "—"
            avg_s  = f"+{avg_m:.1f}" if pd.notna(avg_m) else "—"

            sbadge = streak_badge(streak, sdir, sn)
            l5html = last5_html(last5)

            html = f"""
<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
            border-radius:10px;margin-bottom:6px;
            background:rgba(34,197,94,0.05);
            border:1px solid rgba(34,197,94,0.15);
            font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <span style="color:rgba(148,163,184,0.4);font-size:12px;font-weight:700;
               width:24px;text-align:center;">#{rank}</span>
  <span style="color:#f1f5f9;font-size:14px;font-weight:800;flex:1;">{name}</span>
  <span style="color:rgba(203,213,225,0.5);font-size:11px;">{rec} · {gender} {cls} {region}</span>
  <span style="color:#22c55e;font-size:13px;font-weight:800;margin-left:8px;">{avg_s} pts/game</span>
  <span style="color:rgba(148,163,184,0.4);font-size:10px;margin-left:8px;">TI {ti_s}</span>
  <span style="margin-left:10px;">{sbadge}</span>
  <span style="margin-left:10px;">{l5html}</span>
</div>"""
            components.html(html, height=52, scrolling=False)

# ── FALLERS ───────────────────────────────────────────────────────────

with tab_fallers:
    st.markdown("### 📉 Teams Trending Down")
    st.caption("Worst average margin over their last 5 games — these teams are struggling.")
    st.write("")

    fallers = (
        view[view["AvgMarginRecent"].notna()]
        .sort_values("AvgMarginRecent", ascending=True)
        .head(20)
    )

    if fallers.empty:
        st.info("No data in this view.")
    else:
        for rank, (_, row) in enumerate(fallers.iterrows(), 1):
            name   = str(row.get("Team",   ""))
            rec    = str(row.get("Record", ""))
            cls    = str(row.get("Class",  ""))
            region = str(row.get("Region", ""))
            gender = str(row.get("Gender", ""))
            ti     = row.get("TI", np.nan)
            avg_m  = row.get("AvgMarginRecent", np.nan)
            streak = str(row.get("Streak", ""))
            sdir   = str(row.get("StreakDir", "L"))
            sn     = int(row.get("StreakN", 0))
            last5  = str(row.get("Last5",  ""))

            ti_s  = f"{ti:.4f}"    if pd.notna(ti)  else "—"
            avg_s = f"{avg_m:.1f}" if pd.notna(avg_m) else "—"

            sbadge = streak_badge(streak, sdir, sn)
            l5html = last5_html(last5)

            html = f"""
<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
            border-radius:10px;margin-bottom:6px;
            background:rgba(239,68,68,0.05);
            border:1px solid rgba(239,68,68,0.15);
            font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <span style="color:rgba(148,163,184,0.4);font-size:12px;font-weight:700;
               width:24px;text-align:center;">#{rank}</span>
  <span style="color:#f1f5f9;font-size:14px;font-weight:800;flex:1;">{name}</span>
  <span style="color:rgba(203,213,225,0.5);font-size:11px;">{rec} · {gender} {cls} {region}</span>
  <span style="color:#ef4444;font-size:13px;font-weight:800;margin-left:8px;">{avg_s} pts/game</span>
  <span style="color:rgba(148,163,184,0.4);font-size:10px;margin-left:8px;">TI {ti_s}</span>
  <span style="margin-left:10px;">{sbadge}</span>
  <span style="margin-left:10px;">{l5html}</span>
</div>"""
            components.html(html, height=52, scrolling=False)

# ── STREAK LEADERS ────────────────────────────────────────────────────

with tab_streaks:
    st.markdown("### 🔥 Current Streak Leaders")
    st.write("")

    col_hot, col_cold = st.columns(2)

    with col_hot:
        st.markdown("#### 🟢 Longest Win Streaks")
        hot = (
            view[view["StreakDir"] == "W"]
            .sort_values("StreakN", ascending=False)
            .head(15)
        )
        if hot.empty:
            st.info("No active win streaks.")
        else:
            for _, row in hot.iterrows():
                name   = str(row.get("Team",   ""))
                rec    = str(row.get("Record", ""))
                sn     = int(row.get("StreakN", 0))
                streak = str(row.get("Streak", ""))
                last5  = str(row.get("Last5",  ""))
                l5html = last5_html(last5)
                bar_w  = f"{min(sn / 10 * 100, 100):.0f}%"
                html = f"""
<div style="padding:8px 12px;border-radius:9px;margin-bottom:5px;
            background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);
            font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="color:#f1f5f9;font-size:13px;font-weight:800;flex:1;">{name}</span>
    <span style="color:rgba(203,213,225,0.5);font-size:10px;">{rec}</span>
    <span style="color:#22c55e;font-size:13px;font-weight:900;margin-left:8px;">{streak}</span>
    <span style="margin-left:8px;">{l5html}</span>
  </div>
  <div style="margin-top:5px;height:3px;border-radius:999px;
              background:rgba(148,163,184,0.1);overflow:hidden;">
    <div style="height:100%;width:{bar_w};
                background:linear-gradient(90deg,#22c55e,#16a34a);
                border-radius:999px;"></div>
  </div>
</div>"""
                components.html(html, height=56, scrolling=False)

    with col_cold:
        st.markdown("#### 🔴 Longest Loss Streaks")
        cold = (
            view[view["StreakDir"] == "L"]
            .sort_values("StreakN", ascending=False)
            .head(15)
        )
        if cold.empty:
            st.info("No active loss streaks.")
        else:
            for _, row in cold.iterrows():
                name   = str(row.get("Team",   ""))
                rec    = str(row.get("Record", ""))
                sn     = int(row.get("StreakN", 0))
                streak = str(row.get("Streak", ""))
                last5  = str(row.get("Last5",  ""))
                l5html = last5_html(last5)
                bar_w  = f"{min(sn / 10 * 100, 100):.0f}%"
                html = f"""
<div style="padding:8px 12px;border-radius:9px;margin-bottom:5px;
            background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);
            font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="color:#f1f5f9;font-size:13px;font-weight:800;flex:1;">{name}</span>
    <span style="color:rgba(203,213,225,0.5);font-size:10px;">{rec}</span>
    <span style="color:#ef4444;font-size:13px;font-weight:900;margin-left:8px;">{streak}</span>
    <span style="margin-left:8px;">{l5html}</span>
  </div>
  <div style="margin-top:5px;height:3px;border-radius:999px;
              background:rgba(148,163,184,0.1);overflow:hidden;">
    <div style="height:100%;width:{bar_w};
                background:linear-gradient(90deg,#ef4444,#dc2626);
                border-radius:999px;"></div>
  </div>
</div>"""
                components.html(html, height=56, scrolling=False)

# ── FULL BOARD ────────────────────────────────────────────────────────

with tab_all:
    st.markdown("### 📊 Full Mover Board")
    st.caption("All teams sorted by recent average margin. Last 5 games only.")
    st.write("")

    board = view.copy()
    board = board[board["AvgMarginRecent"].notna()].sort_values("AvgMarginRecent", ascending=False)

    disp_cols = [c for c in [
        "Team", "Gender", "Class", "Region", "Record",
        "TI", "NetEff", "Streak", "Last5", "AvgMarginRecent",
        "RecentWins", "RecentLosses",
    ] if c in board.columns]

    disp = board[disp_cols].copy().rename(columns={
        "AvgMarginRecent": "Avg Margin (L5)",
        "RecentWins":      "W (L5)",
        "RecentLosses":    "L (L5)",
    })

    if "TI" in disp.columns:
        disp["TI"] = disp["TI"].round(4)
    if "NetEff" in disp.columns:
        disp["NetEff"] = disp["NetEff"].round(2)
    if "Avg Margin (L5)" in disp.columns:
        disp["Avg Margin (L5)"] = disp["Avg Margin (L5)"].round(1)

    st.dataframe(disp, hide_index=True, use_container_width=True)

render_footer()
