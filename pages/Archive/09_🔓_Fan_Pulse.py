# pages/08__Fan_Pulse.py  (V30 Fan Pulse - compact 3-across + WinnerPick wiring)
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

from layout import apply_global_layout_tweaks, render_logo, render_page_header, render_footer


# ----------------------------
# Page config + layout
# ----------------------------
st.set_page_config(
    page_title="Fan Pulse (n.): The Voice of the Fans",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_global_layout_tweaks()
render_logo()
render_page_header(
    title="FAN PULSE",
    definition="Fan Pulse (n.): Quick crowd picks, game-to-game.",
    subtitle="Vote winner + hype in seconds. Votes feed Team Center automatically.",
)


# ----------------------------
# Paths (V30: /data)
# ----------------------------
ROOT = Path(__file__).resolve().parents[1]
DATADIR = ROOT / "data"

GAMES_V30_FILE = DATADIR / "games_game_core_v30.parquet"
VOTES_FILE = DATADIR / "fan_pulse_data.csv"

VOTE_COLS = ["GameID", "Poll_Type", "Vote", "Timestamp"]


# ----------------------------
# Loaders / writers
# ----------------------------
@st.cache_data(ttl=120, show_spinner=False)
def load_games_v30() -> pd.DataFrame:
    if not GAMES_V30_FILE.exists():
        return pd.DataFrame()

    df = pd.read_parquet(GAMES_V30_FILE).copy()

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    for c in ["GameID", "Home", "Away"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    for c in ["HomeScore", "AwayScore"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "Played" in df.columns and df["Played"].dtype != bool:
        df["Played"] = df["Played"].fillna(False).astype(bool)

    return df


@st.cache_data(ttl=30, show_spinner=False)
def load_votes() -> pd.DataFrame:
    if not VOTES_FILE.exists():
        return pd.DataFrame(columns=VOTE_COLS)

    df = pd.read_csv(VOTES_FILE)
    for c in VOTE_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[VOTE_COLS].copy()

    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

    for c in ["GameID", "Poll_Type", "Vote"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    return df


def append_votes(new_votes: list[dict]) -> None:
    df_new = pd.DataFrame(new_votes)
    for c in VOTE_COLS:
        if c not in df_new.columns:
            df_new[c] = pd.NA
    df_new = df_new[VOTE_COLS].copy()

    if VOTES_FILE.exists():
        try:
            curr = pd.read_csv(VOTES_FILE)
        except Exception:
            curr = pd.DataFrame(columns=VOTE_COLS)
    else:
        curr = pd.DataFrame(columns=VOTE_COLS)

    for c in VOTE_COLS:
        if c not in curr.columns:
            curr[c] = pd.NA
    curr = curr[VOTE_COLS].copy()

    out = pd.concat([curr, df_new], ignore_index=True)
    VOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(VOTES_FILE, index=False)


# ----------------------------
# Aggregates for quick display
# ----------------------------
def safe_int(x, default: int = 0) -> int:
    try:
        if pd.isna(x):
            return default
        return int(float(x))
    except Exception:
        return default


def build_winner_counts(votes: pd.DataFrame) -> pd.DataFrame:
    """
    Returns index=GameID with:
      TotalVotes, TopPick, TopPickVotes, TopPickShare
    """
    if votes is None or votes.empty:
        return pd.DataFrame()

    v = votes.copy()
    v["GameID"] = v["GameID"].astype(str).str.strip()
    v["Poll_Type"] = v["Poll_Type"].astype(str).str.strip()
    v["Vote"] = v["Vote"].astype(str).str.strip()

    v = v[v["Poll_Type"] == "WinnerPick"].copy()
    v = v[v["Vote"] != ""]
    if v.empty:
        return pd.DataFrame()

    total = v.groupby("GameID")["Vote"].count().rename("TotalVotes")

    def top_pick(series: pd.Series) -> str:
        vc = series.value_counts(dropna=True)
        return str(vc.index[0]) if len(vc) else ""

    def top_pick_votes(series: pd.Series) -> int:
        vc = series.value_counts(dropna=True)
        return int(vc.iloc[0]) if len(vc) else 0

    tp = v.groupby("GameID")["Vote"].apply(top_pick).rename("TopPick")
    tpc = v.groupby("GameID")["Vote"].apply(top_pick_votes).rename("TopPickVotes")

    out = pd.concat([total, tp, tpc], axis=1)
    out["TopPickShare"] = np.where(out["TotalVotes"] > 0, out["TopPickVotes"] / out["TotalVotes"], np.nan)
    return out


# ----------------------------
# Load data
# ----------------------------
games = load_games_v30()
votes = load_votes()

if games.empty:
    st.error("Core v30 games file not found. Expected: data/games_game_core_v30.parquet")
    render_footer()
    st.stop()

# Recent completed games only
if "Played" in games.columns:
    recent = games[games["Played"] == True].copy()
else:
    recent = games.copy()
    if "HomeScore" in recent.columns:
        recent = recent[recent["HomeScore"].notna()].copy()

if "Date" in recent.columns:
    recent = recent.sort_values("Date", ascending=False).head(60)
else:
    recent = recent.head(60)

# Merge pick aggregates
pick_agg = build_winner_counts(votes)
if not pick_agg.empty and "GameID" in recent.columns:
    recent = recent.merge(pick_agg, how="left", left_on="GameID", right_index=True)

st.markdown("---")


# ----------------------------
# Filter + compact grid
# ----------------------------
st.subheader("📣 Vote the winner (3-up grid)")

teams = []
if "Home" in recent.columns and "Away" in recent.columns:
    teams = sorted(pd.unique(pd.concat([recent["Home"], recent["Away"]]).dropna().astype(str)))

c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    selected_team = st.multiselect("Filter by team", options=teams, default=[])
with c2:
    sort_mode = st.radio("Sort by", ["Newest", "Most votes"], horizontal=True)
with c3:
    max_games = st.slider("Show", 6, 30, 12, step=3)

if selected_team:
    recent = recent[(recent["Home"].isin(selected_team)) | (recent["Away"].isin(selected_team))].copy()

if sort_mode == "Most votes" and "TotalVotes" in recent.columns:
    recent = recent.sort_values("TotalVotes", ascending=False, na_position="last")
elif "Date" in recent.columns:
    recent = recent.sort_values("Date", ascending=False)

recent = recent.head(max_games)

if recent.empty:
    st.info("No games match your filters.")
    render_footer()
    st.stop()


def render_game_tile(container, g: pd.Series):
    game_id = str(g.get("GameID", "")).strip()
    home = str(g.get("Home", "Home")).strip()
    away = str(g.get("Away", "Away")).strip()

    dt = g.get("Date", pd.NaT)
    date_str = pd.to_datetime(dt, errors="coerce").strftime("%b %d") if pd.notna(dt) else "Recent"

    hs = safe_int(g.get("HomeScore", np.nan), default=0)
    a_s = safe_int(g.get("AwayScore", np.nan), default=0)

    total_votes = safe_int(g.get("TotalVotes", 0), default=0)
    top_pick = str(g.get("TopPick", "")).strip()
    top_share = g.get("TopPickShare", np.nan)

    with container:
        with st.container(border=True):
            st.markdown(f"**{date_str}**")
            st.markdown(f"{home} **{hs}**  —  {away} **{a_s}**")
            if total_votes > 0 and top_pick:
                share_txt = f"{float(top_share):.0%}" if not pd.isna(top_share) else ""
                st.caption(f"Crowd leaning: {top_pick} ({share_txt}) • {total_votes} vote(s)")
            else:
                st.caption("No crowd pick yet")

            with st.form(key=f"pick_{game_id}"):
                winner_pick = st.radio(
                    "Winner pick",
                    [home, away],
                    horizontal=True,
                    key=f"wp_{game_id}",
                )
                hype = st.slider(
                    "Hype",
                    0, 100, 70,
                    key=f"hy_{game_id}",
                )
                submitted = st.form_submit_button("Vote")

                if submitted:
                    now = pd.Timestamp.now()
                    append_votes(
                        [
                            {"GameID": game_id, "Poll_Type": "WinnerPick", "Vote": str(winner_pick).strip(), "Timestamp": now},
                            {"GameID": game_id, "Poll_Type": "Hype", "Vote": str(int(hype)), "Timestamp": now},
                        ]
                    )
                    st.success("Vote saved.")
                    st.rerun()


# 3 across grid
rows = list(range(0, len(recent), 3))
for start in rows:
    cols = st.columns(3)
    chunk = recent.iloc[start : start + 3]
    for i in range(3):
        if i < len(chunk):
            render_game_tile(cols[i], chunk.iloc[i])
        else:
            cols[i].empty()

st.markdown("---")


# ----------------------------
# Season leaders (simple + compact)
# ----------------------------
st.markdown("### 🏆 Season leaders")

if votes is None or votes.empty:
    st.caption("No votes yet.")
else:
    v = votes.copy()
    v["Poll_Type"] = v["Poll_Type"].astype(str).str.strip()
    v["Vote"] = v["Vote"].astype(str).str.strip()

    col_a, col_b = st.columns(2)

    with col_a:
        wp = v[v["Poll_Type"] == "WinnerPick"].copy()
        wp = wp[wp["Vote"] != ""]
        st.markdown("**Most-picked teams**")
        if wp.empty:
            st.caption("No WinnerPick votes yet.")
        else:
            st.bar_chart(wp["Vote"].value_counts().head(15))

    with col_b:
        hy = v[v["Poll_Type"] == "Hype"].copy()
        hy["VoteNum"] = pd.to_numeric(hy["Vote"], errors="coerce")
        hy = hy.dropna(subset=["VoteNum"])
        st.markdown("**Most-hyped games**")
        if hy.empty:
            st.caption("No hype votes yet.")
        else:
            hype_agg = hy.groupby("GameID")["VoteNum"].mean().sort_values(ascending=False).head(15)
            st.dataframe(
                hype_agg.reset_index().rename(columns={"VoteNum": "Avg Hype"}),
                hide_index=True,
                use_container_width=True,
            )

render_footer()
