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

# ══════════════════════════════════════════════════════════════════════════
#  VISUAL HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _inject_as_css() -> None:
    st.markdown("""<style>
/* ── Section banner ──────────────────────────────────────────────────── */
.as-section-banner {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 20px;
    border-radius: 12px;
    margin: 24px 0 14px;
    border: 1px solid;
}
.as-section-icon { font-size: 1.6rem; }
.as-section-title {
    font-size: 1.1rem;
    font-weight: 900;
    letter-spacing: 0.02em;
}
.as-section-sub {
    font-size: 0.75rem;
    margin-top: 2px;
    opacity: 0.75;
}

/* ── Tier cards ──────────────────────────────────────────────────────── */
.as-card {
    border-radius: 14px;
    padding: 14px 16px 12px;
    margin-bottom: 10px;
    border: 1px solid;
    font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
}
.as-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}
.as-card-rank {
    font-size: 1.3rem;
    font-weight: 900;
    min-width: 30px;
    text-align: center;
    flex-shrink: 0;
}
.as-card-name {
    font-size: 1.0rem;
    font-weight: 900;
    color: #f1f5f9;
    flex: 1;
    line-height: 1.2;
}
.as-card-record {
    font-size: 0.82rem;
    color: #cbd5e1;
    font-weight: 600;
    flex-shrink: 0;
}
.as-card-meta {
    font-size: 0.70rem;
    color: #94a3b8;
    margin-left: 8px;
    flex-shrink: 0;
    white-space: nowrap;
}
.as-rating-pill {
    font-size: 0.72rem;
    font-weight: 900;
    padding: 3px 10px;
    border-radius: 999px;
    margin-left: 8px;
    flex-shrink: 0;
    letter-spacing: 0.04em;
}
.as-card-stats {
    display: flex;
    gap: 0;
    flex-wrap: nowrap;
    margin-bottom: 10px;
    background: rgba(0,0,0,0.20);
    border-radius: 8px;
    padding: 8px 4px;
    overflow-x: auto;
}
.as-stat-cell {
    flex: 1;
    text-align: center;
    min-width: 60px;
    padding: 0 4px;
}
.as-stat-val {
    font-size: 0.88rem;
    font-weight: 800;
    line-height: 1.1;
}
.as-stat-lbl {
    font-size: 0.58rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 3px;
}
.as-card-bar-bg {
    height: 4px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
}
.as-card-bar-fill {
    height: 100%;
    border-radius: 999px;
}

/* ── Snub rows ────────────────────────────────────────────────────────── */
.as-snub-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 10px;
    margin-bottom: 6px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
}
.as-snub-rank { color: #64748b; font-size: 0.80rem; font-weight: 700; min-width: 28px; }
.as-snub-name { color: #f1f5f9; font-size: 0.90rem; font-weight: 800; flex: 1; }
.as-snub-record { color: #94a3b8; font-size: 0.78rem; }
.as-snub-meta { color: #64748b; font-size: 0.70rem; margin-left: 8px; }
.as-snub-rating { color: #fde68a; font-size: 0.82rem; font-weight: 800; margin-left: 10px; }

/* ── Method cards ─────────────────────────────────────────────────────── */
.as-method-step {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    background: rgba(96,165,250,0.05);
    border: 1px solid rgba(96,165,250,0.12);
    border-radius: 10px;
    margin-bottom: 8px;
}
.as-method-num {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: rgba(96,165,250,0.18);
    color: #60a5fa;
    font-size: 0.75rem; font-weight: 900;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.as-method-content { font-size: 0.84rem; color: #e2e8f0; line-height: 1.55; }
.as-method-content strong { color: #93c5fd; }

/* ── Weight table ─────────────────────────────────────────────────────── */
.as-weight-card {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.15);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 12px;
}

/* ── Full rankings table ──────────────────────────────────────────────── */
.as-table-wrap {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.15);
    border-radius: 12px;
    overflow-x: auto;
    margin: 8px 0 16px;
}
</style>
""", unsafe_allow_html=True)


