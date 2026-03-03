# pages/XX__Team_Of_The_Week.py
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import streamlit as st

import layout as L
from components.cards_trophy import inject_trophy_card_css, render_trophy_card
from auth import login_gate, logout_button, get_supabase, get_user, SUPABASE_URL, SUPABASE_KEY

from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

# ============================================================
# Helpers
# ============================================================
def _pick(mod, *names: str) -> Optional[Callable]:
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            return fn
    return None

def _safe_str(x) -> str:
    if x is None:
        return ""
    return str(x).strip()

def _safe_float(x, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, float) and pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def _safe_int(x, default: int = 0) -> int:
    try:
        if x is None:
            return default
        if isinstance(x, float) and pd.isna(x):
            return default
        return int(float(x))
    except Exception:
        return default

def _fmt_signed(x: Optional[float], digits: int = 1) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{float(x):+.{digits}f}"

def _week_label_from_weekid(weekid: str) -> str:
    return _safe_str(weekid).replace("_to_", " → ")

def _segment_label(segment: str) -> str:
    try:
        g, c, r = segment.split("_", 2)
        return f"{g} • Class {c} • {r}"
    except Exception:
        return segment

def class_from_segment(segment: str) -> str:
    try:
        parts = str(segment).split("_")
        if len(parts) >= 2:
            return str(parts[1]).strip().upper()
    except Exception:
        pass
    return ""

# ============================================================
# Class -> Trophy variant mapping
# ============================================================
CLASS_TO_VARIANT = {
    "A": "gold",
    "B": "blue",
    "C": "green",
    "D": "red",
    "S": "red",
}

def variant_for_segment(segment: str) -> str:
    cls = class_from_segment(segment)
    return CLASS_TO_VARIANT.get(cls, "gold")

# ============================================================
# Trophy card wrapper for TOTW
# ============================================================
def render_totw_card(
    container,
    *,
    team_name: str,
    vote_share_pct: float,
    votes: int,
    weekly_score: float,
    games_n: int,
    wk_w: Optional[int],
    wk_l: Optional[int],
    avg_margin: float,
    avg_opp: float,
    avg_surprise: float,
    d_ppg: Optional[float],
    d_oppg: Optional[float],
    pill_text: str,
    variant: str,
) -> None:
    if wk_w is not None and wk_l is not None:
        sub = f"{games_n} game(s) • {wk_w}-{wk_l} this week"
    else:
        sub = f"{games_n} game(s) this week"

    sign = "+" if avg_margin >= 0 else ""
    metric = f"{sign}{avg_margin:.1f} avg margin"

    opp_str    = f"vs. {avg_opp:+.1f} rated opponents"
    sur_str    = f"beat model by {avg_surprise:+.1f} pts"
    supporting = f"{opp_str}  •  {sur_str}"

    render_trophy_card(
        container=container,
        kicker="TEAM OF THE WEEK NOMINEE",
        title=team_name,
        sub=sub,
        metric=metric,
        pill=pill_text,
        variant=variant,
        ribbon_text="VOTE TODAY",
    )

    container.caption(supporting)
    container.caption(f"WeeklyScore {weekly_score:.3f}")

