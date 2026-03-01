# 12__Milestones.py – Community School Records & Milestones
from __future__ import annotations
from pathlib import Path
import uuid, json
from datetime import datetime
import os

import pandas as pd
import streamlit as st

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)
from auth import login_gate, logout_button



from sidebar_auth import render_sidebar_auth

render_sidebar_auth()



st.set_page_config(
    page_title="🏆 Milestones & Records | Analytics207",
    page_icon="🏆",
    layout="wide",
)
apply_global_layout_tweaks()

user = login_gate(required=False)
logout_button()

ROOT       = Path(__file__).resolve().parents[1]
DATA_DIR   = Path(os.environ.get("DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CATS_FILE   = DATA_DIR / "milestone_categories.json"
CLAIMS_FILE = DATA_DIR / "milestone_claims.csv"
VOTES_FILE  = DATA_DIR / "milestone_votes.csv"
RATINGSFILE = DATA_DIR / "core" / "teams_team_season_core_v50.parquet"

# Helper — True when a user is logged in (free or paid, doesn't matter)
_signed_in = user is not None

# ══════════════════════════════════════════════════════════════════════════
#  SIGN-IN WALL (not a paywall — just needs an account)
# ══════════════════════════════════════════════════════════════════════════
_SIGN_IN_CSS = """
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: transparent;
  font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
  color: #f1f5f9;
}
</style>
"""

def _render_sign_in_wall(action: str) -> None:
    import streamlit.components.v1 as components
    components.html(f"""{_SIGN_IN_CSS}
<div style="background:linear-gradient(135deg,#0f172a,#1a1a2e);
            border:1px solid rgba(59,130,246,0.35);border-radius:14px;
            padding:32px 28px;text-align:center;">
  <div style="font-size:2.5rem;margin-bottom:10px;">🔑</div>
  <div style="font-size:1.1rem;font-weight:800;color:#93c5fd;margin-bottom:6px;">
    Sign In to {action}
  </div>
  <div style="font-size:0.85rem;color:#94a3b8;max-width:420px;margin:0 auto;">
    Create a free account or sign in to submit milestones,
    vote on records, and help build Maine's basketball history.
    No subscription required.
  </div>
</div>
""", height=170, scrolling=False)

# ══════════════════════════════════════════════════════════════════════════
#  CATEGORIES  (expanded)
# ══════════════════════════════════════════════════════════════════════════
_DEFAULT_CATS = [
    {"category_id": "1000_point_scorer",    "label": "1,000-Point Scorer",       "icon": "🏀", "value_label": "Career Points",   "requires": ["subject_name","value","season"], "optional": ["evidence_url","source_note"]},
    {"category_id": "state_championship",   "label": "State Championship",       "icon": "🥇", "value_label": "Year",            "requires": ["season"],                         "optional": ["level","evidence_url","source_note"]},
    {"category_id": "regional_championship","label": "Regional Championship",    "icon": "🏆", "value_label": "Year",            "requires": ["season"],                         "optional": ["level","evidence_url","source_note"]},
    {"category_id": "single_game_record",   "label": "Single-Game Scoring Record","icon":"🔥", "value_label": "Points",          "requires": ["subject_name","value","season"], "optional": ["opponent","date","evidence_url","source_note"]},
    {"category_id": "season_wins_record",   "label": "Season Wins Record",       "icon": "📈", "value_label": "Wins",            "requires": ["value","season"],                 "optional": ["evidence_url","source_note"]},
    {"category_id": "win_streak",           "label": "Win Streak",               "icon": "⚡", "value_label": "Consecutive Wins","requires": ["value","season"],                 "optional": ["evidence_url","source_note"]},
    {"category_id": "undefeated_season",    "label": "Undefeated Regular Season","icon": "💎", "value_label": "Year",            "requires": ["season"],                         "optional": ["evidence_url","source_note"]},
    {"category_id": "coach_milestone",      "label": "Coach Milestone",          "icon": "🎓", "value_label": "Career Wins",     "requires": ["subject_name","value","season"], "optional": ["evidence_url","source_note"]},
]

def _seed_categories() -> None:
    if not CATS_FILE.exists() or CATS_FILE.stat().st_size == 0:
        with CATS_FILE.open("w") as f:
            json.dump(_DEFAULT_CATS, f, indent=2)
_seed_categories()

# ══════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════
def _inject_css() -> None:
    st.markdown("""
<style>
/* ── Trophy Banner ── */
.trophy-banner {
    background: linear-gradient(135deg, #1c1400 0%, #1e293b 60%, #0f172a 100%);
    border: 1px solid #854d0e;
    border-radius: 16px;
    padding: 28px 32px 22px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.trophy-banner::before {
    content: "🏆";
    position: absolute;
    right: 28px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 6rem;
    opacity: 0.06;
}
.trophy-banner-title {
    font-size: 0.72rem;
    color: #92400e;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 6px;
}
.trophy-banner-headline {
    font-size: 1.8rem;
    font-weight: 900;
    color: #fef3c7;
    line-height: 1.1;
    margin-bottom: 8px;
}
.trophy-banner-sub {
    font-size: 0.86rem;
    color: #92400e;
}

/* ── Stat Pill ── */
.ms-stat {
    background: #1c1400;
    border: 1px solid #85400e;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}
.ms-stat-val {
    font-size: 2rem;
    font-weight: 900;
    color: #fbbf24;
    line-height: 1;
}
.ms-stat-lbl {
    font-size: 0.65rem;
    color: #92400e;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 4px;
}

/* ── Section Head ── */
.ms-section {
    font-size: 0.72rem;
    font-weight: 700;
    color: #fbbf24;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-bottom: 1px solid #1c1400;
    padding-bottom: 6px;
    margin: 28px 0 16px;
}

/* ── Milestone Card ── */
.ms-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    position: relative;
}
.ms-card-verified  { border-left: 4px solid #22c55e; }
.ms-card-contested { border-left: 4px solid #eab308; }
.ms-card-pending   { border-left: 4px solid #475569; }

.ms-card-icon {
    font-size: 1.6rem;
    line-height: 1;
    margin-bottom: 4px;
}
.ms-card-category {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}
.ms-card-headline {
    font-size: 1.05rem;
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 4px;
}
.ms-card-meta {
    font-size: 0.76rem;
    color: #64748b;
    margin-top: 3px;
}
.ms-card-school {
    font-size: 0.82rem;
    font-weight: 600;
    color: #94a3b8;
}

/* ── Status Badge ── */
.ms-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.ms-badge-verified  { background:rgba(34,197,94,0.15);  border:1px solid rgba(34,197,94,0.5);  color:#22c55e; }
.ms-badge-contested { background:rgba(234,179,8,0.15);  border:1px solid rgba(234,179,8,0.5);  color:#eab308; }
.ms-badge-pending   { background:rgba(71,85,105,0.15);  border:1px solid rgba(71,85,105,0.5);  color:#64748b; }

/* ── Vote Bar ── */
.vote-bar-wrap {
    background: #0f172a;
    border-radius: 999px;
    height: 6px;
    width: 100%;
    margin-top: 8px;
    overflow: hidden;
}
.vote-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: #22c55e;
}

/* ── Category Chip ── */
.cat-chip {
    display: inline-block;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 14px;
    margin: 4px;
    cursor: pointer;
    font-size: 0.82rem;
    color: #cbd5e1;
    font-weight: 600;
    text-align: center;
}
.cat-chip-icon { font-size: 1.1rem; display: block; margin-bottom: 2px; }

/* ── Submit Form ── */
.submit-box {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 24px 28px;
}
.submit-box-title {
    font-size: 1.1rem;
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 4px;
}
.submit-box-sub {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════════════════════════
def _ensure_csv(path: Path, columns: list[str]) -> None:
    if not path.exists() or path.stat().st_size == 0:
        pd.DataFrame(columns=columns).to_csv(path, index=False)

@st.cache_data(ttl=3600)
def load_schools() -> list[str]:
    if not RATINGSFILE.exists(): return []
    try:
        df = pd.read_parquet(RATINGSFILE)
    except Exception: return []
    if "Team" not in df.columns: return []
    return df["Team"].astype(str).str.strip().replace("", pd.NA).dropna().drop_duplicates().sort_values().tolist()

@st.cache_data(ttl=300)
def load_categories() -> list[dict]:
    if not CATS_FILE.exists(): return []
    with CATS_FILE.open() as f: return json.load(f)

@st.cache_data(ttl=300)
def load_claims() -> pd.DataFrame:
    cols = ["claim_id","category_id","school","gender","class","region",
            "subject_name","value_num","value_text","date","season","opponent",
            "level","evidence_url","source_note","payload_json",
            "submitted_by","submitted_at","status_override"]
    _ensure_csv(CLAIMS_FILE, cols)
    try: df = pd.read_csv(CLAIMS_FILE, dtype=str)
    except pd.errors.EmptyDataError: df = pd.DataFrame(columns=cols)
    if "value_num"    in df.columns: df["value_num"]    = pd.to_numeric(df["value_num"], errors="coerce")
    if "submitted_at" in df.columns: df["submitted_at"] = pd.to_datetime(df["submitted_at"], errors="coerce")
    if "date"         in df.columns: df["date"]         = pd.to_datetime(df["date"], errors="coerce")
    return df

@st.cache_data(ttl=300)
def load_votes() -> pd.DataFrame:
    cols = ["claim_id","vote","user_id","timestamp"]
    _ensure_csv(VOTES_FILE, cols)
    try: df = pd.read_csv(VOTES_FILE, dtype=str)
    except pd.errors.EmptyDataError: df = pd.DataFrame(columns=cols)
    return df

def append_claim(row: dict) -> None:
    cols = ["claim_id","category_id","school","gender","class","region",
            "subject_name","value_num","value_text","date","season","opponent",
            "level","evidence_url","source_note","payload_json",
            "submitted_by","submitted_at","status_override"]
    _ensure_csv(CLAIMS_FILE, cols)
    try: existing = pd.read_csv(CLAIMS_FILE, dtype=str)
    except pd.errors.EmptyDataError: existing = pd.DataFrame(columns=cols)
    pd.concat([existing, pd.DataFrame([row])], ignore_index=True).to_csv(CLAIMS_FILE, index=False)
    load_claims.clear()

def upsert_vote(claim_id: str, vote: str, user_id: str) -> None:
    cols = ["claim_id","vote","user_id","timestamp"]
    _ensure_csv(VOTES_FILE, cols)
    try: existing = pd.read_csv(VOTES_FILE, dtype=str)
    except pd.errors.EmptyDataError: existing = pd.DataFrame(columns=cols)
    ts = datetime.utcnow().isoformat()
    df = existing.copy()
    mask = (df["claim_id"] == claim_id) & (df["user_id"] == user_id)
    if mask.any():
        df.loc[mask, "vote"] = vote; df.loc[mask, "timestamp"] = ts
    else:
        df = pd.concat([df, pd.DataFrame([{"claim_id":claim_id,"vote":vote,"user_id":user_id,"timestamp":ts}])], ignore_index=True)
    df.to_csv(VOTES_FILE, index=False)
    load_votes.clear()

@st.cache_data(ttl=5)
def compute_claim_statuses() -> pd.DataFrame:
    claims = load_claims()
    votes  = load_votes()
    if claims.empty:
        claims["confirm_count"] = claims["dispute_count"] = claims["needs_source_count"] = 0
        claims["status"] = "pending"
        return claims
    if votes.empty:
        agg = pd.DataFrame({"claim_id": claims["claim_id"], "confirm_count": 0, "dispute_count": 0, "needs_source_count": 0})
    else:
        agg = votes.groupby(["claim_id","vote"]).size().unstack(fill_value=0).rename_axis(None, axis=1).reset_index()
        for col in ["confirm","dispute","needs_source"]:
            if col not in agg.columns: agg[col] = 0
        agg = agg.rename(columns={"confirm":"confirm_count","dispute":"dispute_count","needs_source":"needs_source_count"})
    merged = claims.merge(agg, on="claim_id", how="left").fillna({"confirm_count":0,"dispute_count":0,"needs_source_count":0})

    def derive_status(row):
        if isinstance(row.get("status_override"), str) and row["status_override"]: return row["status_override"]
        c, d = int(row["confirm_count"]), int(row["dispute_count"])
        if c >= 5 and c - d >= 3: return "verified"
        if d >= 3: return "contested"
        return "pending"

    merged["status"] = merged.apply(derive_status, axis=1)
    return merged

def get_user_id() -> str:
    """Use the auth user's ID if signed in, otherwise a session UUID."""
    if user is not None:
        return str(getattr(user, "id", None) or getattr(user, "email", None) or str(uuid.uuid4()))
    if "milestones_user_id" not in st.session_state:
        st.session_state["milestones_user_id"] = str(uuid.uuid4())
    return st.session_state["milestones_user_id"]

def get_category_maps():
    cats = load_categories()
    id_to_cfg    = {c["category_id"]: c for c in cats} if cats else {}
    label_to_id  = {c["label"]: c["category_id"] for c in cats} if cats else {}
    return cats, id_to_cfg, label_to_id

# ══════════════════════════════════════════════════════════════════════════
#  TROPHY BANNER
# ══════════════════════════════════════════════════════════════════════════
def render_trophy_banner(total: int, verified: int, contested: int, schools: int) -> None:
    st.markdown(f"""
<div class="trophy-banner">
  <div class="trophy-banner-title">Analytics207 · Community Record Book</div>
  <div class="trophy-banner-headline">Maine Basketball History,<br>Preserved by the Community</div>
  <div class="trophy-banner-sub">
    Every record. Every milestone. Submitted, voted on, and verified by fans and coaches across Maine.
  </div>
</div>
""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl in [
        (c1, str(total),    "Total Claims"),
        (c2, str(verified), "✅ Verified"),
        (c3, str(contested),"⚠️ Contested"),
        (c4, str(schools),  "Schools"),
    ]:
        with col:
            st.markdown(f'<div class="ms-stat"><div class="ms-stat-val">{val}</div><div class="ms-stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
#  MILESTONE CARD
# ══════════════════════════════════════════════════════════════════════════
def render_milestone_card(row: pd.Series, cat_cfg: dict, user_id: str,
                          show_votes: bool = True) -> None:
    status   = str(row.get("status", "pending")).lower()
    icon     = cat_cfg.get("icon", "🏅")
    label    = cat_cfg.get("label", row.get("category_id",""))
    school   = str(row.get("school", "")).strip()
    subject  = str(row.get("subject_name", "")).strip()
    season   = str(row.get("season", "")).strip()
    opponent = str(row.get("opponent", "")).strip()
    val_num  = row.get("value_num")
    val_lbl  = cat_cfg.get("value_label","")
    confirms = int(row.get("confirm_count", 0))
    disputes = int(row.get("dispute_count", 0))
    claim_id = str(row.get("claim_id",""))

    if subject and pd.notna(val_num):
        headline = f"{subject} — {int(val_num)} {val_lbl}"
    elif subject:
        headline = subject
    elif pd.notna(val_num):
        headline = f"{int(val_num)} {val_lbl}"
    else:
        headline = label

    meta_parts = []
    if season: meta_parts.append(season)
    if opponent: meta_parts.append(f"vs {opponent}")
    meta_s = " · ".join(meta_parts)

    badge_css  = f"ms-badge-{status}"
    badge_text = {"verified":"✅ Verified","contested":"⚠️ Contested","pending":"🕐 Pending"}.get(status,"🕐 Pending")
    card_css   = f"ms-card-{status}"
    cat_color  = {"verified":"#22c55e","contested":"#eab308","pending":"#475569"}.get(status,"#475569")

    total_votes = confirms + disputes
    confirm_pct = int(confirms / total_votes * 100) if total_votes > 0 else 0

    st.markdown(
        f'<div class="ms-card {card_css}">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">'
        f'<div>'
        f'<div class="ms-card-icon">{icon}</div>'
        f'<div class="ms-card-category" style="color:{cat_color};">{label}</div>'
        f'<div class="ms-card-headline">{headline}</div>'
        f'<div class="ms-card-school">{school}</div>'
        f'<div class="ms-card-meta">{meta_s}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<span class="ms-badge {badge_css}">{badge_text}</span>'
        f'<div style="font-size:0.70rem;color:#475569;margin-top:6px;">{confirms} confirm · {disputes} dispute</div>'
        f'{"<div class=vote-bar-wrap><div class=vote-bar-fill style=width:" + str(confirm_pct) + "%;></div></div>" if total_votes > 0 else ""}'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Vote buttons: only for signed-in users ──
    if show_votes and claim_id:
        if _signed_in:
            vc1, vc2, vc3, _ = st.columns([1, 1, 1, 4])
            with vc1:
                if st.button("✅ Confirm", key=f"confirm_{claim_id}", use_container_width=True):
                    upsert_vote(claim_id, "confirm", user_id)
                    st.rerun()
            with vc2:
                if st.button("⚠️ Dispute", key=f"dispute_{claim_id}", use_container_width=True):
                    upsert_vote(claim_id, "dispute", user_id)
                    st.rerun()
            with vc3:
                if st.button("🔍 Needs Source", key=f"source_{claim_id}", use_container_width=True):
                    upsert_vote(claim_id, "needs_source", user_id)
                    st.rerun()
        else:
            st.caption("🔑 Sign in to vote on this milestone.")

# ══════════════════════════════════════════════════════════════════════════
#  BROWSE VIEW
# ══════════════════════════════════════════════════════════════════════════
def render_browse(df: pd.DataFrame, cats: list, id_to_cfg: dict, user_id: str) -> None:
    st.markdown('<div class="ms-section">📖 Browse Records</div>', unsafe_allow_html=True)

    pending = df[df["status"] == "pending"]
    if not pending.empty:
        st.markdown(
            f'<div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.25);'
            f'border-radius:10px;padding:12px 18px;margin-bottom:18px;font-size:0.85rem;color:#fbbf24;">'
            f'🗳️ <strong>{len(pending)} milestone{"s" if len(pending)>1 else ""} awaiting community votes</strong>'
            f' — {"sign in to " if not _signed_in else ""}confirm or dispute below.'
            f'</div>',
            unsafe_allow_html=True,
        )

    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    with f1:
        school_filter = st.selectbox("School", ["All Schools"] + load_schools(), key="ms_school")
    with f2:
        cat_labels = ["All Categories"] + [c["label"] for c in cats]
        cat_filter = st.selectbox("Category", cat_labels, key="ms_cat")
    with f3:
        status_filter = st.selectbox("Status", ["All", "Verified", "Contested", "Pending"], key="ms_status")
    with f4:
        gender_filter = st.selectbox("Gender", ["All", "Boys", "Girls"], key="ms_gender")

    view = df.copy()
    if school_filter != "All Schools":
        view = view[view["school"].astype(str).str.strip() == school_filter]
    if cat_filter != "All Categories":
        cats_map = {c["label"]: c["category_id"] for c in cats}
        view = view[view["category_id"] == cats_map.get(cat_filter, "")]
    if status_filter != "All":
        view = view[view["status"].str.lower() == status_filter.lower()]
    if gender_filter != "All":
        view = view[view["gender"].astype(str).str.strip().str.title() == gender_filter]

    if view.empty:
        st.info("No milestones found for these filters yet — be the first to submit one!")
        return

    if school_filter == "All Schools":
        schools_in_view = view["school"].dropna().unique()
        for school in sorted(schools_in_view):
            school_ms = view[view["school"] == school]
            st.markdown(
                f'<div style="font-size:1.0rem;font-weight:800;color:#f1f5f9;'
                f'margin:20px 0 8px;border-left:3px solid #fbbf24;padding-left:10px;">'
                f'{school}</div>',
                unsafe_allow_html=True,
            )
            for _, row in school_ms.iterrows():
                cfg = id_to_cfg.get(str(row.get("category_id", "")), {})
                render_milestone_card(row, cfg, user_id, show_votes=True)
    else:
        st.markdown(
            f'<div style="font-size:1.4rem;font-weight:900;color:#fbbf24;margin-bottom:16px;">'
            f'{school_filter} Record Book</div>',
            unsafe_allow_html=True,
        )
        for _, row in view.sort_values(
            "status", key=lambda x: x.map({"verified": 0, "contested": 1, "pending": 2})
        ).iterrows():
            cfg = id_to_cfg.get(str(row.get("category_id", "")), {})
            render_milestone_card(row, cfg, user_id, show_votes=True)

# ══════════════════════════════════════════════════════════════════════════
#  SUBMIT FORM — requires sign-in
# ══════════════════════════════════════════════════════════════════════════
def render_submit_form(cats: list, label_to_id: dict, id_to_cfg: dict) -> None:
    st.markdown('<div class="ms-section">➕ Submit a Milestone</div>', unsafe_allow_html=True)

    # ── Gate: must be signed in to submit ──
    if not _signed_in:
        _render_sign_in_wall("Submit Milestones")
        return

    st.markdown("""
<div class="submit-box">
  <div class="submit-box-title">Know a record that's missing?</div>
  <div class="submit-box-sub">
    Submit it here. The community will confirm or dispute it.
    Verified records need 5+ confirms and a 3-vote confirm margin.
  </div>
</div>
""", unsafe_allow_html=True)
    st.write("")

    schools = load_schools()
    cat_labels = [c["label"] for c in cats]

    with st.form("ms_submit_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            school = st.selectbox("School *", [""] + schools)
            cat_label = st.selectbox("Milestone Type *", cat_labels)
            gender = st.selectbox("Gender", ["Boys","Girls","Both"])
        with fc2:
            subject = st.text_input("Player/Coach Name (if applicable)")
            value   = st.number_input("Value (points, wins, etc.)", min_value=0, value=0)
            season  = st.text_input("Season (e.g. 2024-25)")

        fd1, fd2 = st.columns(2)
        with fd1:
            opponent     = st.text_input("Opponent (if applicable)")
            evidence_url = st.text_input("Evidence URL (optional)")
        with fd2:
            source_note = st.text_area("Source / Notes", height=80)

        # Auto-fill submitter from auth
        submitted_by = str(getattr(user, "name", None) or getattr(user, "email", "")) if user else ""

        submitted = st.form_submit_button("🏆 Submit Milestone", use_container_width=True)

        if submitted:
            if not school or not cat_label:
                st.error("School and Milestone Type are required.")
            else:
                cat_id = label_to_id.get(cat_label, "")
                claim  = {
                    "claim_id":    str(uuid.uuid4()),
                    "category_id": cat_id,
                    "school":      school,
                    "gender":      gender,
                    "class":       "",
                    "region":      "",
                    "subject_name": subject,
                    "value_num":   value if value > 0 else None,
                    "value_text":  "",
                    "date":        "",
                    "season":      season,
                    "opponent":    opponent,
                    "level":       "",
                    "evidence_url": evidence_url,
                    "source_note": source_note,
                    "payload_json": "{}",
                    "submitted_by": submitted_by,
                    "submitted_at": datetime.utcnow().isoformat(),
                    "status_override": "",
                }
                append_claim(claim)
                st.success(f"✅ Milestone submitted for **{school}**! The community will review it.")

# ══════════════════════════════════════════════════════════════════════════
#  RECENTLY VERIFIED  (trophy shelf)
# ══════════════════════════════════════════════════════════════════════════
def render_trophy_shelf(df: pd.DataFrame, id_to_cfg: dict, user_id: str) -> None:
    verified = df[df["status"] == "verified"].copy()
    if verified.empty: return

    st.markdown('<div class="ms-section">🥇 Recently Verified</div>', unsafe_allow_html=True)
    cols = st.columns(min(3, len(verified)))
    for col, (_, row) in zip(cols, verified.head(3).iterrows()):
        cfg     = id_to_cfg.get(str(row.get("category_id","")), {})
        icon    = cfg.get("icon","🏅")
        label   = cfg.get("label","")
        school  = str(row.get("school",""))
        subject = str(row.get("subject_name","")).strip()
        val_num = row.get("value_num")
        val_lbl = cfg.get("value_label","")
        headline = f"{subject} — {int(val_num)} {val_lbl}" if subject and pd.notna(val_num) else (subject or label)
        with col:
            st.markdown(
                f'<div class="ms-card ms-card-verified" style="text-align:center;">'
                f'<div style="font-size:2rem;">{icon}</div>'
                f'<div style="font-size:0.65rem;color:#22c55e;text-transform:uppercase;letter-spacing:.08em;margin:4px 0;">{label}</div>'
                f'<div style="font-size:0.95rem;font-weight:800;color:#f1f5f9;">{headline}</div>'
                f'<div style="font-size:0.78rem;color:#64748b;margin-top:4px;">{school}</div>'
                f'<span class="ms-badge ms-badge-verified" style="margin-top:8px;">✅ Verified</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
def main() -> None:
    _inject_css()
    render_logo()
    render_page_header(
        title="🏆 Milestones & Records",
        definition="Milestones (n.): The moments that define a program — preserved forever.",
        subtitle="Community-powered. Every record submitted and verified by Maine basketball fans and coaches.",
    )

    cats, id_to_cfg, label_to_id = get_category_maps()
    df   = compute_claim_statuses()
    uid  = get_user_id()

    total     = len(df)
    verified  = int((df["status"] == "verified").sum())  if not df.empty else 0
    contested = int((df["status"] == "contested").sum()) if not df.empty else 0
    schools   = int(df["school"].nunique())              if not df.empty else 0

    render_trophy_banner(total, verified, contested, schools)

    tab1, tab2, tab3 = st.tabs(["📖 Browse Records", "🥇 Trophy Shelf", "➕ Submit"])

    with tab1:
        render_browse(df, cats, id_to_cfg, uid)
    with tab2:
        render_trophy_shelf(df, id_to_cfg, uid)
    with tab3:
        render_submit_form(cats, label_to_id, id_to_cfg)

    render_footer()

if __name__ == "__main__":
    main()
