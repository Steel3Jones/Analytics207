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
    page_title="📊 The Aftermath",
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
        f'<div style="font-size:0.72rem;font-weight:700;color:#38bdf8;text-transform:uppercase;'
        f'letter-spacing:0.1em;border-bottom:1px solid #1e293b;padding-bottom:6px;margin:28px 0 16px;">'
        f'{icon} {label}</div>',
        unsafe_allow_html=True
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
  background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#0f172a 100%);
  border:1px solid #334155;border-radius:16px;
  padding:28px 32px 22px;position:relative;overflow:hidden;
">
  <div style="position:absolute;right:24px;top:50%;transform:translateY(-50%);
              font-size:5rem;opacity:0.07;pointer-events:none;">🏀</div>
  <div style="font-size:0.78rem;color:#64748b;text-transform:uppercase;
              letter-spacing:0.1em;margin-bottom:6px;">
    {yday.strftime("%A, %B %d, %Y")} &nbsp;·&nbsp; {gender}
  </div>
  <div style="font-size:2.0rem;font-weight:900;color:#f8fafc;
              line-height:1.1;margin-bottom:8px;">{headline}</div>
  <div style="font-size:0.88rem;color:#94a3b8;">
    {detail_line}
  </div>
</div>
"""
    components.html(html, height=145, scrolling=False)


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

    c0, c1, c2, c3, c4, c5 = st.columns([1.2, 1, 1, 1, 1, 1])

    with c0:
        components.html(f"""{_BASE_CSS}
<div style="background:#0f172a;border:1px solid #334155;border-radius:12px;
            padding:20px 24px;text-align:center;">
  <div style="font-size:3.5rem;font-weight:900;line-height:1;
              margin-bottom:4px;color:{gcol};">{grade}</div>
  <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;
              letter-spacing:0.08em;">Model Grade</div>
  <div style="font-size:0.82rem;color:#94a3b8;margin-top:4px;">
    {n_correct}/{n} picks correct
  </div>
</div>
""", height=130, scrolling=False)

    def _pill(col, val, lbl, sub="", color="#f1f5f9"):
        with col:
            components.html(f"""{_BASE_CSS}
<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
            padding:16px 18px;text-align:center;">
  <div style="font-size:1.8rem;font-weight:800;color:{color};line-height:1;">{val}</div>
  <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;
              letter-spacing:0.07em;margin-top:4px;">{lbl}</div>
  <div style="font-size:0.74rem;color:#94a3b8;margin-top:2px;">{sub}</div>