TIER_CONFIG = {
    1: {
        "label":   "First Team All-State",
        "icon":    "🥇",
        "bg":      "radial-gradient(circle at top left, #1c1400, #0f0c00)",
        "border":  "rgba(245,158,11,0.45)",
        "banner_bg":    "rgba(245,158,11,0.10)",
        "banner_border":"rgba(245,158,11,0.40)",
        "banner_color": "#fde68a",
        "rank_color":   "#fbbf24",
        "val_color":    "#fde68a",
        "bar_start":    "#f59e0b",
        "bar_end":      "#fde68a",
        "pill_bg":      "rgba(245,158,11,0.25)",
        "pill_color":   "#0f0c00",
    },
    2: {
        "label":   "Second Team All-State",
        "icon":    "🥈",
        "bg":      "radial-gradient(circle at top left, #111827, #080f1e)",
        "border":  "rgba(148,163,184,0.35)",
        "banner_bg":    "rgba(148,163,184,0.08)",
        "banner_border":"rgba(148,163,184,0.30)",
        "banner_color": "#e2e8f0",
        "rank_color":   "#cbd5e1",
        "val_color":    "#e2e8f0",
        "bar_start":    "#94a3b8",
        "bar_end":      "#e2e8f0",
        "pill_bg":      "rgba(148,163,184,0.20)",
        "pill_color":   "#0f172a",
    },
    3: {
        "label":   "Third Team All-State",
        "icon":    "🥉",
        "bg":      "radial-gradient(circle at top left, #160f06, #0d0906)",
        "border":  "rgba(180,120,60,0.40)",
        "banner_bg":    "rgba(180,120,60,0.08)",
        "banner_border":"rgba(180,120,60,0.30)",
        "banner_color": "#fed7aa",
        "rank_color":   "#fdba74",
        "val_color":    "#fed7aa",
        "bar_start":    "#b47c3c",
        "bar_end":      "#fed7aa",
        "pill_bg":      "rgba(180,120,60,0.22)",
        "pill_color":   "#160f06",
    },
}


def _safe(val, fmt: str, suffix: str = "") -> str:
    try:
        v = float(val)
        if np.isnan(v): return "--"
        return fmt.format(v) + suffix
    except (TypeError, ValueError):
        return "--"


def pct_fmt(val) -> str:
    try:
        v = float(val)
        if np.isnan(v): return "--"
        return f"{v*100:.1f}%" if abs(v) <= 1.5 else f"{v:.1f}%"
    except (TypeError, ValueError):
        return "--"


def _section_banner(tier: int, subtitle: str) -> None:
    cfg = TIER_CONFIG[tier]
    st.markdown(
        f'<div class="as-section-banner" style="'
        f'background:{cfg["banner_bg"]};'
        f'border-color:{cfg["banner_border"]};'
        f'color:{cfg["banner_color"]};">'
        f'<div class="as-section-icon">{cfg["icon"]}</div>'
        f'<div>'
        f'<div class="as-section-title">{cfg["label"]}</div>'
        f'<div class="as-section-sub">{subtitle}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _tier_card(rank: int, row: pd.Series, tier: int) -> str:
    cfg     = TIER_CONFIG[tier]
    name    = str(row.get("Team",   ""))
    record  = str(row.get("Record", ""))
    cls     = str(row.get("Class",  ""))
    region  = str(row.get("Region", ""))
    rating  = row.get("AllStateRating", np.nan)

    ti_s     = _safe(row.get("TI"),          "{:.4f}")
    net_s    = _safe(row.get("NetEff"),       "{:+.2f}")
    margin_s = _safe(row.get("MarginPG"),     "{:+.1f}")
    wpct_s   = pct_fmt(row.get("WinPct"))
    vstop_s  = pct_fmt(row.get("WinPctVsTop"))
    sos_s    = _safe(row.get("SOS_EWP"),      "{:.3f}")
    close_s  = pct_fmt(row.get("CloseWinPct"))
    rating_s = _safe(rating,                  "{:.1f}")
    bar_w    = f"{float(rating):.1f}%" if pd.notna(rating) else "50%"

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
        f'<div class="as-stat-cell">'
        f'<div class="as-stat-val" style="color:{cfg["val_color"]};">{val}</div>'
        f'<div class="as-stat-lbl">{lbl}</div>'
        f'</div>'
        for val, lbl in stats
    )

    return (
        f'<div class="as-card" style="background:{cfg["bg"]};border-color:{cfg["border"]};">'
        f'<div class="as-card-header">'
        f'<span class="as-card-rank" style="color:{cfg["rank_color"]};">#{rank}</span>'
        f'<span class="as-card-name">{name}</span>'
        f'<span class="as-card-record">{record}</span>'
        f'<span class="as-card-meta">Class {cls} {region}</span>'
        f'<span class="as-rating-pill" style="background:{cfg["pill_bg"]};color:{cfg["rank_color"]};">{rating_s}</span>'
        f'</div>'
        f'<div class="as-card-stats">{stats_html}</div>'
        f'<div class="as-card-bar-bg">'
        f'<div class="as-card-bar-fill" style="width:{bar_w};'
        f'background:linear-gradient(90deg,{cfg["bar_start"]},{cfg["bar_end"]});"></div>'
        f'</div>'
        f'</div>'
    )


