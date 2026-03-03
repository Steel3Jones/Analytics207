# pages/25__All_State_Analytics_Team.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
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


from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

st.set_page_config(
    page_title="All-State Analytics Team | Analytics207",
    page_icon="medal",
    layout="wide",
)
apply_global_layout_tweaks()
login_gate(required=False)
logout_button()

PROJECT_ROOT    = Path(__file__).resolve().parent.parent
DATA_DIR        = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
TEAMS_PATH      = DATA_DIR / "core" / "teams_team_season_analytics_v50.parquet"
TEAMS_CORE_PATH = DATA_DIR / "core" / "teams_team_season_core_v50.parquet"

TEAM_WEIGHT_COLS = {
    "TI":          0.28,
    "NetEff":      0.22,
    "WinPct":      0.15,
    "MarginPG":    0.12,
    "WinPctVsTop": 0.10,
    "SOS_EWP":     0.08,
    "CloseWinPct": 0.05,
}

PENALTY_COLS = {
    "BadLosses": 0.08,
}

WEIGHT_LABELS = {
    "TI":          "Heal Point Index",
    "NetEff":      "Net Efficiency",
    "WinPct":      "Win %",
    "MarginPG":    "Avg Margin/Game",
    "WinPctVsTop": "Win % vs Top Tier",
    "SOS_EWP":     "Strength of Schedule (OWP)",
    "CloseWinPct": "Close Game Win %",
    "BadLosses":   "Bad Losses (penalty)",
}

MIN_GAMES = 10

