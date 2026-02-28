# Home.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import html
import textwrap

import streamlit as st
import layout as L

# ----------------------------
# Page config (call once, at top)
# ----------------------------
st.set_page_config(
    page_title="🏀 ANALYTICS207 | Home",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

import streamlit as st



APP_ROOT = Path(r"C:\\ANALYTICS207\\web")


import pandas as pd  # if not already imported
import plotly.express as px  # if not already imported
from components.home_card import inject_home_card_css, render_home_card

inject_home_card_css()

# ----------------------------
# Layout helpers
# ----------------------------
def _pick(*names: str) -> Optional[Callable]:
    for n in names:
        fn = getattr(L, n, None)
        if callable(fn):
            return fn
    return None

apply_layout = _pick("apply_global_layout_tweaks", "applygloballayouttweaks")
render_logo = _pick("render_logo", "renderlogo")
render_header = _pick("render_page_header", "renderpageheader")
render_footer = _pick("render_footer", "renderfooter")
spacer = _pick("spacer", "spacerlines")





def _load_hero_teams_tsr_df() -> pd.DataFrame:
    df = pd.read_parquet(r"data/teams_team_season_core_v30.parquet")

    target = [
        ("Presque Isle", "Boys"),
        ("Oceanside", "Girls"),
        ("Portland", "Boys"),
        ("Hampden", "Girls"),
    ]

    mask = False
    for team, gender in target:
        mask |= ((df["Team"] == team) & (df["Gender"] == gender))

    snap = df.loc[mask, ["Team", "Gender", "TSR"]].copy()
    snap["Label"] = snap["Team"] + " " + snap["Gender"].str[0]
    snap = snap.sort_values("TSR", ascending=False)

    return snap

def _sp(n: int = 1) -> None:
    if callable(spacer):
        try:
            spacer(n)
            return
        except Exception:
            pass
    for _ in range(max(0, int(n))):
        st.write("")

#if callable(apply_layout):
#   apply_layout()
if callable(render_logo):
    render_logo()

# Keep your global header copy light; no second big logo/title
if callable(render_header):
    render_header(
        title="",
        definition="Inside the data model behind our sports insights.",
        subtitle="Schedules • Ratings • Tournaments • Predictions • Community • Analytics",
    )
else:
    st.caption("Inside the data model behind our sports insights.")

_sp(1)




# ----------------------------
# Global CSS
# ----------------------------


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
    }

    /* HERO CARD (unchanged) */
    .a207-hero-card {
        position: relative;
        border-radius: 24px;
        padding: 1.5rem 1.6rem;
        background: radial-gradient(circle at 0% 0%, #020617, #020617);
        box-shadow:
            0 28px 50px rgba(15,23,42,0.95),
            inset 0 0 0 1px rgba(148,163,184,0.35);
        color: #e5e7eb;
        margin-bottom: 1.6rem;
        overflow: hidden;
    }
    .a207-hero-card::before {
        content: "";
        position: absolute;
        inset: -40%;
        background:
            radial-gradient(circle at 5% 0%, rgba(59,130,246,0.32), transparent 60%),
            radial-gradient(circle at 75% 0%, rgba(244,114,182,0.26), transparent 60%),
            radial-gradient(circle at 100% 40%, rgba(34,197,94,0.16), transparent 60%);
        mix-blend-mode: screen;
        opacity: 0.95;
        pointer-events: none;
    }
    .a207-hero-inner {
        position: relative;
        z-index: 1;
        display: grid;
        grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.6fr);
        gap: 1.4rem;
        align-items: stretch;
    }
    @media (max-width: 1100px) {
        .a207-hero-inner {
            grid-template-columns: minmax(0, 1fr);
        }
    }

    .a207-hero-tag {
        font-size: 0.78rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #a5b4fc;
        margin-bottom: 0.35rem;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    .a207-hero-tag-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: #22c55e;
        box-shadow: 0 0 0 4px rgba(34,197,94,0.35);
    }

    .a207-hero-title {
        font-size: 2rem;
        line-height: 1.1;
        font-weight: 800;
        letter-spacing: 0.02em;
        margin-bottom: 0.35rem;
    }
    .a207-hero-sub {
        font-size: 0.95rem;
        color: #e5e7eb;
        max-width: 32rem;
        margin-bottom: 0.7rem;
    }

    .a207-hero-highlight {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.28rem 0.75rem;
        border-radius: 999px;
        border: 1px solid rgba(248,250,252,0.5);
        background: rgba(15,23,42,0.9);
        font-size: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .a207-hero-highlight-badge {
        padding: 0.08rem 0.45rem;
        border-radius: 999px;
        background: rgba(34,197,94,0.22);
        color: #bbf7d0;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
    }

    .a207-hero-pricing-row {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        margin-bottom: 0.7rem;
        flex-wrap: wrap;
    }
    .a207-hero-price-main {
        font-size: 1.5rem;
        font-weight: 800;
    }
    .a207-hero-price-sub {
        font-size: 0.78rem;
        color: #9ca3af;
    }

    .a207-hero-cta-row {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        flex-wrap: wrap;
    }
    .a207-hero-cta-primary {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.4rem 1.1rem;
        border-radius: 999px;
        border: 1px solid rgba(251,113,133,1);
        background: linear-gradient(135deg, #fb7185, #f97316);
        color: #111827;
        font-size: 0.86rem;
        font-weight: 700;
        cursor: pointer;
    }
    .a207-hero-cta-secondary {
        font-size: 0.8rem;
        color: #9ca3af;
    }

    .a207-hero-social-proof {
        margin-top: 0.55rem;
        font-size: 0.75rem;
        color: #9ca3af;
    }

    .a207-hero-board {
        border-radius: 18px;
        padding: 0.9rem 1rem;
        background: radial-gradient(circle at 10% 0%, rgba(15,23,42,1), #020617);
        box-shadow:
            0 18px 30px rgba(15,23,42,0.9),
            inset 0 0 0 1px rgba(15,23,42,1);
        display: flex;
        flex-direction: column;
        gap: 0.65rem;
    }
    .a207-hero-board-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.78rem;
        color: #9ca3af;
    }
    .a207-hero-board-header span:first-child {
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 600;
        color: #e5e7eb;
    }
    .a207-hero-board-games {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.6rem;
    }
    @media (max-width: 900px) {
        .a207-hero-board-games {
            grid-template-columns: minmax(0, 1fr);
        }
    }
    .a207-hero-game {
        border-radius: 14px;
        padding: 0.6rem 0.7rem;
        background: linear-gradient(135deg, rgba(15,23,42,1), rgba(30,64,175,0.45));
        border: 1px solid rgba(148,163,184,0.6);
        font-size: 0.8rem;
    }
    .a207-hero-game-title {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 0.2rem;
    }
    .a207-hero-game-teams {
        font-weight: 600;
    }
    .a207-hero-game-tip {
        font-size: 0.72rem;
        color: #cbd5f5;
    }
    .a207-hero-game-metrics {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        margin-top: 0.25rem;
        color: #e5e7eb;
    }
    .a207-hero-game-tag {
        font-size: 0.7rem;
        padding: 0.06rem 0.45rem;
        border-radius: 999px;
        background: rgba(15,23,42,0.95);
        border: 1px solid rgba(251,191,36,0.9);
        color: #facc15;
    }
    .a207-hero-board-footer {
        margin-top: 0.3rem;
        font-size: 0.76rem;
        color: #9ca3af;
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
    }

    /* FLAGSHIP CARDS – louder gradients */
    .a207-flagship-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1.1rem;
        margin-bottom: 1.4rem;
    }
    @media (max-width: 1300px) {
        .a207-flagship-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 800px) {
        .a207-flagship-grid { grid-template-columns: minmax(0, 1fr); }
    }

    .a207-flagship-card {
        position: relative;
        overflow: hidden;
        border-radius: 22px;
        padding: 1rem 1.1rem;
        background: radial-gradient(circle at 0% 0%, #020617, #020617);
        box-shadow:
            0 22px 40px rgba(15,23,42,0.95),
            inset 0 0 0 1px rgba(148,163,184,0.55);
        color: #e5e7eb;
        height: 180px;
    }
    .a207-flagship-card::before {
        content: "";
        position: absolute;
        inset: -30%;
        background:
            radial-gradient(circle at 0% 0%, rgba(56,189,248,0.7), transparent 55%),
            radial-gradient(circle at 100% 100%, rgba(59,130,246,0.45), transparent 60%);
        mix-blend-mode: screen;
        opacity: 0.9;
        pointer-events: none;
    }

    .a207-flagship-card[data-key="Prediction Hub"]::before {
        background:
            radial-gradient(circle at 0% 0%, rgba(244,114,182,0.9), transparent 55%),
            radial-gradient(circle at 100% 100%, rgba(251,146,60,0.6), transparent 60%);
    }
    .a207-flagship-card[data-key="Team Center"]::before {
        background:
            radial-gradient(circle at 0% 0%, rgba(129,140,248,0.95), transparent 55%),
            radial-gradient(circle at 100% 100%, rgba(56,189,248,0.6), transparent 60%);
    }
    .a207-flagship-card[data-key="Tournament Central"]::before {
        background:
            radial-gradient(circle at 0% 0%, rgba(250,204,21,0.95), transparent 55%),
            radial-gradient(circle at 100% 100%, rgba(248,113,113,0.65), transparent 60%);
    }

    .a207-flagship-inner {
        position: relative;
        z-index: 1;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .a207-flagship-tag-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #e5e7eb;
        margin-bottom: 0.3rem;
    }
    .a207-flagship-tag-pill {
        padding: 0.08rem 0.55rem;
        border-radius: 999px;
        border: 1px solid rgba(248,250,252,0.65);
        background: rgba(15,23,42,0.9);
    }
    .a207-flagship-title {
        font-size: 1.06rem;
        font-weight: 800;
        margin-bottom: 0.12rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .a207-flagship-desc {
        font-size: 0.82rem;
        color: #e5e7eb;
        max-width: 19rem;
    }
    .a207-flagship-metric {
        margin-top: 0.4rem;
        font-size: 0.8rem;
        color: #c4b5fd;
    }
    .a207-flagship-metric span {
        font-size: 1.15rem;
        font-weight: 800;
        color: #f9fafb;
        margin-right: 0.18rem;
    }



   </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Data model
# ----------------------------
@dataclass(frozen=True)
class HubPage:
    title: str
    desc: str
    icon: str
    path: str
    thumb: str | None


@dataclass(frozen=True)
class NavCard:
    group: str
    title: str
    desc: str
    icon: str
    path: str | None
    variant: str
    metric_label: str
    metric_value: str


def page_exists(path: str) -> bool:
    try:
        return Path(path).exists()
    except Exception:
        return False


# ----------------------------
# Page collections
# ----------------------------
PAGES_CORE = [
    HubPage("Schedules", "Upcoming games and model outlook.", "📅",
            "pages/01__Schedules.py", None),
    HubPage("Prediction Hub", "Model picks, previews, and daily hub.", "🧠",
            "pages/PredictionHub.py", None),
    HubPage("Team Center", "Team profiles, trends, and context.", "🏫",
            "pages/Team_Center.py", None),
    HubPage("The Data Desk", "Deep dives and tools in one place.", "📚",
            "pages/The_Data_Desk.py", None),
]

PAGES_RATINGS = [
    HubPage("Heal Points", "Health/availability signal powering adjustments.", "🩹",
            "pages/Heal_Points.py", None),
    HubPage("True Strength Ratings", "Core strength metric & leaderboards.", "📈",
            "pages/Truth_Strength_Ratings.py", None),
    HubPage("Performance", "Accuracy, calibration, hit rates, and trends.", "📊",
            "pages/Performance.py", None),
    HubPage("Insights", "Storylines and context from the metrics.", "💡",
            "pages/Insights.py", None),
]

PAGES_TOURNAMENT = [
    HubPage("Tournament Central", "Everything postseason in one place.", "🏆",
            "pages/Tournament_Central.py", None),
    HubPage("Bracketology", "Projected brackets and seeding snapshots.", "🧩",
            "pages/Bracketology.py", None),
    HubPage("Trophy Room", "Awards, champions, and season artifacts.", "🥇",
            "pages/Trophy_Room.py", None),
    HubPage("Team of the Week", "Weekly spotlight on standout performances.", "⭐",
            "pages/Team_of_the_Week.py", None),
]

PAGES_CHALLENGES = [
    HubPage("Pick 5 Challenge", "Make picks and track your accuracy.", "🎯",
            "pages/Pick_5_Challenge.py", None),
    HubPage("You vs The Model", "Public picks vs model picks.", "🗳️",
            "pages/You_vs_The_Model.py", None),
    HubPage("Fan Pulse", "What fans are feeling about teams and games.", "📣",
            "pages/Fan_Pulse.py", None),
    HubPage("Fan Hub", "Fan tools, leaderboards, and community.", "🧑‍🤝🧑",
            "pages/Fan_Hub.py", None),
]

PAGES_STORIES = [
    HubPage("Road Trip", "Travel-driven context and schedule spots.", "🚌",
            "pages/Road_Trip.py", None),
    HubPage("Milestones", "Records, streaks, and notable moments.", "🎯",
            "pages/Milestones.py", None),
    HubPage("The Model", "How ratings, spreads, and win % are built.", "🤖",
            "pages/The_Model.py", None),
    HubPage("Glossary", "Definitions for metrics and terminology.", "📖",
            "pages/Glossary.py", None),
]

# ----------------------------
# Nav card builders
# ----------------------------
def _build_nav_cards() -> list[NavCard]:
    cards: list[NavCard] = []
    

    # Keep your original cards, but FIX the one bad variant="Core"
    # (must be one of: core, ratings, tourn, challenges, stories)
    cards.append(
        NavCard(
            group="Premium",
            title="Teams Of The Week",
            desc="",
            icon="📅",
            path="pages/01__Schedules.py",
            variant="Tourn",
            metric_label="A weekly spotlight backed by performance signals and context—not just hype. Open it to see who earned the nod and what the numbers say made the difference.",
            metric_value="10",
        )
    )
    cards.append(
        NavCard(
            group="Premium",
            title="Performance",
            desc="",
            icon="🧠",
            path="pages/PredictionHub.py",
            variant="Tourn",
            metric_label="Proof the model is accountable—accuracy, calibration, and results tracked over time. If you want to know whether the edges hold up, this is the scoreboard.",
            metric_value="19",
        )
    )
    cards.append(
        NavCard(
            group="Premium",
            title="The Trophy Room",
            desc="",
            icon="🏫",
            path="pages/Team_Center.py",
            variant="Tourn",
            metric_label="The season metric champions at current time, these change weekely. Can your team hold on?!?!.",
            metric_value="132",
        )
    )
    cards.append(
        NavCard(
            group="Core",
            title="The Data Desk",
            desc="Filters, exports, and tools for building your own angles.",
            icon="📚",
            path="pages/The_Data_Desk.py",
            variant="ratings",
            metric_label="saved views available",
            metric_value="24",
        )
    )

    # Ratings & indices
    cards.append(
        NavCard(
            group="Core",
            title="Heal Points",
            desc="The official tournament qualification formula used by the MPA.",
            icon="🩹",
            path="pages/Heal_Points.py",
            variant="ratings",
            metric_label="programs with HP events",
            metric_value="48",
        )
    )
    cards.append(
        NavCard(
            group="Core",
            title="Schedules",
            desc="Every game across the state with matchup context and results.",
            icon="📈",
            path="pages/Truth_Strength_Ratings.py",
            variant="Ratings",
            metric_label="TSR updates this week",
            metric_value="7",
        )
    )
    cards.append(
        NavCard(
            group="Premium",
            title="Tournament Central",
            desc="",
            icon="📊",
            path="pages/Performance.py",
            variant="Tourn",
            metric_label="The postseason picture, organized—team quality, résumé signals, and bracket-ready context in one dashboard. It’s where “who gets in?” becomes a data-backed answer instead of a debate.",
            metric_value="57%",
        )
    )
    cards.append(
        NavCard(
            group="Premium",
            title="Bracketology",
            desc="",
            icon="💡",
            path="pages/Insights.py",
            variant="Tourn",
            metric_label="live insddddddddights on deck",
            metric_value="12",
        )
    )

    # Challenges
    cards.append(
        NavCard(
            group="Premium",
            title="Pick 5 Challenge",
            desc="Make five picks a night and chase the model.",
            icon="🎯",
            path="pages/Pick_5_Challenge.py",
            variant="Tourn",
            metric_label="Five picks a week, real scoring, real results—simple to enter, hard to win. Advantage to those who can pick upset winners consistantly!",
            metric_value="214",
        )
    )
    cards.append(
        NavCard(
            group="Premium",
            title="You vs The Model",
            desc="How public picks stack up against our numbers.",
            icon="🗳️",
            path="pages/You_vs_The_Model.py",
            variant="Tourn",
            metric_label="Let's see if the community (YOU) can beat The Model and see who performs over time. It’s competitive, transparent, and brutally honest about what works.",
            metric_value="31",
        )
    )
    cards.append(
        NavCard(
            group="Core",
            title="Fan Pulse",
            desc="Heat checks from the fanbase on every program.",
            icon="📣",
            path="pages/Fan_Pulse.py",
            variant="ratings",   # FIXED (was invalid "Core")
            metric_label="Turn fan opinion into measurable signal—votes, sentiment, and movement over time. It’s the fastest way to see which teams people believe in and where the public is drifting.",
            metric_value="NEW",
        )
    )
    cards.append(
        NavCard(
            group="Core",
            title="Fan Hub",
            desc="Leaderboards, streaks, and community‑driven tools.",
            icon="🧑‍🤝🧑",
            path="pages/Fan_Hub.py",
            variant="ratings",
            metric_label="active users this month",
            metric_value="312",
        )
    )

    # Stories & explainers
    cards.append(
        NavCard(
            group="Core",
            title="Road Trip",
            desc="Travel, back‑to‑backs, and schedule spots that matter.",
            icon="🚌",
            path="pages/Road_Trip.py",
            variant="ratings",
            metric_label="Travel and schedule spots quantified—distance, gas, bus trips. Who travels the furthest?",
            metric_value="180,259",
        )
    )
    cards.append(
        NavCard(
            group="Core",
            title="Milestones",
            desc="Records, streaks, and program‑defining moments.",
            icon="🎯",
            path="pages/Milestones.py",
            variant="ratings",
            metric_label="strddddddeaks of 5+ wins",
            metric_value="21",
        )
    )
    cards.append(
        NavCard(
            group="Core",
            title="Insights",
            desc="Exactly how we turn data into spreads and win odds.",
            icon="🤖",
            path="pages/The_Model.py",
            variant="ratings",
            metric_label="core components exposed",
            metric_value="9",
        )
    )
    cards.append(
        NavCard(
            group="Core",
            title="The Data Desk",
            desc="Plain‑language definitions for every metric we use.",
            icon="📖",
            path="pages/Glossary.py",
            variant="ratings",
            metric_label="metrics in the glossary",
            metric_value="70+",
        )
    )
    return cards









# ----------------------------
# Hero mini‑chart helpers
# ----------------------------
def _load_hero_teams_tsr_df() -> pd.DataFrame:
    df = pd.read_parquet(r"data/teams_team_season_core_v30.parquet")

    target = [
        ("Presque Isle", "Boys"),
        ("Oceanside", "Girls"),
        ("Portland", "Boys"),
        ("Hampden", "Girls"),
    ]

    mask = False
    for team, gender in target:
        mask |= ((df["Team"] == team) & (df["Gender"] == gender))

    snap = df.loc[mask, ["Team", "Gender", "TSR"]].copy()
    snap["Label"] = snap["Team"] + " " + snap["Gender"].str[0]
    snap = snap.sort_values("TSR", ascending=False)
    return snap


def mini_tsr_bar() -> None:
    df = _load_hero_teams_tsr_df()
    if df.empty:
        st.caption("No TSR snapshot available right now.")
        return

    fig = px.bar(
        df,
        x="Label",
        y="TSR",
        color_discrete_sequence=["#fbbf24"],
    )
    fig.update_layout(
        height=140,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,1)",
        font=dict(color="#e5e7eb", size=11),
        xaxis_title=None,
        yaxis_title=None,
    )
    fig.update_traces(marker_line_width=0)

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "staticPlot": True},
    )