# ============================================================
# Page config + layout
# ============================================================
st.set_page_config(
    page_title="🏀 Team of the Week | ANALYTICS207",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_layout  = _pick(L, "apply_global_layout_tweaks", "applygloballayouttweaks")
render_logo   = _pick(L, "render_logo", "renderlogo")
render_header = _pick(L, "render_page_header", "renderpageheader")
render_footer = _pick(L, "render_footer", "renderfooter")
spacer        = _pick(L, "spacer", "spacerlines")

def _sp(n: int = 1) -> None:
    if callable(spacer):
        try:
            spacer(n)
            return
        except Exception:
            pass
    for _ in range(max(0, int(n))):
        st.write("")

if apply_layout:
    apply_layout()
login_gate(required=False)
logout_button()

if render_logo:
    render_logo()
if render_header:
    render_header(
        title="Team of the Week",
        definition="Team of the Week (n.): A weekly spotlight with receipts. THE MODEL nominates two teams, fans pick the winner.",
        subtitle="Vote today — check back to see who takes the crown.",
    )
else:
    st.title("Team of the Week")

inject_trophy_card_css()
_sp(1)

# ─────────────────────────────────────────────
# AUTH — use session_state as single source of truth
# ─────────────────────────────────────────────
_user      = st.session_state.get("user")
_signed_in = _user is not None

# ============================================================
# Data paths
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NOMINEES_PATH = DATA / "totw" / "team_of_week_nominees_v50.parquet"

# ============================================================
# Loaders
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def load_nominees() -> pd.DataFrame:
    if not NOMINEES_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(NOMINEES_PATH).copy()
    for c in ["WeekID", "Segment", "Gender", "Class", "Region", "TeamKey", "Team"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df

def load_votes() -> pd.DataFrame:
    cols = ["Timestamp", "WeekID", "Segment", "Pick", "TeamKey"]
    try:
        sb  = get_supabase()
        res = sb.table("team_of_week_votes").select(
            "timestamp, week_id, segment, pick, team_key"
        ).execute()
        if not res.data:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(res.data).rename(columns={
            "timestamp": "Timestamp",
            "week_id":   "WeekID",
            "segment":   "Segment",
            "pick":      "Pick",
            "team_key":  "TeamKey",
        })
        return df[cols]
    except Exception:
        return pd.DataFrame(columns=cols)

def append_vote(weekid: str, segment: str, pick: str, teamkey: str) -> None:
    user    = st.session_state.get("user")
    session = st.session_state.get("session")
    if not user or not session:
        st.warning("You must be signed in to vote.")
        return
    try:
        from supabase import create_client
        # Use a fresh client with the user's JWT so RLS sees authenticated user
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        sb.postgrest.auth(session.access_token)
        sb.table("team_of_week_votes").upsert(
            {
                "week_id":  _safe_str(weekid),
                "segment":  _safe_str(segment),
                "pick":     _safe_str(pick),
                "team_key": _safe_str(teamkey),
                "user_id":  user.id,
            },
            on_conflict="week_id,segment,user_id",
        ).execute()
        st.rerun()
    except Exception as e:
        st.error(f"Vote failed: {e}")

# ============================================================
# Main UI
# ============================================================
nom = load_nominees()
if nom.empty:
    st.error("Missing/empty: data/totw/team_of_week_nominees_v50.parquet")
    if render_footer:
        _sp(2)
        render_footer()
    st.stop()

weeks = sorted([_safe_str(w) for w in nom["WeekID"].dropna().unique().tolist() if _safe_str(w)])
if not weeks:
    st.error("Nominees loaded but no WeekID values found.")
    if render_footer:
        _sp(2)
        render_footer()
    st.stop()

# ============================================================
# Filters
# ============================================================
colW, colG, colC, colR = st.columns([2, 1, 1, 1], gap="medium")

with colW:
    week_sel = st.selectbox("Week", options=weeks, index=len(weeks) - 1)
    st.caption(_week_label_from_weekid(week_sel))

with colG:
    genders    = sorted(nom["Gender"].dropna().unique().tolist())
    gender_sel = st.selectbox("Gender", options=["All"] + genders)

with colC:
    classes   = sorted(nom["Class"].dropna().unique().tolist())
    class_sel = st.selectbox("Class", options=["All"] + classes)

with colR:
    regions    = sorted(nom["Region"].dropna().unique().tolist())
    region_sel = st.selectbox("Region", options=["All"] + regions)

d = nom[nom["WeekID"] == week_sel].copy()
if gender_sel != "All":
    d = d[d["Gender"] == gender_sel]
if class_sel != "All":
    d = d[d["Class"] == class_sel]
if region_sel != "All":
    d = d[d["Region"] == region_sel]

segments = sorted([_safe_str(s) for s in d["Segment"].dropna().unique().tolist() if _safe_str(s)])
if not segments:
    st.warning("No segments match your filters.")
    if render_footer:
        _sp(2)
        render_footer()
    st.stop()

votes    = load_votes()
votes_wk = votes[votes["WeekID"].astype(str) == str(week_sel)].copy()

def tally_for_segment(segment: str) -> pd.DataFrame:
    v = votes_wk[votes_wk["Segment"].astype(str) == str(segment)].copy()
    if v.empty:
        return pd.DataFrame({"TeamKey": [], "Votes": []})
    return v.groupby("TeamKey", dropna=False).size().reset_index(name="Votes")

st.divider()

# ============================================================
# Matchup renderer
# ============================================================
def render_matchup(segment: str) -> None:
    seg = d[d["Segment"] == segment].copy()
    if seg.empty:
        return

    if "RankInSegment" not in seg.columns:
        seg = seg.sort_values("WeeklyScore", ascending=False).copy()
        seg["RankInSegment"] = range(1, len(seg) + 1)

    seg = seg.sort_values("RankInSegment")
    if len(seg) < 2:
        return

    a = seg.iloc[0].to_dict()
    b = seg.iloc[1].to_dict()

    teamA_key, teamA = _safe_str(a.get("TeamKey")), _safe_str(a.get("Team"))
    teamB_key, teamB = _safe_str(b.get("TeamKey")), _safe_str(b.get("Team"))

    tally  = tally_for_segment(segment)
    votesA = int(tally.loc[tally["TeamKey"] == teamA_key, "Votes"].iloc[0]) if (tally["TeamKey"] == teamA_key).any() else 0
    votesB = int(tally.loc[tally["TeamKey"] == teamB_key, "Votes"].iloc[0]) if (tally["TeamKey"] == teamB_key).any() else 0
    total  = votesA + votesB
    pctA   = (votesA / total * 100.0) if total > 0 else 0.0
    pctB   = (votesB / total * 100.0) if total > 0 else 0.0

    st.subheader(_segment_label(segment))

    variant   = variant_for_segment(segment)
    pill_text = _segment_label(segment)

    left, right = st.columns(2, gap="large")

    with left:
        render_totw_card(
            left,
            team_name=teamA or "Nominee A",
            vote_share_pct=pctA,
            votes=votesA,
            weekly_score=_safe_float(a.get("WeeklyScore")),
            games_n=_safe_int(a.get("Games")),
            wk_w=_safe_int(a.get("Wins")) if "Wins" in a else None,
            wk_l=_safe_int(a.get("Losses")) if "Losses" in a else None,
            avg_margin=_safe_float(a.get("AvgMargin")),
            avg_opp=_safe_float(a.get("AvgOppRating")),
            avg_surprise=_safe_float(a.get("AvgSurprise")),
            d_ppg=None,
            d_oppg=None,
            pill_text=pill_text,
            variant=variant,
        )
        if _signed_in:
            if st.button(f"Vote: {teamA}", key=f"voteA_{segment}", use_container_width=True, disabled=(teamA_key == "")):
                append_vote(week_sel, segment, "A", teamA_key)
        else:
            st.info("🔑 Sign in to vote.")
        if total > 0:
            st.progress(int(pctA), text=f"{votesA} vote(s) — {pctA:.0f}%")
        else:
            st.caption("No votes yet")

    with right:
        render_totw_card(
            right,
            team_name=teamB or "Nominee B",
            vote_share_pct=pctB,
            votes=votesB,
            weekly_score=_safe_float(b.get("WeeklyScore")),
            games_n=_safe_int(b.get("Games")),
            wk_w=_safe_int(b.get("Wins")) if "Wins" in b else None,
            wk_l=_safe_int(b.get("Losses")) if "Losses" in b else None,
            avg_margin=_safe_float(b.get("AvgMargin")),
            avg_opp=_safe_float(b.get("AvgOppRating")),
            avg_surprise=_safe_float(b.get("AvgSurprise")),
            d_ppg=None,
            d_oppg=None,
            pill_text=pill_text,
            variant=variant,
        )
        if _signed_in:
            if st.button(f"Vote: {teamB}", key=f"voteB_{segment}", use_container_width=True, disabled=(teamB_key == "")):
                append_vote(week_sel, segment, "B", teamB_key)
        else:
            st.info("🔑 Sign in to vote.")
        if total > 0:
            st.progress(int(pctB), text=f"{votesB} vote(s) — {pctB:.0f}%")
        else:
            st.caption("No votes yet")

    st.divider()

for seg in segments:
    render_matchup(seg)

# ============================================================
# Past winners
# ============================================================
st.subheader("Past winners")

votes_all = load_votes()
nom_all   = load_nominees()

if votes_all.empty:
    st.info("No votes recorded yet.")
else:
    tally_all = (
        votes_all.groupby(["WeekID", "Segment", "TeamKey"], dropna=False)
        .size()
        .reset_index(name="Votes")
    )

    nom_key   = nom_all[["WeekID", "Segment", "TeamKey", "Team", "Gender", "Class", "Region"]].drop_duplicates()
    tally_all = tally_all.merge(nom_key, on=["WeekID", "Segment", "TeamKey"], how="left")

    if gender_sel != "All":
        tally_all = tally_all[tally_all["Gender"] == gender_sel]
    if class_sel != "All":
        tally_all = tally_all[tally_all["Class"] == class_sel]
    if region_sel != "All":
        tally_all = tally_all[tally_all["Region"] == region_sel]

    if tally_all.empty:
        st.info("No past winners for the selected filters yet.")
    else:
        tally_all = tally_all.sort_values(["WeekID", "Segment", "Votes"], ascending=[False, True, False])
        winners   = (
            tally_all.groupby(["WeekID", "Segment"], dropna=False)
            .head(1)
            .copy()
        )

        winners["Week"]    = winners["WeekID"].apply(_week_label_from_weekid)
        winners["Segment"] = winners["Segment"].apply(_segment_label)

        st.dataframe(
            winners[["Week", "Segment", "Team", "Votes"]].rename(columns={"Team": "Winner"}),
            use_container_width=True,
            hide_index=True,
        )

_sp(2)
if render_footer:
    render_footer()
else:
    st.caption("© 2026 Analytics207")