def _as_df_html(df: pd.DataFrame, max_rows: int = 100) -> str:
    th_s = (
        "padding:0.28rem 0.6rem;font-size:0.65rem;text-transform:uppercase;"
        "letter-spacing:0.10em;color:#60a5fa;background:rgba(9,14,28,0.9);"
        "border-bottom:2px solid rgba(96,165,250,0.20);white-space:nowrap;"
        "font-weight:700;text-align:left;"
    )
    td_s = (
        "padding:0.30rem 0.6rem;font-size:0.80rem;color:#e2e8f0;"
        "border-bottom:1px solid rgba(255,255,255,0.04);white-space:nowrap;"
    )
    thead = "".join(f'<th style="{th_s}">{c}</th>' for c in df.columns)
    rows = ""
    for _, row in df.head(max_rows).iterrows():
        cells = "".join(f'<td style="{td_s}">{v}</td>' for v in row.values)
        rows += f'<tr>{cells}</tr>'
    return (
        f'<div class="as-table-wrap">'
        f'<table style="width:100%;border-collapse:collapse;min-width:600px;">'
        f'<thead><tr>{thead}</tr></thead><tbody>{rows}</tbody></table></div>'
    )


_inject_as_css()

# ── Filters ──────────────────────────────────────────────────────────────
st.write("")
fc1, fc2 = st.columns(2)
with fc1:
    sel_gender = st.selectbox("Gender", ["Boys", "Girls"], key="as_gender")
with fc2:
    sel_class = st.selectbox("Class", ["All", "A", "B", "C", "D", "S"], key="as_class")
sel_region = "All"
st.write("")

# ══════════════════════════════════════════════════════════════════════════
#  🔒 SUBSCRIBER GATE
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

# ── Data ─────────────────────────────────────────────────────────────────
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

class_label = "All Classes" if sel_class == "All" else f"Class {sel_class}"

