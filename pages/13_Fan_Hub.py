# pages/XX__Fan_Hub.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from layout import apply_global_layout_tweaks, render_logo, render_footer
from auth import login_gate, logout_button, get_supabase
from sidebar_auth import render_sidebar_auth

st.set_page_config(
    page_title="🏟️ Fan Hub | Analytics207",
    page_icon="🏟️",
    layout="wide",
)

render_sidebar_auth()
apply_global_layout_tweaks()
login_gate(required=False)
logout_button()

_user      = st.session_state.get("user")
_uid       = _user.id if _user else None
_signed_in = _user is not None

ROOT     = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
NOMINEES_PATH       = DATA_DIR / "totw" / "team_of_week_nominees_v50.parquet"
WEEKLY_WINNERS_FILE = DATA_DIR / "pick5" / "pick5_weekly_winners_v50.parquet"

MIN_PICKS_LEADERBOARD = 10

SUPABASE_URL      = "https://lofxbafahfogptdkjhhv.supabase.co"
import os as _os
SUPABASE_ANON_KEY = _os.environ.get("SUPABASE_ANON_KEY", "")

@st.cache_resource
def _get_sb():
    from supabase import create_client
    import streamlit as _st
    key = SUPABASE_ANON_KEY or _st.secrets.get("SUPABASE_KEY", "")
    return create_client(SUPABASE_URL, key)


# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
def _inject_css() -> None:
    st.markdown("""
<style>
.fh-hero {
    background: linear-gradient(135deg, #0a0a0a, #0f172a);
    border-top: 4px solid transparent;
    border-image: linear-gradient(90deg, #f43f5e, #f97316, #facc15, #4ade80, #60a5fa) 1;
    border-radius: 20px;
    padding: 40px 44px 32px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.fh-hero::before {
    content: "🏟️";
    position: absolute; right: 40px; top: 50%;
    transform: translateY(-50%);
    font-size: 9rem; opacity: 0.04;
}
.fh-hero-eyebrow {
    font-size: 0.7rem; font-weight: 800;
    background: linear-gradient(90deg, #f43f5e, #f97316, #facc15, #4ade80, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-transform: uppercase; letter-spacing: 0.18em; margin-bottom: 8px;
}
.fh-hero-title {
    font-size: 2.8rem; font-weight: 900;
    background: linear-gradient(90deg, #f43f5e, #f97316, #facc15, #4ade80, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1.05; margin-bottom: 10px;
}
.fh-hero-sub {
    font-size: 0.92rem; color: #94a3b8; max-width: 580px;
}
.fh-pill {
    background: #0f172a;
    border-radius: 14px; padding: 18px 20px; text-align: center;
}
.fh-pill-val { font-size: 2.2rem; font-weight: 900; line-height: 1; }
.fh-pill-lbl {
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; margin-top: 5px; color: #475569;
}
.fh-section {
    font-size: 0.7rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.14em; padding-bottom: 8px;
    border-bottom: 2px solid; margin: 32px 0 18px;
}
.fh-lb-card { background: #0a0f1e; border-radius: 14px; overflow: hidden; margin-bottom: 8px; }
.fh-lb-row {
    display: flex; align-items: center; gap: 14px;
    padding: 14px 18px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.fh-lb-row:last-child { border-bottom: none; }
.fh-lb-rank { font-size: 1.4rem; font-weight: 900; min-width: 36px; text-align: center; }
.fh-lb-name { font-size: 0.95rem; font-weight: 800; color: #f1f5f9; flex: 1; }
.fh-lb-sub  { font-size: 0.72rem; color: #475569; margin-top: 2px; }
.fh-lb-pts  { font-size: 1.15rem; font-weight: 900; text-align: right; }
.fh-vote-wrap {
    background: #0a0f1e; border-left: 3px solid #f43f5e;
    border-radius: 0 12px 12px 0; padding: 16px 20px; margin-bottom: 10px;
}
.fh-vote-teams {
    display: flex; justify-content: space-between;
    font-size: 0.85rem; font-weight: 800; color: #e2e8f0; margin-bottom: 8px;
}
.fh-vote-bar-bg {
    background: rgba(255,255,255,0.05); border-radius: 999px;
    height: 10px; width: 100%; overflow: hidden; margin-bottom: 6px;
}
.fh-vote-bar-fill {
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, #f43f5e, #f97316);
}
.fh-vote-pcts { display: flex; justify-content: space-between; font-size: 0.68rem; color: #475569; }
.fh-ms-card {
    background: #0a0f1e; border-left: 3px solid #facc15;
    border-radius: 0 12px 12px 0; padding: 16px 20px; margin-bottom: 8px;
    display: flex; align-items: center; gap: 16px;
}
.fh-ms-icon  { font-size: 2rem; }
.fh-ms-body  { flex: 1; }
.fh-ms-title { font-size: 0.92rem; font-weight: 800; color: #fef3c7; }
.fh-ms-sub   { font-size: 0.72rem; color: #475569; margin-top: 3px; }
.fh-ms-badge {
    background: rgba(250,204,21,0.1); border: 1px solid rgba(250,204,21,0.35);
    border-radius: 999px; padding: 3px 12px;
    font-size: 0.65rem; font-weight: 800; color: #facc15;
    text-transform: uppercase; letter-spacing: 0.07em;
}
.fh-p5-card {
    border-radius: 14px; padding: 20px 24px; margin-bottom: 10px;
    position: relative; overflow: hidden;
}
.fh-p5-card::before {
    content: "💎"; position: absolute; right: 16px; top: 50%;
    transform: translateY(-50%); font-size: 4rem; opacity: 0.06;
}
.fh-p5-name  { font-size: 1.1rem; font-weight: 900; color: #f1f5f9; }
.fh-p5-week  { font-size: 0.7rem; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
.fh-p5-pts   { font-size: 2rem; font-weight: 900; }
.fh-p5-picks { font-size: 0.72rem; color: #64748b; margin-top: 6px; }
.fh-coming {
    background: #0a0f1e; border: 1px dashed rgba(255,255,255,0.07);
    border-radius: 14px; padding: 40px; text-align: center;
}
.fh-coming-icon  { font-size: 3rem; margin-bottom: 10px; }
.fh-coming-title { font-size: 1rem; font-weight: 800; color: #334155; }
.fh-coming-sub   { font-size: 0.78rem; color: #1e293b; margin-top: 4px; }
.fvm-vs-model-badge {
    padding: 4px 12px; border-radius: 999px;
    font-size: 0.65rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.07em;
}
.badge-beating { background: rgba(52,211,153,0.12);  border: 1px solid rgba(52,211,153,0.3);  color: #34d399; }
.badge-losing  { background: rgba(248,113,113,0.12); border: 1px solid rgba(248,113,113,0.3); color: #f87171; }
.badge-tied    { background: rgba(148,163,184,0.12); border: 1px solid rgba(148,163,184,0.3); color: #94a3b8; }

/* ── Stump The Model styles ── */
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
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  DATA LOADERS
# ══════════════════════════════════════════════════════════════

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




def load_totw_votes() -> pd.DataFrame:
    try:
        sb  = _get_sb()
        res = sb.table("team_of_week_votes").select("week_id,segment,team_key,user_id").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"TOTW votes load error: {e}")
        return pd.DataFrame()


def load_totw_nominees() -> pd.DataFrame:
    if not NOMINEES_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(NOMINEES_PATH).copy()
        for c in ["WeekID", "Segment", "TeamKey", "Team"]:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame()


def load_milestone_claims() -> pd.DataFrame:
    try:
        sb  = _get_sb()
        res = sb.table("milestone_claims").select("claim_id,school,submitted_by,submitted_at,category_id").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"Milestone claims load error: {e}")
        return pd.DataFrame()


def load_milestone_votes() -> pd.DataFrame:
    try:
        sb  = _get_sb()
        res = sb.table("milestone_votes").select("claim_id,vote,user_id").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"Milestone votes load error: {e}")
        return pd.DataFrame()


def load_pick5_rosters() -> pd.DataFrame:
    try:
        sb  = _get_sb()
        res = sb.table("pick_5_rosters").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"Pick 5 rosters load error: {e}")
        return pd.DataFrame()


def load_fan_picks() -> pd.DataFrame:
    try:
        sb  = _get_sb()
        res = sb.table("fan_picks").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"Fan picks load error: {e}")
        return pd.DataFrame()


def load_stump_picks() -> pd.DataFrame:
    try:
        sb  = _get_sb()
        res = sb.table("stump_picks").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            if "stumped"       in df.columns: df["stumped"]       = df["stumped"].fillna(False).astype(bool)
            if "points_earned" in df.columns: df["points_earned"] = pd.to_numeric(df["points_earned"], errors="coerce").fillna(0)
            if "model_conf"    in df.columns: df["model_conf"]    = pd.to_numeric(df["model_conf"],    errors="coerce").fillna(0)
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


# ══════════════════════════════════════════════════════════════
#  WEEK HELPERS
# ══════════════════════════════════════════════════════════════
def week_bounds(anchor) -> tuple[pd.Timestamp, pd.Timestamp]:
    anchor = pd.Timestamp(anchor).normalize()
    sunday = anchor - pd.Timedelta(days=(anchor.weekday() + 1) % 7)
    return sunday, sunday + pd.Timedelta(days=6)


def fmt_week(d) -> str:
    s, e = week_bounds(d)
    return f"{s.strftime('%b %d')} – {e.strftime('%b %d, %Y')}"


# ══════════════════════════════════════════════════════════════
#  RENDER HELPERS
# ══════════════════════════════════════════════════════════════
RANK_ICONS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
P5_COLORS  = ["#fbbf24", "#94a3b8", "#cd7c2f"]


def _pill(val, lbl, color: str) -> str:
    return (
        f'<div class="fh-pill">'
        f'<div class="fh-pill-val" style="color:{color};">{val}</div>'
        f'<div class="fh-pill-lbl">{lbl}</div>'
        f'</div>'
    )


def _section(title: str, color: str) -> None:
    st.markdown(
        f'<div class="fh-section" style="color:{color};border-color:{color}40;">{title}</div>',
        unsafe_allow_html=True,
    )


def _coming_soon(icon: str, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="fh-coming">'
        f'<div class="fh-coming-icon">{icon}</div>'
        f'<div class="fh-coming-title">{title}</div>'
        f'<div class="fh-coming-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _model_on_fan_games(all_picks: pd.DataFrame) -> tuple[int, int, float]:
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


# ══════════════════════════════════════════════════════════════
#  TAB 1 — COMMUNITY DASHBOARD
# ══════════════════════════════════════════════════════════════
def render_community_tab(
    totw_votes: pd.DataFrame,
    ms_claims: pd.DataFrame,
    ms_votes: pd.DataFrame,
    p5: pd.DataFrame,
    fan_picks: pd.DataFrame,
    stump_picks: pd.DataFrame,
) -> None:
    total_voters      = totw_votes["user_id"].nunique()  if not totw_votes.empty  and "user_id" in totw_votes.columns  else 0
    total_votes       = len(totw_votes)
    total_claims      = len(ms_claims)
    total_p5_players  = p5["Manager"].nunique()          if not p5.empty          and "Manager" in p5.columns          else 0
    total_fan_pickers = fan_picks["user_id"].nunique()   if not fan_picks.empty   and "user_id" in fan_picks.columns   else 0
    total_stumpers    = stump_picks["user_id"].nunique() if not stump_picks.empty and "user_id" in stump_picks.columns else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, val, lbl, color in [
        (c1, total_voters,       "TOTW Voters",       "#a78bfa"),
        (c2, total_votes,        "Total Votes Cast",  "#f9a8d4"),
        (c3, total_claims,       "Milestones Filed",  "#fbbf24"),
        (c4, total_p5_players,   "Pick 5 Players",    "#4ade80"),
        (c5, total_fan_pickers,  "Fan vs Model",      "#67e8f9"),
        (c6, total_stumpers,     "Stump Players",     "#c4b5fd"),
    ]:
        with col:
            st.markdown(_pill(val, lbl, color), unsafe_allow_html=True)

    st.write("")
    left, right = st.columns(2, gap="large")

    with left:
        _section("💎 Pick 5 Season Leaderboard", "#a78bfa")
        if p5.empty or "Manager" not in p5.columns:
            _coming_soon("💎", "No picks yet", "Season standings will appear here once picks are submitted.")
        else:
            p5["Pts"] = pd.to_numeric(p5.get("ActualPts", pd.Series(dtype=str)), errors="coerce").fillna(0)
            season_lb = (
                p5.groupby("Manager", dropna=False)
                .agg(TotalPts=("Pts", "sum"), Weeks=("WeekID", "nunique"), Picks=("Class", "count"))
                .reset_index()
                .sort_values("TotalPts", ascending=False)
                .reset_index(drop=True)
                .head(5)
            )
            rows_html = ""
            for i, row in season_lb.iterrows():
                icon  = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
                color = ["#fbbf24", "#94a3b8", "#cd7c2f", "#64748b", "#64748b"][i] if i < 5 else "#64748b"
                rows_html += (
                    f'<div class="fh-lb-row">'
                    f'<div class="fh-lb-rank">{icon}</div>'
                    f'<div style="flex:1;">'
                    f'<div class="fh-lb-name">{row["Manager"]}</div>'
                    f'<div class="fh-lb-sub">{int(row["Weeks"])} week(s) · {int(row["Picks"])} picks</div>'
                    f'</div>'
                    f'<div class="fh-lb-pts" style="color:{color};">+{int(row["TotalPts"])}</div>'
                    f'</div>'
                )
            st.markdown(f'<div class="fh-lb-card">{rows_html}</div>', unsafe_allow_html=True)

    with right:
        _section("🏆 Top Milestone Contributors", "#fbbf24")
        if ms_claims.empty or "submitted_by" not in ms_claims.columns:
            _coming_soon("🏆", "No milestones yet", "Top submitters will appear here once records are filed.")
        else:
            contrib = (
                ms_claims.groupby("submitted_by", dropna=False)
                .size().reset_index(name="Submitted")
                .sort_values("Submitted", ascending=False)
                .head(5)
            )
            rows_html = ""
            for i, row in contrib.iterrows():
                icon  = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
                color = ["#fbbf24", "#94a3b8", "#cd7c2f", "#64748b", "#64748b"][i] if i < 5 else "#64748b"
                name  = str(row["submitted_by"]).split("@")[0] if "@" in str(row["submitted_by"]) else str(row["submitted_by"])
                rows_html += (
                    f'<div class="fh-lb-row">'
                    f'<div class="fh-lb-rank">{icon}</div>'
                    f'<div style="flex:1;">'
                    f'<div class="fh-lb-name">{name}</div>'
                    f'<div class="fh-lb-sub">{int(row["Submitted"])} milestone(s) submitted</div>'
                    f'</div>'
                    f'<div class="fh-lb-pts" style="color:{color};">{int(row["Submitted"])}</div>'
                    f'</div>'
                )
            st.markdown(f'<div class="fh-lb-card">{rows_html}</div>', unsafe_allow_html=True)

    _section("🗳️ Most Active TOTW Voters", "#f9a8d4")
    if totw_votes.empty or "user_id" not in totw_votes.columns:
        _coming_soon("🗳️", "No votes yet", "Most active voters will appear here.")
    else:
        voter_lb = (
            totw_votes[totw_votes["user_id"].notna()]
            .groupby("user_id", dropna=False)
            .size().reset_index(name="Votes")
            .sort_values("Votes", ascending=False)
            .head(5)
        )
        if voter_lb.empty:
            _coming_soon("🗳️", "No logged-in voters yet", "Sign-in votes will appear here.")
        else:
            cols = st.columns(min(5, len(voter_lb)))
            for col, (_, row) in zip(cols, voter_lb.iterrows()):
                uid   = str(row["user_id"])
                label = uid[:8] + "…" if len(uid) > 10 else uid
                with col:
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#1e1b4b,#1e293b);'
                        f'border:1px solid rgba(249,168,212,0.25);border-radius:12px;'
                        f'padding:16px;text-align:center;">'
                        f'<div style="font-size:1.8rem;font-weight:900;color:#f9a8d4;">{int(row["Votes"])}</div>'
                        f'<div style="font-size:0.62rem;color:#64748b;text-transform:uppercase;'
                        f'letter-spacing:0.08em;margin-top:4px;">votes</div>'
                        f'<div style="font-size:0.72rem;color:#94a3b8;margin-top:6px;">{label}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )


# ══════════════════════════════════════════════════════════════
#  TAB 2 — TEAM OF THE WEEK
# ══════════════════════════════════════════════════════════════
def render_totw_tab(totw_votes: pd.DataFrame, nominees: pd.DataFrame) -> None:
    today   = pd.Timestamp(datetime.today().date())
    ws, we  = week_bounds(today)
    week_id = f"{ws.strftime('%Y-%m-%d')}_to_{we.strftime('%Y-%m-%d')}"

    _section("🗳️ Current Week Vote Totals", "#f9a8d4")

    if totw_votes.empty:
        _coming_soon("🗳️", "No votes yet this week", "Votes will appear here in real time.")
        return

    wk_votes = (
        totw_votes[totw_votes["week_id"].astype(str) == week_id].copy()
        if "week_id" in totw_votes.columns
        else pd.DataFrame()
    )

    if wk_votes.empty:
        _coming_soon("🗳️", "No votes this week yet", f"Week of {fmt_week(today)}")
    else:
        tally = (
            wk_votes.groupby(["segment", "team_key"], dropna=False)
            .size().reset_index(name="Votes")
        )
        nom_key = (
            nominees[["WeekID", "Segment", "TeamKey", "Team"]].drop_duplicates()
            if not nominees.empty else pd.DataFrame()
        )

        for seg in sorted(tally["segment"].unique()):
            seg_tally = tally[tally["segment"] == seg]
            teams = seg_tally.set_index("team_key")["Votes"].to_dict()
            total = sum(teams.values())
            if total == 0:
                continue

            team_names = {}
            if not nom_key.empty:
                for tk in teams:
                    match = nom_key[
                        (nom_key["Segment"].astype(str) == seg) &
                        (nom_key["TeamKey"].astype(str) == str(tk))
                    ]
                    team_names[tk] = match["Team"].iloc[0] if not match.empty else tk
            else:
                team_names = {tk: tk for tk in teams}

            items = sorted(teams.items(), key=lambda x: -x[1])

            if len(items) >= 2:
                (tk_a, va), (tk_b, vb) = items[0], items[1]
                pct_a  = va / total * 100
                pct_b  = vb / total * 100
                name_a = team_names.get(tk_a, tk_a)
                name_b = team_names.get(tk_b, tk_b)
                st.markdown(
                    f'<div class="fh-vote-wrap">'
                    f'<div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;'
                    f'letter-spacing:0.1em;margin-bottom:8px;">{seg}</div>'
                    f'<div class="fh-vote-teams"><span>{name_a}</span><span>{name_b}</span></div>'
                    f'<div class="fh-vote-bar-bg">'
                    f'<div class="fh-vote-bar-fill" style="width:{pct_a:.0f}%;"></div>'
                    f'</div>'
                    f'<div class="fh-vote-pcts">'
                    f'<span>{va} vote(s) — {pct_a:.0f}%</span>'
                    f'<span>{vb} vote(s) — {pct_b:.0f}%</span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                (tk_a, va) = items[0]
                name_a = team_names.get(tk_a, tk_a)
                st.markdown(
                    f'<div class="fh-vote-wrap">'
                    f'<div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;'
                    f'letter-spacing:0.1em;margin-bottom:8px;">{seg}</div>'
                    f'<div class="fh-vote-teams"><span>{name_a}</span>'
                    f'<span style="color:#475569;">No other votes</span></div>'
                    f'<div class="fh-vote-bar-bg">'
                    f'<div class="fh-vote-bar-fill" style="width:100%;"></div>'
                    f'</div>'
                    f'<div class="fh-vote-pcts"><span>{va} vote(s) — 100%</span><span>—</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    _section("📊 All-Time Vote Totals by Team", "#a78bfa")
    if not totw_votes.empty and "team_key" in totw_votes.columns:
        all_tally = (
            totw_votes.groupby("team_key", dropna=False)
            .size().reset_index(name="TotalVotes")
            .sort_values("TotalVotes", ascending=False)
            .head(10)
        )
        nom_key = nominees[["TeamKey", "Team"]].drop_duplicates() if not nominees.empty else pd.DataFrame()
        if not nom_key.empty:
            all_tally = all_tally.merge(
                nom_key.rename(columns={"TeamKey": "team_key"}), on="team_key", how="left"
            )
            all_tally["Team"] = all_tally.get("Team", all_tally["team_key"]).fillna(all_tally["team_key"])
        else:
            all_tally["Team"] = all_tally["team_key"]

        rows_html = ""
        for i, row in all_tally.iterrows():
            icon = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
            rows_html += (
                f'<div class="fh-lb-row">'
                f'<div class="fh-lb-rank">{icon}</div>'
                f'<div class="fh-lb-name" style="flex:1;">{row["Team"]}</div>'
                f'<div class="fh-lb-pts" style="color:#a78bfa;">🗳️ {int(row["TotalVotes"])}</div>'
                f'</div>'
            )
        st.markdown(f'<div class="fh-lb-card">{rows_html}</div>', unsafe_allow_html=True)
    else:
        _coming_soon("📊", "No vote data yet", "All-time totals will appear here.")


# ══════════════════════════════════════════════════════════════
#  TAB 3 — PICK 5 HALL OF FAME
# ══════════════════════════════════════════════════════════════
def render_pick5_tab(p5: pd.DataFrame) -> None:
    today   = pd.Timestamp(datetime.today().date())
    ws, we  = week_bounds(today)
    week_id = f"{ws.strftime('%Y-%m-%d')}_to_{we.strftime('%Y-%m-%d')}"

    _section("💎 This Week's Picks", "#4ade80")

    if p5.empty or "WeekID" not in p5.columns:
        _coming_soon("💎", "No picks submitted yet", "Be the first to lock in your picks!")
    else:
        p5["Pts"] = pd.to_numeric(p5.get("ActualPts", pd.Series(dtype=str)), errors="coerce").fillna(0)
        wk = p5[p5["WeekID"].astype(str) == week_id].copy()

        if wk.empty:
            _coming_soon("💎", "No picks this week yet", f"Week of {fmt_week(today)}")
        else:
            lb = (
                wk.groupby("Manager", dropna=False)
                .agg(TotalPts=("Pts", "sum"), Picks=("Class", "count"))
                .reset_index()
                .sort_values("TotalPts", ascending=False)
                .reset_index(drop=True)
                .head(3)
            )
            cols = st.columns(min(3, len(lb)))
            for col, (i, row) in zip(cols, lb.iterrows()):
                gradient  = ["linear-gradient(135deg,#1a1a2e,#2d1b69)", "linear-gradient(135deg,#1a1a2e,#1e293b)", "linear-gradient(135deg,#1a1a2e,#1e293b)"][i]
                pts_color = P5_COLORS[i] if i < 3 else "#64748b"
                icon      = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
                mgr_picks = wk[wk["Manager"] == row["Manager"]]
                picks_str = " · ".join(
                    f'{r["Class"]}: {r.get("Pick", "?")}'
                    for _, r in mgr_picks.iterrows()
                    if pd.notna(r.get("Pick"))
                )
                with col:
                    st.markdown(
                        f'<div class="fh-p5-card" style="background:{gradient};'
                        f'border:1px solid rgba(255,255,255,0.08);">'
                        f'<div class="fh-p5-week">{fmt_week(today)} {icon}</div>'
                        f'<div class="fh-p5-name">{row["Manager"]}</div>'
                        f'<div class="fh-p5-pts" style="color:{pts_color};">+{int(row["TotalPts"])} pts</div>'
                        f'<div class="fh-p5-picks">{picks_str}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    _section("🏆 Season Leaderboard", "#fbbf24")
    if p5.empty or "Manager" not in p5.columns:
        _coming_soon("🏆", "Season standings coming soon", "Submit weekly picks to appear here.")
    else:
        p5["Pts"] = pd.to_numeric(p5.get("ActualPts", pd.Series(dtype=str)), errors="coerce").fillna(0)
        season = (
            p5.groupby("Manager", dropna=False)
            .agg(TotalPts=("Pts", "sum"), Weeks=("WeekID", "nunique"), Picks=("Class", "count"))
            .reset_index()
            .sort_values("TotalPts", ascending=False)
            .reset_index(drop=True)
        )
        rows_html = ""
        for i, row in season.iterrows():
            icon  = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
            color = P5_COLORS[i] if i < 3 else "#64748b"
            rows_html += (
                f'<div class="fh-lb-row">'
                f'<div class="fh-lb-rank">{icon}</div>'
                f'<div style="flex:1;">'
                f'<div class="fh-lb-name">{row["Manager"]}</div>'
                f'<div class="fh-lb-sub">{int(row["Weeks"])} week(s) · {int(row["Picks"])} total picks</div>'
                f'</div>'
                f'<div class="fh-lb-pts" style="color:{color};">+{int(row["TotalPts"])}</div>'
                f'</div>'
            )
        st.markdown(f'<div class="fh-lb-card">{rows_html}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  TAB 4 — MILESTONES SPOTLIGHT
# ══════════════════════════════════════════════════════════════
def render_milestones_tab(ms_claims: pd.DataFrame, ms_votes: pd.DataFrame) -> None:
    _section("🏅 Recent Submissions", "#fbbf24")

    if ms_claims.empty:
        _coming_soon("🏆", "No milestones filed yet", "Be the first to submit a record!")
        return

    recent = (
        ms_claims.sort_values("submitted_at", ascending=False).head(6)
        if "submitted_at" in ms_claims.columns
        else ms_claims.head(6)
    )

    CAT_ICONS = {
        "1000_point_scorer": "🏀", "state_championship": "🥇",
        "regional_championship": "🏆", "single_game_record": "🔥",
        "season_wins_record": "📈", "win_streak": "⚡",
        "undefeated_season": "💎", "coach_milestone": "🎓",
    }
    CAT_LABELS = {
        "1000_point_scorer": "1,000-Point Scorer", "state_championship": "State Championship",
        "regional_championship": "Regional Championship", "single_game_record": "Single-Game Record",
        "season_wins_record": "Season Wins Record", "win_streak": "Win Streak",
        "undefeated_season": "Undefeated Season", "coach_milestone": "Coach Milestone",
    }

    if not ms_votes.empty and "claim_id" in ms_votes.columns:
        vote_counts = ms_votes.groupby("claim_id").size().reset_index(name="VoteCount")
    else:
        vote_counts = pd.DataFrame(columns=["claim_id", "VoteCount"])

    for _, row in recent.iterrows():
        cat    = str(row.get("category_id", ""))
        icon   = CAT_ICONS.get(cat, "🏅")
        lbl    = CAT_LABELS.get(cat, cat)
        school = str(row.get("school", "")).strip()
        by     = str(row.get("submitted_by", "")).split("@")[0]
        cid    = str(row.get("claim_id", ""))
        vc     = int(vote_counts.loc[vote_counts["claim_id"] == cid, "VoteCount"].iloc[0]) if cid in vote_counts["claim_id"].values else 0

        st.markdown(
            f'<div class="fh-ms-card">'
            f'<div class="fh-ms-icon">{icon}</div>'
            f'<div class="fh-ms-body">'
            f'<div class="fh-ms-title">{school} — {lbl}</div>'
            f'<div class="fh-ms-sub">Submitted by {by} · {vc} community vote(s)</div>'
            f'</div>'
            f'<div class="fh-ms-badge">🕐 Pending</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _section("📊 Submissions by School", "#fbbf24")
    if "school" in ms_claims.columns:
        school_counts = (
            ms_claims.groupby("school", dropna=False)
            .size().reset_index(name="Count")
            .sort_values("Count", ascending=False)
            .head(8)
        )
        rows_html = ""
        for i, row in school_counts.iterrows():
            icon = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
            rows_html += (
                f'<div class="fh-lb-row">'
                f'<div class="fh-lb-rank">{icon}</div>'
                f'<div class="fh-lb-name" style="flex:1;">{row["school"]}</div>'
                f'<div class="fh-lb-pts" style="color:#fbbf24;">{int(row["Count"])} claim(s)</div>'
                f'</div>'
            )
        st.markdown(f'<div class="fh-lb-card">{rows_html}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  TAB 5 — FAN vs MODEL
# ══════════════════════════════════════════════════════════════
def render_fan_vs_model_tab(fan_picks: pd.DataFrame, display_names: dict) -> None:
    if fan_picks.empty:
        _coming_soon("🤖", "No picks yet", "Be the first to submit picks and claim the top spot!")
        return

    scored = fan_picks[
        fan_picks["actual_winner"].notna() &
        (fan_picks["actual_winner"] != "") &
        (fan_picks["actual_winner"] != "None")
    ].copy()

    if scored.empty:
        _coming_soon("⏳", "No results yet", "Check back after games finish tonight.")
        return

    scored["fan_correct"]   = scored["fan_correct"].fillna(False).astype(bool)
    scored["model_correct"] = scored["model_correct"].fillna(False).astype(bool)

    model_wins, model_losses, model_pct = _model_on_fan_games(fan_picks)
    model_total = model_wins + model_losses

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

    lb = (
        scored.groupby("user_id", dropna=False)
        .agg(Total=("fan_correct", "count"), FanWins=("fan_correct", "sum"), ModelWins=("model_correct", "sum"))
        .reset_index()
    )
    lb = lb[lb["Total"] >= MIN_PICKS_LEADERBOARD]
    lb["FanPct"] = lb["FanWins"] / lb["Total"] * 100
    lb["Edge"]   = lb["FanPct"] - model_pct
    lb = lb.sort_values("FanPct", ascending=False).reset_index(drop=True)

    if lb.empty:
        _coming_soon("⏳", f"Need {MIN_PICKS_LEADERBOARD}+ picks to appear",
                     "Keep picking — leaderboard unlocks at 10 scored picks.")
        return

    _section("🏆 Fan Leaderboard", "#fbbf24")

    rows_html = ""
    for i, row in lb.iterrows():
        icon  = RANK_ICONS[i] if i < len(RANK_ICONS) else f"#{i+1}"
        uid   = str(row["user_id"])
        label = display_names.get(uid, f"Fan#{uid[:6]}")
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
            f'<div class="fh-lb-row">'
            f'<div class="fh-lb-rank">{icon}</div>'
            f'<div style="flex:1;">'
            f'<div class="fh-lb-name" style="{name_style}">{label}{me_tag}</div>'
            f'<div class="fh-lb-sub">{int(row["Total"])} picks · '
            f'{int(row["FanWins"])}-{int(row["Total"] - row["FanWins"])}</div>'
            f'</div>'
            f'<div style="margin-right:16px;">'
            f'<span class="fvm-vs-model-badge {badge_cls}">{badge_txt}</span>'
            f'</div>'
            f'<div style="text-align:center;min-width:60px;">'
            f'<div style="font-size:1.1rem;font-weight:900;color:#67e8f9;">{row["FanPct"]:.1f}%</div>'
            f'<div style="font-size:0.55rem;color:#475569;text-transform:uppercase;letter-spacing:0.07em;margin-top:2px;">Win %</div>'
            f'</div>'
            f'</div>'
        )
    st.markdown(f'<div class="fh-lb-card">{rows_html}</div>', unsafe_allow_html=True)
    st.caption(f"Minimum {MIN_PICKS_LEADERBOARD} scored picks required · Head to 🤖 Fan vs. The Model to make picks")


# ══════════════════════════════════════════════════════════════
#  TAB 6 — STUMP THE MODEL LEADERBOARD
# ══════════════════════════════════════════════════════════════
def render_stump_leaderboard_tab(stump_picks: pd.DataFrame, display_names: dict) -> None:
    if stump_picks.empty:
        _coming_soon("🧠", "No stump attempts yet", "Be the first to challenge the model!")
        return

    scored = stump_picks[
        stump_picks["actual_winner"].notna() &
        (stump_picks["actual_winner"].astype(str).str.strip() != "") &
        (stump_picks["actual_winner"].astype(str).str.strip() != "None") &
        (stump_picks["actual_winner"].astype(str).str.strip() != "nan")
    ].copy()

    if scored.empty:
        _coming_soon("⏳", "No results yet", "Check back after tonight's games finish.")
        return

    scored["stumped"]       = scored["stumped"].fillna(False).astype(bool)
    scored["points_earned"] = pd.to_numeric(scored["points_earned"], errors="coerce").fillna(0)

    # ── Season stats strip ────────────────────────────────────
    total_stumps  = int(scored["stumped"].sum())
    total_pts     = int(scored["points_earned"].sum())
    total_attempts = len(scored)
    unique_players = scored["user_id"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl, color in [
        (c1, unique_players,  "Players",         "#a855f7"),
        (c2, total_attempts,  "Total Attempts",  "#c4b5fd"),
        (c3, total_stumps,    "Successful Stumps","#34d399"),
        (c4, total_pts,       "Points Awarded",  "#f97316"),
    ]:
        with col:
            st.markdown(_pill(val, lbl, color), unsafe_allow_html=True)

    st.write("")

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
            f'Stumped the model at {bs_conf:.0f}% confidence · Game: {bs_game}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Leaderboard ───────────────────────────────────────────
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
    lb = lb[lb["Attempts"] >= 3]
    lb = lb.sort_values(["TotalPts", "Stumps"], ascending=False).reset_index(drop=True)

    _section("🧠 Season Stump Leaderboard", "#a855f7")

    if lb.empty:
        _coming_soon("⏳", "Need 3+ scored attempts to appear", "Keep stumping to unlock your spot!")
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
    st.caption("Minimum 3 scored attempts required · Head to 🧠 Stump The Model to play")

def render_survivor_tab(survivor_picks: pd.DataFrame, display_names: dict) -> None:
    
    if survivor_picks.empty:

        _coming_soon("☠️", "No survivors yet", "Head to ☠️ Survivor to make your first pick!")
        return

    all_users = survivor_picks["user_id"].dropna().unique().tolist()
    scored    = survivor_picks[survivor_picks["survived"].notna()].copy()

    standings = []
    for uid in all_users:
        u        = survivor_picks[survivor_picks["user_id"] == uid]
        u_scored = scored[scored["user_id"] == uid]
        mull     = bool(u["mulligan_used"].any())
        survived = int(u_scored["survived"].fillna(False).sum())
        losses   = u_scored[u_scored["survived"] == False]
        alive    = True
        if len(losses) >= 2 or (len(losses) == 1 and mull):
            alive = False
        standings.append({"user_id": uid, "alive": alive, "weeks_survived": survived, "mulligan_used": mull})

    lb          = pd.DataFrame(standings).sort_values(["alive", "weeks_survived"], ascending=[False, False]).reset_index(drop=True)
    alive_count = int(lb["alive"].sum())
    total_count = len(lb)

    # ── Summary pills ─────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    for col, val, lbl, color in [
        (c1, alive_count,               "Still Alive",  "#22c55e"),
        (c2, total_count - alive_count, "Eliminated",   "#dc2626"),
        (c3, total_count,               "Total Players","#f97316"),
    ]:
        with col:
            st.markdown(_pill(val, lbl, color), unsafe_allow_html=True)

    st.write("")

    # ── Still standing ────────────────────────────────────────
    _section("🟢 Still Standing", "#22c55e")
    alive_lb = lb[lb["alive"] == True]
    if alive_lb.empty:
        _coming_soon("☠️", "Everyone's been eliminated!", "No survivors remain.")
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
                f'<div class="fh-lb-row">'
                f'<div class="fh-lb-rank">{"🥇" if i == 0 else "🟢"}</div>'
                f'<div style="flex:1;">'
                f'<div class="fh-lb-name" style="{name_style}">{label}{me_tag}{mull_tag}</div>'
                f'<div class="fh-lb-sub">{int(row["weeks_survived"])} week(s) survived</div>'
                f'</div>'
                f'<div style="font-size:1.1rem;font-weight:900;color:#22c55e;">{int(row["weeks_survived"])}w</div>'
                f'</div>'
            )
        st.markdown(f'<div class="fh-lb-card">{rows_html}</div>', unsafe_allow_html=True)

    # ── Eliminated ────────────────────────────────────────────
    dead_lb = lb[lb["alive"] == False]
    if not dead_lb.empty:
        _section("💀 Eliminated", "#dc2626")
        rows_html = ""
        for _, row in dead_lb.iterrows():
            uid   = str(row["user_id"])
            label = display_names.get(uid, f"Fan#{uid[:6]}")
            rows_html += (
                f'<div class="fh-lb-row" style="opacity:0.5;">'
                f'<div class="fh-lb-rank">💀</div>'
                f'<div style="flex:1;">'
                f'<div class="fh-lb-name" style="color:#475569;">{label}</div>'
                f'<div class="fh-lb-sub">{int(row["weeks_survived"])} week(s) survived</div>'
                f'</div>'
                f'<div style="font-size:1.1rem;font-weight:900;color:#475569;">{int(row["weeks_survived"])}w</div>'
                f'</div>'
            )
        st.markdown(f'<div class="fh-lb-card">{rows_html}</div>', unsafe_allow_html=True)

    st.caption("Head to ☠️ Survivor to make your weekly pick")

# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
def main() -> None:
    _inject_css()
    render_logo()

    st.markdown("""
<div class="fh-hero">
  <div class="fh-hero-eyebrow">Analytics207 · Community</div>
  <div class="fh-hero-title">The Fan Hub</div>
  <div class="fh-hero-sub">
    Your home for everything community — vote totals, milestone records,
    Pick 5 standings, Fan vs. Model, Stump The Model, and Survivor standings.
  </div>
</div>
""", unsafe_allow_html=True)

    totw_votes      = load_totw_votes()
    nominees        = load_totw_nominees()
    ms_claims       = load_milestone_claims()
    ms_votes        = load_milestone_votes()
    p5              = load_pick5_rosters()
    fan_picks       = load_fan_picks()
    stump_picks     = load_stump_picks()
    survivor_picks  = load_survivor_picks()
    display_names   = load_display_names()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏠 Community",
        "🗳️ Team of the Week",
        "💎 Pick 5",
        "🏆 Milestones",
        "🤖 Fan vs. Model",
        "🧠 Stump The Model",
        "☠️ Survivor",
    ])

    with tab1:
        render_community_tab(totw_votes, ms_claims, ms_votes, p5, fan_picks, stump_picks)
    with tab2:
        render_totw_tab(totw_votes, nominees)
    with tab3:
        render_pick5_tab(p5)
    with tab4:
        render_milestones_tab(ms_claims, ms_votes)
    with tab5:
        render_fan_vs_model_tab(fan_picks, display_names)
    with tab6:
        render_stump_leaderboard_tab(stump_picks, display_names)
    with tab7:
        render_survivor_tab(survivor_picks, display_names)

    render_footer()


if __name__ == "__main__":
    main()

