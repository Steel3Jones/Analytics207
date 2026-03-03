# pages/XX__Fan_vs_Model.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime, date
import os

import numpy as np
import pandas as pd
import streamlit as st

from layout import apply_global_layout_tweaks, render_logo, render_footer
from auth import login_gate, logout_button, get_supabase, is_logged_in
from sidebar_auth import render_sidebar_auth

render_sidebar_auth()

st.set_page_config(
    page_title="🤖 Fan vs. Model | Analytics207",
    page_icon="🤖",
    layout="wide",
)
apply_global_layout_tweaks()
login_gate(required=False)
logout_button()

_user = st.session_state.get("user")
_uid  = _user.id if _user else None

ROOT      = Path(__file__).resolve().parents[1]
DATA_DIR  = Path(os.environ.get("DATA_DIR", ROOT / "data"))
CORE_PATH = DATA_DIR / "core"        / "games_game_core_v50.parquet"
PRED_PATH = DATA_DIR / "predictions" / "games_predictions_current.parquet"

MIN_PICKS_LEADERBOARD = 10
MIN_PICKS_WEEKLY      = 3


# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
def _inject_css() -> None:
    st.markdown("""
<style>
.fvm-hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 24px; padding: 48px 52px 40px;
    margin-bottom: 32px; position: relative; overflow: hidden;
}
.fvm-hero::before {
    content: "🤖"; position: absolute; right: -10px; top: 50%;
    transform: translateY(-50%); font-size: 14rem; opacity: 0.06;
}
.fvm-hero-eyebrow {
    font-size: 0.7rem; font-weight: 800; letter-spacing: 0.2em;
    text-transform: uppercase; margin-bottom: 10px;
    background: linear-gradient(90deg, #67e8f9, #a78bfa, #f9a8d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.fvm-hero-title {
    font-size: 3.4rem; font-weight: 900; line-height: 1;
    background: linear-gradient(90deg, #67e8f9, #a78bfa, #f9a8d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
}
.fvm-hero-sub { font-size: 1rem; color: #94a3b8; max-width: 600px; line-height: 1.6; }
.fvm-hero-badges { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
.fvm-badge {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 999px; padding: 6px 16px;
    font-size: 0.72rem; font-weight: 700; color: #cbd5e1;
    text-transform: uppercase; letter-spacing: 0.08em;
}
.fvm-stat-strip { display: flex; gap: 12px; margin-bottom: 28px; flex-wrap: wrap; }
.fvm-stat {
    flex: 1; min-width: 120px;
    background: #0a0f1e;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px; padding: 20px 18px; text-align: center;
}
.fvm-stat-val { font-size: 2rem; font-weight: 900; line-height: 1; }
.fvm-stat-lbl {
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #475569; margin-top: 6px;
}
.fvm-game-card {
    background: #0a0f1e;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px; padding: 20px 24px;
    margin-bottom: 12px; position: relative; overflow: hidden;
}
.fvm-game-card:hover { border-color: rgba(103,232,249,0.3); }
.fvm-game-meta {
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #475569; margin-bottom: 10px;
}
.fvm-matchup {
    font-size: 1.25rem; font-weight: 900; color: #f1f5f9;
    margin-bottom: 8px; display: flex; align-items: center; gap: 12px;
}
.fvm-vs { font-size: 0.75rem; color: #475569; font-weight: 700; }
.fvm-model-hint {
    font-size: 0.72rem; color: #64748b; margin-top: 6px;
    display: flex; align-items: center; gap: 6px;
}
.fvm-conf-bar-bg {
    background: rgba(255,255,255,0.05); border-radius: 999px;
    height: 4px; width: 80px; overflow: hidden; display: inline-block;
    vertical-align: middle;
}
.fvm-conf-bar-fill {
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, #67e8f9, #a78bfa);
}
.fvm-picked-badge {
    position: absolute; top: 16px; right: 16px;
    background: rgba(52,211,153,0.12); border: 1px solid rgba(52,211,153,0.3);
    border-radius: 999px; padding: 3px 12px;
    font-size: 0.62rem; font-weight: 800; color: #34d399;
    text-transform: uppercase; letter-spacing: 0.08em;
}
.fvm-result-card {
    background: #0a0f1e;
    border-radius: 16px; padding: 18px 22px; margin-bottom: 10px;
    display: flex; align-items: center; gap: 16px;
    border-left: 3px solid transparent;
}
.fvm-result-win     { border-left-color: #34d399; }
.fvm-result-loss    { border-left-color: #f87171; }
.fvm-result-pending { border-left-color: #475569; }
.fvm-result-icon    { font-size: 1.8rem; min-width: 36px; text-align: center; }
.fvm-result-body    { flex: 1; }
.fvm-result-matchup { font-size: 0.92rem; font-weight: 800; color: #f1f5f9; }
.fvm-result-sub     { font-size: 0.7rem; color: #475569; margin-top: 3px; }
.fvm-result-outcome { text-align: right; }
.fvm-result-you     { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #475569; }
.fvm-result-verdict { font-size: 1.1rem; font-weight: 900; }
.fvm-lb-card { background: #0a0f1e; border-radius: 16px; overflow: hidden; }
.fvm-lb-row {
    display: flex; align-items: center; gap: 14px;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.fvm-lb-row:last-child { border-bottom: none; }
.fvm-lb-rank { font-size: 1.5rem; font-weight: 900; min-width: 40px; text-align: center; }
.fvm-lb-name { font-size: 0.95rem; font-weight: 800; color: #f1f5f9; flex: 1; }
.fvm-lb-sub  { font-size: 0.68rem; color: #475569; margin-top: 2px; }
.fvm-lb-stat { text-align: center; min-width: 60px; }
.fvm-lb-stat-val { font-size: 1.1rem; font-weight: 900; }
.fvm-lb-stat-lbl { font-size: 0.55rem; color: #475569; text-transform: uppercase; letter-spacing: 0.07em; margin-top: 2px; }
.fvm-vs-model-badge {
    padding: 4px 12px; border-radius: 999px;
    font-size: 0.65rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.07em;
}
.badge-beating { background: rgba(52,211,153,0.12);  border: 1px solid rgba(52,211,153,0.3);  color: #34d399; }
.badge-losing  { background: rgba(248,113,113,0.12); border: 1px solid rgba(248,113,113,0.3); color: #f87171; }
.badge-tied    { background: rgba(148,163,184,0.12); border: 1px solid rgba(148,163,184,0.3); color: #94a3b8; }
.fvm-section {
    font-size: 0.7rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.14em; padding-bottom: 8px;
    border-bottom: 2px solid; margin: 28px 0 18px;
}
.fvm-empty {
    background: #0a0f1e; border: 1px dashed rgba(255,255,255,0.07);
    border-radius: 16px; padding: 48px; text-align: center;
}
.fvm-empty-icon  { font-size: 3rem; margin-bottom: 12px; }
.fvm-empty-title { font-size: 1rem; font-weight: 800; color: #334155; }
.fvm-empty-sub   { font-size: 0.78rem; color: #1e293b; margin-top: 4px; }
.fvm-h2h {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px; padding: 28px 32px; margin-bottom: 28px;
}
.fvm-h2h-title {
    font-size: 0.65rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.14em; color: #475569; margin-bottom: 16px; text-align: center;
}
.fvm-h2h-row  { display: flex; align-items: center; gap: 16px; }
.fvm-h2h-side { flex: 1; text-align: center; }
.fvm-h2h-name { font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }
.fvm-h2h-pct  { font-size: 2.8rem; font-weight: 900; line-height: 1; }
.fvm-h2h-rec  { font-size: 0.68rem; color: #475569; margin-top: 4px; }
.fvm-h2h-bar-bg {
    flex: 2; height: 12px; background: rgba(255,255,255,0.05);
    border-radius: 999px; overflow: hidden;
}
.fvm-h2h-bar-fan   { height: 100%; border-radius: 999px 0 0 999px; background: linear-gradient(90deg,#67e8f9,#a78bfa); float: left; }
.fvm-h2h-bar-model { height: 100%; border-radius: 0 999px 999px 0; background: linear-gradient(90deg,#f97316,#f43f5e); float: right; }
.fvm-signin-nudge {
    background: linear-gradient(135deg, #0f172a, #1e1b4b);
    border: 1px solid rgba(103,232,249,0.2);
    border-radius: 16px; padding: 32px; text-align: center; margin-bottom: 16px;
}
.fvm-signin-nudge-icon  { font-size: 2.5rem; margin-bottom: 10px; }
.fvm-signin-nudge-title { font-size: 1.1rem; font-weight: 900; color: #f1f5f9; margin-bottom: 6px; }
.fvm-signin-nudge-sub   { font-size: 0.82rem; color: #64748b; margin-bottom: 0; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  DATA LOADERS
# ══════════════════════════════════════════════════════════════
def _clean_gameids(s: pd.Series) -> pd.Series:
    return (
        s.astype(str).str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(",", "", regex=True)
    )


def load_games() -> pd.DataFrame:
    try:
        games = pd.read_parquet(CORE_PATH)
        preds = pd.read_parquet(PRED_PATH)
        games["GameID"] = _clean_gameids(games["GameID"])
        preds["GameID"] = _clean_gameids(preds["GameID"])
        pred_cols = [c for c in ["GameID", "PredHomeWinProb", "PredMargin"] if c in preds.columns]
        preds = preds[pred_cols].drop_duplicates(subset=["GameID"], keep="first")
        df = games.merge(preds, on="GameID", how="left")
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
        if "Gender" in df.columns:
            df["Gender"] = df["Gender"].astype(str).str.strip().str.title()
        for col in ["Home", "Away", "HomeClass", "AwayClass", "HomeRegion", "AwayRegion"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        if "Played" in df.columns:
            df["Played"] = df["Played"].astype("boolean")
        for col in ["PredHomeWinProb", "PredMargin", "HomeScore", "AwayScore"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.reset_index(drop=True)
    except Exception as e:
        st.warning(f"Games load error: {e}")
        return pd.DataFrame()


def load_fan_picks() -> pd.DataFrame:
    try:
        sb  = get_supabase()
        res = sb.table("fan_picks").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"Fan picks load error: {e}")
        return pd.DataFrame()


def load_display_names() -> dict:
    try:
        sb  = get_supabase()
        res = sb.table("profiles").select("id, display_name").execute()
        return {
            r["id"]: r.get("display_name") or f"Fan{r['id'][:6]}"
            for r in (res.data or [])
        }
    except:
        return {}


def save_pick(game_id: str, week_id: str, fan_pick: str, home: str, away: str,
              model_pick: str, model_confidence: float) -> bool:
    try:
        sb = get_supabase()
        sb.table("fan_picks").upsert({
            "user_id":          str(_uid),
            "game_id":          game_id,
            "week_id":          week_id,
            "fan_pick":         fan_pick,
            "home_team":        home,
            "away_team":        away,
            "model_pick":       model_pick,
            "model_confidence": model_confidence,
            "locked":           False,
        }, on_conflict="user_id,game_id").execute()
        return True
    except Exception as e:
        st.error(f"Could not save pick: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def week_id_for(d: date) -> str:
    ts     = pd.Timestamp(d)
    sunday = ts - pd.Timedelta(days=(ts.weekday() + 1) % 7)
    sat    = sunday + pd.Timedelta(days=6)
    return f"{sunday.strftime('%Y-%m-%d')}_to_{sat.strftime('%Y-%m-%d')}"


def get_available_games(df: pd.DataFrame) -> pd.DataFrame:
    today    = date.today()
    tomorrow = today + pd.Timedelta(days=1)
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame()
    mask = (
        (df["Date"] >= today) &
        (df["Date"] <= tomorrow) &
        (df["Played"].fillna(False) == False) &
        df["PredHomeWinProb"].notna()
    )
    return df[mask].copy()


def get_model_pick(row) -> tuple[str, float]:
    phwp = float(row.get("PredHomeWinProb") or 0.5)
    pm   = float(row.get("PredMargin") or 0)
    pick = row["Home"] if pm > 0 else row["Away"]
    conf = round(max(phwp, 1 - phwp) * 100, 1)
    return pick, conf


def compute_my_stats(my_picks: pd.DataFrame) -> dict:
    if my_picks.empty:
        return {"total": 0, "correct": 0, "pct": 0.0, "model_correct": 0, "model_pct": 0.0, "pending": 0}
    scored  = my_picks[my_picks["actual_winner"].notna() & (my_picks["actual_winner"] != "")]
    pending = len(my_picks) - len(scored)
    fan_w   = int(scored["fan_correct"].fillna(False).sum())   if "fan_correct"   in scored.columns else 0
    mod_w   = int(scored["model_correct"].fillna(False).sum()) if "model_correct" in scored.columns else 0
    total   = len(scored)
    return {
        "total":         total,
        "correct":       fan_w,
        "pct":           round(fan_w / total * 100, 1) if total else 0.0,
        "model_correct": mod_w,
        "model_pct":     round(mod_w / total * 100, 1) if total else 0.0,
        "pending":       pending,
    }


def _model_on_fan_games(all_picks: pd.DataFrame) -> tuple[int, int, float]:
    """
    Return (model_wins, model_losses, model_pct) calculated ONLY on the
    unique set of game_ids that fans have actually picked and been scored on.
    """
    if all_picks.empty:
        return 0, 0, 0.0
    scored = all_picks[
        all_picks["actual_winner"].notna() &
        (all_picks["actual_winner"] != "") &
        (all_picks["actual_winner"] != "None")
    ].copy()
    if scored.empty or "model_correct" not in scored.columns:
        return 0, 0, 0.0
    unique_games = scored.drop_duplicates(subset=["game_id"])
    model_wins   = int(unique_games["model_correct"].fillna(False).astype(bool).sum())
    model_total  = len(unique_games)
    model_losses = model_total - model_wins
    model_pct    = round(model_wins / model_total * 100, 1) if model_total else 0.0
    return model_wins, model_losses, model_pct


CLASS_COLORS = {"A": "#f43f5e", "B": "#f97316", "C": "#facc15", "D": "#4ade80", "S": "#60a5fa"}
RANK_ICONS   = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


def _section(title: str, color: str) -> None:
    st.markdown(
        f'<div class="fvm-section" style="color:{color};border-color:{color}40;">{title}</div>',
        unsafe_allow_html=True,
    )


def _empty(icon: str, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="fvm-empty">'
        f'<div class="fvm-empty-icon">{icon}</div>'
        f'<div class="fvm-empty-title">{title}</div>'
        f'<div class="fvm-empty-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _signin_nudge() -> None:
    st.markdown(
        '<div class="fvm-signin-nudge">'
        '<div class="fvm-signin-nudge-icon">🔐</div>'
        '<div class="fvm-signin-nudge-title">Sign in to make picks</div>'
        '<div class="fvm-signin-nudge-sub">'
        'Head to <strong>My Account</strong> in the sidebar to sign in or create a free account.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
#  TAB 1 — MAKE PICKS
# ══════════════════════════════════════════════════════════════
def render_pick_tab(games: pd.DataFrame, all_picks: pd.DataFrame) -> None:
    if not _uid:
        _signin_nudge()
        return

    my_picks    = all_picks[all_picks["user_id"] == str(_uid)].copy() if not all_picks.empty and "user_id" in all_picks.columns else pd.DataFrame()
    my_game_ids = set(my_picks["game_id"].astype(str).tolist()) if not my_picks.empty else set()
    avail       = get_available_games(games)

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        gender_f = st.selectbox("Gender", ["Both", "Boys", "Girls"], key="fvm_gender")
    with fc2:
        class_opts  = ["All"] + sorted(avail["HomeClass"].dropna().unique().tolist()) if "HomeClass" in avail.columns else ["All"]
        class_f     = st.selectbox("Class", class_opts, key="fvm_class")
    with fc3:
        region_opts = ["All"] + sorted(avail["HomeRegion"].dropna().unique().tolist()) if "HomeRegion" in avail.columns else ["All"]
        region_f    = st.selectbox("Region", region_opts, key="fvm_region")

    if "Gender" in avail.columns and gender_f != "Both":
        avail = avail[avail["Gender"] == gender_f]
    if "HomeClass" in avail.columns and class_f != "All":
        avail = avail[avail["HomeClass"] == class_f]
    if "HomeRegion" in avail.columns and region_f != "All":
        avail = avail[avail["HomeRegion"] == region_f]

    st.caption(f"**{len(avail)} game(s)** available · Today & Tomorrow only · Pick as many or as few as you want")
    st.write("")

    if avail.empty:
        _empty("🏀", "No games available right now", "Check back tomorrow when new games are added to the slate.")
        return

    for _, row in avail.iterrows():
        game_id        = str(row["GameID"])
        home           = str(row.get("Home", "Home"))
        away           = str(row.get("Away", "Away"))
        cls            = str(row.get("HomeClass", "?"))
        region         = str(row.get("HomeRegion", ""))
        gender         = str(row.get("Gender", ""))
        gdate          = str(row.get("Date", ""))
        week_id        = week_id_for(row["Date"])
        already_picked = game_id in my_game_ids
        model_pick, model_conf = get_model_pick(row)
        cls_color      = CLASS_COLORS.get(cls, "#60a5fa")

        badge = (
            f'<div class="fvm-picked-badge">✅ Picked: {my_picks[my_picks["game_id"]==game_id].iloc[0]["fan_pick"]}</div>'
            if already_picked else ""
        )

        st.markdown(
            f'<div class="fvm-game-card">{badge}'
            f'<div class="fvm-game-meta">'
            f'<span style="color:{cls_color};">Class {cls}</span> &nbsp;·&nbsp; '
            f'{region} &nbsp;·&nbsp; {gender} &nbsp;·&nbsp; {gdate}'
            f'</div>'
            f'<div class="fvm-matchup">'
            f'<span>{away}</span><span class="fvm-vs">@</span><span>{home}</span>'
            f'</div>'
            f'<div class="fvm-model-hint">'
            f'🤖 Model leans <strong style="color:#a78bfa;">{model_pick}</strong>'
            f'&nbsp;·&nbsp;'
            f'<span class="fvm-conf-bar-bg"><span class="fvm-conf-bar-fill" style="width:{model_conf:.0f}%;"></span></span>'
            f'&nbsp;<span style="color:#64748b;">{model_conf:.0f}% confident</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if not already_picked:
            bc1, bc2, bc3 = st.columns([2, 2, 6])
            with bc1:
                if st.button(f"🏠 {home}", key=f"pick_home_{game_id}", use_container_width=True):
                    if save_pick(game_id, week_id, home, home, away, model_pick, model_conf):
                        st.success(f"✅ Locked in **{home}**!")
                        st.rerun()
            with bc2:
                if st.button(f"✈️ {away}", key=f"pick_away_{game_id}", use_container_width=True):
                    if save_pick(game_id, week_id, away, home, away, model_pick, model_conf):
                        st.success(f"✅ Locked in **{away}**!")
                        st.rerun()
        else:
            fan_p = str(my_picks[my_picks["game_id"] == game_id].iloc[0].get("fan_pick", ""))
            other = away if fan_p == home else home
            cc1, cc2, cc3 = st.columns([2, 2, 6])
            with cc1:
                if st.button(f"🔄 Switch to {other}", key=f"switch_{game_id}", use_container_width=True):
                    if save_pick(game_id, week_id, other, home, away, model_pick, model_conf):
                        st.success(f"✅ Switched to **{other}**!")
                        st.rerun()
        st.write("")


# ══════════════════════════════════════════════════════════════
#  TAB 2 — MY RESULTS
# ══════════════════════════════════════════════════════════════
def render_my_results_tab(games: pd.DataFrame, all_picks: pd.DataFrame) -> None:
    if not _uid:
        _signin_nudge()
        return

    my_picks = (
        all_picks[all_picks["user_id"] == str(_uid)].copy()
        if not all_picks.empty and "user_id" in all_picks.columns
        else pd.DataFrame()
    )

    if my_picks.empty:
        _empty("🎯", "No picks yet", "Head to the Pick tab and start predicting games!")
        return

    stats = compute_my_stats(my_picks)

    if stats["total"] > 0:
        fan_pct   = stats["pct"]
        model_pct = stats["model_pct"]
        total_pct = fan_pct + model_pct
        fan_bar   = int(fan_pct / total_pct * 100) if total_pct > 0 else 50
        mod_bar   = 100 - fan_bar

        if fan_pct > model_pct:
            verdict, verdict_color = "🔥 YOU'RE BEATING THE MODEL", "#34d399"
        elif fan_pct < model_pct:
            verdict, verdict_color = "🤖 MODEL IS WINNING", "#f87171"
        else:
            verdict, verdict_color = "🤝 ALL SQUARE", "#94a3b8"

        st.markdown(
            f'<div class="fvm-h2h">'
            f'<div class="fvm-h2h-title" style="color:{verdict_color};">{verdict}</div>'
            f'<div class="fvm-h2h-row">'
            f'<div class="fvm-h2h-side">'
            f'<div class="fvm-h2h-name" style="color:#67e8f9;">🧑 You</div>'
            f'<div class="fvm-h2h-pct" style="color:#67e8f9;">{fan_pct:.0f}%</div>'
            f'<div class="fvm-h2h-rec">{stats["correct"]}-{stats["total"]-stats["correct"]}</div>'
            f'</div>'
            f'<div class="fvm-h2h-bar-bg">'
            f'<div class="fvm-h2h-bar-fan"   style="width:{fan_bar}%;"></div>'
            f'<div class="fvm-h2h-bar-model" style="width:{mod_bar}%;"></div>'
            f'</div>'
            f'<div class="fvm-h2h-side">'
            f'<div class="fvm-h2h-name" style="color:#f97316;">🤖 Model</div>'
            f'<div class="fvm-h2h-pct" style="color:#f97316;">{model_pct:.0f}%</div>'
            f'<div class="fvm-h2h-rec">{stats["model_correct"]}-{stats["total"]-stats["model_correct"]}</div>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    s1, s2, s3, s4 = st.columns(4)
    for col, val, lbl, color in [
        (s1, stats["total"],         "Games Scored",    "#67e8f9"),
        (s2, stats["correct"],       "Your Correct",    "#34d399"),
        (s3, f"{stats['pct']:.0f}%", "Your Win %",      "#a78bfa"),
        (s4, stats["pending"],       "Pending Results", "#fbbf24"),
    ]:
        with col:
            st.markdown(
                f'<div class="fvm-stat">'
                f'<div class="fvm-stat-val" style="color:{color};">{val}</div>'
                f'<div class="fvm-stat-lbl">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")
    _section("📋 Pick by Pick Breakdown", "#67e8f9")

    if not games.empty and "GameID" in games.columns:
        games_slim           = games[["GameID", "HomeScore", "AwayScore", "Played"]].copy()
        games_slim["GameID"] = _clean_gameids(games_slim["GameID"])
        my_picks = my_picks.merge(
            games_slim.rename(columns={"GameID": "game_id"}),
            on="game_id", how="left", suffixes=("", "_live"),
        )

    sort_col = "created_at" if "created_at" in my_picks.columns else my_picks.columns[0]
    for _, row in my_picks.sort_values(sort_col, ascending=False).iterrows():
        home       = str(row.get("home_team",     "Home"))
        away       = str(row.get("away_team",     "Away"))
        fan_pick   = str(row.get("fan_pick",      "?"))
        model_pick = str(row.get("model_pick",    "?"))
        actual     = str(row.get("actual_winner", "") or "")
        fan_c      = row.get("fan_correct")
        mod_c      = row.get("model_correct")
        conf       = float(row.get("model_confidence") or 0)
        played_val = bool(row.get("Played") or False)

        if played_val and actual and actual not in ("", "None", "nan"):
            if fan_c:
                icon, card_cls, verdict_you = "✅", "fvm-result-win",  "YOU WIN"
            else:
                icon, card_cls, verdict_you = "❌", "fvm-result-loss", "YOU LOSE"
            verdict_color = "#34d399" if fan_c else "#f87171"
            model_verdict = ("✅" if mod_c else "❌") + f" Model {'correct' if mod_c else 'wrong'}"
        else:
            icon, card_cls, verdict_you = "⏳", "fvm-result-pending", "PENDING"
            verdict_color = "#475569"
            model_verdict = f"Model picked {model_pick}"

        agree_txt = "🤝 Agreed with model" if fan_pick == model_pick else f"⚔️ Went against model ({conf:.0f}% conf)"

        st.markdown(
            f'<div class="fvm-result-card {card_cls}">'
            f'<div class="fvm-result-icon">{icon}</div>'
            f'<div class="fvm-result-body">'
            f'<div class="fvm-result-matchup">{away} @ {home}</div>'
            f'<div class="fvm-result-sub">'
            f'Your pick: <strong style="color:#f1f5f9;">{fan_pick}</strong> &nbsp;·&nbsp; '
            f'{model_verdict} &nbsp;·&nbsp; {agree_txt}'
            f'</div>'
            f'</div>'
            f'<div class="fvm-result-outcome">'
            f'<div class="fvm-result-you">You</div>'
            f'<div class="fvm-result-verdict" style="color:{verdict_color};">{verdict_you}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════
#  TAB 3 — LEADERBOARD
# ══════════════════════════════════════════════════════════════
def render_leaderboard_tab(all_picks: pd.DataFrame, display_names: dict) -> None:
    if all_picks.empty:
        _empty("🏆", "No picks yet", "Be the first to submit picks and claim the top spot!")
        return

    scored = all_picks[
        all_picks["actual_winner"].notna() &
        (all_picks["actual_winner"] != "") &
        (all_picks["actual_winner"] != "None")
    ].copy()

    if scored.empty:
        _empty("⏳", "No results yet", "Check back after games finish tonight.")
        return

    scored["fan_correct"]   = scored["fan_correct"].fillna(False).astype(bool)
    scored["model_correct"] = scored["model_correct"].fillna(False).astype(bool)

    # ── Global model benchmark (unique games fans picked) ──────
    model_wins, model_losses, model_pct = _model_on_fan_games(all_picks)
    model_total = model_wins + model_losses

    # ── Per-fan leaderboard stats ──────────────────────────────
    lb = (
        scored.groupby("user_id", dropna=False)
        .agg(Total=("fan_correct", "count"), FanWins=("fan_correct", "sum"), ModelWins=("model_correct", "sum"))
        .reset_index()
    )
    lb = lb[lb["Total"] >= MIN_PICKS_LEADERBOARD]
    lb["FanPct"]   = lb["FanWins"]   / lb["Total"] * 100
    lb["ModelPct"] = lb["ModelWins"] / lb["Total"] * 100
    lb["Edge"]     = lb["FanPct"] - model_pct  # compare against global banner model %
    lb = lb.sort_values("FanPct", ascending=False).reset_index(drop=True)

    # ── Model banner ───────────────────────────────────────────
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1a0a2e,#2d1b4e);'
        f'border:1px solid rgba(249,115,22,0.3);border-radius:16px;'
        f'padding:20px 28px;margin-bottom:24px;display:flex;align-items:center;gap:20px;">'
        f'<div style="font-size:2.5rem;">🤖</div>'
        f'<div>'
        f'<div style="font-size:0.65rem;font-weight:800;text-transform:uppercase;'
        f'letter-spacing:0.12em;color:#f97316;margin-bottom:4px;">The Model — On Fan-Picked Games</div>'
        f'<div style="font-size:1.8rem;font-weight:900;color:#f97316;">'
        f'{model_wins}-{model_losses} &nbsp;·&nbsp; {model_pct:.1f}%</div>'
        f'<div style="font-size:0.68rem;color:#475569;margin-top:2px;">'
        f'Beat this % to earn 🔥 status · Based on {model_total} unique games fans picked</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if lb.empty:
        _empty("⏳", f"Need {MIN_PICKS_LEADERBOARD}+ picks to appear",
               "Keep picking — leaderboard unlocks at 10 scored picks.")
        return

    _section("🏆 Fan Leaderboard", "#fbbf24")

    rows_html = ""
    for i, row in lb.iterrows():
        icon  = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
        uid   = str(row["user_id"])
        label = display_names.get(uid, f"Fan{uid[:6]}")
        edge  = row["Edge"]

        is_me      = (_uid and uid == str(_uid))
        name_style = "color:#67e8f9;" if is_me else ""
        me_tag     = ' &nbsp;<span style="font-size:0.6rem;color:#67e8f9;font-weight:800;">(you)</span>' if is_me else ""

        if edge > 2:
            badge_cls, badge_txt = "badge-beating", f"🔥 +{edge:.1f}% vs Model"
        elif edge < -2:
            badge_cls, badge_txt = "badge-losing",  f"🤖 -{abs(edge):.1f}% vs Model"
        else:
            badge_cls, badge_txt = "badge-tied",    "🤝 Even with Model"

        rows_html += (
            f'<div class="fvm-lb-row">'
            f'<div class="fvm-lb-rank">{icon}</div>'
            f'<div style="flex:1;">'
            f'<div class="fvm-lb-name" style="{name_style}">{label}{me_tag}</div>'
            f'<div class="fvm-lb-sub">{int(row["Total"])} picks · '
            f'{int(row["FanWins"])}-{int(row["Total"] - row["FanWins"])}</div>'
            f'</div>'
            f'<div style="margin-right:16px;">'
            f'<span class="fvm-vs-model-badge {badge_cls}">{badge_txt}</span>'
            f'</div>'
            f'<div class="fvm-lb-stat">'
            f'<div class="fvm-lb-stat-val" style="color:#67e8f9;">{row["FanPct"]:.1f}%</div>'
            f'<div class="fvm-lb-stat-lbl">Win %</div>'
            f'</div>'
            f'</div>'
        )
    st.markdown(f'<div class="fvm-lb-card">{rows_html}</div>', unsafe_allow_html=True)
    st.caption(
        f"Minimum {MIN_PICKS_LEADERBOARD} scored picks required to appear · "
        f"Minimum {MIN_PICKS_WEEKLY} picks/week for weekly spotlight"
    )


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
def main() -> None:
    _inject_css()
    render_logo()

    st.markdown("""
<div class="fvm-hero">
  <div class="fvm-hero-eyebrow">Analytics207 · Fan Challenge</div>
  <div class="fvm-hero-title">Fan vs. The Model</div>
  <div class="fvm-hero-sub">
    Think you know Maine hoops better than the algorithm? Pick today's games,
    track your record, and climb the leaderboard. The model doesn't sleep —
    but neither do real fans.
  </div>
  <div class="fvm-hero-badges">
    <span class="fvm-badge">🎯 Pick Today & Tomorrow's Games</span>
    <span class="fvm-badge">🤖 Compete vs. The Model</span>
    <span class="fvm-badge">🏆 Season Leaderboard</span>
    <span class="fvm-badge">🔥 Free to Play</span>
  </div>
</div>
""", unsafe_allow_html=True)

    games         = load_games()
    all_picks     = load_fan_picks()
    display_names = load_display_names()

    my_picks = (
        all_picks[all_picks["user_id"] == str(_uid)].copy()
        if not all_picks.empty and "user_id" in all_picks.columns and _uid
        else pd.DataFrame()
    )
    stats       = compute_my_stats(my_picks)
    avail_count = len(get_available_games(games)) if not games.empty else 0
    total_fans  = all_picks["user_id"].nunique() if not all_picks.empty and "user_id" in all_picks.columns else 0

    # ── Top stat strip: model % scoped to fan-picked games only ──
    model_wins, model_losses, model_win_pct = _model_on_fan_games(all_picks)

    strip_html = ""
    for val, lbl, color in [
        (avail_count,                  "Games Open",         "#67e8f9"),
        (stats["total"],               "Your Picks Scored",  "#34d399"),
        (f"{stats['pct']:.0f}%",       "Your Win %",         "#a78bfa"),
        (f"{model_win_pct:.0f}%",      "Model Win %",        "#f97316"),
        (total_fans,                   "Total Fans Playing", "#f9a8d4"),
    ]:
        strip_html += (
            f'<div class="fvm-stat">'
            f'<div class="fvm-stat-val" style="color:{color};">{val}</div>'
            f'<div class="fvm-stat-lbl">{lbl}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="fvm-stat-strip">{strip_html}</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "🎯 Make Picks",
        "📊 My Results",
        "🏆 Leaderboard",
    ])

    with tab1:
        render_pick_tab(games, all_picks)
    with tab2:
        render_my_results_tab(games, all_picks)
    with tab3:
        render_leaderboard_tab(all_picks, display_names)

    render_footer()


if __name__ == "__main__":
    main()
