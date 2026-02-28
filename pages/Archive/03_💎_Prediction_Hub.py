from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
    spacer,
    TableColumn,
    render_html_table,
    render_performance_strip,
)


st.set_page_config(page_title="The Model's Prediction", layout="wide")


def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name.lower() == "pages":
        return here.parent.parent
    return here.parent


ROOT = _find_project_root()
DATA_DIR = ROOT / "data"

PRED_PATH = DATA_DIR / "games_predictions_current.parquet"
GAMES_PATH = DATA_DIR / "games_game_core_v30.parquet"


@st.cache_data(show_spinner=False)
def load_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_parquet(path)


def _norm_str(s: pd.Series) -> pd.Series:
    return s.astype("string").fillna("").str.strip()


def build_view(games: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    g = games.copy()
    g["GameID"] = _norm_str(g["GameID"])

    p = pred.copy()
    if "GameID" in p.columns:
        p["GameID"] = _norm_str(p["GameID"])
        # If pred has duplicates per GameID, keep last row
        if p["GameID"].duplicated().any():
            p = p.sort_values("GameID").drop_duplicates("GameID", keep="last")
        g = g.merge(p, on="GameID", how="left", suffixes=("", "_p"))

    date_raw = pd.to_datetime(g.get("Date"), errors="coerce")
    date_str = date_raw.dt.strftime("%b %d").fillna("")

    home = _norm_str(g.get("Home", pd.Series([""] * len(g))))
    away = _norm_str(g.get("Away", pd.Series([""] * len(g))))

    gender = _norm_str(g.get("Gender", pd.Series([""] * len(g))))
    home_class = _norm_str(g.get("HomeClass", pd.Series([""] * len(g))))
    away_class = _norm_str(g.get("AwayClass", pd.Series([""] * len(g))))
    home_region = _norm_str(g.get("HomeRegion", pd.Series([""] * len(g))))
    away_region = _norm_str(g.get("AwayRegion", pd.Series([""] * len(g))))

    phwp = pd.to_numeric(g.get("PredHomeWinProb"), errors="coerce")
    pred_home_wins = phwp >= 0.5
    pred_winner = np.where(pred_home_wins, home, away)

    if "FavProb" in g.columns and g["FavProb"].notna().any():
        conf = pd.to_numeric(g["FavProb"], errors="coerce")
    else:
        conf = np.where(pred_home_wins, phwp, 1 - phwp)

    spread = pd.to_numeric(g.get("PredMargin"), errors="coerce")
    spread_pts = spread.abs()

    hs = pd.to_numeric(g.get("HomeScore"), errors="coerce")
    aw = pd.to_numeric(g.get("AwayScore"), errors="coerce")

    played = g.get("Played")
    if played is None:
        played = (hs.notna() & aw.notna())
    played = pd.Series(played, index=g.index).astype(bool)

    actual_winner = _norm_str(g.get("WinnerTeam", pd.Series([""] * len(g))))
    has_actual = played & actual_winner.ne("")

    correct = np.where(
        has_actual,
        _norm_str(pd.Series(pred_winner, index=g.index)).eq(actual_winner),
        None,
    )

    out = pd.DataFrame(
        {
            "Date": date_str,
            "Gender": gender,
            "Class": home_class,
            "AwayClass": away_class,
            "Region": home_region,
            "AwayRegion": away_region,
            "Home": home,
            "Away": away,
            "PredWinner": _norm_str(pd.Series(pred_winner, index=g.index)),
            "SpreadPts": spread_pts,
            "Conf": conf,
            "HomeScore": hs,
            "AwayScore": aw,
            "Correct": pd.Series(correct, index=g.index),
            "_DateSort": date_raw,
            "_Played": played,
        }
    )

    return out.sort_values(["_DateSort", "Home", "Away"], ascending=[True, True, True])


def _default_index(options: list[str], target: str) -> int:
    tl = target.strip().lower()
    for i, v in enumerate(options):
        if str(v).strip().lower() == tl:
            return i
    return 0


def render_prediction_hub_body() -> None:
    pred = load_parquet(PRED_PATH)
    games = load_parquet(GAMES_PATH)

    df = build_view(games, pred)

    spacer(1)

    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

    genders = [g for g in sorted(df["Gender"].dropna().unique().tolist()) if str(g).strip()]
    classes = [c for c in sorted(pd.concat([df["Class"], df["AwayClass"]]).dropna().unique().tolist()) if str(c).strip()]
    regions = [r for r in sorted(pd.concat([df["Region"], df["AwayRegion"]]).dropna().unique().tolist()) if str(r).strip()]

    with c1:
        gender = st.selectbox("Gender", genders, index=_default_index(genders, "boys") if genders else 0)
    with c2:
        sel_class = st.selectbox("Class", classes, index=_default_index(classes, "a") if classes else 0)
    with c3:
        region = st.selectbox("Region", regions, index=_default_index(regions, "north") if regions else 0)
    with c4:
        search = st.text_input("Search team", placeholder="Enter Team")

    q = df.copy()
    if gender:
        q = q[q["Gender"].str.lower() == str(gender).lower()]

    team_mode = bool(search.strip())

    if sel_class:
        if team_mode:
            sc = str(sel_class).lower()
            q = q[(q["Class"].str.lower() == sc) | (q["AwayClass"].str.lower() == sc)]
        else:
            q = q[q["Class"].str.lower() == str(sel_class).lower()]

    if region:
        if team_mode:
            sr = str(region).lower()
            q = q[(q["Region"].str.lower() == sr) | (q["AwayRegion"].str.lower() == sr)]
        else:
            q = q[q["Region"].str.lower() == str(region).lower()]

    if team_mode:
        s = search.strip()
        q = q[q["Home"].str.contains(s, case=False, na=False) | q["Away"].str.contains(s, case=False, na=False)]

    label = "Performance" if not team_mode else f"Performance for {search.strip().upper()}"

    played_df = q[q["_Played"]].copy()
    total_games = int(len(q))
    played_games = int(len(played_df))
    correct_games = int(pd.to_numeric(played_df["Correct"], errors="coerce").fillna(0).sum()) if played_games else 0

    render_performance_strip(total_games, played_games, correct_games, label=label)

    cols = [
        TableColumn("Date", "Date", kind="mono"),
        TableColumn("Home", "Home"),
        TableColumn("Away", "Away"),
        TableColumn("Favorite", "PredWinner"),
        TableColumn("Spread", "SpreadPts", kind="mono"),
        TableColumn("Confidence", "Conf", kind="pill_conf"),
        TableColumn("Final", "Final", kind="final_score"),
        TableColumn("Result", "Correct", kind="result_icon"),
    ]

    # FIX: Spread decimals only
    q = q.copy()
    q["SpreadPts"] = pd.to_numeric(q["SpreadPts"], errors="coerce").round(1)

    render_html_table(q, cols, title="Full Games List")


def main() -> None:
    apply_global_layout_tweaks()
    render_logo()
    render_page_header(
        title="🎯Prediction Hub",
        definition="Prediction Hub (n.): Where projections meet accountability.",
        subtitle="Model spreads, win probabilities, confidence tiers, and full season performance tracking.",
    )
    spacer(1)
    render_prediction_hub_body()
    spacer(2)
    render_footer()


if __name__ == "__main__":
    main()