@st.cache_data(ttl=3600)
def load_teams() -> pd.DataFrame:
    path = TEAMS_PATH if TEAMS_PATH.exists() else TEAMS_CORE_PATH
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)

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

    num_cols = [
        "TI", "Wins", "Losses", "Games", "WinPct", "NetEff",
        "MarginPG", "PPG", "OPPG", "LuckZ",
        "SOS_EWP", "OWP", "OOWP", "RPI",
        "WinPctVsTop", "CloseWinPct", "RoadWinPct",
        "ScheduleAdjWins", "QualityWins", "BadLosses",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if {"Wins", "Losses"}.issubset(df.columns) and "Record" not in df.columns:
        df["Record"] = (
            df["Wins"].fillna(0).astype(int).astype(str) + "-" +
            df["Losses"].fillna(0).astype(int).astype(str)
        )

    if {"Wins", "Losses"}.issubset(df.columns):
        computed = df["Wins"].fillna(0) + df["Losses"].fillna(0)
        if "Games" in df.columns:
            df["Games"] = df["Games"].fillna(computed)
        else:
            df["Games"] = computed

    return df

teams_df = load_teams()

def zscore_col(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    std = s.std(ddof=0)
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / std

def compute_allstate_score(df: pd.DataFrame):
    out = df.copy()
    score = pd.Series(0.0, index=out.index)
    used_cols: list[str] = []

    for col, weight in TEAM_WEIGHT_COLS.items():
        if col in out.columns and out[col].notna().any():
            score += zscore_col(out[col]).fillna(0) * weight
            used_cols.append(col)

    for col, weight in PENALTY_COLS.items():
        if col in out.columns and out[col].notna().any():
            score -= zscore_col(out[col]).fillna(0) * weight

    out["AllStateScore"] = score
    mn, mx = score.min(), score.max()
    if mx > mn:
        out["AllStateRating"] = ((score - mn) / (mx - mn) * 100).round(1)
    else:
        out["AllStateRating"] = 50.0

    return out, used_cols

render_logo()
render_page_header(
    title="All-State Analytics Team",
    definition="All-State (n.): The best teams in Maine -- as determined purely by the numbers.",
    subtitle=(
        "First, Second, and Third Team All-State by class and gender. "
        "No committee. No politics. Just metrics and a model that doesn't play favorites."
    ),
)
st.write("")

fc1, fc2 = st.columns(2)
with fc1:
    sel_gender = st.selectbox("Gender", ["Boys", "Girls"], key="as_gender")
with fc2:
    sel_class = st.selectbox("Class", ["All", "A", "B", "C", "D", "S"], key="as_class")

sel_region = "All"

st.write("")

# ══════════════════════════════════════════════════════════════════════════
#  🔒 SUBSCRIBER GATE — everything below filters is locked
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
    All-State Analytics Team — Subscriber Only
  </div>
  <div style="font-size:0.85rem;color:#94a3b8;max-width:460px;margin:0 auto;">
    Subscribe to unlock the full All-State selections, methodology breakdown,
    complete rankings, and composite scores for every eligible team.
  </div>
</div>
""", height=200, scrolling=False)
    render_footer()
    st.stop()

view = teams_df[teams_df["Gender"] == sel_gender].copy()

if sel_class != "All":
    view = view[view["Class"] == sel_class]

if "Games" in view.columns:
    view = view[view["Games"].fillna(0) >= MIN_GAMES]

if view.empty:
    st.warning("No eligible teams found for this filter combination.")
    st.stop()

view, used_cols = compute_allstate_score(view)
view = view.sort_values("AllStateScore", ascending=False).reset_index(drop=True)

n_total  = len(view)
per_tier = max(3, min(5, n_total // 4))

TIER_CONFIG = {
    1: ("First Team All-State",  "rgba(245,158,11,0.18)",  "rgba(245,158,11,0.5)",  "#fde68a"),
    2: ("Second Team All-State", "rgba(148,163,184,0.12)", "rgba(148,163,184,0.4)", "#e2e8f0"),
    3: ("Third Team All-State",  "rgba(180,120,60,0.12)",  "rgba(180,120,60,0.4)",  "#fed7aa"),
}

def _safe(val, fmt: str, suffix: str = "") -> str:
    try:
        v = float(val)
        if np.isnan(v):
            return "--"
        return fmt.format(v) + suffix
    except (TypeError, ValueError):
        return "--"

def pct_fmt(val) -> str:
    try:
        v = float(val)
        if np.isnan(v):
            return "--"
        return f"{v*100:.1f}%" if abs(v) <= 1.5 else f"{v:.1f}%"
    except (TypeError, ValueError):
        return "--"

def tier_card_html(rank: int, row: pd.Series, tier: int) -> str:
    _, bg, border, text_color = TIER_CONFIG[tier]
    name    = str(row.get("Team",       ""))
    record  = str(row.get("Record",     ""))
    cls     = str(row.get("Class",      ""))
    region  = str(row.get("Region",     ""))
    rating  = row.get("AllStateRating", np.nan)

    ti_s     = _safe(row.get("TI"),          "{:.4f}")
    net_s    = _safe(row.get("NetEff"),      "{:+.2f}")
    margin_s = _safe(row.get("MarginPG"),    "{:+.1f}")
    wpct_s   = pct_fmt(row.get("WinPct"))
    vstop_s  = pct_fmt(row.get("WinPctVsTop"))
    sos_s    = _safe(row.get("SOS_EWP"),     "{:.3f}")
    close_s  = pct_fmt(row.get("CloseWinPct"))
    rating_s = _safe(rating,                "{:.1f}")
    bar_w    = f"{rating:.1f}%" if pd.notna(rating) else "50%"

    stats = [
        (ti_s,     "TI"),
        (net_s,    "Net Eff"),
        (margin_s, "Margin/G"),
        (wpct_s,   "Win %"),
        (vstop_s,  "vs Top"),
        (sos_s,    "SOS"),
        (close_s,  "Close W%"),
    ]

    stats_html = "".join(
        f'<div style="text-align:center;">'
        f'<div style="font-size:12px;font-weight:800;color:{text_color};">{val}</div>'
        f'<div style="font-size:9px;color:rgba(148,163,184,0.5);text-transform:uppercase;'
        f'letter-spacing:.07em;margin-top:1px;">{lbl}</div>'
        f'</div>'
        for val, lbl in stats
    )

    return (
        f'<div style="background:{bg};border:1px solid {border};border-radius:14px;'
        f'padding:13px 15px 11px;margin-bottom:8px;'
        f'font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:9px;">'
        f'<span style="color:{text_color};font-size:17px;font-weight:900;'
        f'min-width:26px;text-align:center;">#{rank}</span>'
        f'<span style="color:#f1f5f9;font-size:15px;font-weight:900;flex:1;">{name}</span>'
        f'<span style="color:rgba(203,213,225,0.6);font-size:11px;">{record}</span>'
        f'<span style="color:rgba(148,163,184,0.5);font-size:10px;margin-left:8px;">'
        f'Class {cls} {region}</span>'
        f'<span style="background:{border};color:#0f172a;font-size:10px;font-weight:900;'
        f'padding:3px 10px;border-radius:999px;margin-left:10px;">{rating_s}</span>'
        f'</div>'
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:9px;">{stats_html}</div>'
        f'<div style="height:3px;border-radius:999px;background:rgba(148,163,184,0.1);overflow:hidden;">'
        f'<div style="height:100%;width:{bar_w};'
        f'background:linear-gradient(90deg,{border},{text_color});'
        f'border-radius:999px;"></div></div>'
        f'</div>'
    )

def section_header_html(title: str, subtitle: str, color: str) -> str:
    return (
        f'<!doctype html><html><head><meta charset="utf-8"/></head>'
        f'<body style="margin:0;background:transparent;'
        f'font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">'
        f'<div style="border-left:4px solid {color};padding:8px 0 8px 16px;margin:8px 0 16px;">'
        f'<div style="font-size:18px;font-weight:900;color:#f1f5f9;">{title}</div>'
        f'<div style="font-size:11px;color:rgba(203,213,225,0.55);margin-top:3px;">{subtitle}</div>'
        f'</div></body></html>'
    )

tab_teams, tab_method, tab_full = st.tabs([
    "All-State Teams",
    "Methodology",
    "Full Rankings",
])

with tab_teams:
    first_team  = view.iloc[0:per_tier]
    second_team = view.iloc[per_tier:per_tier*2]
    third_team  = view.iloc[per_tier*2:per_tier*3]
    class_label = "All Classes" if sel_class == "All" else f"Class {sel_class}"

    components.html(
        section_header_html(
            "First Team All-State",
            f"The {per_tier} highest-rated teams -- {sel_gender} {class_label} (Statewide).",
            "#f59e0b",
        ),
        height=70, scrolling=False,
    )
    col1, col2 = st.columns(2)
    for i, (_, row) in enumerate(first_team.iterrows()):
        with (col1 if i % 2 == 0 else col2):
            components.html(tier_card_html(i + 1, row, tier=1), height=135, scrolling=False)

    st.write("")

    if not second_team.empty:
        components.html(
            section_header_html(
                "Second Team All-State",
                "Honorable mentions that narrowly missed the first team.",
                "#94a3b8",
            ),
            height=70, scrolling=False,
        )
        col1, col2 = st.columns(2)
        for i, (_, row) in enumerate(second_team.iterrows()):
            with (col1 if i % 2 == 0 else col2):
                components.html(tier_card_html(per_tier + i + 1, row, tier=2), height=135, scrolling=False)

        st.write("")

    if not third_team.empty:
        components.html(
            section_header_html(
                "Third Team All-State",
                "Strong seasons that deserve recognition.",
                "#b47c3c",
            ),
            height=70, scrolling=False,
        )
        col1, col2 = st.columns(2)
        for i, (_, row) in enumerate(third_team.iterrows()):
            with (col1 if i % 2 == 0 else col2):
                components.html(tier_card_html(per_tier*2 + i + 1, row, tier=3), height=135, scrolling=False)

    st.write("")

    snubs = view.iloc[per_tier*3:per_tier*3+4]
    if not snubs.empty:
        st.markdown("---")
        st.markdown("### Notable Snubs")
        st.caption("Just outside the third team -- the teams that will spark the most debate.")
        st.write("")
        col1, col2 = st.columns(2)
        for i, (_, row) in enumerate(snubs.iterrows()):
            rank     = per_tier * 3 + i + 1
            name     = str(row.get("Team",       ""))
            record   = str(row.get("Record",     ""))
            cls      = str(row.get("Class",      ""))
            region   = str(row.get("Region",     ""))
            rating_s = _safe(row.get("AllStateRating"), "{:.1f}")
            html = (
                f'<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;'
                f'borderradius:10px;margin-bottom:6px;'
                f'background:rgba(255,255,255,0.02);'
                f'border:1px solid rgba(255,255,255,0.07);'
                f'font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;">'
                f'<span style="color:rgba(148,163,184,0.4);font-size:12px;font-weight:700;width:24px;">#{rank}</span>'
                f'<span style="color:#f1f5f9;font-size:13px;font-weight:800;flex:1;">{name}</span>'
                f'<span style="color:rgba(203,213,225,0.5);font-size:11px;">{record}</span>'
                f'<span style="color:rgba(148,163,184,0.4);font-size:10px;margin-left:8px;">Class {cls} {region}</span>'
                f'<span style="color:#fde68a;font-size:12px;font-weight:700;margin-left:10px;">{rating_s}</span>'
                f'</div>'
            )
            with (col1 if i % 2 == 0 else col2):
                components.html(html, height=52, scrolling=False)

with tab_method:
    st.markdown("### How the All-State Score Works")
    st.write("")

    col_explain, col_weights = st.columns([0.55, 0.45], gap="large")

    with col_explain:
        available = [c for c in TEAM_WEIGHT_COLS if c in view.columns and view[c].notna().any()]
        missing   = [c for c in TEAM_WEIGHT_COLS if c not in available]

        st.markdown("""
**The Analytics207 All-State Score** is a composite ranking built from
150+ metrics collected throughout the season. No human votes. No politics.
Just the numbers.


#### The Process


1. **Eligibility** -- Teams must have played at least 10 games to qualify.


2. **Z-Score Normalization** -- Every metric is converted to a z-score
   within the filtered group so teams are judged relative to peers.


3. **Weighted Composite** -- Z-scores are weighted and summed into a
   single All-State Score.


4. **Penalty Deductions** -- Bad losses subtract from the score.


5. **Statewide Pool** -- Rankings always use the full state pool for each class.
   North/South splits are excluded to prevent small-pool inflation.
        """)

        if missing:
            st.info(
                f"**{len(missing)} metric(s) skipped** (not available): "
                + ", ".join(f"`{m}`" for m in missing)
            )

    with col_weights:
        st.markdown("#### Score Weights")
        st.write("")

        weight_data = []
        for col, w in TEAM_WEIGHT_COLS.items():
            avail = "OK" if col in view.columns and view[col].notna().any() else "missing"
            weight_data.append({
                "Metric":      col,
                "Description": WEIGHT_LABELS[col],
                "Weight":      f"{w*100:.0f}%",
                "Type":        "Positive",
                "Status":      avail,
            })
        for col, w in PENALTY_COLS.items():
            avail = "OK" if col in view.columns and view[col].notna().any() else "missing"
            weight_data.append({
                "Metric":      col,
                "Description": WEIGHT_LABELS[col],
                "Weight":      f"{w*100:.0f}%",
                "Type":        "Penalty",
                "Status":      avail,
            })

        st.dataframe(pd.DataFrame(weight_data), hide_index=True, use_container_width=True)
        st.write("")
        st.metric("Minimum Games Played", f"{MIN_GAMES} games")

with tab_full:
    st.markdown("### Complete Rankings")
    st.caption("Every eligible team ranked by All-State composite score. Score (0-100) normalized within filter.")
    st.write("")

    full = view.copy()
    if "Rank" in full.columns:
        full = full.drop(columns=["Rank"])
    full.insert(0, "Rank", range(1, len(full) + 1))

    def _tier_label(rank: int) -> str:
        if rank <= per_tier:     return "1st Team"
        if rank <= per_tier * 2: return "2nd Team"
        if rank <= per_tier * 3: return "3rd Team"
        return "--"

    full["All-State"] = full["Rank"].apply(_tier_label)

    disp_cols = [c for c in [
        "Rank", "All-State", "Team", "Gender", "Class", "Region", "Record",
        "AllStateRating", "TI", "NetEff", "WinPct", "MarginPG",
        "SOS_EWP", "WinPctVsTop", "CloseWinPct",
        "QualityWins", "BadLosses",
    ] if c in full.columns]

    disp = full[disp_cols].copy().rename(columns={
        "AllStateRating": "Score (0-100)",
        "NetEff":         "Net Eff",
        "WinPct":         "Win %",
        "MarginPG":       "Margin/G",
        "SOS_EWP":        "SOS (OWP)",
        "WinPctVsTop":    "vs Top",
        "CloseWinPct":    "Close W%",
        "QualityWins":    "Qual. Wins",
        "BadLosses":      "Bad Losses",
    })

    for col, dec in [("TI", 4), ("Net Eff", 2), ("Margin/G", 1), ("SOS (OWP)", 3)]:
        if col in disp.columns:
            disp[col] = pd.to_numeric(disp[col], errors="coerce").round(dec)

    for col in ["Win %", "vs Top", "Close W%"]:
        if col in disp.columns:
            raw = pd.to_numeric(disp[col], errors="coerce")
            disp[col] = raw.apply(
                lambda v: f"{v*100:.1f}%" if pd.notna(v) and abs(v) <= 1.5
                else (f"{v:.1f}%" if pd.notna(v) else "--")
            )

    st.dataframe(disp, hide_index=True, use_container_width=True)

render_footer()
