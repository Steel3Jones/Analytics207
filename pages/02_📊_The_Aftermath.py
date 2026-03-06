from __future__ import annotations


from pathlib import Path
import os
import datetime as dt


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
    page_title="📊 The Aftermath - The Day After",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)


SHOW_LOCKS = True


# ══════════════════════════════════════════════════════════════════════════
#  PATHS
# ══════════════════════════════════════════════════════════════════════════
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
ANALYTICS_PATH = DATA_DIR / "core" / "games_analytics_v50.parquet"
PREDS_PATH     = DATA_DIR / "predictions" / "games_predictions_current.parquet"


# ══════════════════════════════════════════════════════════════════════════
#  SHARED IFRAME STYLES
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


def _inject_aftermath_css() -> None:
    st.markdown("""
<style>
/* ── SECTION PILL HEADS ── */
.am-section-head {
    display: inline-block;
    background: rgba(96,165,250,0.10);
    border: 1px solid rgba(96,165,250,0.22);
    border-radius: 999px;
    padding: 0.20rem 0.85rem;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #93c5fd;
    margin-bottom: 0.6rem;
    margin-top: 1.4rem;
}

/* ── FILTER ROW ── */
.am-filter-bar {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.18);
    border-radius: 14px;
    padding: 0.9rem 1.1rem 0.6rem;
    margin-bottom: 0.8rem;
}

/* ── REPORT CARD ── */
.am-report-grid {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 0.5rem;
}
.am-grade-card {
    background: radial-gradient(circle at top left, #142040, #060c1a);
    border: 1px solid rgba(96,165,250,0.22);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    text-align: center;
    min-width: 120px;
    flex-shrink: 0;
}
.am-grade-val {
    font-size: 3.2rem;
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.02em;
}
.am-stat-card {
    flex: 1;
    min-width: 100px;
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.16);
    border-radius: 12px;
    padding: 0.8rem 0.9rem;
    text-align: center;
}
.am-stat-val {
    font-size: 1.65rem;
    font-weight: 800;
    line-height: 1.1;
}
.am-stat-lbl {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #64748b;
    margin-top: 3px;
}
.am-stat-sub {
    font-size: 0.70rem;
    color: #475569;
    margin-top: 2px;
}

/* ── GAME CARDS (Tonight's Card / upset) ── */
.am-game-card {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.16);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
}
.am-game-card-left { flex: 1; min-width: 0; }
.am-game-tag {
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 3px;
}
.am-game-matchup {
    font-size: 0.95rem;
    font-weight: 700;
    color: #f1f5f9;
}
.am-game-meta {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 2px;
}
.am-game-right {
    text-align: right;
    flex-shrink: 0;
}
.am-game-score {
    font-size: 1.4rem;
    font-weight: 900;
}
.am-game-winner {
    font-size: 0.72rem;
    color: #64748b;
    margin-top: 2px;
}

/* ── SEASON OVER CARD ── */
.am-season-over {
    background: radial-gradient(circle at top left, #0a1f12, #060c1a);
    border: 1px solid rgba(34,197,94,0.25);
    border-radius: 14px;
    padding: 2rem 2rem;
    text-align: center;
    margin-top: 1rem;
}

/* ── NO GAMES ── */
.am-no-games {
    background: radial-gradient(circle at top left, #0f1e38, #080f1e);
    border: 1px solid rgba(96,165,250,0.14);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    color: #475569;
    font-size: 0.88rem;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  DATA
# ══════════════════════════════════════════════════════════════════════════
def _clean_gameids(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.strip()
               .str.replace(r"\.0$", "", regex=True)
               .str.replace(",", "", regex=True))


@st.cache_data
def load_games() -> pd.DataFrame:
    analytics = pd.read_parquet(ANALYTICS_PATH).copy()
    preds     = pd.read_parquet(PREDS_PATH).copy()

    analytics["GameID"] = _clean_gameids(analytics["GameID"])
    preds["GameID"]     = _clean_gameids(preds["GameID"])

    df = analytics.merge(preds, on="GameID", how="left", suffixes=("", "_pred"))

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].astype(str).str.strip().str.title()
        df = df[df["Gender"].isin(["Boys", "Girls"])].copy()
    if "Played" in df.columns:
        df["Played"] = df["Played"].fillna(False).astype(bool)

    for col in ["Home", "Away", "HomeClass", "AwayClass", "HomeRegion", "AwayRegion"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    for col in [
        "HomeScore", "AwayScore", "Margin", "AbsMargin",
        "HomeWinFlag", "AwayWinFlag", "HomeTI", "AwayTI", "HomePI", "AwayPI",
        "PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore",
        "PredTotalPoints", "PredSpreadAbs", "PredWinnerProb", "PredWinnerProbPct",
        "EloDiff", "StrengthGap", "ResultHomeWin",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["ActualMargin"] = df["Margin"]

    if {"ActualMargin", "PredMargin"}.issubset(df.columns):
        df["AbsSpreadError"] = (df["ActualMargin"] - df["PredMargin"]).abs()

    if "PredHomeWinProb" in df.columns:
        p = df["PredHomeWinProb"]
        df["FavProb"] = p.where(p >= 0.5, 1.0 - p)

    if {"ResultHomeWin", "PredHomeWinProb"}.issubset(df.columns):
        pred_home_wins = (df["PredHomeWinProb"] >= 0.5).astype(float)
        df["ModelCorrect"] = (pred_home_wins == df["ResultHomeWin"]).astype(float)
        df.loc[df["ResultHomeWin"].isna(), "ModelCorrect"] = np.nan

    if "PredMargin" in df.columns:
        df["FavoriteIsHome"] = (df["PredMargin"] > 0).astype(float)
        df.loc[df["PredMargin"].isna(), "FavoriteIsHome"] = np.nan

    df["Winner"] = np.where(
        df["ActualMargin"].isna(), "—",
        np.where(df["ActualMargin"] > 0, df["Home"],
        np.where(df["ActualMargin"] < 0, df["Away"], "Tie"))
    )
    df["Favorite"] = np.where(
        df["PredMargin"].isna(), "—",
        np.where(df["PredMargin"] > 0, df["Home"],
        np.where(df["PredMargin"] < 0, df["Away"], "Pick'em"))
    )

    return df.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════
def _matchup(row) -> str:
    return f"{row.get('Away', '')} @ {row.get('Home', '')}"


def _final(row) -> str:
    a = row.get("AwayScore")
    h = row.get("HomeScore")
    if pd.isna(a) or pd.isna(h):
        return "—"
    return f"{int(a)}–{int(h)}"


def _grade(acc: float) -> tuple[str, str]:
    if acc >= 0.85: return "A+", "#4ade80"
    if acc >= 0.78: return "A",  "#4ade80"
    if acc >= 0.72: return "B+", "#a3e635"
    if acc >= 0.65: return "B",  "#facc15"
    if acc >= 0.55: return "C",  "#fb923c"
    return "D", "#f87171"


def _card_type(row) -> tuple[str, str]:
    mc  = row.get("ModelCorrect", np.nan)
    err = row.get("AbsSpreadError", np.nan)
    if pd.notna(mc) and float(mc) == 0.0:
        return "upset",  "#f59e0b"
    if pd.notna(err) and err <= 3:
        return "nail",   "#22c55e"
    if pd.notna(err) and err >= 15:
        return "miss",   "#ef4444"
    return "normal", "#334155"


def _section_header(icon: str, label: str) -> None:
    st.markdown(
        f'<div class="am-section-head">{icon} {label}</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════
#  LOCK WALL — shown to non-subscribers in place of detailed sections
# ══════════════════════════════════════════════════════════════════════════
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
    Subscribe to unlock full model breakdowns, spread performance,
    upset analysis, and the complete game log.
  </div>
</div>
""", height=160, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════
#  NIGHT SUMMARY BANNER  (visible to all — scores are public)
# ══════════════════════════════════════════════════════════════════════════
def render_night_banner(dfy: pd.DataFrame, yday: dt.date, gender: str) -> None:
    n = len(dfy)
    sub = is_subscribed()

    if sub:
        n_correct = int(dfy["ModelCorrect"].fillna(0).sum())
        n_upsets  = int((dfy["ModelCorrect"].fillna(1) == 0).sum())
        acc       = n_correct / n if n > 0 else 0.0
        _, gcol   = _grade(acc)

        avg_miss_s = "—"
        if "AbsSpreadError" in dfy.columns and dfy["AbsSpreadError"].notna().any():
            avg_miss_s = f"{dfy['AbsSpreadError'].mean():.1f} pts"

        if n_upsets == 0:
            headline = f"The Model ran the table — {n_correct}/{n} correct picks"
        elif n_upsets >= 3:
            headline = f"Chaos night — {n_upsets} upsets rattled the model"
        else:
            headline = f"{n_correct}/{n} correct · {n_upsets} upset{'s' if n_upsets != 1 else ''} shook things up"

        detail_line = (
            f"{n} games played &nbsp;·&nbsp;"
            f"Model accuracy: <strong style=\"color:{gcol};\">{acc:.0%}</strong> &nbsp;·&nbsp;"
            f"Avg spread miss: <strong style=\"color:#f1f5f9;\">{avg_miss_s}</strong>"
        )
    else:
        headline = f"{n} games were played last night"
        detail_line = (
            f"{n} games played &nbsp;·&nbsp;"
            f"<span style=\"color:#fbbf24;\">🔒 Subscribe to see model accuracy &amp; spread analysis</span>"
        )

    html = f"""{_BASE_CSS}
<div style="
  background: radial-gradient(circle at top left, #142040, #060c1a);
  border: 1px solid rgba(96,165,250,0.25);
  border-radius: 16px;
  padding: 28px 32px 24px;
  position: relative;
  overflow: hidden;
">
  <div style="position:absolute;right:28px;top:50%;transform:translateY(-50%);
              font-size:6rem;opacity:0.06;pointer-events:none;user-select:none;">🏀</div>
  <div style="font-size:0.70rem;color:#475569;text-transform:uppercase;
              letter-spacing:0.13em;margin-bottom:8px;font-weight:600;">
    ⚡ The Aftermath &nbsp;·&nbsp; {yday.strftime("%A, %B %d, %Y")} &nbsp;·&nbsp; {gender}
  </div>
  <div style="font-size:1.85rem;font-weight:900;color:#f8fafc;
              line-height:1.15;margin-bottom:10px;letter-spacing:-0.01em;">{headline}</div>
  <div style="height:1px;background:rgba(96,165,250,0.12);margin-bottom:10px;"></div>
  <div style="font-size:0.85rem;color:#94a3b8;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
    {detail_line}
  </div>
</div>
"""
    components.html(html, height=155, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════
#  MODEL REPORT CARD
# ══════════════════════════════════════════════════════════════════════════
def render_report_card(dfy: pd.DataFrame) -> None:
    if not is_subscribed():
        _render_lock_wall("Model Report Card")
        return

    n           = len(dfy)
    n_correct   = int(dfy["ModelCorrect"].fillna(0).sum())
    n_upsets    = int((dfy["ModelCorrect"].fillna(1) == 0).sum())
    acc         = n_correct / n if n > 0 else 0.0
    grade, gcol = _grade(acc)

    avg_err = med_err = np.nan
    nailed  = blowout = 0
    if "AbsSpreadError" in dfy.columns:
        e = dfy["AbsSpreadError"]
        if e.notna().any():
            avg_err = float(e.mean())
            med_err = float(e.median())
            nailed  = int((e <= 3).sum())
            blowout = int((e >= 15).sum())

    avg_s = f"{avg_err:.1f}" if pd.notna(avg_err) else "—"
    med_s = f"median {med_err:.1f}" if pd.notna(med_err) else ""

    _section_header("🧠", "Model Report Card")

    def _stat_card(val, lbl, sub="", color="#60a5fa"):
        return (
            f'<div class="am-stat-card">'
            f'<div class="am-stat-val" style="color:{color};">{val}</div>'
            f'<div class="am-stat-lbl">{lbl}</div>'
            f'<div class="am-stat-sub">{sub}</div>'
            f'</div>'
        )

    stats_html = (
        f'<div class="am-stat-card" style="border-color:rgba(96,165,250,0.28);">'
        f'<div class="am-grade-val" style="color:{gcol};">{grade}</div>'
        f'<div class="am-stat-lbl">Model Grade</div>'
        f'<div class="am-stat-sub">{n_correct}/{n} correct</div>'
        f'</div>'
        + _stat_card(f"{acc:.0%}",  "Pick Accuracy",    f"{n_correct} of {n}", gcol)
        + _stat_card(avg_s,         "Avg Miss",         med_s,                 "#94a3b8")
        + _stat_card(str(nailed),   "Nailed ≤3 pts",    "tight calls",         "#4ade80")
        + _stat_card(str(blowout),  "Big Misses ≥15",   "whiffs",              "#f87171")
        + _stat_card(str(n_upsets), "Upsets",           "fav lost",            "#f59e0b")
    )
    st.markdown(f'<div class="am-report-grid">{stats_html}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  UPSET SPOTLIGHT
# ══════════════════════════════════════════════════════════════════════════
def render_upset_spotlight(dfy: pd.DataFrame) -> None:
    if not is_subscribed():
        _render_lock_wall("Upset Spotlight")
        return

    upsets = dfy[
        (dfy["ModelCorrect"].fillna(1) == 0) &
        (pd.to_numeric(dfy["FavProb"], errors="coerce").fillna(0) >= 0.65)
    ].copy()

    _section_header("⚠️", "Upset Spotlight")

    if upsets.empty:
        st.markdown(
            '<div style="color:#475569;font-size:0.88rem;padding:12px 0;">'
            'No upsets last night — the favorites held serve.</div>',
            unsafe_allow_html=True
        )
        return

    upsets = upsets.sort_values("FavProb", ascending=False)
    top    = upsets.iloc[0]
    rest   = upsets.iloc[1:3]

    fav_pct  = float(top["FavProb"]) * 100 if pd.notna(top.get("FavProb")) else None
    fav_s    = f"{fav_pct:.0f}%" if fav_pct else ""
    winner   = top.get("Winner", "—")
    favorite = top.get("Favorite", "—")
    loser    = favorite
    dog_lbl  = f"{loser} was the {fav_s} favorite — {winner} had other ideas" if fav_s else ""

    components.html(f"""{_BASE_CSS}
<div style="background:linear-gradient(135deg,#1c1400,#1e293b);
            border:1px solid #854d0e;border-radius:12px;
            padding:20px 24px;margin-bottom:10px;">
  <div style="font-size:0.68rem;color:#fbbf24;text-transform:uppercase;
              letter-spacing:0.1em;margin-bottom:6px;">🔥 Biggest Upset of the Night</div>
  <div style="font-size:1.15rem;font-weight:800;color:#fef3c7;
              margin-bottom:4px;">{_matchup(top)}</div>
  <div style="font-size:1.6rem;font-weight:900;color:#f59e0b;">{_final(top)}</div>
  <div style="font-size:0.78rem;color:#92400e;margin-top:6px;">{dog_lbl}</div>
</div>
""", height=150, scrolling=False)

    if not rest.empty:
        cols = st.columns(len(rest))
        for col, (_, row) in zip(cols, rest.iterrows()):
            fp2  = float(row["FavProb"]) * 100 if pd.notna(row.get("FavProb")) else None
            fp_s = f"Fav was {fp2:.0f}%" if fp2 else ""
            with col:
                components.html(f"""{_BASE_CSS}
<div style="background:#1e293b;border:1px solid #334155;border-radius:12px;
            padding:16px 18px;border-left:4px solid #f59e0b;">
  <div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.08em;margin-bottom:6px;color:#f59e0b;">⚠️ Upset</div>
  <div style="font-size:1.0rem;font-weight:700;color:#f1f5f9;
              margin-bottom:4px;">{_matchup(row)}</div>
  <div style="font-size:1.3rem;font-weight:900;color:#4ade80;">{_final(row)}</div>
  <div style="font-size:0.76rem;color:#64748b;margin-top:4px;">
    {fp_s} · Winner: <strong>{row.get('Winner', '—')}</strong>
  </div>
</div>
""", height=130, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════
#  SPREAD PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════
def _miss_color_css(val) -> str:
    try:
        v = float(val)
        if v <= 3:  return "#4ade80"
        if v <= 8:  return "#a3e635"
        if v <= 15: return "#fb923c"
        return "#f87171"
    except Exception:
        return "#64748b"


def _spread_table_html(subset: pd.DataFrame, accent: str, title: str, title_icon: str) -> str:
    rows_html = ""
    for _, row in subset.iterrows():
        mc      = row.get("ModelCorrect", np.nan)
        pred    = row.get("PredMargin", np.nan)
        act     = row.get("ActualMargin", np.nan)
        err     = row.get("AbsSpreadError", np.nan)
        correct = pd.notna(mc) and float(mc) == 1.0
        mc_html  = '<span style="color:#4ade80;font-weight:700;">✓</span>' if correct else '<span style="color:#f87171;">✗</span>'
        miss_col = _miss_color_css(err)
        miss_s   = f'{float(err):.1f}' if pd.notna(err)  else "—"
        pred_s   = f'{float(pred):+.1f}' if pd.notna(pred) else "—"
        act_s    = f'{float(act):+.1f}'  if pd.notna(act)  else "—"
        rows_html += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<td style="padding:0.30rem 0.4rem;text-align:center;width:28px;">{mc_html}</td>'
            f'<td style="padding:0.30rem 0.5rem;text-align:left;color:#e2e8f0;font-size:0.82rem;">{_matchup(row)}</td>'
            f'<td style="padding:0.30rem 0.5rem;color:#94a3b8;font-size:0.80rem;white-space:nowrap;">{_final(row)}</td>'
            f'<td style="padding:0.30rem 0.5rem;text-align:center;color:#93c5fd;font-size:0.80rem;">{pred_s}</td>'
            f'<td style="padding:0.30rem 0.5rem;text-align:center;color:#cbd5e1;font-size:0.80rem;">{act_s}</td>'
            f'<td style="padding:0.30rem 0.5rem;text-align:center;color:{miss_col};font-weight:700;font-size:0.82rem;">{miss_s}</td>'
            f'</tr>'
        )
    th_style = f'padding:0.26rem 0.5rem;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.10em;color:{accent};background:rgba(9,14,28,0.9);border-bottom:2px solid {accent}55;'
    headers  = [("", "center", "28px"), ("Matchup", "left", "auto"), ("Final", "left", "auto"),
                ("Pred", "center", "52px"), ("Actual", "center", "52px"), ("Miss", "center", "48px")]
    thead    = "".join(f'<th style="{th_style}text-align:{a};width:{w};">{h}</th>' for h, a, w in headers)
    return (
        f'<div style="background:radial-gradient(circle at top left,#0f1e38,#080f1e);'
        f'border:1px solid rgba(96,165,250,0.18);border-radius:12px;'
        f'padding:0.85rem 0.85rem 0.5rem;overflow:hidden;">'
        f'<div style="font-size:0.75rem;font-weight:700;color:{accent};margin-bottom:0.55rem;">'
        f'{title_icon} {title}</div>'
        f'<table style="width:100%;border-collapse:collapse;table-layout:auto;">'
        f'<thead><tr>{thead}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )


def render_spread_performance(dfy: pd.DataFrame) -> None:
    if not is_subscribed():
        _render_lock_wall("Spread Performance")
        return

    if "AbsSpreadError" not in dfy.columns:
        st.caption("Spread error data not available.")
        return

    _section_header("🎯", "Spread Performance")

    errs  = dfy[dfy["AbsSpreadError"].notna()]
    best  = errs.sort_values("AbsSpreadError").head(5)
    worst = errs.sort_values("AbsSpreadError", ascending=False).head(5)

    col_nail, col_miss = st.columns(2)
    with col_nail:
        st.markdown(_spread_table_html(best,  "#4ade80", "Closest Calls",  "✅"), unsafe_allow_html=True)
    with col_miss:
        st.markdown(_spread_table_html(worst, "#f87171", "Biggest Misses", "💥"), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  FULL GAME LOG
# ══════════════════════════════════════════════════════════════════════════
def render_full_game_log(dfy: pd.DataFrame) -> None:
    if not is_subscribed():
        _render_lock_wall("Full Game Log")
        return

    df = dfy.copy()
    if "AbsSpreadError" in df.columns:
        df = df.sort_values("AbsSpreadError", ascending=True)

    TAG_LABELS = {"upset": "⚠️ Upset", "nail": "🎯 Nailed", "miss": "💥 Miss", "normal": "—"}
    TAG_COLS   = {"upset": "#f59e0b",  "nail": "#4ade80",   "miss": "#f87171",  "normal": "#475569"}
    ROW_BG     = {"upset": "rgba(245,158,11,0.05)", "nail": "rgba(34,197,94,0.04)",
                  "miss":  "rgba(239,68,68,0.05)",  "normal": "transparent"}

    headers = [("", "center", "28px"), ("Matchup", "left", "auto"), ("Final", "center", "72px"),
               ("Winner", "left", "auto"), ("Pred", "center", "52px"), ("Actual", "center", "52px"),
               ("Miss", "center", "48px"), ("Fav%", "center", "52px"), ("Tag", "center", "80px")]
    th_base = "padding:0.26rem 0.5rem;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.10em;color:#f59e0b;background:rgba(9,14,28,0.9);border-bottom:2px solid rgba(245,158,11,0.35);"
    thead   = "".join(f'<th style="{th_base}text-align:{a};width:{w};">{h}</th>' for h, a, w in headers)

    rows_html = ""
    for _, row in df.iterrows():
        mc      = row.get("ModelCorrect", np.nan)
        err     = row.get("AbsSpreadError", np.nan)
        pred    = row.get("PredMargin", np.nan)
        act     = row.get("ActualMargin", np.nan)
        fp      = row.get("FavProb", np.nan)
        ct, _   = _card_type(row)
        correct = pd.notna(mc) and float(mc) == 1.0

        mc_html  = '<span style="color:#4ade80;font-weight:700;">✓</span>' if correct else '<span style="color:#f87171;">✗</span>'
        miss_s   = f'{float(err):.1f}'  if pd.notna(err)  else "—"
        pred_s   = f'{float(pred):+.1f}' if pd.notna(pred) else "—"
        act_s    = f'{float(act):+.1f}'  if pd.notna(act)  else "—"
        fp_s     = f'{float(fp)*100:.0f}%' if pd.notna(fp) else "—"
        fp_col   = "#3b82f6" if pd.notna(fp) and float(fp)*100 >= 80 else ("#f59e0b" if pd.notna(fp) and float(fp)*100 < 65 else "#94a3b8")
        miss_col = _miss_color_css(err)
        tag_lbl  = TAG_LABELS.get(ct, "—")
        tag_col  = TAG_COLS.get(ct, "#475569")
        row_bg   = ROW_BG.get(ct, "transparent")
        winner   = str(row.get("Winner", "—"))

        rows_html += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);background:{row_bg};">'
            f'<td style="padding:0.28rem 0.4rem;text-align:center;">{mc_html}</td>'
            f'<td style="padding:0.28rem 0.5rem;color:#e2e8f0;font-size:0.82rem;">{_matchup(row)}</td>'
            f'<td style="padding:0.28rem 0.5rem;color:#94a3b8;font-size:0.80rem;text-align:center;">{_final(row)}</td>'
            f'<td style="padding:0.28rem 0.5rem;color:#f1f5f9;font-size:0.80rem;font-weight:600;">{winner}</td>'
            f'<td style="padding:0.28rem 0.5rem;text-align:center;color:#93c5fd;font-size:0.80rem;">{pred_s}</td>'
            f'<td style="padding:0.28rem 0.5rem;text-align:center;color:#cbd5e1;font-size:0.80rem;">{act_s}</td>'
            f'<td style="padding:0.28rem 0.5rem;text-align:center;color:{miss_col};font-weight:700;font-size:0.82rem;">{miss_s}</td>'
            f'<td style="padding:0.28rem 0.5rem;text-align:center;color:{fp_col};font-size:0.80rem;">{fp_s}</td>'
            f'<td style="padding:0.28rem 0.5rem;text-align:center;color:{tag_col};font-size:0.72rem;font-weight:700;">{tag_lbl}</td>'
            f'</tr>'
        )

    html = (
        f'<div style="background:radial-gradient(circle at top left,#0f1e38,#080f1e);'
        f'border:1px solid rgba(96,165,250,0.18);border-radius:12px;'
        f'padding:0.85rem 0.85rem 0.5rem;overflow:auto;">'
        f'<table style="width:100%;border-collapse:collapse;min-width:640px;">'
        f'<thead><tr>{thead}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  TONIGHT'S CARD
# ══════════════════════════════════════════════════════════════════════════
TAG_EMOJI  = {"Game of the Night":"🟣","Upset Watch":"⚠️","Lock Zone":"🔒","Featured":"⭐"}
TAG_COLOR  = {"Game of the Night":"#a855f7","Upset Watch":"#f59e0b",
              "Lock Zone":"#3b82f6","Featured":"#64748b"}
TAG_BORDER = {"Game of the Night":"#a855f7","Upset Watch":"#f59e0b",
              "Lock Zone":"#3b82f6","Featured":"#334155"}


def tag_games(df: pd.DataFrame) -> pd.DataFrame:
    d  = df.copy()
    fp = pd.to_numeric(d.get("FavProb",    np.nan), errors="coerce")
    pm = pd.to_numeric(d.get("PredMargin", np.nan), errors="coerce")
    d["_Closeness"]     = (fp - 0.50).abs()
    d["_AbsPredMargin"] = pm.abs()
    d["_DogProb"]       = 1.0 - fp
    d["Tag"]            = "Featured"
    if d["_Closeness"].notna().any():
        d.loc[d["_Closeness"].idxmin(), "Tag"] = "Game of the Night"
    d.loc[d["_DogProb"].between(0.25, 0.40) & (d["_AbsPredMargin"] <= 12), "Tag"] = "Upset Watch"
    d.loc[fp >= 0.80, "Tag"] = "Lock Zone"
    return d


def render_season_complete() -> None:
    _section_header("🏆", "Season Complete")
    st.markdown(
        '<div class="am-season-over">'
        '<div style="font-size:2.5rem;margin-bottom:10px;">🏆</div>'
        '<div style="font-size:1.2rem;font-weight:800;color:#4ade80;margin-bottom:6px;">The Season Is Over</div>'
        '<div style="font-size:0.88rem;color:#64748b;">The regular season has wrapped up. '
        'Use the date picker above to look back at any night from the season.</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_tonight(df_day: pd.DataFrame, day: dt.date, gender: str) -> None:
    _section_header("🔮", "Tonight's Card")
    st.caption(f"{day.strftime('%A, %B %d')} · {gender} · {len(df_day)} games on the slate")

    if df_day.empty:
        st.markdown('<div class="am-no-games">No games on the card for this date and filters.</div>', unsafe_allow_html=True)
        return

    if not is_subscribed():
        _render_lock_wall("Tonight's Card")
        return

    tagged = tag_games(df_day)
    order  = {"Game of the Night":0,"Upset Watch":1,"Lock Zone":2,"Featured":3}
    tagged["_ord"] = tagged["Tag"].map(order).fillna(9)
    tagged = tagged.sort_values(["_ord", "_Closeness"]).head(8)

    cards_html = ""
    for _, row in tagged.iterrows():
        tag   = row.get("Tag", "Featured")
        fp    = row.get("FavProb", np.nan)
        pm    = row.get("PredMargin", np.nan)
        total = row.get("PredTotalPoints", np.nan)
        fav   = row.get("Favorite", "—")
        fp_s  = f"{fp*100:.0f}% win prob" if pd.notna(fp)    else ""
        pm_s  = f"Line: {pm:+.1f}"        if pd.notna(pm)    else ""
        tot_s = f"O/U {total:.0f}"        if pd.notna(total) else ""
        meta  = " &nbsp;·&nbsp; ".join(x for x in [pm_s, fp_s, tot_s] if x)
        tcol  = TAG_COLOR.get(tag,  "#64748b")
        tbord = TAG_BORDER.get(tag, "rgba(96,165,250,0.18)")
        emoj  = TAG_EMOJI.get(tag,  "⭐")

        cards_html += (
            f'<div class="am-game-card" style="border-left:4px solid {tbord};">'
            f'<div class="am-game-card-left">'
            f'<div class="am-game-tag" style="color:{tcol};">{emoj} {tag}</div>'
            f'<div class="am-game-matchup">{_matchup(row)}</div>'
            f'<div class="am-game-meta">{meta}</div>'
            f'</div>'
            f'<div class="am-game-right">'
            f'<div style="font-size:0.68rem;color:#475569;">Favorite</div>'
            f'<div style="font-size:0.92rem;font-weight:700;color:#f1f5f9;">{fav}</div>'
            f'</div>'
            f'</div>'
        )
    st.markdown(cards_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
def main() -> None:
    apply_global_layout_tweaks()
    _inject_aftermath_css()

    user = login_gate(required=False)
    logout_button()

    render_logo()
    render_page_header(
        title="⚡ The Aftermath",
        definition="Aftermath (n.): Last night's wreckage — scores, upsets, and how the model held up.",
        subtitle="Pick a night. See everything. The model doesn't hide.",
    )

    if not ANALYTICS_PATH.exists():
        st.error(f"Analytics parquet not found: {ANALYTICS_PATH}")
        render_footer()
        return
    if not PREDS_PATH.exists():
        st.error(f"Predictions parquet not found: {PREDS_PATH}")
        render_footer()
        return

    df_games = load_games()
    if df_games.empty or "Date" not in df_games.columns:
        st.info("Aftermath data not available yet.")
        render_footer()
        return

    played_dates    = sorted(df_games[df_games["Played"] == True]["Date"].dropna().unique().tolist())
    available_dates = sorted(df_games["Date"].dropna().unique().tolist())
    last_played     = played_dates[-1] if played_dates else None
    season_over     = last_played is not None and dt.date.today() > last_played
    # Default to last played game date
    default_date = last_played if last_played else (max(available_dates) if available_dates else dt.date.today())

    c1, c2, c3, c4 = st.columns([1.1, 1.0, 0.8, 0.9])
    with c1:
        day = st.date_input(
            "Game Date", value=default_date,
            min_value=min(available_dates) if available_dates else None,
            max_value=max(available_dates) if available_dates else None,
        )
    with c2:
        gender = st.selectbox("Gender", ["Boys", "Girls"], index=0, key="aftermath_gender")
    with c3:
        cls = st.selectbox("Class", ["All","A","B","C","D","S"], index=0, key="aftermath_class")
    with c4:
        region = st.selectbox("Region", ["All","North","South"], index=0, key="aftermath_region")

    # Look up games on the selected date directly
    dfy = df_games[
        (df_games["Date"] == day) &
        (df_games["Gender"] == gender) &
        (df_games["Played"] == True)
    ].copy()
    if cls    != "All" and "HomeClass"  in dfy.columns:
        dfy = dfy[dfy["HomeClass"] == cls]
    if region != "All" and "HomeRegion" in dfy.columns:
        dfy = dfy[dfy["HomeRegion"] == region]
    display_date = day

    st.write("")

    if dfy.empty:
        st.markdown(
            f'<div class="am-no-games">No completed games found for {day.strftime("%b %d")} — try a different date.</div>',
            unsafe_allow_html=True,
        )
    else:
        render_night_banner(dfy, display_date, gender)
        render_report_card(dfy)
        render_upset_spotlight(dfy)
        render_spread_performance(dfy)
        with st.expander(f"📋 Full Game Log — {len(dfy)} games", expanded=False):
            render_full_game_log(dfy)

    # Tonight's Card — only show if season is still active
    if season_over:
        render_season_complete()
    else:
        next_day = day + dt.timedelta(days=1)
        df_day = df_games[
            (df_games["Date"] == next_day) &
            (df_games["Gender"] == gender) &
            (df_games["Played"] == False)
        ].copy()
        if cls    != "All" and "HomeClass"  in df_day.columns:
            df_day = df_day[df_day["HomeClass"] == cls]
        if region != "All" and "HomeRegion" in df_day.columns:
            df_day = df_day[df_day["HomeRegion"] == region]
        render_tonight(df_day, next_day, gender)

    render_footer()


if __name__ == "__main__":
    main()