def _load_hero_teams_form_df() -> pd.DataFrame:
    df = pd.read_parquet(r"data/teams_team_season_core_v30.parquet")

    target = [
        ("Presque Isle", "Boys"),
        ("Oceanside", "Girls"),
        ("Portland", "Boys"),
        ("Hampden", "Girls"),
    ]

    mask = False
    for team, gender in target:
        mask |= ((df["Team"] == team) & (df["Gender"] == gender))

    cols = ["Team", "Gender", "Last5MarginPG"]
    cols = [c for c in cols if c in df.columns]
    snap = df.loc[mask, cols].copy()

    if "Last5MarginPG" not in snap.columns and "L5MarginPG" in df.columns:
        snap["Last5MarginPG"] = df.loc[mask, "L5MarginPG"].values

    if "Last5MarginPG" not in snap.columns:
        return pd.DataFrame()

    snap["Label"] = snap["Team"] + " " + snap["Gender"].str[0]
    snap = snap.sort_values("Last5MarginPG", ascending=False)
    return snap


def mini_form_bar() -> None:
    df = _load_hero_teams_form_df()
    if df.empty:
        st.caption("No recent form snapshot available.")
        return

    fig = px.bar(
        df,
        x="Label",
        y="Last5MarginPG",
        color_discrete_sequence=["#38bdf8"],
    )
    fig.update_layout(
        height=140,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,1)",
        font=dict(color="#e5e7eb", size=11),
        xaxis_title=None,
        yaxis_title=None,
    )
    fig.update_traces(marker_line_width=0)

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "staticPlot": True},
    )


