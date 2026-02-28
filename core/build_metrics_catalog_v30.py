#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\ANALYTICS207")
CORE = ROOT / "core"
DATA = ROOT / "data"

CATALOG_IN = CORE / "metrics_catalog.csv"
CATALOG_OUT = CORE / "metrics_catalog_v30.csv"

TEAMS_PARQUET = DATA / "teams_team_season_core_v30.parquet"
GAMES_PARQUET = DATA / "games_game_core_v30.parquet"
PERF_PARQUET = DATA / "performance_summary_v30.parquet"


def load_catalog() -> pd.DataFrame:
    cat = pd.read_csv(CATALOG_IN)
    required = {"metric_key", "column", "source", "group", "label", "active"}
    missing = required - set(cat.columns)
    if missing:
        raise ValueError(f"Catalog missing required columns: {missing}")
    return cat


def ensure_row(cat: pd.DataFrame,
               metric_key: str,
               column: str,
               source: str,
               group: str,
               label: str,
               short_label: str | None = None,
               fmt: str | None = None,
               unit: str | None = None,
               description: str | None = None,
               active: int = 1) -> pd.DataFrame:
    """
    Ensure a single row exists; if it does, keep existing values and only
    update source if needed.
    """
    mask = (cat["metric_key"] == metric_key)
    if mask.any():
        # If it exists, optionally fix source but otherwise leave as-is
        idx = cat.index[mask][0]
        if cat.at[idx, "source"] != source:
            cat.at[idx, "source"] = source
        return cat

    row = {
        "metric_key": metric_key,
        "column": column,
        "label": label,
        "short_label": short_label or "",
        "source": source,
        "group": group,
        "format": fmt or "",
        "unit": unit or "",
        "description": description or "",
        "active": active,
    }
    return pd.concat([cat, pd.DataFrame([row])], ignore_index=True)


def sync_teams(cat: pd.DataFrame) -> pd.DataFrame:
    teams_cols = pd.read_parquet(TEAMS_PARQUET).columns.tolist()

    # Promote any teams_core_future metrics that exist in data
    for col in teams_cols:
        mask = (cat["column"] == col) & (cat["source"] == "teams_core_future")
        cat.loc[mask, "source"] = "teams_core_v30"

    # Ensure required teams_core_v30 rows exist for every TEAMS column
    for col in teams_cols:
        if not ((cat["column"] == col) & (cat["source"] == "teams_core_v30")).any():
            # Simple grouping heuristics based on name
            if col in {"TeamKey", "Team", "Gender", "Class", "Region",
                       "Division", "Season"}:
                group = "Team Identity & Context"
            elif "Rest" in col or "Games" in col or "Wins" in col or "Losses" in col or "Record" in col:
                group = "Basic Results & Record"
            elif "PPG" in col or "Margin" in col or "Score" in col:
                group = "Scoring & Margin"
            elif "Close" in col or "Blowout" in col:
                group = "Close Games & Blowouts"
            elif "Q1_" in col or "Q2_" in col or "Q3_" in col or "Q4_" in col:
                group = "Resume & Quality Wins/Losses"
            else:
                group = "Other Team Metrics"

            label = col  # you can refine later
            cat = ensure_row(
                cat,
                metric_key=col,
                column=col,
                source="teams_core_v30",
                group=group,
                label=label,
                active=0 if group == "Other Team Metrics" else 1,
            )

    return cat


def sync_games(cat: pd.DataFrame) -> pd.DataFrame:
    games_cols = pd.read_parquet(GAMES_PARQUET).columns.tolist()

    # Promote any games_core_future metrics that exist in data
    for col in games_cols:
        mask = (cat["column"] == col) & (cat["source"].str.startswith("games_core"))
        # if it exists under some other games_* source, force to games_core_v30
        cat.loc[mask, "source"] = "games_core_v30"

    # Ensure rows for every games column
    for col in games_cols:
        if not ((cat["column"] == col) & (cat["source"] == "games_core_v30")).any():
            if col in {"GameID", "Date", "Season", "Gender",
                       "Home", "Away", "HomeKey", "AwayKey",
                       "HomeClass", "AwayClass",
                       "HomeRegion", "AwayRegion",
                       "HomeDivision", "AwayDivision",
                       "GameNum"}:
                group = "Game Details"
            elif col in {"HomeScore", "AwayScore", "Margin", "ActualMargin"} \
                    or "PPG" in col or "OPPG" in col or "NetEff" in col or "AvgTotal" in col:
                group = "Scoring & Margin"
            elif col in {"TI", "PI", "Rank", "RecordText",
                         "WinPoints", "OppPreliminaryIndex",
                         "HomeTI", "AwayTI", "HomePI", "AwayPI",
                         "HomeRank", "AwayRank"}:
                group = "Tournament & Preliminary Indices"
            elif col in {"PredHomeWinProb", "PredMargin",
                         "PredHomeScore", "PredAwayScore",
                         "PredTotalPoints", "FavoriteIsHome",
                         "FavoriteTeamKey", "FavProb", "ModelCorrect"}:
                group = "Model Predictions"
            elif col in {"Played", "WinFlag", "LossFlag", "TieFlag", "Winner", "WinnerTeam"}:
                group = "Flags & Outcomes"
            elif col in {"ScrapedAt", "CoreVersion"}:
                group = "Metadata"
            else:
                group = "Other Game Metrics"

            label = col
            cat = ensure_row(
                cat,
                metric_key=col,
                column=col,
                source="games_core_v30",
                group=group,
                label=label,
                active=0 if group == "Other Game Metrics" else 1,
            )

    return cat


def sync_perf(cat: pd.DataFrame) -> pd.DataFrame:
    perf_cols = pd.read_parquet(PERF_PARQUET).columns.tolist()

    # Any existing performance_agg rows: keep, but we will ensure the real cols exist
    for col in perf_cols:
        if not ((cat["column"] == col) & (cat["source"] == "performance_agg")).any():
            group = "Model Performance Metrics"
            label = col
            if col in {"OverallAccuracy", "UpsetRate",
                       "Within5Pts", "Within10Pts"}:
                fmt = "%"
            else:
                fmt = ""
            cat = ensure_row(
                cat,
                metric_key=col,
                column=col,
                source="performance_agg",
                group=group,
                label=label,
                fmt=fmt,
                active=1,
            )

    return cat


def main() -> None:
    print(f"Loading base catalog from {CATALOG_IN}")
    cat = load_catalog()

    cat = sync_teams(cat)
    cat = sync_games(cat)
    cat = sync_perf(cat)

    # Sort for sanity: by source, then group, then metric_key
    cat_sorted = cat.sort_values(["source", "group", "metric_key"]).reset_index(drop=True)

    cat_sorted.to_csv(CATALOG_OUT, index=False)
    print(f"Wrote synced catalog to {CATALOG_OUT}")
    print("Row counts by source:")
    print(cat_sorted["source"].value_counts())


if __name__ == "__main__":
    main()
