from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import importlib.util
import shutil
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = Path(r"C:\ANALYTICS207")
DATA_DIR = ROOT / "data"

ENGINE_VERSION = "v34c_prod_20260208"

TRUTH_PATH = DATA_DIR / "truth.csv"

TEAMS_OUT = DATA_DIR / "teams_team_season_core_v30.parquet"
GAMES_OUT = DATA_DIR / "games_game_core_v30.parquet"

# Debug copy to validate nightly output vs core
TEAMS_DEBUG_OUT = DATA_DIR / "teams_team_season_core_v30_FROM_NIGHTLY.parquet"

PERF_SUMMARY_OUT = DATA_DIR / "performance_summary_v30.parquet"
PERF_GAMES_OUT = DATA_DIR / "performance_games_v30.parquet"
PERF_CALIB_OUT = DATA_DIR / "performance_calibration_v30.parquet"
PERF_SPREAD_OUT = DATA_DIR / "performance_by_spread_v30.parquet"

PRED_CURRENT_OUT = DATA_DIR / "games_predictions_current.parquet"
PRED_ARCHIVE_DIR = DATA_DIR / "predictions" / "archives"

# Trophy Room output (consumed by the Streamlit page)
TROPHY_OUT = DATA_DIR / "trophy_room_v30.parquet"

# NEW: Team of the Week nominees output (consumed by voting page)
TEAM_OF_WEEK_OUT = DATA_DIR / "team_of_week_nominees.parquet"

V34C_SCRIPT = ROOT / "walkforward" / "v34" / "walk_forward_scorespread_v34c.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.core_v30 import (  # type: ignore
    build_core_v30,
    build_performance_tables_v30,
    _enrich_games_v30,
    _enrich_teams_from_games_v30,  # imported but not used (kept for now)
)
import core.core_v30 as cv30

print("Nightly core_v30 file:", cv30.__file__)
print("Nightly identity:", getattr(cv30, "CORE_V30_IDENTITY", "MISSING"))