def _load_hero_teams_eff_df() -> pd.DataFrame:
    df = pd.read_parquet(r"data/teams_team_season_core_v30.parquet")

    target = [
        ("Presque Isle", "Boys"),
        ("Oceanside", "Girls"),
        ("Portland", "Boys"),
        ("Hampden", "Girls"),
    ]

    mask = False
    for team, gender in target:
        mask |= ((df["Team"] == team) & (df["Gender"] == gender))

    needed = ["Team", "Gender", "OffEff", "DefEff"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        return pd.DataFrame()

    snap = df.loc[mask, needed].copy()
    snap["Label"] = snap["Team"] + " " + snap["Gender"].str[0]
    return snap


def mini_eff_chart() -> None:
    df = _load_hero_teams_eff_df()
    if df.empty:
        st.caption("No efficiency snapshot available.")
        return

    if df[["OffEff", "DefEff"]].isna().all().all():
        st.caption("No efficiency snapshot available.")
        return

    long_df = df.melt(
        id_vars=["Label"],
        value_vars=["OffEff", "DefEff"],
        var_name="Metric",
        value_name="Value",
    ).dropna(subset=["Value"])

    if long_df.empty:
        st.caption("No efficiency snapshot available.")
        return

    fig = px.bar(
        long_df,
        x="Label",
        y="Value",
        color="Metric",
        barmode="group",
        color_discrete_map={"OffEff": "#f97316", "DefEff": "#6366f1"},
    )
    fig.update_layout(
        height=140,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,1)",
        font=dict(color="#e5e7eb", size=11),
        xaxis_title=None,
        yaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_traces(marker_line_width=0)

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "staticPlot": True},
    )

