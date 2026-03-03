# pages/XX__Stump_The_Model.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime, date
import os

import pandas as pd
import streamlit as st

from layout import apply_global_layout_tweaks, render_logo, render_footer
from auth import login_gate, logout_button, get_supabase, is_logged_in
from sidebar_auth import render_sidebar_auth

render_sidebar_auth()

st.set_page_config(
    page_title="🧠 Stump The Model | Analytics207",
    page_icon="🧠",
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

SUPABASE_URL = "https://lofxbafahfogptdkjhhv.supabase.co"
# ⚠️  Paste your real anon/public key from Supabase → Settings → API here:
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


# ══════════════════════════════════════════════════════════════
#  DIRECT SUPABASE CLIENT (bypasses cached broken client)
# ══════════════════════════════════════════════════════════════
@st.cache_resource
def _get_sb():
    from supabase import create_client
    key = SUPABASE_ANON_KEY or st.secrets.get("SUPABASE_KEY", "")
    return create_client(SUPABASE_URL, key)


# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
def _inject_css() -> None:
    st.markdown("""
<style>
.stm-hero {
    background: linear-gradient(135deg, #0a0a0a, #1a0533, #0d1b2a);
    border-radius: 24px; padding: 48px 52px 40px;
    margin-bottom: 32px; position: relative; overflow: hidden;
    border-top: 4px solid #a855f7;
}
.stm-hero::before {
    content: "🧠"; position: absolute; right: 40px; top: 50%;
    transform: translateY(-50%); font-size: 14rem; opacity: 0.05;
}
.stm-hero-eyebrow {
    font-size: 0.7rem; font-weight: 800; letter-spacing: 0.2em;
    text-transform: uppercase; margin-bottom: 10px;
    background: linear-gradient(90deg, #a855f7, #ec4899, #f97316);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.stm-hero-title {
    font-size: 3.4rem; font-weight: 900; line-height: 1;
    background: linear-gradient(90deg, #a855f7, #ec4899, #f97316);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
}
.stm-hero-sub { font-size: 1rem; color: #94a3b8; max-width: 620px; line-height: 1.6; }
.stm-hero-badges { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
.stm-badge {
    background: rgba(168,85,247,0.1);
    border: 1px solid rgba(168,85,247,0.3);
    border-radius: 999px; padding: 6px 16px;
    font-size: 0.72rem; font-weight: 700; color: #c4b5fd;
    text-transform: uppercase; letter-spacing: 0.08em;
}
.stm-how-card {
    background: #0a0f1e;
    border: 1px solid rgba(168,85,247,0.2);
    border-radius: 16px; padding: 20px 24px; text-align: center;
}
.stm-how-icon  { font-size: 2.2rem; margin-bottom: 10px; }
.stm-how-title { font-size: 0.88rem; font-weight: 800; color: #f1f5f9; margin-bottom: 6px; }
.stm-how-desc  { font-size: 0.75rem; color: #64748b; line-height: 1.5; }
.stm-pts-card {
    background: linear-gradient(135deg, #1a0533, #0d1b2a);
    border: 1px solid rgba(168,85,247,0.25);
    border-radius: 16px; padding: 16px 20px; text-align: center;
}
.stm-pts-val { font-size: 2rem; font-weight: 900; }
.stm-pts-lbl { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #475569; margin-top: 4px; }
.stm-pts-desc { font-size: 0.7rem; color: #64748b; margin-top: 6px; }
.stm-game-card {
    background: #0a0f1e;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px; padding: 22px 26px;
    margin-bottom: 14px; position: relative; overflow: hidden;
    transition: border-color 0.2s;
}
.stm-game-card:hover { border-color: rgba(168,85,247,0.4); }
.stm-game-card.locked {
    opacity: 0.6;
    border-color: rgba(255,255,255,0.04);
}
.stm-game-meta {
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #475569; margin-bottom: 10px;
    display: flex; align-items: center; gap: 10px;
}
.stm-lock-badge {
    background: rgba(248,113,113,0.12); border: 1px solid rgba(248,113,113,0.3);
    border-radius: 999px; padding: 2px 10px;
    font-size: 0.6rem; font-weight: 800; color: #f87171;
    text-transform: uppercase;
}
.stm-open-badge {
    background: rgba(52,211,153,0.12); border: 1px solid rgba(52,211,153,0.3);
    border-radius: 999px; padding: 2px 10px;
    font-size: 0.6rem; font-weight: 800; color: #34d399;
    text-transform: uppercase;
}
.stm-matchup {
    font-size: 1.3rem; font-weight: 900; color: #f1f5f9;
    margin-bottom: 10px; display: flex; align-items: center; gap: 12px;
}
.stm-vs { font-size: 0.75rem; color: #475569; font-weight: 700; }
.stm-model-block {
    background: rgba(168,85,247,0.06);
    border: 1px solid rgba(168,85,247,0.15);
    border-radius: 12px; padding: 12px 16px; margin-top: 10px;
    display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
}
.stm-model-leans {
    font-size: 0.72rem; color: #94a3b8;
    display: flex; align-items: center; gap: 8px;
}
.stm-conf-bar-bg {
    background: rgba(255,255,255,0.05); border-radius: 999px;
    height: 6px; width: 100px; overflow: hidden; display: inline-block;
    vertical-align: middle;
}
.stm-conf-bar-fill {
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, #a855f7, #ec4899);
}
.stm-pts-reward {
    margin-left: auto;
    background: rgba(168,85,247,0.1); border: 1px solid rgba(168,85,247,0.3);
    border-radius: 999px; padding: 4px 14px;
    font-size: 0.7rem; font-weight: 800; color: #c4b5fd;
}
.stm-already-picked {
    position: absolute; top: 16px; right: 16px;
    background: rgba(168,85,247,0.15); border: 1px solid rgba(168,85,247,0.4);
    border-radius: 999px; padding: 3px 12px;
    font-size: 0.62rem; font-weight: 800; color: #c4b5fd;
    text-transform: uppercase; letter-spacing: 0.08em;
}
.stm-result-card {
    background: #0a0f1e; border-radius: 16px;
    padding: 18px 22px; margin-bottom: 10px;
    display: flex; align-items: center; gap: 16px;
    border-left: 3px solid transparent;
}
.stm-result-stumped  { border-left-color: #a855f7; }
.stm-result-miss     { border-left-color: #475569; }
.stm-result-pending  { border-left-color: #fbbf24; }
.stm-lb-card { background: #0a0f1e; border-radius: 16px; overflow: hidden; }
.stm-lb-row {
    display: flex; align-items: center; gap: 14px;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.stm-lb-row:last-child { border-bottom: none; }
.stm-lb-rank { font-size: 1.5rem; font-weight: 900; min-width: 40px; text-align: center; }
.stm-lb-name { font-size: 0.95rem; font-weight: 800; color: #f1f5f9; flex: 1; }
.stm-lb-sub  { font-size: 0.68rem; color: #475569; margin-top: 2px; }
.stm-section {
    font-size: 0.7rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.14em; padding-bottom: 8px;
    border-bottom: 2px solid; margin: 28px 0 18px;
}
.stm-empty {
    background: #0a0f1e; border: 1px dashed rgba(255,255,255,0.07);
    border-radius: 16px; padding: 48px; text-align: center;
}
.stm-empty-icon  { font-size: 3rem; margin-bottom: 12px; }
.stm-empty-title { font-size: 1rem; font-weight: 800; color: #334155; }
.stm-empty-sub   { font-size: 0.78rem; color: #1e293b; margin-top: 4px; }
.stm-signin-nudge {
    background: linear-gradient(135deg, #0f172a, #1a0533);
    border: 1px solid rgba(168,85,247,0.3);
    border-radius: 16px; padding: 32px; text-align: center; margin-bottom: 16px;
}
.stm-stat {
    flex: 1; min-width: 120px;
    background: #0a0f1e;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px; padding: 20px 18px; text-align: center;
}
.stm-stat-val { font-size: 2rem; font-weight: 900; line-height: 1; }
.stm-stat-lbl {
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #475569; margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def _clean_gameids(s: pd.Series) -> pd.Series:
    return (
        s.astype(str).str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(",", "", regex=True)
    )


def is_game_locked(row) -> bool:
    game_date = pd.Timestamp(row["Date"])
    now       = pd.Timestamp.now()
    weekday   = game_date.weekday()
    if weekday == 5:
        lock_time = game_date + pd.Timedelta(hours=12)
    else:
        lock_time = game_date + pd.Timedelta(hours=16, minutes=30)
    return now >= lock_time


def points_for_conf(conf: float) -> int:
    if conf >= 85:  return 5
    if conf >= 75:  return 3
    if conf >= 65:  return 2
    return 1


def conf_label(conf: float) -> str:
    if conf >= 85:  return "🔥 Jackpot — 5 pts"
    if conf >= 75:  return "💎 Big stump — 3 pts"
    if conf >= 65:  return "⚡ Good stump — 2 pts"
    return "✅ Stump — 1 pt"


RANK_ICONS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
CLASS_COLORS = {"A": "#f43f5e", "B": "#f97316", "C": "#facc15", "D": "#4ade80", "S": "#60a5fa"}


def _section(title: str, color: str) -> None:
    st.markdown(
        f'<div class="stm-section" style="color:{color};border-color:{color}40;">{title}</div>',
        unsafe_allow_html=True,
    )


def _empty(icon: str, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="stm-empty">'
        f'<div class="stm-empty-icon">{icon}</div>'
        f'<div class="stm-empty-title">{title}</div>'
        f'<div class="stm-empty-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _signin_nudge() -> None:
    st.markdown(
        '<div class="stm-signin-nudge">'
        '<div style="font-size:2.5rem;margin-bottom:10px;">🔐</div>'
        '<div style="font-size:1.1rem;font-weight:900;color:#f1f5f9;margin-bottom:6px;">Sign in to play</div>'
        '<div style="font-size:0.82rem;color:#64748b;">'
        'Head to <strong>My Account</strong> in the sidebar to sign in or create a free account.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
#  DATA LOADERS
# ══════════════════════════════════════════════════════════════
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


def load_stump_picks() -> pd.DataFrame:
    try:
        sb  = _get_sb()
        res = sb.table("stump_picks").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # normalize types
            if "stumped" in df.columns:
                df["stumped"] = df["stumped"].fillna(False).astype(bool)
            if "points_earned" in df.columns:
                df["points_earned"] = pd.to_numeric(df["points_earned"], errors="coerce").fillna(0)
            if "model_conf" in df.columns:
                df["model_conf"] = pd.to_numeric(df["model_conf"], errors="coerce").fillna(0)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Stump picks load error: {e}")
        return pd.DataFrame()


def load_display_names() -> dict:
    try:
        sb  = _get_sb()
        res = sb.table("profiles").select("id, display_name").execute()
        return {
            r["id"]: r.get("display_name") or f"Fan#{r['id'][:6]}"
            for r in (res.data or [])
        }
    except:
        return {}


def save_stump_pick(game_id: str, user_pick: str, model_pick: str,
                    model_conf: float) -> bool:
    try:
        sb = _get_sb()
        sb.table("stump_picks").upsert({
            "user_id":    str(_uid),
            "game_id":    game_id,
            "user_pick":  user_pick,
            "model_pick": model_pick,
            "model_conf": model_conf,
            "points_earned": 0,
        }, on_conflict="user_id,game_id").execute()
        return True
    except Exception as e:
        st.error(f"Could not save pick: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  AVAILABLE GAMES
# ══════════════════════════════════════════════════════════════
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
    pm   = float(row.get("PredMargin") or 0)
    phwp = float(row.get("PredHomeWinProb") or 0.5)
    pick = row["Home"] if pm > 0 else row["Away"]
    conf = round(max(phwp, 1 - phwp) * 100, 1)
    return pick, conf


# ══════════════════════════════════════════════════════════════
#  TAB 1 — STUMP IT
# ══════════════════════════════════════════════════════════════
def render_stump_tab(games: pd.DataFrame, stump_picks: pd.DataFrame) -> None:
    if not _uid:
        _signin_nudge()
        return

    avail = get_available_games(games)

    my_picks = (
        stump_picks[stump_picks["user_id"] == str(_uid)]
        if not stump_picks.empty and "user_id" in stump_picks.columns
        else pd.DataFrame()
    )
    my_game_ids = set(my_picks["game_id"].astype(str).tolist()) if not my_picks.empty else set()

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        gender_f = st.selectbox("Gender", ["Both", "Boys", "Girls"], key="stm_gender")
    with fc2:
        class_opts = ["All"] + sorted(avail["HomeClass"].dropna().unique().tolist()) if "HomeClass" in avail.columns else ["All"]
        class_f    = st.selectbox("Class", class_opts, key="stm_class")
    with fc3:
        region_opts = ["All"] + sorted(avail["HomeRegion"].dropna().unique().tolist()) if "HomeRegion" in avail.columns else ["All"]
        region_f    = st.selectbox("Region", region_opts, key="stm_region")

    if "Gender" in avail.columns and gender_f != "Both":
        avail = avail[avail["Gender"] == gender_f]
    if "HomeClass" in avail.columns and class_f != "All":
        avail = avail[avail["HomeClass"] == class_f]
    if "HomeRegion" in avail.columns and region_f != "All":
        avail = avail[avail["HomeRegion"] == region_f]

    open_games   = [r for _, r in avail.iterrows() if not is_game_locked(r)]
    locked_games = [r for _, r in avail.iterrows() if is_game_locked(r)]

    st.caption(
        f"**{len(open_games)} game(s) open** for stumping · "
        f"**{len(locked_games)} locked** · "
        f"Weekday picks lock 4:30 PM · Saturday picks lock Noon"
    )
    st.write("")

    if avail.empty:
        _empty("🧠", "No games available right now", "Check back tomorrow when new games are added.")
        return

    if open_games:
        _section("🟢 Open — Pick Your Stump", "#34d399")
        for row in open_games:
            _render_game_card(row, my_game_ids, my_picks, locked=False)

    if locked_games:
        _section("🔴 Locked — Awaiting Results", "#f87171")
        for row in locked_games:
            _render_game_card(row, my_game_ids, my_picks, locked=True)


def _render_game_card(row, my_game_ids: set, my_picks: pd.DataFrame, locked: bool) -> None:
    game_id     = str(row["GameID"])
    home        = str(row.get("Home", "Home"))
    away        = str(row.get("Away", "Away"))
    cls         = str(row.get("HomeClass", "?"))
    region      = str(row.get("HomeRegion", ""))
    gender      = str(row.get("Gender", ""))
    gdate       = str(row.get("Date", ""))
    cls_color   = CLASS_COLORS.get(cls, "#60a5fa")
    model_pick, model_conf = get_model_pick(row)
    pts         = points_for_conf(model_conf)
    pts_lbl     = conf_label(model_conf)
    already     = game_id in my_game_ids
    lock_cls    = "locked" if locked else ""

    fan_picked = ""
    if already and not my_picks.empty:
        match = my_picks[my_picks["game_id"] == game_id]
        if not match.empty:
            fan_picked = str(match.iloc[0]["user_pick"])

    already_badge = (
        f'<div class="stm-already-picked">🧠 Targeting: {fan_picked}</div>'
        if already else ""
    )

    st.markdown(
        f'<div class="stm-game-card {lock_cls}">{already_badge}'
        f'<div class="stm-game-meta">'
        f'<span style="color:{cls_color};">Class {cls}</span>'
        f'<span>·</span><span>{region}</span>'
        f'<span>·</span><span>{gender}</span>'
        f'<span>·</span><span>{gdate}</span>'
        f'<span class="{"stm-lock-badge" if locked else "stm-open-badge"}">'
        f'{"🔒 Locked" if locked else "🟢 Open"}</span>'
        f'</div>'
        f'<div class="stm-matchup">'
        f'<span>{away}</span><span class="stm-vs">@</span><span>{home}</span>'
        f'</div>'
        f'<div class="stm-model-block">'
        f'<div class="stm-model-leans">'
        f'🤖 Model leans <strong style="color:#c4b5fd;margin:0 6px;">{model_pick}</strong>'
        f'<span class="stm-conf-bar-bg">'
        f'<span class="stm-conf-bar-fill" style="width:{model_conf:.0f}%;"></span>'
        f'</span>'
        f'<span style="color:#64748b;margin-left:6px;">{model_conf:.0f}% confident</span>'
        f'</div>'
        f'<div class="stm-pts-reward">{pts_lbl}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not locked and not already:
        stump_target = away if model_pick == home else home
        bc1, bc2 = st.columns([3, 7])
        with bc1:
            if st.button(
                f"🧠 Stump It — Pick {stump_target}",
                key=f"stump_{game_id}",
                use_container_width=True,
            ):
                if save_stump_pick(game_id, stump_target, model_pick, model_conf):
                    st.success(f"🧠 Stump attempt locked! You picked **{stump_target}** against the model's {model_pick} ({model_conf:.0f}% conf) — worth **{pts} pt(s)** if correct!")
                    st.rerun()
    elif not locked and already:
        st.caption(f"✅ You're targeting **{fan_picked}** to stump the model on this one.")

    st.write("")


# ══════════════════════════════════════════════════════════════
#  TAB 2 — MY RESULTS
# ══════════════════════════════════════════════════════════════
def render_my_results_tab(stump_picks: pd.DataFrame) -> None:
    if not _uid:
        _signin_nudge()
        return

    my_picks = (
        stump_picks[stump_picks["user_id"] == str(_uid)].copy()
        if not stump_picks.empty and "user_id" in stump_picks.columns
        else pd.DataFrame()
    )

    if my_picks.empty:
        _empty("🧠", "No stump attempts yet", "Head to the Stump It tab and start challenging the model!")
        return

    scored  = my_picks[my_picks["actual_winner"].notna() & (my_picks["actual_winner"] != "")]
    pending = len(my_picks) - len(scored)

    total_stumps = int(scored["stumped"].fillna(False).sum())       if "stumped"       in scored.columns else 0
    total_pts    = int(scored["points_earned"].fillna(0).sum())     if "points_earned" in scored.columns else 0
    total_tries  = len(scored)
    stump_rate   = round(total_stumps / total_tries * 100, 1) if total_tries else 0.0

    strip_html = ""
    for val, lbl, color in [
        (total_tries,          "Attempts Scored",   "#a855f7"),
        (total_stumps,         "Successful Stumps", "#34d399"),
        (f"{stump_rate:.0f}%", "Stump Rate",        "#ec4899"),
        (total_pts,            "Total Points",      "#f97316"),
        (pending,              "Pending",           "#fbbf24"),
    ]:
        strip_html += (
            f'<div class="stm-stat">'
            f'<div class="stm-stat-val" style="color:{color};">{val}</div>'
            f'<div class="stm-stat-lbl">{lbl}</div>'
            f'</div>'
        )
    st.markdown(f'<div style="display:flex;gap:12px;margin-bottom:28px;flex-wrap:wrap;">{strip_html}</div>', unsafe_allow_html=True)

    _section("📋 My Stump History", "#a855f7")

    sort_col = "created_at" if "created_at" in my_picks.columns else my_picks.columns[0]
    for _, row in my_picks.sort_values(sort_col, ascending=False).iterrows():
        game_id    = str(row.get("game_id", ""))
        user_pick  = str(row.get("user_pick", "?"))
        model_pick = str(row.get("model_pick", "?"))
        model_conf = float(row.get("model_conf") or 0)
        actual     = str(row.get("actual_winner", "") or "")
        stumped    = row.get("stumped")
        pts        = int(row.get("points_earned") or 0)

        if actual and actual not in ("", "None", "nan"):
            if stumped:
                icon, card_cls = "🧠", "stm-result-stumped"
                verdict        = f'<span style="color:#a855f7;font-weight:900;">STUMPED IT! +{pts} pts</span>'
            else:
                icon, card_cls = "❌", "stm-result-miss"
                verdict        = '<span style="color:#475569;font-weight:900;">Model was right</span>'
        else:
            icon, card_cls = "⏳", "stm-result-pending"
            verdict        = '<span style="color:#fbbf24;font-weight:900;">Pending</span>'

        st.markdown(
            f'<div class="stm-result-card {card_cls}">'
            f'<div style="font-size:1.8rem;min-width:36px;text-align:center;">{icon}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.92rem;font-weight:800;color:#f1f5f9;">{game_id}</div>'
            f'<div style="font-size:0.7rem;color:#475569;margin-top:3px;">'
            f'Your pick: <strong style="color:#c4b5fd;">{user_pick}</strong> &nbsp;·&nbsp; '
            f'Model picked: <strong style="color:#f97316;">{model_pick}</strong> &nbsp;·&nbsp; '
            f'Model confidence: {model_conf:.0f}%'
            f'</div>'
            f'</div>'
            f'<div style="text-align:right;">{verdict}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════
#  TAB 3 — LEADERBOARD
# ══════════════════════════════════════════════════════════════
def render_leaderboard_tab(stump_picks: pd.DataFrame, display_names: dict) -> None:
    if stump_picks.empty:
        _empty("🏆", "No stump attempts yet", "Be the first to challenge the model!")
        return

    scored = stump_picks[
        stump_picks["actual_winner"].notna() &
        (stump_picks["actual_winner"].astype(str).str.strip() != "") &
        (stump_picks["actual_winner"].astype(str).str.strip() != "None") &
        (stump_picks["actual_winner"].astype(str).str.strip() != "nan")
    ].copy()

    if scored.empty:
        _empty("⏳", "No results yet", "Check back after tonight's games finish.")
        return

    scored["stumped"]       = scored["stumped"].fillna(False).astype(bool)
    scored["points_earned"] = pd.to_numeric(scored["points_earned"], errors="coerce").fillna(0)

    lb = (
        scored.groupby("user_id", dropna=False)
        .agg(
            TotalPts =("points_earned", "sum"),
            Stumps   =("stumped",        "sum"),
            Attempts =("stumped",        "count"),
        )
        .reset_index()
    )
    lb["StumpRate"] = (lb["Stumps"] / lb["Attempts"] * 100).round(1)
    # ── lowered to 1 for testing, raise to 3 in production ──
    lb = lb[lb["Attempts"] >= 1]
    lb = lb.sort_values(["TotalPts", "Stumps"], ascending=False).reset_index(drop=True)

    # ── Best stump trophy ─────────────────────────────────────
    best_stump = scored[scored["stumped"] == True].nlargest(1, "model_conf") if "model_conf" in scored.columns else pd.DataFrame()

    if not best_stump.empty:
        bs      = best_stump.iloc[0]
        bs_uid  = str(bs["user_id"])
        bs_name = display_names.get(bs_uid, f"Fan#{bs_uid[:6]}")
        bs_conf = float(bs["model_conf"])
        bs_game = str(bs["game_id"])
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1a0533,#2d1b4e);'
            f'border:1px solid rgba(168,85,247,0.4);border-radius:16px;'
            f'padding:20px 28px;margin-bottom:24px;display:flex;align-items:center;gap:20px;">'
            f'<div style="font-size:2.5rem;">👑</div>'
            f'<div>'
            f'<div style="font-size:0.65rem;font-weight:800;text-transform:uppercase;'
            f'letter-spacing:0.12em;color:#a855f7;margin-bottom:4px;">Best Stump This Season</div>'
            f'<div style="font-size:1.4rem;font-weight:900;color:#f1f5f9;">{bs_name}</div>'
            f'<div style="font-size:0.72rem;color:#475569;margin-top:2px;">'
            f'Stumped the model when it was {bs_conf:.0f}% confident · Game: {bs_game}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _section("🧠 Season Stump Leaderboard", "#a855f7")

    if lb.empty:
        _empty("⏳", "No qualifying entries yet", "Keep stumping to appear on the leaderboard.")
        return

    rows_html = ""
    for i, row in lb.iterrows():
        icon  = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
        uid   = str(row["user_id"])
        label = display_names.get(uid, f"Fan#{uid[:6]}")
        is_me = (_uid and uid == str(_uid))
        name_style = "color:#a855f7;" if is_me else ""
        me_tag     = ' &nbsp;<span style="font-size:0.6rem;color:#a855f7;font-weight:800;">(you)</span>' if is_me else ""

        rows_html += (
            f'<div class="stm-lb-row">'
            f'<div class="stm-lb-rank">{icon}</div>'
            f'<div style="flex:1;">'
            f'<div class="stm-lb-name" style="{name_style}">{label}{me_tag}</div>'
            f'<div class="stm-lb-sub">'
            f'{int(row["Stumps"])} stumps · {int(row["Attempts"])} attempts · {row["StumpRate"]:.0f}% rate'
            f'</div>'
            f'</div>'
            f'<div style="text-align:center;min-width:80px;margin-right:12px;">'
            f'<div style="font-size:0.65rem;color:#475569;text-transform:uppercase;letter-spacing:0.07em;">Stump Rate</div>'
            f'<div style="font-size:1rem;font-weight:900;color:#ec4899;">{row["StumpRate"]:.0f}%</div>'
            f'</div>'
            f'<div style="text-align:center;min-width:70px;">'
            f'<div style="font-size:0.65rem;color:#475569;text-transform:uppercase;letter-spacing:0.07em;">Points</div>'
            f'<div style="font-size:1.2rem;font-weight:900;color:#a855f7;">+{int(row["TotalPts"])}</div>'
            f'</div>'
            f'</div>'
        )
    st.markdown(f'<div class="stm-lb-card">{rows_html}</div>', unsafe_allow_html=True)
    st.caption("Minimum 3 scored attempts required to appear on leaderboard")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
def main() -> None:
    _inject_css()
    render_logo()

    st.markdown("""
<div class="stm-hero">
  <div class="stm-hero-eyebrow">Analytics207 · Fan Challenge</div>
  <div class="stm-hero-title">Stump The Model 🧠</div>
  <div class="stm-hero-sub">
    The model thinks it knows everything about Maine hoops. Prove it wrong.
    Find the games where The Model is overconfident — pick the upset — and earn
    points. The bigger the model's confidence, the bigger your reward for
    proving it wrong.
  </div>
  <div class="stm-hero-badges">
    <span class="stm-badge">🧠 Pick Against The Model</span>
    <span class="stm-badge">🔥 5 pts for 85%+ conf upsets</span>
    <span class="stm-badge">📊 Season Leaderboard</span>
    <span class="stm-badge">👑 Best Stump Trophy</span>
    <span class="stm-badge">🆓 Free to Play</span>
  </div>
</div>
""", unsafe_allow_html=True)

    h1, h2, h3, h4 = st.columns(4)
    for col, icon, title, desc in [
        (h1, "🤖", "Model Makes a Pick",    "Every game the model predicts a winner with a confidence score."),
        (h2, "🧠", "You Pick The Upset",    "Choose games where you think the model is wrong and pick the other team."),
        (h3, "🔥", "Earn Points",           "Stump a 55% model = 1 pt. Stump an 85%+ model = 5 pts jackpot."),
        (h4, "🏆", "Climb The Leaderboard", "Best stumpers of the season earn bragging rights and the crown."),
    ]:
        with col:
            st.markdown(
                f'<div class="stm-how-card">'
                f'<div class="stm-how-icon">{icon}</div>'
                f'<div class="stm-how-title">{title}</div>'
                f'<div class="stm-how-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")

    _section("💰 Points Guide", "#f97316")
    p1, p2, p3, p4 = st.columns(4)
    for col, pts, lbl, desc, color in [
        (p1, "1 pt",  "55–64% Confident",  "Model is slightly leaning",  "#64748b"),
        (p2, "2 pts", "65–74% Confident",  "Model is fairly sure",       "#4ade80"),
        (p3, "3 pts", "75–84% Confident",  "Model is very confident",    "#f97316"),
        (p4, "5 pts", "85%+ Confident 🔥", "Model is almost certain",    "#a855f7"),
    ]:
        with col:
            st.markdown(
                f'<div class="stm-pts-card">'
                f'<div class="stm-pts-val" style="color:{color};">{pts}</div>'
                f'<div class="stm-pts-lbl">{lbl}</div>'
                f'<div class="stm-pts-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")

    games         = load_games()
    stump_picks   = load_stump_picks()
    display_names = load_display_names()

    tab1, tab2, tab3 = st.tabs([
        "🧠 Stump It",
        "📊 My Results",
        "🏆 Leaderboard",
    ])

    with tab1:
        render_stump_tab(games, stump_picks)
    with tab2:
        render_my_results_tab(stump_picks)
    with tab3:
        render_leaderboard_tab(stump_picks, display_names)

    render_footer()


if __name__ == "__main__":
    main()