</div>
""", height=100, scrolling=False)

    _pill(c1, f"{acc:.0%}",  "Pick Accuracy",    f"{n_correct} of {n}", gcol)
    _pill(c2, avg_s,         "Avg Miss (pts)",   med_s,                 "#94a3b8")
    _pill(c3, str(nailed),   "Nailed (≤3 pts)",  "tight calls",         "#4ade80")
    _pill(c4, str(blowout),  "Big Misses (≥15)", "whiffs",              "#f87171")
    _pill(c5, str(n_upsets), "Upsets",           "fav lost",            "#f59e0b")


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
def render_spread_performance(dfy: pd.DataFrame) -> None:
    if not is_subscribed():
        _render_lock_wall("Spread Performance")
        return

    if "AbsSpreadError" not in dfy.columns:
        st.caption("Spread error data not available.")
        return

    _section_header("🎯", "Spread Performance")

    def _build_spread_table(subset: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, row in subset.iterrows():
            mc      = row.get("ModelCorrect", np.nan)
            pred    = row.get("PredMargin", np.nan)
            act     = row.get("ActualMargin", np.nan)
            err     = row.get("AbsSpreadError", np.nan)
            correct = pd.notna(mc) and float(mc) == 1.0
            rows.append({
                "✓":       "✅" if correct else "❌",
                "Matchup": _matchup(row),
                "Final":   _final(row),
                "Pred":    round(float(pred), 1) if pd.notna(pred) else None,
                "Actual":  round(float(act),  1) if pd.notna(act)  else None,
                "Miss":    round(float(err),  1) if pd.notna(err)  else None,
            })
        return pd.DataFrame(rows)

    def _style_spread(df: pd.DataFrame, mode: str):
        def _miss_color(val):
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return "color: #64748b;"
            if val <= 3:  return "color: #4ade80; font-weight: bold;"
            if val <= 8:  return "color: #a3e635;"
            if val <= 15: return "color: #fb923c;"
            return "color: #f87171; font-weight: bold;"

        bg = "#052e16" if mode == "nail" else "#2d0b0b"
        return (
            df.style
            .applymap(_miss_color, subset=["Miss"])
            .set_properties(**{
                "background-color": bg,
                "color": "#f1f5f9",
                "text-align": "left",
            })
            .format({
                "Pred":   lambda v: f"{v:+.1f}" if v is not None else "—",
                "Actual": lambda v: f"{v:+.1f}" if v is not None else "—",
                "Miss":   lambda v: f"{v:.1f}"  if v is not None else "—",
            }, na_rep="—")
            .hide(axis="index")
        )

    col_nail, col_miss = st.columns(2)

    with col_nail:
        st.markdown("##### ✅ Closest Calls")
        best = dfy[dfy["AbsSpreadError"].notna()].sort_values("AbsSpreadError").head(5)
        tbl  = _build_spread_table(best)
        st.dataframe(_style_spread(tbl, "nail"), use_container_width=True, hide_index=True)

    with col_miss:
        st.markdown("##### 💥 Biggest Misses")
        worst = dfy[dfy["AbsSpreadError"].notna()].sort_values("AbsSpreadError", ascending=False).head(5)
        tbl   = _build_spread_table(worst)
        st.dataframe(_style_spread(tbl, "miss"), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════
#  FULL GAME LOG
# ══════════════════════════════════════════════════════════════════════════
def render_full_game_log(dfy: pd.DataFrame) -> None:
    if not is_subscribed():
        _render_lock_wall("Full Game Log")
        return

    _section_header("📋", "Full Game Log")

    df = dfy.copy()
    if "AbsSpreadError" in df.columns:
        df = df.sort_values("AbsSpreadError", ascending=True)

    rows = []
    for _, row in df.iterrows():
        mc     = row.get("ModelCorrect", np.nan)
        err    = row.get("AbsSpreadError", np.nan)
        pred   = row.get("PredMargin", np.nan)
        act    = row.get("ActualMargin", np.nan)
        fp     = row.get("FavProb", np.nan)
        ct, _  = _card_type(row)
        correct = pd.notna(mc) and float(mc) == 1.0

        rows.append({
            "✓":        "✅" if correct else "❌",
            "Matchup":  _matchup(row),
            "Final":    _final(row),
            "Winner":   row.get("Winner", "—"),
            "Favorite": row.get("Favorite", "—"),
            "Pred":     round(float(pred), 1) if pd.notna(pred) else None,
            "Actual":   round(float(act),  1) if pd.notna(act)  else None,
            "Miss":     round(float(err),  1) if pd.notna(err)  else None,
            "Fav%":     round(float(fp) * 100) if pd.notna(fp)  else None,
            "Tag":      {"upset":"⚠️ Upset","nail":"🎯 Nailed","miss":"💥 Miss","normal":"—"}[ct],
        })

    tbl = pd.DataFrame(rows)

    def _row_bg(row):
        tag = row["Tag"]
        if "Upset"  in str(tag): bg = "#2d1f00"
        elif "Nail" in str(tag): bg = "#052e16"
        elif "Miss" in str(tag): bg = "#2d0b0b"
        else:                    bg = "#1e293b"
        return [f"background-color: {bg}; color: #f1f5f9;"] * len(row)

    def _miss_color(val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "color: #64748b;"
        if val <= 3:  return "color: #4ade80; font-weight: bold;"
        if val <= 8:  return "color: #a3e635;"
        if val <= 15: return "color: #fb923c;"
        return "color: #f87171; font-weight: bold;"

    def _fav_color(val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "color: #64748b;"
        if val >= 80: return "color: #3b82f6; font-weight: bold;"
        if val >= 65: return "color: #94a3b8;"
        return "color: #f59e0b; font-weight: bold;"

    def _tag_color(val):
        if "Upset"  in str(val): return "color: #f59e0b; font-weight: bold;"
        if "Nailed" in str(val): return "color: #4ade80; font-weight: bold;"
        if "Miss"   in str(val): return "color: #f87171; font-weight: bold;"
        return "color: #64748b;"

    styled = (
        tbl.style
        .apply(_row_bg, axis=1)
        .applymap(_miss_color, subset=["Miss"])
        .applymap(_fav_color,  subset=["Fav%"])
        .applymap(_tag_color,  subset=["Tag"])
        .format({
            "Pred":   lambda v: f"{v:+.1f}" if v is not None else "—",
            "Actual": lambda v: f"{v:+.1f}" if v is not None else "—",
            "Miss":   lambda v: f"{v:.1f}"  if v is not None else "—",
            "Fav%":   lambda v: f"{v:.0f}%" if v is not None else "—",
        }, na_rep="—")
        .set_properties(**{"text-align": "left"})
        .hide(axis="index")
    )

    st.dataframe(styled, use_container_width=True, height=min(600, 38 + len(tbl) * 35))


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


def render_tonight(df_day: pd.DataFrame, day: dt.date, gender: str) -> None:
    _section_header("🔮", "Tonight's Card")
    st.caption(f"{day.strftime('%A, %B %d')} · {gender} · {len(df_day)} games on the slate")

    if df_day.empty:
        st.info("No games on the card tonight for these filters.")
        return

    if not is_subscribed():
        _render_lock_wall("Tonight's Card")
        return

    tagged = tag_games(df_day)
    order  = {"Game of the Night":0,"Upset Watch":1,"Lock Zone":2,"Featured":3}
    tagged["_ord"] = tagged["Tag"].map(order).fillna(9)
    tagged = tagged.sort_values(["_ord", "_Closeness"]).head(8)

    for _, row in tagged.iterrows():
        tag   = row.get("Tag", "Featured")
        fp    = row.get("FavProb", np.nan)
        pm    = row.get("PredMargin", np.nan)
        total = row.get("PredTotalPoints", np.nan)
        fav   = row.get("Favorite", "—")
        fp_s  = f"{fp*100:.0f}% win prob" if pd.notna(fp)    else ""
        pm_s  = f"Line: {pm:+.1f}"         if pd.notna(pm)    else ""
        tot_s = f"O/U {total:.0f}"         if pd.notna(total) else ""
        tcol  = TAG_COLOR.get(tag,  "#64748b")
        tbord = TAG_BORDER.get(tag, "#334155")
        emoj  = TAG_EMOJI.get(tag,  "⭐")

        components.html(f"""{_BASE_CSS}