# ----------------------------
# Rendering helpers
# ----------------------------
def _render_hero_card() -> None:
    col_left, col_right = st.columns([1.2, 1.6])

    with col_left:
        st.markdown(
            """
            <div>
              <div class="a207-hero-tag">
                <span class="a207-hero-tag-dot"></span>
                <span>TONIGHT'S BOARD • RAITINGS. PREDICTIONS. EDGES.</span>
              </div>
              <div class="a207-hero-title">
                Every game, every edge,<br>🧠The model for the entire state.
              </div>
              <div class="a207-hero-sub">
                True Strength ratings, projected scores, and calculated spreads driven by real data analytics..
              </div>
              <div class="a207-hero-highlight">
                <span class="a207-hero-highlight-badge">NEW</span>
                <span>Full 2025–26 coverage for boys and girls programs statewide.</span>
              </div>
              <div class="a207-hero-pricing-row">
                <div>
                  <div class="a207-hero-price-main">$6<span style="font-size:0.9rem;">/mo</span></div>
                  <div class="a207-hero-price-sub">or $60 for the full season • cancel anytime</div>
                </div>
              </div>
              <div class="a207-hero-cta-row">
                <div class="a207-hero-cta-primary">
                  <span>Unlock EVERYTHING Now!</span>
                  <span>→</span>
                </div>
                <div class="a207-hero-cta-secondary">
                  Get 🧠The Model’s projections—spreads and projected scores—updated nightly..
                </div>
              </div>
              <div class="a207-hero-social-proof">
                Trusted by coaches, media, and hoops sickos across Maine.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            """
            <div class="a207-hero-board">
              <div class="a207-hero-board-header">
                <span>TONIGHT'S GAMES</span>
                <span>Model edges, TSR gaps, upset radar</span>
              </div>
              <div class="a207-hero-board-games">
                <div class="a207-hero-game">
                  <div class="a207-hero-game-title">
                    <div class="a207-hero-game-teams">Oceanside at Cony</div>
                    <div class="a207-hero-game-tip">TSR Δ 7.4 • 7:00 PM</div>
                  </div>
                  <div class="a207-hero-game-metrics">
                    <div>Cony win prob: <strong>68%</strong></div>
                    <div class="a207-hero-game-tag">EDGE: CONY </div>
                  </div>
                </div>
                <div class="a207-hero-game">
                  <div class="a207-hero-game-title">
                    <div class="a207-hero-game-teams">Bangor at Portland</div>
                    <div class="a207-hero-game-tip">TSR Δ 1.2 • 6:30 PM</div>
                  </div>
                  <div class="a207-hero-game-metrics">
                    <div>Portland win prob: <strong>54%</strong></div>
                    <div class="a207-hero-game-tag">CONFIDENCE - 50/50</div>
                  </div>
                </div>
                <div class="a207-hero-game">
                  <div class="a207-hero-game-title">
                    <div class="a207-hero-game-teams">Brewer at Hampden</div>
                    <div class="a207-hero-game-tip">Back‑to‑back • 7:00 PM</div>
                  </div>
                  <div class="a207-hero-game-metrics">
                    <div>Upset chance: <strong>31%</strong></div>
                    <div class="a207-hero-game-tag">WHO WILL WIN</div>
                  </div>
                </div>
                <div class="a207-hero-game">
                  <div class="a207-hero-game-title">
                    <div class="a207-hero-game-teams">Edward Little at Lewiston</div>
                    <div class="a207-hero-game-tip">Derby • TSR Δ 0.3</div>
                  </div>
                  <div class="a207-hero-game-metrics">
                    <div>Over 135.5: <strong>59%</strong></div>
                    <div class="a207-hero-game-tag">UPSET WATCH</div>
                  </div>
                </div>
              </div>
              <div class="a207-hero-board-footer">
                <span>Subscribers get data on every game statewide, predictions, projections and more!.</span>
                <span>Powered by 🧠 The Model's statewide rating engine.</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Shot share (TSR)")
            mini_tsr_bar()
        with c2:
            st.caption("Rating trend")
            mini_form_bar()
        with c3:
            st.caption("Edge breakdown")
            mini_eff_chart()


def _render_platform_grid(nav_cards: list[NavCard]) -> None:
    st.markdown("### Start with the core views")
    _sp(0)

    c1, c2, c3, c4 = st.columns(4)

    render_home_card(
        c1,
        kicker="PREMIUM",
        title="THE MODEL",
        sub="The fun predictive engine powering every projection, rating, and insight across the platform.",
        metric="230 Metrics",
        pill="Metrics Tracked",
        variant="tourn",
        ribbon_text="",
    )

    render_home_card(
        c2,
        kicker="PREMIUM",
        title="Prediction Hub",
        sub="Model spreads, win %, confidence indexing, and rolling performance metrics on every prediction.",
        metric="NEW!",
        pill="Games with edge",
        variant="tourn",
        ribbon_text="",
    )

    render_home_card(
        c3,
        kicker="PREMIUM",
        title="Team Center",
        sub="Efficiency profiles, model outputs, award tracking, fan metrics, in one consolidated view.",
        metric="258 Teams",
        pill="Teams tracked",
        variant="tourn",
        ribbon_text="",
    )

    render_home_card(
        c4,
        kicker="PREMIUM",
        title="True Strength Rating (TSR)",
        sub="A statewide power index measuring true team quality beyond wins and losses.",
        metric="A/B/C/D/S",
        pill="Brackets tracked",
        variant="tourn",
        ribbon_text="TEST",
    )

    _sp(2)

    st.markdown("### More tools (Core + Premium)")
    st.caption(
        "More ratings, tools, and explainers built on the same engine — "
        "Some are free, some require Premium—look for the badge."
    )
    _sp(0)

    # IMPORTANT: render using the per-card variant (supports mixed rows)
    cards_per_row = 4
    cols = st.columns(cards_per_row)
    for idx, card in enumerate(nav_cards):
        col = cols[idx % cards_per_row]
        render_home_card(
            col,
            kicker=("PREMIUM" if card.group.strip().lower() == "premium" else "CORE"),
            title=card.title,
            sub=card.desc,
            metric=card.metric_value,
            pill=card.metric_label,
            variant=card.variant,
            ribbon_text="",
        )


# ----------------------------
# Render page
# ----------------------------
_render_hero_card()

nav_cards = _build_nav_cards()
_sp(1)
_render_platform_grid(nav_cards)

_sp(2)
if callable(render_footer):
    render_footer()
else:
    st.caption("© 2026 Analytics207")



