from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import pandas as pd
import streamlit as st

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

TEAMS_SEASON_PATH = DATA_DIR / "teams_team_season_core_v30.parquet"
GAMES_PATH = DATA_DIR / "games_game_core_v30.parquet"
PRED_PATH = DATA_DIR / "games_predictions_current.parquet"


def inject_tournament_central_css() -> None:
    st.markdown(
        """
        <style>
        .tc-table { width: 100%; table-layout: fixed; border-collapse: collapse; }
        .tc-table th, .tc-table td { white-space: nowrap; text-overflow: ellipsis; overflow: hidden; text-align: center; vertical-align: middle; }
        .tc-table th { padding: 0.25rem 0.55rem; font-size: 0.82rem; }
        .tc-table td { padding: 0.25rem 0.55rem; font-size: 0.82rem; }

        .pill-base { display:inline-flex; align-items:center; justify-content:center; padding:0.05rem 0.55rem; border-radius:999px;
                    font-size:0.72rem; line-height:1.1; font-weight:700; min-width:3.0rem; gap:0.25rem; }
        .seed-pill { background: rgba(129,140,248,0.12); border:1px solid rgba(129,140,248,0.80); color:#818cf8; }
        .form-hot { background: rgba(248,113,113,0.14); border:1px solid rgba(248,113,113,0.90); color:#f97373; }
        .form-cold { background: rgba(59,130,246,0.14); border:1px solid rgba(59,130,246,0.90); color:#60a5fa; }
        .form-neutral { background: rgba(148,163,184,0.10); border:1px solid rgba(148,163,184,0.60); color:#94a3b8; }
        .move-up { background: rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.80); color:#4ade80; }
        .move-down { background: rgba(239,68,68,0.10); border:1px solid rgba(239,68,68,0.85); color:#fca5a5; }

        .matchup-card { padding:0.35rem 0.55rem; border-radius:0.45rem; border:1px solid rgba(148,163,184,0.35);
                        background: rgba(15,23,42,0.80); margin-bottom:0.35rem; }
        .matchup-header { font-size:0.75rem; opacity:0.85; margin-bottom:0.15rem; display:flex; justify-content:space-between; }
        .matchup-team { display:flex; align-items:center; justify-content:space-between; gap:0.35rem; font-size:0.82rem; }
        .matchup-team-name { flex:1; text-align:left; }
        .matchup-meta { font-size:0.72rem; opacity:0.85; }
        .matchup-tags { display:flex; gap:0.25rem; }

        .edge-pill { display:inline-flex; align-items:center; gap:0.35rem; padding:0.05rem 0.55rem; border-radius:999px;
                     font-size:0.72rem; font-weight:600; margin-bottom:0.20rem; }
        .edge-strong { background: rgba(34,197,94,0.14); border:1px solid rgba(34,197,94,0.90); color:#22c55e; }
        .edge-medium { background: rgba(52,211,153,0.12); border:1px solid rgba(52,211,153,0.85); color:#34d399; }
        .edge-close { background: rgba(59,130,246,0.14); border:1px solid rgba(59,130,246,0.90); color:#60a5fa; }
        .edge-team { font-weight:700; }
        .edge-meta { opacity:0.85; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_teams() -> pd.DataFrame:
    if not TEAMS_SEASON_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(TEAMS_SEASON_PATH).copy()
    for col in ["TeamKey", "Team", "Gender", "Class", "Region", "Season"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Class" in df.columns:
        df["Class"] = df["Class"].str.upper()
    if "Region" in df.columns:
        df["Region"] = df["Region"].str.title()

    numericcols = [
        "TI", "ProjectedSeed", "GamesRemaining", "Games", "Wins", "Losses",
        "ScheduleAdjWins", "NetEff", "Last5MarginPG", "Streak", "TSR", "TSRDisplay",
        "LuckZ", "PPG", "OPPG",
    ]
    for col in numericcols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Qualified" in df.columns:
        df["Qualified"] = df["Qualified"].astype(str).str.upper()

    if "PrevSeed" in df.columns:
        df["PrevSeed"] = pd.to_numeric(df["PrevSeed"], errors="coerce")

    if {"Wins", "Losses"}.issubset(df.columns):
        df["Record"] = df["Wins"].fillna(0).astype(int).astype(str) + "-" + df["Losses"].fillna(0).astype(int).astype(str)

    return df


@st.cache_data
def load_games() -> pd.DataFrame:
    if not GAMES_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(GAMES_PATH).copy()
    for c in ["GameID", "Season", "Gender", "Home", "Away", "HomeKey", "AwayKey"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


@st.cache_data
def load_preds() -> pd.DataFrame:
    if not PRED_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(PRED_PATH).copy()
    for c in ["GameID", "Season", "Gender", "Home", "Away", "HomeKey", "AwayKey"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].str.title()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def format_seed_pill(seed: Optional[float]) -> str:
    if pd.isna(seed):
        return ""
    try:
        v = int(seed)
    except Exception:
        return ""
    return f"<div class='pill-base seed-pill'>{v}</div>"


def form_bucket(row: pd.Series) -> str:
    last5 = row.get("Last5MarginPG", pd.NA)
    streak = row.get("Streak", pd.NA)
    hot = False
    cold = False
    if pd.notna(last5) and float(last5) >= 5:
        hot = True
    if pd.notna(streak) and float(streak) >= 3:
        hot = True
    if pd.notna(last5) and float(last5) <= -4:
        cold = True
    if pd.notna(streak) and float(streak) <= -2:
        cold = True
    if hot and not cold:
        return "HOT"
    if cold and not hot:
        return "COLD"
    return "NEUTRAL"


def format_form_pill(bucket: str) -> str:
    b = (bucket or "").upper()
    if b == "HOT":
        label, css = "HOT", "form-hot"
    elif b == "COLD":
        label, css = "COLD", "form-cold"
    else:
        label, css = "EVEN", "form-neutral"
    return f"<div class='pill-base {css}'>{label}</div>"


def movement_delta(row: pd.Series) -> Optional[int]:
    cur = row.get("ProjectedSeed", pd.NA)
    prev = row.get("PrevSeed", pd.NA)
    if pd.isna(cur) or pd.isna(prev):
        return None
    try:
        return int(prev) - int(cur)
    except Exception:
        return None


def format_movement_pill(delta: Optional[int]) -> str:
    if delta is None or delta == 0:
        return ""
    if delta > 0:
        return f"<div class='pill-base move-up'>+{delta}</div>"
    return f"<div class='pill-base move-down'>{delta}</div>"


def build_slice(df: pd.DataFrame, gender: str, cls: str, region: str) -> pd.DataFrame:
    q = df.copy()
    if "Gender" in q.columns:
        q = q[q["Gender"] == gender.title()]
    if "Class" in q.columns:
        q = q[q["Class"] == cls.upper()]
    if "Region" in q.columns:
        q = q[q["Region"] == region.title()]
    if q.empty:
        return q

    if "ProjectedSeed" in q.columns and q["ProjectedSeed"].notna().any():
        q = q.sort_values(["ProjectedSeed", "TI"], ascending=[True, False])
        q["ProjectedSeed"] = pd.to_numeric(q["ProjectedSeed"], errors="coerce")
    else:
        q = q.sort_values(["TI"], ascending=[False])

    q["SEED"] = pd.to_numeric(q.get("ProjectedSeed", pd.NA), errors="coerce")
    q["SEED"] = q["SEED"].rank(method="first").astype("Int64")

    q["FORMBUCKET"] = q.apply(form_bucket, axis=1)
    q["MOVEDELTA"] = q.apply(movement_delta, axis=1)
    return q.reset_index(drop=True)


def find_game_edge(games: pd.DataFrame, preds: pd.DataFrame, season: str, gender: str, home_team: str, away_team: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Returns (pred_margin_home, pred_winprob_home, coreversion) for the scheduled game if found.
    """
    if games.empty or preds.empty:
        return None, None, None

    g = games.copy()
    p = preds.copy()

    # Find matching game row (same season/gender/home/away)
    sub = g[
        (g.get("Season", "").astype(str) == str(season)) &
        (g.get("Gender", "").astype(str) == str(gender).title()) &
        (g.get("Home", "").astype(str) == str(home_team)) &
        (g.get("Away", "").astype(str) == str(away_team))
    ]
    if sub.empty:
        return None, None, None

    gameid = str(sub.iloc[0].get("GameID", "")).strip()
    if not gameid:
        return None, None, None

    ps = p[p.get("GameID", "").astype(str) == gameid]
    if ps.empty:
        return None, None, None

    r = ps.iloc[0]
    margin = r.get("PredMargin", pd.NA)
    winp = r.get("PredHomeWinProb", pd.NA)
    ver = r.get("CoreVersion", None)
    if pd.isna(margin) or pd.isna(winp):
        return None, None, ver
    return float(margin), float(winp), (str(ver) if ver is not None else None)


def format_edge_pill(home_team: str, away_team: str, margin_home: Optional[float], winprob_home: Optional[float]) -> str:
    if margin_home is None or winprob_home is None:
        return "<div class='edge-pill edge-close'><span class='edge-meta'>Model edge</span> <span class='edge-meta'>N/A</span></div>"

    favored = home_team if margin_home >= 0 else away_team
    margin = abs(float(margin_home))
    favwin = winprob_home if margin_home >= 0 else (1.0 - winprob_home)
    winpct = 100.0 * float(favwin)

    if margin >= 15:
        tier = "edge-strong"
    elif margin >= 8:
        tier = "edge-medium"
    else:
        tier = "edge-close"

    return (
        f"<div class='edge-pill {tier}'>"
        f"<span class='edge-meta'>Model</span> "
        f"<span class='edge-team'>{favored}</span> "
        f"<span class='edge-meta'>{margin:.1f} pts | {winpct:.0f}%</span>"
        f"</div>"
    )


def render_bracket_block(q: pd.DataFrame, games: pd.DataFrame, preds: pd.DataFrame, cutoff: int = 8, playinmax: int = 10) -> None:
    if q.empty:
        st.info("No teams found for this slice.")
        return

    main = q[q["SEED"] <= cutoff].copy()
    playin = q[(q["SEED"] > cutoff) & (q["SEED"] <= playinmax)].copy()

    st.subheader("IF THE TOURNAMENT STARTED TODAY")
    st.markdown("**Bracket + play-ins** (Model edge uses new-engine scheduled-game predictions only.)")

    def get_team(seed: int) -> Optional[pd.Series]:
        sub = main[main["SEED"] == seed]
        if sub.empty:
            return None
        return sub.iloc[0]

    # Play-in (9 vs 10) if present
    if len(playin) >= 2:
        p9 = playin[playin["SEED"] == 9].head(1)
        p10 = playin[playin["SEED"] == 10].head(1)
        if not p9.empty and not p10.empty:
            r9 = p9.iloc[0]
            r10 = p10.iloc[0]
            st.caption("Play-in winner advances to face the 1-seed.")
            margin, winp, _ = find_game_edge(games, preds, r9.get("Season", ""), r9.get("Gender", ""), r9.get("Team", ""), r10.get("Team", ""))
            st.markdown("<div class='matchup-card'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='matchup-header'><span>Scheduled game edge</span><span class='matchup-meta'>9 vs 10</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown(format_edge_pill(r9.get("Team", ""), r10.get("Team", ""), margin, winp), unsafe_allow_html=True)
            for r in [r9, r10]:
                tags = format_form_pill(r["FORMBUCKET"]) + format_movement_pill(r["MOVEDELTA"])
                st.markdown(
                    f"<div class='matchup-team'>{format_seed_pill(r['SEED'])}"
                    f"<span class='matchup-team-name'>{r.get('Team','')}</span>"
                    f"<span class='matchup-meta'>{r.get('Record','')}</span>"
                    f"<span class='matchup-tags'>{tags}</span></div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # Main bracket pairs
    pairs = [(1, cutoff), (4, 5), (2, 7), (3, 6)]
    for s1, s2 in pairs:
        t1 = get_team(s1)
        t2 = get_team(s2)
        if t1 is None or t2 is None:
            continue

        margin, winp, _ = find_game_edge(games, preds, t1.get("Season", ""), t1.get("Gender", ""), t1.get("Team", ""), t2.get("Team", ""))

        st.markdown("<div class='matchup-card'>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='matchup-header'><span>Scheduled game edge</span><span class='matchup-meta'>{s1} vs {s2}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(format_edge_pill(t1.get("Team", ""), t2.get("Team", ""), margin, winp), unsafe_allow_html=True)

        tags1 = format_form_pill(t1["FORMBUCKET"]) + format_movement_pill(t1["MOVEDELTA"])
        tags2 = format_form_pill(t2["FORMBUCKET"]) + format_movement_pill(t2["MOVEDELTA"])

        st.markdown(
            f"<div class='matchup-team'>{format_seed_pill(t1['SEED'])}"
            f"<span class='matchup-team-name'>{t1.get('Team','')}</span>"
            f"<span class='matchup-meta'>{t1.get('Record','')}</span>"
            f"<span class='matchup-tags'>{tags1}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='matchup-team'>{format_seed_pill(t2['SEED'])}"
            f"<span class='matchup-team-name'>{t2.get('Team','')}</span>"
            f"<span class='matchup-meta'>{t2.get('Record','')}</span>"
            f"<span class='matchup-tags'>{tags2}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Table view
    display = q.copy()
    display["FORMPILL"] = display["FORMBUCKET"].apply(format_form_pill)
    display["MOVEPILL"] = display["MOVEDELTA"].apply(format_movement_pill)

    basecols = {
        "SEED": display["SEED"].apply(format_seed_pill),
        "TEAM": display.get("Team", ""),
        "RECORD": display.get("Record", ""),
        "FORM": display["FORMPILL"],
        "MOVE": display["MOVEPILL"],
        "GMS REM": pd.to_numeric(display.get("GamesRemaining", pd.NA), errors="coerce").astype("Int64"),
        "SCHED ADJ WINS": pd.to_numeric(display.get("ScheduleAdjWins", pd.NA), errors="coerce").round(1),
        "HEAL TI": pd.to_numeric(display.get("TI", pd.NA), errors="coerce").round(2),
        "L5 MARGIN": pd.to_numeric(display.get("Last5MarginPG", pd.NA), errors="coerce").round(1),
        "LuckZ": pd.to_numeric(display.get("LuckZ", pd.NA), errors="coerce").round(2),
    }

    tsrcol = "TSRDisplay" if "TSRDisplay" in display.columns else ("TSR" if "TSR" in display.columns else None)
    if tsrcol:
        tsrraw = pd.to_numeric(display.get(tsrcol), errors="coerce")
        if tsrraw.notna().any():
            basecols["TSR"] = (100.0 + tsrraw).round(1)

    table = pd.DataFrame(basecols)
    html = table.to_html(escape=False, index=False, classes="tc-table")
    st.markdown(html, unsafe_allow_html=True)


def main() -> None:
    apply_global_layout_tweaks()
    inject_tournament_central_css()
    render_logo()
    render_page_header(
        title="🏆Tournament Central",
        definition="Tournament Central (n.): Your command center for every postseason matchup and title chase.",
        subtitle="Learns from team and game data to estimate win chances, spreads, and likely results before tipoff.",
    )
    st.write("")
    st.write("")
    teams = load_teams()
    games = load_games()
    preds = load_preds()

    cols = st.columns(3)
    with cols[0]:
        gender = st.selectbox("Gender", ["Boys", "Girls"], index=0)
    with cols[1]:
        cls = st.selectbox("Class", ["A", "B", "C", "D", "S"], index=0)
    with cols[2]:
        region = st.selectbox("Region", ["North", "South"], index=0)

    cutoff = 8
    playinmax = 10

    slicedf = build_slice(teams, gender=gender, cls=cls, region=region)
    if slicedf.empty:
        st.warning("No teams found for this selection.")
        render_footer()
        return

    st.caption(f"{gender} Class {cls} {region} — bracket, form, movement, and scheduled-game model edge.")
    render_bracket_block(slicedf, games=games, preds=preds, cutoff=cutoff, playinmax=playinmax)

    render_footer()


if __name__ == "__main__":
    main()