# ── Live season notice ───────────────────────────────────────────────────
st.markdown(
    '<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.30);'
    'border-left:4px solid #f59e0b;border-radius:10px;padding:12px 18px;margin:0 0 18px;'
    'display:flex;align-items:flex-start;gap:12px;">'
    '<div style="font-size:1.2rem;flex-shrink:0;margin-top:1px;">📡</div>'
    '<div>'
    '<div style="font-size:0.80rem;font-weight:800;color:#fbbf24;letter-spacing:0.04em;margin-bottom:3px;">'
    'LIVE RANKINGS — UPDATES THROUGHOUT THE SEASON'
    '</div>'
    '<div style="font-size:0.78rem;color:#fde68a;line-height:1.6;">'
    'These selections are a <strong>moving target</strong> and recalculate automatically as new games are played. '
    'A team ranked First Team today could move up, down, or off the list tomorrow. '
    'Final All-State selections are locked at the <strong>end of the regular season</strong> — '
    'playoffs, scrimmages, and exhibitions are not counted.'
    '</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Tabs ─────────────────────────────────────────────────────────────────
tab_teams, tab_method, tab_full = st.tabs([
    "All-State Teams",
    "Methodology",
    "Full Rankings",
])

# ════════════════════════════════════════════════════════════════════════
# TAB 1 — ALL-STATE TEAMS
# ════════════════════════════════════════════════════════════════════════
with tab_teams:
    first_team  = view.iloc[0:per_tier]
    second_team = view.iloc[per_tier:per_tier*2]
    third_team  = view.iloc[per_tier*2:per_tier*3]

    # ── First Team ───────────────────────────────────────────────────────
    _section_banner(1, f"The {per_tier} highest-rated teams — {sel_gender} {class_label} (Statewide)")
    col1, col2 = st.columns(2)
    for i, (_, row) in enumerate(first_team.iterrows()):
        with (col1 if i % 2 == 0 else col2):
            st.markdown(_tier_card(i + 1, row, tier=1), unsafe_allow_html=True)

    # ── Second Team ──────────────────────────────────────────────────────
    if not second_team.empty:
        st.write("")
        _section_banner(2, "Honorable mentions that narrowly missed the first team.")
        col1, col2 = st.columns(2)
        for i, (_, row) in enumerate(second_team.iterrows()):
            with (col1 if i % 2 == 0 else col2):
                st.markdown(_tier_card(per_tier + i + 1, row, tier=2), unsafe_allow_html=True)

    # ── Third Team ───────────────────────────────────────────────────────
    if not third_team.empty:
        st.write("")
        _section_banner(3, "Strong seasons that deserve recognition.")
        col1, col2 = st.columns(2)
        for i, (_, row) in enumerate(third_team.iterrows()):
            with (col1 if i % 2 == 0 else col2):
                st.markdown(_tier_card(per_tier*2 + i + 1, row, tier=3), unsafe_allow_html=True)

    # ── Notable Snubs ─────────────────────────────────────────────────────
    snubs = view.iloc[per_tier*3:per_tier*3+4]
    if not snubs.empty:
        st.write("")
        st.markdown(
            '<div style="display:inline-flex;align-items:center;gap:8px;padding:6px 16px;'
            'border-radius:999px;border:1px solid rgba(148,163,184,0.25);'
            'background:rgba(148,163,184,0.05);font-size:0.73rem;font-weight:700;'
            'letter-spacing:0.10em;text-transform:uppercase;color:#94a3b8;margin:16px 0 10px;">'
            '💬 Notable Snubs</div>',
            unsafe_allow_html=True,
        )
        st.caption("Just outside the third team — the teams that will spark the most debate.")

        col1, col2 = st.columns(2)
        for i, (_, row) in enumerate(snubs.iterrows()):
            rank     = per_tier * 3 + i + 1
            name     = str(row.get("Team",   ""))
            record   = str(row.get("Record", ""))
            cls      = str(row.get("Class",  ""))
            region   = str(row.get("Region", ""))
            rating_s = _safe(row.get("AllStateRating"), "{:.1f}")
            html = (
                f'<div class="as-snub-row">'
                f'<span class="as-snub-rank">#{rank}</span>'
                f'<span class="as-snub-name">{name}</span>'
                f'<span class="as-snub-record">{record}</span>'
                f'<span class="as-snub-meta">Class {cls} {region}</span>'
                f'<span class="as-snub-rating">{rating_s}</span>'
                f'</div>'
            )
            with (col1 if i % 2 == 0 else col2):
                st.markdown(html, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════
# TAB 2 — METHODOLOGY
# ════════════════════════════════════════════════════════════════════════
with tab_method:
    st.markdown(
        '<div style="display:inline-flex;align-items:center;gap:8px;padding:6px 16px;'
        'border-radius:999px;border:1px solid rgba(96,165,250,0.35);'
        'background:rgba(96,165,250,0.07);font-size:0.73rem;font-weight:700;'
        'letter-spacing:0.10em;text-transform:uppercase;color:#93c5fd;margin:8px 0 14px;">'
        '📐 How the All-State Score Works</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    col_explain, col_weights = st.columns([0.55, 0.45], gap="large")

    with col_explain:
        available = [c for c in TEAM_WEIGHT_COLS if c in view.columns and view[c].notna().any()]
        missing   = [c for c in TEAM_WEIGHT_COLS if c not in available]

        st.markdown(
            '<div style="background:radial-gradient(circle at top left,#0f1e38,#080f1e);'
            'border:1px solid rgba(96,165,250,0.15);border-radius:12px;padding:16px 18px;margin-bottom:12px;">'
            '<div style="font-size:0.84rem;color:#bfdbfe;line-height:1.65;">'
            'The <strong style="color:#93c5fd;">Analytics207 All-State Score</strong> is a composite ranking built from '
            '150+ metrics collected throughout the season. No human votes. No politics. Just the numbers.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        steps = [
            ("<strong>Eligibility</strong> — Teams must have played at least 10 games to qualify."),
            ("<strong>Z-Score Normalization</strong> — Every metric is converted to a z-score within the filtered group so teams are judged relative to peers."),
            ("<strong>Weighted Composite</strong> — Z-scores are weighted and summed into a single All-State Score."),
            ("<strong>Penalty Deductions</strong> — Bad losses subtract from the score."),
            ("<strong>Statewide Pool</strong> — Rankings always use the full state pool for each class. North/South splits are excluded to prevent small-pool inflation."),
        ]
        steps_html = "".join(
            f'<div class="as-method-step">'
            f'<div class="as-method-num">{i+1}</div>'
            f'<div class="as-method-content">{s}</div>'
            f'</div>'
            for i, s in enumerate(steps)
        )
        st.markdown(steps_html, unsafe_allow_html=True)

        if missing:
            st.info(
                f"**{len(missing)} metric(s) skipped** (not available in current data): "
                + ", ".join(f"`{m}`" for m in missing)
            )

    with col_weights:
        st.markdown(
            '<div style="display:inline-flex;align-items:center;gap:8px;padding:6px 16px;'
            'border-radius:999px;border:1px solid rgba(96,165,250,0.35);'
            'background:rgba(96,165,250,0.07);font-size:0.73rem;font-weight:700;'
            'letter-spacing:0.10em;text-transform:uppercase;color:#93c5fd;margin:0 0 10px;">'
            '⚖️ Score Weights</div>',
            unsafe_allow_html=True,
        )

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

        st.markdown(_as_df_html(pd.DataFrame(weight_data)), unsafe_allow_html=True)

        st.markdown(
            f'<div style="background:radial-gradient(circle at top left,#0f1e38,#080f1e);'
            f'border:1px solid rgba(96,165,250,0.15);border-radius:10px;padding:12px 16px;margin-top:4px;'
            f'display:flex;align-items:center;gap:12px;">'
            f'<div style="font-size:0.63rem;font-weight:700;letter-spacing:0.10em;text-transform:uppercase;color:#94a3b8;">Min Games Played</div>'
            f'<div style="font-size:1.4rem;font-weight:900;color:#60a5fa;">{MIN_GAMES}</div>'
            f'<div style="font-size:0.75rem;color:#94a3b8;">games required to qualify</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ════════════════════════════════════════════════════════════════════════
# TAB 3 — FULL RANKINGS
# ════════════════════════════════════════════════════════════════════════
with tab_full:
    st.markdown(
        '<div style="display:inline-flex;align-items:center;gap:8px;padding:6px 16px;'
        'border-radius:999px;border:1px solid rgba(96,165,250,0.35);'
        'background:rgba(96,165,250,0.07);font-size:0.73rem;font-weight:700;'
        'letter-spacing:0.10em;text-transform:uppercase;color:#93c5fd;margin:8px 0 6px;">'
        '📋 Complete Rankings</div>',
        unsafe_allow_html=True,
    )
    st.caption("Every eligible team ranked by All-State composite score. Score (0–100) normalized within filter.")
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

    st.markdown(_as_df_html(disp), unsafe_allow_html=True)

render_footer()