<div style="background:#0f172a;border:1px solid #1e3a5f;border-radius:12px;
            padding:14px 18px;margin-bottom:8px;border-left:4px solid {tbord};">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
              flex-wrap:wrap;gap:8px;">
    <div style="flex:1;min-width:0;">
      <div style="font-size:0.64rem;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.06em;color:{tcol};margin-bottom:3px;">
        {emoj} {tag}
      </div>
      <div style="font-size:0.95rem;font-weight:700;color:#f1f5f9;">
        {_matchup(row)}
      </div>
      <div style="font-size:0.82rem;color:#94a3b8;margin-top:2px;">
        {pm_s} &nbsp;·&nbsp; {fp_s} &nbsp;·&nbsp; {tot_s}
      </div>
    </div>
    <div style="text-align:right;flex-shrink:0;">
      <div style="font-size:0.78rem;color:#64748b;">Fav</div>
      <div style="font-size:0.95rem;font-weight:700;color:#f1f5f9;">{fav}</div>
    </div>
  </div>
</div>
""", height=95, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
def main() -> None:
    apply_global_layout_tweaks()

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

    available_dates = sorted(pd.Series(df_games["Date"].dropna().unique()).tolist())
    default_date    = available_dates[-1] if available_dates else dt.date.today()

    c1, c2, c3, c4 = st.columns([1.1, 1.0, 0.8, 0.9])
    with c1:
        day = st.date_input(
            "Night", value=default_date,
            min_value=min(available_dates) if available_dates else None,
            max_value=max(available_dates) if available_dates else None,
        )
    with c2:
        gender = st.selectbox("Gender", ["Boys", "Girls"], index=0, key="aftermath_gender")
    with c3:
        cls = st.selectbox("Class", ["All","A","B","C","D","S"], index=0, key="aftermath_class")
    with c4:
        region = st.selectbox("Region", ["All","North","South"], index=0, key="aftermath_region")

    yday = day - dt.timedelta(days=1)
    dfy  = df_games[
        (df_games["Date"] == yday) &
        (df_games["Gender"] == gender) &
        (df_games["Played"] == True)
    ].copy()
    if cls    != "All" and "HomeClass"  in dfy.columns:
        dfy = dfy[dfy["HomeClass"] == cls]
    if region != "All" and "HomeRegion" in dfy.columns:
        dfy = dfy[dfy["HomeRegion"] == region]

    df_day = df_games[
        (df_games["Date"] == day) &
        (df_games["Gender"] == gender) &
        (df_games["Played"] == False)
    ].copy()
    if cls    != "All" and "HomeClass"  in df_day.columns:
        df_day = df_day[df_day["HomeClass"] == cls]
    if region != "All" and "HomeRegion" in df_day.columns:
        df_day = df_day[df_day["HomeRegion"] == region]

    st.markdown("---")

    if dfy.empty:
        st.info(f"No completed games found for {yday.strftime('%b %d')} with these filters.")
    else:
        render_night_banner(dfy, yday, gender)
        render_report_card(dfy)
        render_upset_spotlight(dfy)
        render_spread_performance(dfy)
        with st.expander(f"📋 Full Game Log — {len(dfy)} games", expanded=False):
            render_full_game_log(dfy)

    render_tonight(df_day, day, gender)
    render_footer()


if __name__ == "__main__":
    main()