def _atomic_write_parquet(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet", dir=str(out_path.parent)) as tmp:
        tmp_path = Path(tmp.name)
    df.to_parquet(tmp_path, index=False)
    tmp_path.replace(out_path)


def _run_v34c_main() -> None:
    if not V34C_SCRIPT.exists():
        raise FileNotFoundError(f"Missing v34c script at {V34C_SCRIPT}")

    spec = importlib.util.spec_from_file_location("v34c_mod", str(V34C_SCRIPT))
    if spec is None:
        raise RuntimeError(f"Could not create import spec for {V34C_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if loader is None:
        raise RuntimeError("Could not load v34c module loader")
    loader.exec_module(mod)

    if not hasattr(mod, "main"):
        raise RuntimeError("v34c script has no main function")

    mod.main()

    if not PRED_CURRENT_OUT.exists():
        raise RuntimeError(f"v34c did not write expected file {PRED_CURRENT_OUT}")


def _validate_predictions(games: pd.DataFrame, pred: pd.DataFrame) -> None:
    for c in [
        "GameID",
        "PredHomeWinProb",
        "PredMargin",
        "PredHomeScore",
        "PredAwayScore",
        "PredTotalPoints",
        "CoreVersion",
    ]:
        if c not in pred.columns:
            raise RuntimeError(f"games_predictions_current missing required column: {c}")

    pred["GameID"] = pred["GameID"].astype(str).str.strip()
    games_ids = set(games["GameID"].astype(str).str.strip().dropna().unique().tolist())
    pred_ids = set(pred["GameID"].dropna().unique().tolist())

    if len(pred) != len(games):
        raise RuntimeError(f"Pred row mismatch: pred={len(pred)} games={len(games)}")

    if games_ids != pred_ids:
        overlap = len(games_ids.intersection(pred_ids))
        raise RuntimeError(
            f"Pred GameID set mismatch. overlap={overlap} "
            f"games={len(games_ids)} pred={len(pred_ids)}"
        )

    if pred["CoreVersion"].nunique() != 1:
        raise RuntimeError("CoreVersion not uniform in games_predictions_current")
    if str(pred["CoreVersion"].iloc[0]) != ENGINE_VERSION:
        raise RuntimeError(f"CoreVersion unexpected: {pred['CoreVersion'].iloc[0]} != {ENGINE_VERSION}")


# ----------------- Trophy Room v30 builder -----------------
def build_trophy_room_v30(teams: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """
    Build Trophy Room rows for Streamlit.

    First draft:
    - Uses team-season core metrics (teams_team_season_core_v30.parquet) for breadth.
    - Keeps schema compatible with the existing Trophy Room page (Scope/Gender/Class/Region/Category/... + Card fields).
    - Latest season only for now to keep output clean (no page changes required).
    """
    required = ["TeamKey", "Team", "Gender", "Class", "Region", "Season"]
    for c in required:
        if c not in teams.columns:
            raise RuntimeError(f"teams missing required column: {c}")

    seasons = sorted([str(x) for x in teams["Season"].dropna().unique().tolist() if str(x).strip() != ""])
    if not seasons:
        raise RuntimeError("teams has no Season values")
    season_latest = seasons[-1]

    t = teams[teams["Season"].astype(str) == season_latest].copy()

    TROPHY_DEFS = [
        ("Strength & resume", 10, "Top TSR", 10, "TSR", "max", "Strength & resume"),
        ("Strength & resume", 10, "Top PI", 20, "PI", "max", "Strength & resume"),
        ("Strength & resume", 10, "Top TI", 30, "TI", "max", "Strength & resume"),
        ("Strength & resume", 10, "Best RPI", 40, "RPI", "max", "Strength & resume"),
        ("Strength & resume", 10, "Best SOS (EWP)", 50, "SOS_EWP", "max", "Strength & resume"),
        ("Clutch & dominance", 20, "Best Close Win%", 10, "CloseWinPct", "max", "Clutch & dominance"),
        ("Clutch & dominance", 20, "Best Clutch Close Win%", 20, "ClutchCloseGameWinPct", "max", "Clutch & dominance"),
        ("Clutch & dominance", 20, "Highest Blowout Rate", 30, "BlowoutRate", "max", "Clutch & dominance"),
        ("Clutch & dominance", 20, "Biggest blowouts (margin)", 40, "BlowoutMarginPG", "max", "Clutch & dominance"),
        ("Offense & defense", 30, "Best NetEff", 10, "NetEff", "max", "Offense & defense"),
        ("Offense & defense", 30, "Best OffEff", 20, "OffEff", "max", "Offense & defense"),
        ("Offense & defense", 30, "Best DefEff", 30, "DefEff", "min", "Offense & defense"),
        ("Offense & defense", 30, "Most points per game", 40, "PPG", "max", "Offense & defense"),
        ("Offense & defense", 30, "Toughest defense (low OPPG)", 50, "OPPG", "min", "Offense & defense"),
        ("Road, home & neutral", 40, "Best Road Win%", 10, "RoadWinPct", "max", "Road, home & neutral"),
        ("Road, home & neutral", 40, "Best Home Win%", 20, "HomeWinPct", "max", "Road, home & neutral"),
        ("Road, home & neutral", 40, "Best Neutral Win%", 30, "NeutralWinPct", "max", "Road, home & neutral"),
        ("Road, home & neutral", 40, "Biggest home/road split", 40, "HomeRoadDiff", "max", "Road, home & neutral"),
        ("Momentum & streaks", 50, "Best Last5 Margin", 10, "Last5MarginPG", "max", "Momentum & streaks"),
        ("Momentum & streaks", 50, "Best Last10 Margin", 20, "Last10MarginPG", "max", "Momentum & streaks"),
        ("Momentum & streaks", 50, "Longest win streak", 30, "WinsInRow", "max", "Momentum & streaks"),
        ("Consistency & grit", 60, "Best Win%", 10, "WinPct", "max", "Consistency & grit"),
        ("Consistency & grit", 60, "Most Consistent (low std)", 20, "MarginStd", "min", "Consistency & grit"),
        ("Consistency & grit", 60, "Most Consistent (low std L10)", 30, "MarginStdL10", "min", "Consistency & grit"),
    ]

    def _winner(df: pd.DataFrame, metric_col: str, direction: str):
        s = pd.to_numeric(df[metric_col], errors="coerce")
        d = df.loc[s.notna()].copy()
        if d.empty:
            return None
        d["_m"] = pd.to_numeric(d[metric_col], errors="coerce")
        asc = True if direction == "min" else False
        return d.sort_values(["_m", "Team"], ascending=[asc, True]).iloc[0]

    rows: list[dict] = []

    def _emit(scope: str, df: pd.DataFrame):
        for (cat, cat_sort, trophy_name, trophy_sort, metric_col, direction, kicker) in TROPHY_DEFS:
            if metric_col not in df.columns:
                continue

            if scope == "Gender":
                group_cols = ["Gender"]
            elif scope == "GenderClass":
                group_cols = ["Gender", "Class"]
            else:
                group_cols = ["Gender", "Class", "Region"]

            for _, gdf in df.groupby(group_cols, dropna=False):
                w = _winner(gdf, metric_col, direction)
                if w is None:
                    continue

                gender = str(w["Gender"])
                cls = str(w["Class"]) if scope != "Gender" else ""
                region = str(w["Region"]) if scope == "GenderClassRegion" else ""

                metric_val = pd.to_numeric(w[metric_col], errors="coerce")
                if pd.isna(metric_val):
                    continue

                team_name = str(w["Team"])
                record = ""
                if "Record" in df.columns and pd.notna(w.get("Record", None)):
                    record = str(w["Record"])

                rows.append(
                    dict(
                        Season=season_latest,
                        Scope=scope,
                        Gender=gender,
                        Class=cls,
                        Region=region,
                        Category=cat,
                        CategorySort=int(cat_sort),
                        TrophyName=trophy_name,
                        TrophySort=int(trophy_sort),
                        CardKicker=kicker,
                        CardTitle=team_name,
                        CardSub=(record if record else f"Leads {metric_col}"),
                        CardMetric=float(metric_val),
                    )
                )

    _emit("Gender", t)
    _emit("GenderClass", t)
    _emit("GenderClassRegion", t)

    return pd.DataFrame(rows)


# ----------------- NEW: Team of the Week nominees v30 builder -----------------
def _week_bounds(anchor_date: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    d = pd.Timestamp(anchor_date).normalize()
    start = d - pd.Timedelta(days=d.weekday())  # Monday
    end = start + pd.Timedelta(days=6)
    return start, end


def _zscore(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    mu = x.mean()
    sd = x.std(ddof=0)
    if sd == 0 or pd.isna(sd):
        return pd.Series(np.zeros(len(x)), index=s.index)
    return (x - mu) / sd


def build_team_of_week_nominees_v30(games: pd.DataFrame) -> pd.DataFrame:
    """
    Build Team-of-the-Week nominees: top 2 teams per (Gender, Class, Region)
    for the latest week containing the latest played game in the dataset.

    Uses per-game scoring with a games-played confidence adjustment so
    1-game weeks are eligible but penalized.
    """
    g = games.copy()
    if "Date" not in g.columns:
        raise RuntimeError("games missing Date")

    g["Date"] = pd.to_datetime(g["Date"], errors="coerce")
    g = g[g["Date"].notna()].copy()
    g["DateOnly"] = g["Date"].dt.normalize()

    if "Played" in g.columns:
        g = g[g["Played"] == True].copy()

    if g.empty:
        return pd.DataFrame()

    anchor = g["DateOnly"].max()
    week_start, week_end = _week_bounds(anchor)

    wk = g[(g["DateOnly"] >= week_start) & (g["DateOnly"] <= week_end)].copy()
    if wk.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    week_id = f"{week_start.date()}_to_{week_end.date()}"

    for _, r in wk.iterrows():
        gid = r.get("GameID")
        date = r.get("DateOnly")
        gender = r.get("Gender")

        home_key, away_key = r.get("HomeKey"), r.get("AwayKey")
        home, away = r.get("Home"), r.get("Away")
        home_class, away_class = r.get("HomeClass"), r.get("AwayClass")
        home_region, away_region = r.get("HomeRegion"), r.get("AwayRegion")

        home_rating = pd.to_numeric(r.get("HomeRating"), errors="coerce")
        away_rating = pd.to_numeric(r.get("AwayRating"), errors="coerce")

        actual_home = pd.to_numeric(r.get("ActualMargin"), errors="coerce")
        if pd.isna(actual_home):
            hs = pd.to_numeric(r.get("HomeScore"), errors="coerce")
            aS = pd.to_numeric(r.get("AwayScore"), errors="coerce")
            actual_home = (hs - aS) if pd.notna(hs) and pd.notna(aS) else np.nan

        pred_home = pd.to_numeric(r.get("PredMargin"), errors="coerce")
        winflag = pd.to_numeric(r.get("WinFlag"), errors="coerce")

        rows.append(
            {
                "WeekID": week_id,
                "WeekStart": week_start,
                "WeekEnd": week_end,
                "Segment": f"{gender}_{home_class}_{home_region}",
                "Gender": gender,
                "Class": home_class,
                "Region": home_region,
                "GameID": gid,
                "Date": date,
                "TeamKey": home_key,
                "Team": home,
                "OppRating": away_rating,
                "TeamActualMargin": float(actual_home) if pd.notna(actual_home) else np.nan,
                "TeamPredMargin": float(pred_home) if pd.notna(pred_home) else np.nan,
                "WinFlag": winflag,
            }
        )

        rows.append(
            {
                "WeekID": week_id,
                "WeekStart": week_start,
                "WeekEnd": week_end,
                "Segment": f"{gender}_{away_class}_{away_region}",
                "Gender": gender,
                "Class": away_class,
                "Region": away_region,
                "GameID": gid,
                "Date": date,
                "TeamKey": away_key,
                "Team": away,
                "OppRating": home_rating,
                "TeamActualMargin": (-float(actual_home)) if pd.notna(actual_home) else np.nan,
                "TeamPredMargin": (-float(pred_home)) if pd.notna(pred_home) else np.nan,
                "WinFlag": winflag,
            }
        )

    tg = pd.DataFrame(rows)
    tg["CappedMargin"] = pd.to_numeric(tg["TeamActualMargin"], errors="coerce").clip(-25, 25)
    tg["Surprise"] = pd.to_numeric(tg["TeamActualMargin"], errors="coerce") - pd.to_numeric(
        tg["TeamPredMargin"], errors="coerce"
    )

    tg["z_margin"] = tg.groupby("Segment")["CappedMargin"].transform(_zscore)
    tg["z_opp"] = tg.groupby("Segment")["OppRating"].transform(_zscore)
    tg["z_surprise"] = tg.groupby("Segment")["Surprise"].transform(_zscore)

    tg["GameScore"] = 0.60 * tg["z_margin"] + 0.25 * tg["z_opp"] + 0.15 * tg["z_surprise"]

    team_week = (
        tg.groupby(
            ["WeekID", "WeekStart", "WeekEnd", "Segment", "Gender", "Class", "Region", "TeamKey", "Team"], dropna=False
        )
        .agg(
            Games=("GameID", "count"),
            Wins=("WinFlag", lambda s: int(pd.to_numeric(s, errors="coerce").fillna(0).sum())),
            AvgMargin=("TeamActualMargin", "mean"),
            AvgOppRating=("OppRating", "mean"),
            AvgSurprise=("Surprise", "mean"),
            MeanGameScore=("GameScore", "mean"),
        )
        .reset_index()
    )

    n = team_week["Games"].clip(lower=1)
    team_week["Confidence"] = np.sqrt(n / 2.0).clip(upper=1.25)
    team_week["WeeklyScore"] = team_week["MeanGameScore"] * team_week["Confidence"]

    team_week = team_week.sort_values(["Segment", "WeeklyScore"], ascending=[True, False])
    team_week["RankInSegment"] = team_week.groupby("Segment").cumcount() + 1
    nominees = team_week[team_week["RankInSegment"] <= 2].copy()

    return nominees


def main() -> None:
    print("Rebuilding TEAMS_OUT and GAMES_OUT via build_core_v30...")
    teams, games = build_core_v30(TRUTH_PATH)

    wanted = ["TeamKey", "Team", "Gender", "Class", "Region", "Season"]
    print("Nightly (rebuilt) teams identity present:", [c for c in wanted if c in teams.columns])

    games = _enrich_games_v30(games)

    # Write core outputs (pre-v34c)
    _atomic_write_parquet(teams, TEAMS_OUT)
    _atomic_write_parquet(games, GAMES_OUT)
    teams.to_parquet(TEAMS_DEBUG_OUT, index=False)

    # Build + write Team of the Week nominees
    team_of_week = build_team_of_week_nominees_v30(games=games)
    _atomic_write_parquet(team_of_week, TEAM_OF_WEEK_OUT)
    print(f"Wrote {len(team_of_week):,} Team of the Week nominee rows to {TEAM_OF_WEEK_OUT}")

    # Build + write Trophy Room parquet (v30)
    trophy = build_trophy_room_v30(teams=teams, games=games)
    _atomic_write_parquet(trophy, TROPHY_OUT)
    print(f"Wrote {len(trophy):,} trophy rows to {TROPHY_OUT}")

    # Archive prior predictions-current (before v34c overwrites it)
    PRED_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if PRED_CURRENT_OUT.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prior = PRED_ARCHIVE_DIR / f"games_predictions_current_before_{stamp}.parquet"
        shutil.copy2(PRED_CURRENT_OUT, prior)

    # Run v34c and load predictions
    _run_v34c_main()
    pred = pd.read_parquet(PRED_CURRENT_OUT)
    _validate_predictions(games, pred)

    def _clean_gameid(s: pd.Series) -> pd.Series:
        x = s.astype(str).str.strip()
        x = x.str.replace(r"\.0$", "", regex=True)
        x = x.str.replace(",", "", regex=False)
        return x

    # Normalize IDs
    games = games.copy()
    pred = pred.copy()
    games["GameID"] = _clean_gameid(games["GameID"])
    pred["GameID"] = _clean_gameid(pred["GameID"])

    # Authoritative prediction columns from v34c
    pred_cols = [
        "GameID",
        "PredHomeWinProb",
        "PredMargin",
        "PredHomeScore",
        "PredAwayScore",
        "PredTotalPoints",
        "CoreVersion",
    ]
    pred_keep = [c for c in pred_cols if c in pred.columns]
    pred2 = pred[pred_keep].drop_duplicates(subset=["GameID"], keep="first").copy()

    # Drop any existing prediction columns from games-core, then merge v34c in
    for c in pred_cols:
        if c != "GameID" and c in games.columns:
            games = games.drop(columns=[c])

    games = games.merge(pred2, on="GameID", how="left")

    # Guardrail: predictions must be present for every game
    missing_pm = int(pd.to_numeric(games["PredMargin"], errors="coerce").isna().sum())
    missing_wp = int(pd.to_numeric(games["PredHomeWinProb"], errors="coerce").isna().sum())
    if missing_pm != 0 or missing_wp != 0:
        raise RuntimeError(f"After v34c merge: missing PredMargin={missing_pm}, PredHomeWinProb={missing_wp}")

    # Rewrite games-core so all pages use one prediction truth
    _atomic_write_parquet(games, GAMES_OUT)

    # Build performance off the unified games dataframe
    perf_summary, perf_games, perf_calib, perf_spread = build_performance_tables_v30(games)

    _atomic_write_parquet(perf_summary, PERF_SUMMARY_OUT)
    _atomic_write_parquet(perf_games, PERF_GAMES_OUT)
    _atomic_write_parquet(perf_calib, PERF_CALIB_OUT)
    _atomic_write_parquet(perf_spread, PERF_SPREAD_OUT)

    print(f"Wrote {len(teams)} teams (rebuilt) to {TEAMS_OUT}")
    print(f"Wrote {len(games)} games (rebuilt+enriched+v34c preds) to {GAMES_OUT}")
    print(f"Wrote {len(pred)} rows to {PRED_CURRENT_OUT}")
    print(f"CoreVersion locked to: {ENGINE_VERSION}")
    print(f"Wrote v30 performance summary to {PERF_SUMMARY_OUT}")
    print(f"Wrote nightly debug teams to {TEAMS_DEBUG_OUT}")


if __name__ == "__main__":
    main()
