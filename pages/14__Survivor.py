# pages/14__Survivor.py
from __future__ import annotations

from pathlib import Path
from datetime import date
import os

import pandas as pd
import streamlit as st

from layout import apply_global_layout_tweaks, render_logo, render_footer
from auth import login_gate, logout_button
from sidebar_auth import render_sidebar_auth

render_sidebar_auth()

st.set_page_config(
    page_title="☠️ Survivor | Analytics207",
    page_icon="☠️",
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

SUPABASE_URL      = "https://lofxbafahfogptdkjhhv.supabase.co"
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

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
.sv-hero {
    background: linear-gradient(135deg, #0a0a0a, #1a0a00, #0d0a00);
    border-radius: 24px; padding: 48px 52px 40px;
    margin-bottom: 32px; position: relative; overflow: hidden;
    border-top: 4px solid #f97316;
}
.sv-hero::before {
    content: "☠️"; position: absolute; right: 40px; top: 50%;
    transform: translateY(-50%); font-size: 14rem; opacity: 0.05;
}
.sv-hero-eyebrow {
    font-size: 0.7rem; font-weight: 800; letter-spacing: 0.2em;
    text-transform: uppercase; margin-bottom: 10px;
    background: linear-gradient(90deg, #f97316, #fbbf24, #dc2626);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.sv-hero-title {
    font-size: 3.4rem; font-weight: 900; line-height: 1;
    background: linear-gradient(90deg, #f97316, #fbbf24, #dc2626);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 12px;
}
.sv-hero-sub { font-size: 1rem; color: #94a3b8; max-width: 620px; line-height: 1.6; }
.sv-hero-badges { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
.sv-badge {
    background: rgba(249,115,22,0.1);
    border: 1px solid rgba(249,115,22,0.3);
    border-radius: 999px; padding: 6px 16px;
    font-size: 0.72rem; font-weight: 700; color: #fdba74;
    text-transform: uppercase; letter-spacing: 0.08em;
}
.sv-how-card {
    background: #0a0f1e;
    border: 1px solid rgba(249,115,22,0.2);
    border-radius: 16px; padding: 20px 24px; text-align: center;
}
.sv-how-icon  { font-size: 2.2rem; margin-bottom: 10px; }
.sv-how-title { font-size: 0.88rem; font-weight: 800; color: #f1f5f9; margin-bottom: 6px; }
.sv-how-desc  { font-size: 0.75rem; color: #64748b; line-height: 1.5; }
.sv-status-alive {
    background: linear-gradient(135deg, #052e16, #14532d);
    border: 1px solid rgba(34,197,94,0.4);
    border-radius: 16px; padding: 20px 28px;
    display: flex; align-items: center; gap: 20px; margin-bottom: 24px;
}
.sv-status-mulligan {
    background: linear-gradient(135deg, #1c1917, #292524);
    border: 1px solid rgba(251,191,36,0.4);
    border-radius: 16px; padding: 20px 28px;
    display: flex; align-items: center; gap: 20px; margin-bottom: 24px;
}
.sv-status-dead {
    background: linear-gradient(135deg, #1a0000, #2d0000);
    border: 1px solid rgba(220,38,38,0.4);
    border-radius: 16px; padding: 20px 28px;
    display: flex; align-items: center; gap: 20px; margin-bottom: 24px;
}
.sv-game-card {
    background: #0a0f1e;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px; padding: 22px 26px;
    margin-bottom: 14px; position: relative; overflow: hidden;
}
.sv-game-card:hover { border-color: rgba(249,115,22,0.4); }
.sv-game-card.locked { opacity: 0.55; border-color: rgba(255,255,255,0.04); }
.sv-game-card.picked { border-color: rgba(249,115,22,0.5); }
.sv-game-meta {
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #475569; margin-bottom: 10px;
    display: flex; align-items: center; gap: 10px;
}
.sv-matchup {
    font-size: 1.3rem; font-weight: 900; color: #f1f5f9;
    margin-bottom: 10px; display: flex; align-items: center; gap: 12px;
}
.sv-vs { font-size: 0.75rem; color: #475569; font-weight: 700; }
.sv-conf-block {
    background: rgba(249,115,22,0.06);
    border: 1px solid rgba(249,115,22,0.15);
    border-radius: 12px; padding: 12px 16px; margin-top: 10px;
    display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
}
.sv-conf-bar-bg {
    background: rgba(255,255,255,0.05); border-radius: 999px;
    height: 6px; width: 100px; overflow: hidden; display: inline-block;
    vertical-align: middle;
}
.sv-conf-bar-fill {
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, #f97316, #fbbf24);
}
.sv-danger  { background: rgba(220,38,38,0.1);  border:1px solid rgba(220,38,38,0.3);  border-radius:999px; padding:3px 12px; font-size:0.65rem; font-weight:800; color:#f87171; }
.sv-risky   { background: rgba(234,179,8,0.1);  border:1px solid rgba(234,179,8,0.3);  border-radius:999px; padding:3px 12px; font-size:0.65rem; font-weight:800; color:#fbbf24; }
.sv-solid   { background: rgba(34,197,94,0.1);  border:1px solid rgba(34,197,94,0.3);  border-radius:999px; padding:3px 12px; font-size:0.65rem; font-weight:800; color:#4ade80; }
.sv-lock    { background: rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3); border-radius:999px; padding:3px 12px; font-size:0.65rem; font-weight:800; color:#a5b4fc; }
.sv-used-badge {
    position: absolute; top: 16px; right: 16px;
    background: rgba(220,38,38,0.15); border: 1px solid rgba(220,38,38,0.4);
    border-radius: 999px; padding: 3px 12px;
    font-size: 0.62rem; font-weight: 800; color: #f87171;
    text-transform: uppercase;
}
.sv-picked-badge {
    position: absolute; top: 16px; right: 16px;
    background: rgba(249,115,22,0.15); border: 1px solid rgba(249,115,22,0.4);
    border-radius: 999px; padding: 3px 12px;
    font-size: 0.62rem; font-weight: 800; color: #fdba74;
    text-transform: uppercase;
}
.sv-history-card {
    background: #0a0f1e; border-radius: 14px;
    padding: 16px 20px; margin-bottom: 8px;
    display: flex; align-items: center; gap: 16px;
    border-left: 3px solid transparent;
}
.sv-survived  { border-left-color: #22c55e; }
.sv-mulligan  { border-left-color: #fbbf24; }
.sv-dead      { border-left-color: #dc2626; }
.sv-pending   { border-left-color: #475569; }
.sv-lb-card   { background: #0a0f1e; border-radius: 16px; overflow: hidden; }
.sv-lb-row {
    display: flex; align-items: center; gap: 14px;
    padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.04);
}
.sv-lb-row:last-child { border-bottom: none; }
.sv-lb-rank { font-size: 1.5rem; font-weight: 900; min-width: 40px; text-align: center; }
.sv-lb-name { font-size: 0.95rem; font-weight: 800; color: #f1f5f9; flex: 1; }
.sv-lb-sub  { font-size: 0.68rem; color: #475569; margin-top: 2px; }
.sv-section {
    font-size: 0.7rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.14em; padding-bottom: 8px;
    border-bottom: 2px solid; margin: 28px 0 18px;
}
.sv-empty {
    background: #0a0f1e; border: 1px dashed rgba(255,255,255,0.07);
    border-radius: 16px; padding: 48px; text-align: center;
}
.sv-empty-icon  { font-size: 3rem; margin-bottom: 12px; }
.sv-empty-title { font-size: 1rem; font-weight: 800; color: #334155; }
.sv-empty-sub   { font-size: 0.78rem; color: #1e293b; margin-top: 4px; }
.sv-signin-nudge {
    background: linear-gradient(135deg, #0f172a, #1a0a00);
    border: 1px solid rgba(249,115,22,0.3);
    border-radius: 16px; padding: 32px; text-align: center; margin-bottom: 16px;
}
.sv-stat {
    flex: 1; min-width: 120px; background: #0a0f1e;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px; padding: 20px 18px; text-align: center;
}
.sv-stat-val { font-size: 2rem; font-weight: 900; line-height: 1; }
.sv-stat-lbl {
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

def week_bounds(anchor=None) -> tuple[pd.Timestamp, pd.Timestamp]:
    anchor = pd.Timestamp(anchor or date.today()).normalize()
    sunday = anchor - pd.Timedelta(days=(anchor.weekday() + 1) % 7)
    return sunday, sunday + pd.Timedelta(days=6)

def current_week_id() -> str:
    s, e = week_bounds()
    return f"{s.strftime('%Y-%m-%d')}_to_{e.strftime('%Y-%m-%d')}"

def fmt_week(week_id: str) -> str:
    try:
        s = pd.Timestamp(week_id.split("_to_")[0])
        e = pd.Timestamp(week_id.split("_to_")[1])
        return f"{s.strftime('%b %d')} – {e.strftime('%b %d, %Y')}"
    except:
        return week_id

def is_game_locked(row) -> bool:
    game_date = pd.Timestamp(row["Date"])
    now       = pd.Timestamp.now()
    weekday   = game_date.weekday()
    lock_time = game_date + pd.Timedelta(hours=12) if weekday == 5 else game_date + pd.Timedelta(hours=16, minutes=30)
    return now >= lock_time

def conf_tier(conf: float) -> tuple[str, str]:
    if conf >= 85: return "💎 Lock",        "sv-lock"
    if conf >= 75: return "🟢 Solid",       "sv-solid"
    if conf >= 65: return "🟡 Risky",       "sv-risky"
    return            "🔴 Danger Zone",     "sv-danger"

def get_model_pick(row) -> tuple[str, float]:
    pm   = float(row.get("PredMargin") or 0)
    phwp = float(row.get("PredHomeWinProb") or 0.5)
    pick = row["Home"] if pm > 0 else row["Away"]
    conf = round(max(phwp, 1 - phwp) * 100, 1)
    return pick, conf

RANK_ICONS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def _section(title: str, color: str) -> None:
    st.markdown(
        f'<div class="sv-section" style="color:{color};border-color:{color}40;">{title}</div>',
        unsafe_allow_html=True,
    )

def _empty(icon: str, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="sv-empty"><div class="sv-empty-icon">{icon}</div>'
        f'<div class="sv-empty-title">{title}</div>'
        f'<div class="sv-empty-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )

def _signin_nudge() -> None:
    st.markdown(
        '<div class="sv-signin-nudge">'
        '<div style="font-size:2.5rem;margin-bottom:10px;">🔐</div>'
        '<div style="font-size:1.1rem;font-weight:900;color:#f1f5f9;margin-bottom:6px;">Sign in to play</div>'
        '<div style="font-size:0.82rem;color:#64748b;">'
        'Head to <strong>My Account</strong> in the sidebar to sign in or create a free account.'
        '</div></div>',
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
        for col in ["PredHomeWinProb", "PredMargin"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.reset_index(drop=True)
    except Exception as e:
        st.warning(f"Games load error: {e}")
        return pd.DataFrame()

def load_survivor_picks() -> pd.DataFrame:
    try:
        sb  = _get_sb()
        res = sb.table("survivor_picks").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            if "survived"      in df.columns: df["survived"]      = df["survived"].fillna(False).astype(bool)
            if "mulligan_used" in df.columns: df["mulligan_used"] = df["mulligan_used"].fillna(False).astype(bool)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Survivor picks load error: {e}")
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

def save_survivor_pick(week_id: str, game_id: str, team_picked: str) -> bool:
    try:
        sb = _get_sb()
        sb.table("survivor_picks").upsert({
            "user_id":     str(_uid),
            "week_id":     week_id,
            "game_id":     game_id,
            "team_picked": team_picked,
        }, on_conflict="user_id,week_id").execute()
        return True
    except Exception as e:
        st.error(f"Could not save pick: {e}")
        return False


# ══════════════════════════════════════════════════════════════
#  GAME AVAILABILITY
# ══════════════════════════════════════════════════════════════
MIN_CONF = 55.0

def get_week_games(df: pd.DataFrame) -> pd.DataFrame:
    ws, we = week_bounds()
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame()
    mask = (
        (df["Date"] >= ws.date()) &
        (df["Date"] <= we.date()) &
        (df["Played"].fillna(False) == False) &
        df["PredHomeWinProb"].notna()
    )
    eligible = df[mask].copy()
    if eligible.empty:
        return pd.DataFrame()
    eligible["_conf"] = eligible.apply(
        lambda r: round(max(float(r.get("PredHomeWinProb") or 0.5), 1 - float(r.get("PredHomeWinProb") or 0.5)) * 100, 1),
        axis=1
    )
    return eligible[eligible["_conf"] >= MIN_CONF].copy()


# ══════════════════════════════════════════════════════════════
#  USER STATUS
# ══════════════════════════════════════════════════════════════
def get_user_status(picks: pd.DataFrame) -> dict:
    """Returns alive, mulligan_used, mulligan_available, weeks_survived, teams_used, eliminated_week."""
    if picks.empty or "user_id" not in picks.columns:
        return {"alive": True, "mulligan_used": False, "weeks_survived": 0, "teams_used": set(), "eliminated_week": None}

    my = picks[picks["user_id"] == str(_uid)].copy() if _uid else pd.DataFrame()
    if my.empty:
        return {"alive": True, "mulligan_used": False, "weeks_survived": 0, "teams_used": set(), "eliminated_week": None}

    scored = my[my["actual_winner"].notna() & (my["actual_winner"].astype(str).str.strip() != "")]
    mulligan_used   = bool(my["mulligan_used"].any())
    weeks_survived  = int(scored["survived"].fillna(False).sum())
    teams_used      = set(my["team_picked"].astype(str).str.strip().tolist())

    # Eliminated = has a non-survived scored pick AND mulligan already used
    losses = scored[scored["survived"] == False]
    alive  = True
    eliminated_week = None
    if len(losses) >= 2:
        alive = False
        eliminated_week = losses.iloc[-1]["week_id"]
    elif len(losses) == 1 and mulligan_used:
        alive = False
        eliminated_week = losses.iloc[-1]["week_id"]

    return {
        "alive":           alive,
        "mulligan_used":   mulligan_used,
        "weeks_survived":  weeks_survived,
        "teams_used":      teams_used,
        "eliminated_week": eliminated_week,
    }


# ══════════════════════════════════════════════════════════════
#  TAB 1 — MAKE YOUR PICK
# ══════════════════════════════════════════════════════════════
def render_pick_tab(games: pd.DataFrame, survivor_picks: pd.DataFrame) -> None:
    if not _uid:
        _signin_nudge()
        return

    status  = get_user_status(survivor_picks)
    week_id = current_week_id()
    ws, we  = week_bounds()

    # ── Status banner ─────────────────────────────────────────
    if not status["alive"]:
        st.markdown(
            f'<div class="sv-status-dead">'
            f'<div style="font-size:3rem;">💀</div>'
            f'<div>'
            f'<div style="font-size:0.65rem;font-weight:800;text-transform:uppercase;letter-spacing:0.12em;color:#dc2626;margin-bottom:4px;">Eliminated</div>'
            f'<div style="font-size:1.4rem;font-weight:900;color:#f1f5f9;">Your run is over</div>'
            f'<div style="font-size:0.72rem;color:#475569;margin-top:2px;">You survived {status["weeks_survived"]} week(s) · Eliminated week of {fmt_week(status["eliminated_week"] or "")}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        return

    mulligan_txt = "✅ Mulligan Available" if not status["mulligan_used"] else "☠️ Mulligan Used"
    mulligan_color = "#fbbf24" if not status["mulligan_used"] else "#dc2626"
    banner_cls    = "sv-status-mulligan" if status["mulligan_used"] else "sv-status-alive"

    st.markdown(
        f'<div class="{banner_cls}">'
        f'<div style="font-size:3rem;">{"🟢" if not status["mulligan_used"] else "🟡"}</div>'
        f'<div style="flex:1;">'
        f'<div style="font-size:0.65rem;font-weight:800;text-transform:uppercase;letter-spacing:0.12em;color:#22c55e;margin-bottom:4px;">Still Alive</div>'
        f'<div style="font-size:1.4rem;font-weight:900;color:#f1f5f9;">{status["weeks_survived"]} week(s) survived</div>'
        f'<div style="font-size:0.72rem;color:#475569;margin-top:2px;">Week of {ws.strftime("%b %d")} – {we.strftime("%b %d, %Y")}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:0.72rem;font-weight:800;color:{mulligan_color};">{mulligan_txt}</div>'
        f'<div style="font-size:0.62rem;color:#475569;margin-top:3px;">{len(status["teams_used"])} team(s) used</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── This week's pick ──────────────────────────────────────
    my_week_pick = pd.DataFrame()
    if not survivor_picks.empty and "user_id" in survivor_picks.columns:
        my_week_pick = survivor_picks[
            (survivor_picks["user_id"] == str(_uid)) &
            (survivor_picks["week_id"] == week_id)
        ]

    avail = get_week_games(games)

    # ── Filters ───────────────────────────────────────────────
    fc1, fc2 = st.columns(2)
    with fc1:
        gender_f = st.selectbox("Gender", ["Both", "Boys", "Girls"], key="sv_gender")
    with fc2:
        class_opts = ["All"] + sorted(avail["HomeClass"].dropna().unique().tolist()) if not avail.empty and "HomeClass" in avail.columns else ["All"]
        class_f    = st.selectbox("Class", class_opts, key="sv_class")

    if not avail.empty:
        if "Gender" in avail.columns and gender_f != "Both":
            avail = avail[avail["Gender"] == gender_f]
        if "HomeClass" in avail.columns and class_f != "All":
            avail = avail[avail["HomeClass"] == class_f]

    open_games   = [r for _, r in avail.iterrows() if not is_game_locked(r)] if not avail.empty else []
    locked_games = [r for _, r in avail.iterrows() if is_game_locked(r)]     if not avail.empty else []

    already_picked = not my_week_pick.empty
    picked_team    = str(my_week_pick.iloc[0]["team_picked"]) if already_picked else ""
    picked_game    = str(my_week_pick.iloc[0]["game_id"])     if already_picked else ""

    if already_picked:
        st.markdown(
            f'<div style="background:rgba(249,115,22,0.08);border:1px solid rgba(249,115,22,0.3);'
            f'border-radius:14px;padding:16px 22px;margin-bottom:18px;display:flex;align-items:center;gap:14px;">'
            f'<div style="font-size:2rem;">🏆</div>'
            f'<div><div style="font-size:0.65rem;font-weight:800;text-transform:uppercase;'
            f'letter-spacing:0.1em;color:#f97316;margin-bottom:3px;">This Week\'s Pick — Locked In</div>'
            f'<div style="font-size:1.2rem;font-weight:900;color:#f1f5f9;">{picked_team}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    if avail.empty:
        _empty("📅", "No eligible games this week", f"Games with {MIN_CONF:.0f}%+ model confidence will appear here.")
        return

    st.caption(
        f"**{len(open_games)} game(s) open** · **{len(locked_games)} locked** · "
        f"Minimum {MIN_CONF:.0f}% model confidence shown · "
        f"Teams you've already used are marked"
    )
    st.write("")

    if open_games:
        _section("🟢 Open — Choose Your Survivor Pick", "#22c55e")
        for row in open_games:
            _render_game_card(row, status, already_picked, picked_game, week_id, locked=False)

    if locked_games:
        _section("🔴 Locked — Awaiting Results", "#dc2626")
        for row in locked_games:
            _render_game_card(row, status, already_picked, picked_game, week_id, locked=True)


def _render_game_card(row, status: dict, already_picked: bool, picked_game: str, week_id: str, locked: bool) -> None:
    game_id   = str(row["GameID"])
    home      = str(row.get("Home", "Home"))
    away      = str(row.get("Away", "Away"))
    cls       = str(row.get("HomeClass", "?"))
    region    = str(row.get("HomeRegion", ""))
    gender    = str(row.get("Gender", ""))
    gdate     = str(row.get("Date", ""))
    conf      = float(row.get("_conf", 0))
    tier_lbl, tier_cls = conf_tier(conf)
    model_pick, _ = get_model_pick(row)

    this_game_picked = (already_picked and picked_game == game_id)
    lock_cls         = "locked" if locked else ""
    pick_cls         = "picked" if this_game_picked else ""

    home_used = home in status["teams_used"] and not this_game_picked
    away_used = away in status["teams_used"] and not this_game_picked

    used_badge   = ""
    picked_badge = ""
    if this_game_picked:
        picked_badge = f'<div class="sv-picked-badge">✅ Your Pick</div>'
    elif home_used and away_used:
        used_badge = f'<div class="sv-used-badge">⚠️ Both Teams Used</div>'
    elif home_used:
        used_badge = f'<div class="sv-used-badge">⚠️ {home} Used</div>'
    elif away_used:
        used_badge = f'<div class="sv-used-badge">⚠️ {away} Used</div>'

    st.markdown(
        f'<div class="sv-game-card {lock_cls} {pick_cls}">{used_badge}{picked_badge}'
        f'<div class="sv-game-meta">'
        f'<span>Class {cls}</span><span>·</span><span>{region}</span>'
        f'<span>·</span><span>{gender}</span><span>·</span><span>{gdate}</span>'
        f'<span class="{"sv-danger" if locked else "sv-solid"}" style="margin-left:4px;">'
        f'{"🔒 Locked" if locked else "🟢 Open"}</span>'
        f'</div>'
        f'<div class="sv-matchup"><span>{away}</span><span class="sv-vs">@</span><span>{home}</span></div>'
        f'<div class="sv-conf-block">'
        f'<div style="font-size:0.72rem;color:#94a3b8;">🤖 Model favors <strong style="color:#fdba74;margin:0 6px;">{model_pick}</strong>'
        f'<span class="sv-conf-bar-bg"><span class="sv-conf-bar-fill" style="width:{conf:.0f}%;"></span></span>'
        f'<span style="color:#64748b;margin-left:6px;">{conf:.0f}% confident</span></div>'
        f'<span class="{tier_cls}" style="margin-left:auto;">{tier_lbl}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    if not locked and not already_picked:
        # Pick buttons for each team — grey out used teams
        b1, b2, b3 = st.columns([3, 3, 4])
        home_disabled = home in status["teams_used"]
        away_disabled = away in status["teams_used"]

        with b1:
            if st.button(
                f"{'🚫' if home_disabled else '✅'} {home}",
                key=f"sv_home_{game_id}",
                use_container_width=True,
                disabled=home_disabled,
            ):
                if save_survivor_pick(week_id, game_id, home):
                    st.success(f"🏆 Locked in **{home}** for week of {fmt_week(week_id)}!")
                    st.rerun()

        with b2:
            if st.button(
                f"{'🚫' if away_disabled else '✅'} {away}",
                key=f"sv_away_{game_id}",
                use_container_width=True,
                disabled=away_disabled,
            ):
                if save_survivor_pick(week_id, game_id, away):
                    st.success(f"🏆 Locked in **{away}** for week of {fmt_week(week_id)}!")
                    st.rerun()

    elif not locked and already_picked and this_game_picked:
        st.caption("✅ This is your pick for this week — results pending.")

    st.write("")


# ══════════════════════════════════════════════════════════════
#  TAB 2 — MY SURVIVAL LOG
# ══════════════════════════════════════════════════════════════
def render_my_log_tab(survivor_picks: pd.DataFrame) -> None:
    if not _uid:
        _signin_nudge()
        return

    my = (
        survivor_picks[survivor_picks["user_id"] == str(_uid)].copy()
        if not survivor_picks.empty and "user_id" in survivor_picks.columns
        else pd.DataFrame()
    )

    if my.empty:
        _empty("☠️", "No picks yet", "Head to the Pick tab and make your first survival pick!")
        return

    status = get_user_status(survivor_picks)

    # ── Stat strip ────────────────────────────────────────────
    scored   = my[my["actual_winner"].notna() & (my["actual_winner"].astype(str).str.strip() != "")]
    pending  = len(my) - len(scored)
    survived = int(scored["survived"].fillna(False).sum())
    losses   = int((scored["survived"] == False).sum())

    strip_html = ""
    for val, lbl, color in [
        (survived,                          "Weeks Survived",  "#22c55e"),
        (losses,                            "Losses",          "#dc2626"),
        ("✅" if not status["mulligan_used"] else "☠️ Used", "Mulligan", "#fbbf24"),
        (pending,                           "Pending",         "#475569"),
        ("🟢 Alive" if status["alive"] else "💀 Out", "Status", "#f97316"),
    ]:
        strip_html += (
            f'<div class="sv-stat">'
            f'<div class="sv-stat-val" style="color:{color};">{val}</div>'
            f'<div class="sv-stat-lbl">{lbl}</div>'
            f'</div>'
        )
    st.markdown(f'<div style="display:flex;gap:12px;margin-bottom:28px;flex-wrap:wrap;">{strip_html}</div>', unsafe_allow_html=True)

    # ── Teams used tracker ────────────────────────────────────
    _section("🚫 Teams You've Used", "#f97316")
    if status["teams_used"]:
        teams_html = "".join(
            f'<span style="background:rgba(220,38,38,0.1);border:1px solid rgba(220,38,38,0.3);'
            f'border-radius:999px;padding:4px 14px;font-size:0.75rem;font-weight:800;'
            f'color:#f87171;margin:4px;">{t}</span>'
            for t in sorted(status["teams_used"])
        )
        st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:20px;">{teams_html}</div>', unsafe_allow_html=True)
    else:
        st.caption("No teams used yet.")

    # ── Pick history ──────────────────────────────────────────
    _section("📋 My Survival History", "#f97316")

    sort_col = "week_id" if "week_id" in my.columns else my.columns[0]
    for _, row in my.sort_values(sort_col, ascending=False).iterrows():
        week    = str(row.get("week_id", ""))
        team    = str(row.get("team_picked", "?"))
        actual  = str(row.get("actual_winner", "") or "")
        surv    = row.get("survived")
        mull    = bool(row.get("mulligan_used", False))
        game_id = str(row.get("game_id", ""))

        if actual and actual not in ("", "None", "nan"):
            if surv and not mull:
                icon, card_cls = "✅", "sv-survived"
                verdict = '<span style="color:#22c55e;font-weight:900;">Survived</span>'
            elif surv and mull:
                icon, card_cls = "🟡", "sv-mulligan"
                verdict = '<span style="color:#fbbf24;font-weight:900;">Survived (Mulligan Used)</span>'
            else:
                icon, card_cls = "💀", "sv-dead"
                verdict = '<span style="color:#dc2626;font-weight:900;">Eliminated</span>'
        else:
            icon, card_cls = "⏳", "sv-pending"
            verdict = '<span style="color:#475569;font-weight:900;">Pending</span>'

        st.markdown(
            f'<div class="sv-history-card {card_cls}">'
            f'<div style="font-size:1.8rem;min-width:36px;text-align:center;">{icon}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.78rem;font-weight:800;color:#94a3b8;">{fmt_week(week)}</div>'
            f'<div style="font-size:1rem;font-weight:900;color:#f1f5f9;margin-top:2px;">{team}</div>'
            f'<div style="font-size:0.68rem;color:#475569;margin-top:2px;">Game: {game_id}</div>'
            f'</div>'
            f'<div style="text-align:right;">{verdict}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════
#  TAB 3 — LEADERBOARD
# ══════════════════════════════════════════════════════════════
def render_leaderboard_tab(survivor_picks: pd.DataFrame, display_names: dict) -> None:
    if survivor_picks.empty:
        _empty("☠️", "No survivors yet", "Be the first to make a pick!")
        return

    scored = survivor_picks[
        survivor_picks["actual_winner"].notna() &
        (survivor_picks["actual_winner"].astype(str).str.strip() != "") &
        (survivor_picks["actual_winner"].astype(str).str.strip() != "None")
    ].copy()

    # ── Who's still alive ─────────────────────────────────────
    all_users = survivor_picks["user_id"].dropna().unique().tolist()

    standings = []
    for uid in all_users:
        u_picks = survivor_picks[survivor_picks["user_id"] == uid]
        u_scored = scored[scored["user_id"] == uid]
        mulligan_used  = bool(u_picks["mulligan_used"].any())
        weeks_survived = int(u_scored["survived"].fillna(False).sum())
        losses         = u_scored[u_scored["survived"] == False]
        alive = True
        if len(losses) >= 2:
            alive = False
        elif len(losses) == 1 and mulligan_used:
            alive = False

        standings.append({
            "user_id":        uid,
            "alive":          alive,
            "weeks_survived": weeks_survived,
            "mulligan_used":  mulligan_used,
            "total_picks":    len(u_picks),
        })

    lb = pd.DataFrame(standings)
    lb = lb.sort_values(["alive", "weeks_survived"], ascending=[False, False]).reset_index(drop=True)

    alive_count = int(lb["alive"].sum())
    total_count = len(lb)

    # ── Summary banner ────────────────────────────────────────
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#052e16,#1a0000);'
        f'border:1px solid rgba(249,115,22,0.3);border-radius:16px;'
        f'padding:20px 28px;margin-bottom:24px;display:flex;align-items:center;gap:28px;">'
        f'<div style="text-align:center;min-width:80px;">'
        f'<div style="font-size:2.5rem;font-weight:900;color:#22c55e;">{alive_count}</div>'
        f'<div style="font-size:0.6rem;color:#475569;text-transform:uppercase;letter-spacing:0.1em;">Still Alive</div>'
        f'</div>'
        f'<div style="text-align:center;min-width:80px;">'
        f'<div style="font-size:2.5rem;font-weight:900;color:#dc2626;">{total_count - alive_count}</div>'
        f'<div style="font-size:0.6rem;color:#475569;text-transform:uppercase;letter-spacing:0.1em;">Eliminated</div>'
        f'</div>'
        f'<div style="text-align:center;min-width:80px;">'
        f'<div style="font-size:2.5rem;font-weight:900;color:#f97316;">{total_count}</div>'
        f'<div style="font-size:0.6rem;color:#475569;text-transform:uppercase;letter-spacing:0.1em;">Total Players</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Alive players ─────────────────────────────────────────
    alive_lb = lb[lb["alive"] == True]
    _section("🟢 Still Standing", "#22c55e")

    if alive_lb.empty:
        _empty("☠️", "Everyone's been eliminated!", "No survivors remain.")
    else:
        rows_html = ""
        for i, row in alive_lb.iterrows():
            uid   = str(row["user_id"])
            label = display_names.get(uid, f"Fan#{uid[:6]}")
            is_me = (_uid and uid == str(_uid))
            name_style = "color:#f97316;" if is_me else ""
            me_tag     = ' &nbsp;<span style="font-size:0.6rem;color:#f97316;font-weight:800;">(you)</span>' if is_me else ""
            mull_tag   = ' &nbsp;<span style="font-size:0.6rem;color:#fbbf24;">mulligan used</span>' if row["mulligan_used"] else ""

            rows_html += (
                f'<div class="sv-lb-row">'
                f'<div class="sv-lb-rank">{"🥇" if i == 0 else "🟢"}</div>'
                f'<div style="flex:1;">'
                f'<div class="sv-lb-name" style="{name_style}">{label}{me_tag}{mull_tag}</div>'
                f'<div class="sv-lb-sub">{int(row["weeks_survived"])} week(s) survived · {int(row["total_picks"])} pick(s) made</div>'
                f'</div>'
                f'<div style="text-align:center;min-width:70px;">'
                f'<div style="font-size:1.2rem;font-weight:900;color:#22c55e;">{int(row["weeks_survived"])}w</div>'
                f'<div style="font-size:0.55rem;color:#475569;text-transform:uppercase;letter-spacing:0.07em;margin-top:2px;">survived</div>'
                f'</div>'
                f'</div>'
            )
        st.markdown(f'<div class="sv-lb-card">{rows_html}</div>', unsafe_allow_html=True)

    # ── Eliminated players ────────────────────────────────────
    dead_lb = lb[lb["alive"] == False]
    if not dead_lb.empty:
        _section("💀 Eliminated", "#dc2626")
        rows_html = ""
        for _, row in dead_lb.iterrows():
            uid   = str(row["user_id"])
            label = display_names.get(uid, f"Fan#{uid[:6]}")
            is_me = (_uid and uid == str(_uid))
            name_style = "color:#f97316;" if is_me else "color:#475569;"
            me_tag     = ' &nbsp;<span style="font-size:0.6rem;color:#f97316;font-weight:800;">(you)</span>' if is_me else ""

            rows_html += (
                f'<div class="sv-lb-row" style="opacity:0.6;">'
                f'<div class="sv-lb-rank">💀</div>'
                f'<div style="flex:1;">'
                f'<div class="sv-lb-name" style="{name_style}">{label}{me_tag}</div>'
                f'<div class="sv-lb-sub">{int(row["weeks_survived"])} week(s) survived</div>'
                f'</div>'
                f'<div style="text-align:center;min-width:70px;">'
                f'<div style="font-size:1.2rem;font-weight:900;color:#475569;">{int(row["weeks_survived"])}w</div>'
                f'<div style="font-size:0.55rem;color:#475569;text-transform:uppercase;letter-spacing:0.07em;margin-top:2px;">survived</div>'
                f'</div>'
                f'</div>'
            )
        st.markdown(f'<div class="sv-lb-card">{rows_html}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
def main() -> None:
    _inject_css()
    render_logo()

    st.markdown("""
<div class="sv-hero">
  <div class="sv-hero-eyebrow">Analytics207 · Fan Challenge</div>
  <div class="sv-hero-title">☠️ Survivor</div>
  <div class="sv-hero-sub">
    One pick. One chance. No second chances — except one.
    Pick a winning team every week without repeating. One wrong pick
    and you're out. The last fan standing takes the crown.
  </div>
  <div class="sv-hero-badges">
    <span class="sv-badge">🏀 1 Pick Per Week</span>
    <span class="sv-badge">🚫 No Repeat Teams</span>
    <span class="sv-badge">☠️ Single Elimination</span>
    <span class="sv-badge">🟡 1 Mulligan</span>
    <span class="sv-badge">🏆 Last Fan Standing Wins</span>
    <span class="sv-badge">🆓 Free to Play</span>
  </div>
</div>
""", unsafe_allow_html=True)

    h1, h2, h3, h4 = st.columns(4)
    for col, icon, title, desc in [
        (h1, "🏀", "Pick 1 Team",         "Each week pick exactly one team to win their game."),
        (h2, "🚫", "No Repeats",           "Once you use a team they're gone forever. Choose wisely."),
        (h3, "☠️", "Win or Go Home",       "Your team loses = you're eliminated. One mulligan saves you once."),
        (h4, "🏆", "Last One Standing",    "Survive the most weeks to claim the Survivor crown."),
    ]:
        with col:
            st.markdown(
                f'<div class="sv-how-card">'
                f'<div class="sv-how-icon">{icon}</div>'
                f'<div class="sv-how-title">{title}</div>'
                f'<div class="sv-how-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")

    games           = load_games()
    survivor_picks  = load_survivor_picks()
    display_names   = load_display_names()

    tab1, tab2, tab3 = st.tabs([
        "🏀 Make Your Pick",
        "📋 My Survival Log",
        "🏆 Leaderboard",
    ])

    with tab1:
        render_pick_tab(games, survivor_picks)
    with tab2:
        render_my_log_tab(survivor_picks)
    with tab3:
        render_leaderboard_tab(survivor_picks, display_names)

    render_footer()


if __name__ == "__main__":
    main()
