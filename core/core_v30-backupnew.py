# C:\ANALYTICS207\core\core_v30.py
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HCA_POINTS_V30 = 3.5  # home court advantage in points


def _add_rank_views(df: pd.DataFrame, metric: str, *, prefix: str | None = None) -> pd.DataFrame:
    """
    Add statewide and subgroup rank columns for a given metric.
    """
    out = df.copy()
    name = prefix or metric

    if metric not in out.columns:
        return out

    # Statewide
    out[f"{name}RankState"] = out[metric].rank(method="min", ascending=False)

    # By Gender
    if "Gender" in out.columns:
        out[f"{name}RankByGender"] = (
            out.groupby("Gender")[metric].rank(method="min", ascending=False)
        )

    # By Class
    if "Class" in out.columns:
        out[f"{name}RankByClass"] = (
            out.groupby("Class")[metric].rank(method="min", ascending=False)
        )

    # By Gender+Class
    if {"Gender", "Class"}.issubset(out.columns):
        out[f"{name}RankByGenderClass"] = (
            out.groupby(["Gender", "Class"])[metric].rank(method="min", ascending=False)
        )

    return out


def build_performance_tables_v30(
    games: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Build v30 performance tables from games that already contain:
    PredHomeWinProb, PredMargin, ActualMargin, ModelCorrect, FavoriteIsHome, Played,
    Date, Home, Away, HomeScore, AwayScore, Gender.

    Returns:
      summary_df, perf_games_df, calib_df, spread_df
    """
    df = games.copy()

    # Only grade completed games
    played = df[df["Played"].fillna(False)].copy()
    if played.empty:
        summary = pd.DataFrame(
            [
                {
                    "TotalGames": 0,
                    "CorrectGames": 0,
                    "OverallAccuracy": 0.0,
                    "UpsetRate": 0.0,
                    "MAE": 0.0,
                    "RMSE": 0.0,
                    "Within5Pts": 0.0,
                    "Within10Pts": 0.0,
                    "BrierScore": 0.0,
                }
            ]
        )

        perfgames = pd.DataFrame(
            columns=[
                "Date",
                "Home",
                "Away",
                "HomeScore",
                "AwayScore",
                "Favorite",
                "FavProbPct",
                "ModelCorrect",
                "PredMargin",
                "ActualMargin",
                "Gender",
            ]
        )

        calib = pd.DataFrame(
            columns=["ConfBucket", "Games", "Correct", "HitRate", "AvgProb"]
        )
        spreadperf = pd.DataFrame(
            columns=["SpreadBucket", "Games", "Correct", "HitRate", "AvgSpread", "MAE"]
        )
        return summary, perfgames, calib, spreadperf

    # Actual outcome: home win = 1, else 0 (ties count as 0.5 if they exist)
    hs = played["HomeScore"].astype(float)
    as_ = played["AwayScore"].astype(float)
    outcome_home = np.where(hs > as_, 1.0, np.where(hs < as_, 0.0, 0.5))

    phome = played["PredHomeWinProb"].astype(float)
    pred_margin = played["PredMargin"].astype(float)
    actual_margin = played["ActualMargin"].astype(float)

    # Favorite and favorite probability
    favorite_is_home = played["FavoriteIsHome"].fillna(False)
    played["Favorite"] = np.where(favorite_is_home, played["Home"], played["Away"])
    favprob = np.where(favorite_is_home, phome, 1.0 - phome)
    played["FavProbPct"] = 100.0 * favprob

    # Core per-game performance frame (like v25/v26)
    perfgames = pd.DataFrame(
        {
            "Date": played["Date"],
            "Home": played["Home"],
            "Away": played["Away"],
            "HomeScore": played["HomeScore"],
            "AwayScore": played["AwayScore"],
            "Favorite": played["Favorite"],
            "FavProbPct": played["FavProbPct"],
            "ModelCorrect": played["ModelCorrect"],
            "PredMargin": pred_margin,
            "ActualMargin": actual_margin,
            "Gender": played.get("Gender", np.nan),
        }
    )

    # Summary metrics
    totalgames = len(perfgames)
    correctgames = int(pd.Series(perfgames["ModelCorrect"]).fillna(False).sum())
    overallacc = 100.0 * correctgames / totalgames if totalgames else 0.0
    upsetrate = 100.0 - overallacc if totalgames else 0.0

    err = (pred_margin - actual_margin).abs()
    mae = float(err.mean())
    rmse = float(np.sqrt(((pred_margin - actual_margin) ** 2).mean()))
    within5 = float(100.0 * (err <= 5.0).mean())
    within10 = float(100.0 * (err <= 10.0).mean())

    brier = float(((phome - outcome_home) ** 2).mean())

    summary = pd.DataFrame(
        [
            {
                "TotalGames": totalgames,
                "CorrectGames": correctgames,
                "OverallAccuracy": overallacc,
                "UpsetRate": upsetrate,
                "MAE": mae,
                "RMSE": rmse,
                "Within5Pts": within5,
                "Within10Pts": within10,
                "BrierScore": brier,
            }
        ]
    )

    # Calibration buckets (by favorite prob)
    calibdf = perfgames.copy()
    bins = [50, 60, 70, 80, 90, 101]
    labels = ["50-59", "60-69", "70-79", "80-89", "90-100"]
    calibdf["ConfBucket"] = pd.cut(
        calibdf["FavProbPct"].clip(50, 100), bins=bins, labels=labels, right=False
    )

    calib = (
        calibdf.dropna(subset=["ConfBucket"])
        .groupby("ConfBucket", dropna=True, observed=False)
        .agg(
            Games=("ModelCorrect", "size"),
            Correct=(
                "ModelCorrect",
                lambda s: int(pd.Series(s).fillna(False).sum()),
            ),
            HitRate=(
                "ModelCorrect",
                lambda s: float(
                    100.0 * pd.Series(s).fillna(False).mean()
                )
                if len(s)
                else 0.0,
            ),
            AvgProb=("FavProbPct", "mean"),
        )
        .reset_index()
    )

    # Performance by spread size
    spreaddf = perfgames.copy()
    spreaddf["AbsSpread"] = spreaddf["PredMargin"].abs()

    spreadbins = [0, 2, 5, 8, 12, 100]
    spreadlabels = ["0-2", "2-5", "5-8", "8-12", "12+"]
    spreaddf["SpreadBucket"] = pd.cut(
        spreaddf["AbsSpread"], bins=spreadbins, labels=spreadlabels, right=False
    )

    def _mae_bucket(sub: pd.DataFrame) -> float:
        if sub.empty:
            return 0.0
        return float((sub["PredMargin"] - sub["ActualMargin"]).abs().mean())

    spreadperf = (
        spreaddf.dropna(subset=["SpreadBucket"])
        .groupby("SpreadBucket", dropna=True, observed=False)
        .apply(
            lambda sub: pd.Series(
                {
                    "Games": int(len(sub)),
                    "Correct": int(
                        pd.Series(sub["ModelCorrect"]).fillna(False).sum()
                    ),
                    "HitRate": float(
                        100.0
                        * pd.Series(sub["ModelCorrect"]).fillna(False).mean()
                    )
                    if len(sub)
                    else 0.0,
                    "AvgSpread": float(sub["AbsSpread"].mean())
                    if len(sub)
                    else 0.0,
                    "MAE": _mae_bucket(sub),
                }
            )
        )
        .reset_index()
    )

    return summary, perfgames, calib, spreadperf


def _add_game_predictions_v30(games: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """
    Add per-game model predictions and evaluation fields to games_game_core_v30.
    Uses team NetEff, PPG, OPPG and a 3.5-point home court advantage.
    """
    g = games.copy()

    # Build mapping dicts keyed by TeamKey (handles non-unique TeamKey safely)
    teams_keyed = teams.set_index("TeamKey")
    ppg_map = teams_keyed["PPG"].to_dict()
    oppg_map = teams_keyed["OPPG"].to_dict()
    neteff_map = teams_keyed["NetEff"].to_dict()
    avgtotal_map = (teams_keyed["PPG"] + teams_keyed["OPPG"]).to_dict()

    # Map home/away metrics onto game rows
    g["HomePPG"] = g["HomeKey"].map(ppg_map)
    g["HomeOPPG"] = g["HomeKey"].map(oppg_map)
    g["HomeNetEff"] = g["HomeKey"].map(neteff_map)
    g["HomeAvgTotal"] = g["HomeKey"].map(avgtotal_map)

    g["AwayPPG"] = g["AwayKey"].map(ppg_map)
    g["AwayOPPG"] = g["AwayKey"].map(oppg_map)
    g["AwayNetEff"] = g["AwayKey"].map(neteff_map)
    g["AwayAvgTotal"] = g["AwayKey"].map(avgtotal_map)

    # Per-matchup expected total
    g["PredTotalPoints"] = (g["HomeAvgTotal"] + g["AwayAvgTotal"]) / 2.0

    # Predicted margin (home - away) from NetEff plus home court
    net_diff = g["HomeNetEff"] - g["AwayNetEff"]
    hca = np.where(g["IsNeutral"].fillna(False), 0.0, HCA_POINTS_V30)
    g["PredMargin"] = net_diff + hca

    # Predicted scores
    g["PredHomeScore"] = (g["PredTotalPoints"] + g["PredMargin"]) / 2.0
    g["PredAwayScore"] = (g["PredTotalPoints"] - g["PredMargin"]) / 2.0

    # Elo-style win probability for home team
    RATING_PER_POINT_V30 = 20.0
    PROB_SCALE_V30 = 400.0
    diffrating = g["PredMargin"] * RATING_PER_POINT_V30
    g["PredHomeWinProb"] = 1.0 / (1.0 + 10.0 ** (-diffrating / PROB_SCALE_V30))

    # Favorite
    g["FavoriteIsHome"] = g["PredHomeWinProb"] >= 0.5
    g["FavoriteTeamKey"] = np.where(g["FavoriteIsHome"], g["HomeKey"], g["AwayKey"])

    # Actuals for played games
    g["ActualMargin"] = np.where(
        g["Played"].fillna(False),
        g["HomeScore"] - g["AwayScore"],
        np.nan,
    )

    fav_is_home = g["FavoriteIsHome"]
    actual_margin = g["ActualMargin"]

    g["ModelCorrect"] = np.where(
        g["Played"].fillna(False),
        np.where(
            fav_is_home,
            actual_margin > 0,
            actual_margin < 0,
        ),
        np.nan,
    )

    return g


TEAM_KITCHEN_SINK_COLS_V30 = [
    "TeamKey","Team","Gender","Class","Region","Division","Season",
    "Games","Wins","Losses","Ties","Record","WinPct","GamesScheduled","GamesRemaining",
    "PointsFor","PointsAgainst","PPG","OPPG","MarginPG","MarginStd","MarginStdL10",
    "L5PPG","L5MarginPG","HighestScore","LowestScore","HighestMargin","LowestMargin",
    "HomeGames","HomeWins","HomeLosses","HomeWinPct","HomeMarginPG",
    "RoadGames","RoadWins","RoadLosses","RoadWinPct","RoadMarginPG",
    "NeutralGames","NeutralWins","NeutralLosses","NeutralWinPct","NeutralMarginPG",
    "CloseGames","CloseWins","CloseLosses","CloseWinPct",
    "BlowoutGames","BlowoutRate","BlowoutMarginPG",
    "GamesMargin0to3","WinsMargin0to3","WinPctMargin0to3",
    "GamesMargin4to10","WinsMargin4to10","WinPctMargin4to10",
    "GamesMargin11to20","WinsMargin11to20","WinPctMargin11to20",
    "GamesMargin21plus","WinsMargin21plus","WinPctMargin21plus",
    "Streak","StreakLabel",
    "EarlyGames","EarlyWins","EarlyMarginPG",
    "LateGames","LateWins","LateMarginPG","IsLateSkew",
    "InDivisionWins","CrossDivisionWins",
    "AvgRestDays","ShortRestGames","ShortRestShare","LongRestGames","LongRestShare",
    "ScrapedAt","CoreVersion","LastGameDate",
]




def _ensure_team_schema_v30(teams: pd.DataFrame) -> pd.DataFrame:
    out = teams.copy()
    for c in TEAM_KITCHEN_SINK_COLS_V30:
        if c not in out.columns:
            out[c] = np.nan
    ordered = TEAM_KITCHEN_SINK_COLS_V30 + [
        c for c in out.columns if c not in TEAM_KITCHEN_SINK_COLS_V30
    ]
    out = out.reindex(columns=ordered)
    return out

GAME_KITCHEN_SINK_COLS_V30 = [
    # Core identity
    "GameID", "Date", "Season", "Gender",

    # Teams
    "Home", "Away", "HomeKey", "AwayKey",
    "HomeClass", "AwayClass", "HomeRegion", "AwayRegion",
    "HomeDivision", "AwayDivision",

    # Scores / outcomes
    "HomeScore", "AwayScore",
    "Played", "Margin", "IsNeutral",
    "WinnerTeam",
    "Winner",

    # Predictions / model eval
    "HomeRating", "AwayRating",
    "PredHomeWinProb", "PredMargin",
    "PredHomeScore", "PredAwayScore", "PredTotalPoints",
    "FavoriteIsHome", "FavoriteTeamKey",
    "FavProb",
    "ModelCorrect", "ActualMargin",

    # Opponent strength fields already in your build
    "HomeTI", "AwayTI", "HomePI", "AwayPI", "HomeRank", "AwayRank",

    # Metadata
    "ScrapedAt", "CoreVersion",
]



def _ensure_game_schema_v30(games: pd.DataFrame) -> pd.DataFrame:
    out = games.copy()
    for c in GAME_KITCHEN_SINK_COLS_V30:
        if c not in out.columns:
            out[c] = np.nan
    ordered = GAME_KITCHEN_SINK_COLS_V30 + [c for c in out.columns if c not in GAME_KITCHEN_SINK_COLS_V30]
    return out.reindex(columns=ordered)




ROOT = Path(r"C:\ANALYTICS207")
DATA_DIR = ROOT / "data"
TRUTH_CSV = DATA_DIR / "truth.csv"


def load_truth_csv(path: Path = TRUTH_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    df["Date"] = pd.to_datetime(df.get("Date", None), errors="coerce")
    df["ScrapedAt"] = pd.to_datetime(df.get("ScrapedAt", None), errors="coerce")

    if "Gender" in df.columns:
        df["Gender"] = (
            df["Gender"].astype(str).str.strip().str.title()
        )

    for col in ["Team1", "Team2", "HomeTeam", "AwayTeam", "Winner", "Loser"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def _build_team_key(name: str, gender: str, cls: str, region: str) -> str:
    return f"{name.strip()}_{gender.strip()}_{cls.strip()}_{region.strip()}"


def _parse_div(div: str) -> tuple[str, str]:
    div = str(div)
    if "-" not in div:
        return "Unknown", "Unknown"
    region, cls = div.split("-", 1)
    return region.strip().title(), cls.strip().upper()


def _coalesce_bool_series(
    df: pd.DataFrame, candidates: list[str]
) -> pd.Series | None:
    for c in candidates:
        if c in df.columns:
            s = df[c]
            if s.dtype == bool:
                return s
            ss = s.astype(str).str.strip().str.lower()
            return ss.isin(["true", "t", "1", "y", "yes"])
    return None


def build_games_core(games_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Build games_core_v30:
    - Identity-safe HomeKey/AwayKey by each side's own div snapshot (v26 style).
    - Adds IsNeutral detection (best-effort).
    - Adds team-perspective opponent strength columns by joining opponent TI/PI/Rank from same row.
    """
    g = games_raw.copy()

    # Season
    if "Date" in g.columns:
        g["Season"] = g["Date"].dt.year.astype("Int64").astype(str)
    else:
        g["Season"] = pd.Series([None] * len(g), dtype="object")

    # Team division map from Team1 snapshot
    teamdiv_map: dict[str, str] = {}
    if "Team1" in g.columns and "SchoolDivision" in g.columns:
        for _, row in g.iterrows():
            team1 = str(row.get("Team1", "")).strip()
            div = str(row.get("SchoolDivision", "")).strip()
            if team1 and div:
                teamdiv_map[team1] = div

    def get_team_div(team: str) -> str:
        return teamdiv_map.get(str(team).strip(), "Unknown-Unknown")

    # Home/Away
    g["Home"] = g.get("HomeTeam", "").astype(str).str.strip()
    g["Away"] = g.get("AwayTeam", "").astype(str).str.strip()

    # Per-side divisions
    g["HomeDivision"] = g["Home"].apply(get_team_div)
    g["AwayDivision"] = g["Away"].apply(get_team_div)

    home_parsed = g["HomeDivision"].map(_parse_div)
    away_parsed = g["AwayDivision"].map(_parse_div)

    g["HomeRegion"] = [r for r, _ in home_parsed]
    g["HomeClass"] = [c for _, c in home_parsed]
    g["AwayRegion"] = [r for r, _ in away_parsed]
    g["AwayClass"] = [c for _, c in away_parsed]

    # Team keys
    g["HomeKey"] = g.apply(
        lambda r: _build_team_key(
            r["Home"], r.get("Gender", ""), r["HomeClass"], r["HomeRegion"]
        ),
        axis=1,
    )
    g["AwayKey"] = g.apply(
        lambda r: _build_team_key(
            r["Away"], r.get("Gender", ""), r["AwayClass"], r["AwayRegion"]
        ),
        axis=1,
    )

    # Scores / played / margin
    g["HomeScore"] = pd.to_numeric(
        g.get("HomeScore", np.nan), errors="coerce"
    )
    g["AwayScore"] = pd.to_numeric(
        g.get("AwayScore", np.nan), errors="coerce"
    )
    g["Played"] = g["HomeScore"].notna() & g["AwayScore"].notna()
    g["Margin"] = np.where(
        g["Played"], g["HomeScore"] - g["AwayScore"], np.nan
    )

    # Winner team string
    g["WinnerTeam"] = np.where(
        g["Played"] & (g["HomeScore"] > g["AwayScore"]),
        g["Home"],
        np.where(
            g["Played"] & (g["AwayScore"] > g["HomeScore"]), g["Away"], None
        ),
    )

    # Neutral detection (best-effort)
    neutral = _coalesce_bool_series(
        g, ["NeutralSite", "Neutral", "IsNeutral", "NeutralFlag"]
    )
    if neutral is None:
        if "Site" in g.columns:
            neutral = g["Site"].astype(str).str.lower().str.contains(
                "neutral", na=False
            )
        elif "LocationType" in g.columns:
            neutral = (
                g["LocationType"].astype(str).str.lower().eq("neutral")
            )
        else:
            neutral = pd.Series([False] * len(g), dtype=bool)
    g["IsNeutral"] = neutral

    # ---- Add opponent strength columns for each side (row-level) ----
    for c in ["TI", "PI", "Rank"]:
        if c not in g.columns:
            g[c] = np.nan

    team_metric_rows = (
        g[["GameID", "Team1", "TI", "PI", "Rank"]].copy()
        if "Team1" in g.columns
        else None
    )
    if team_metric_rows is not None:
        team_metric_rows["Team1"] = (
            team_metric_rows["Team1"].astype(str).str.strip()
        )
        team_metric_rows = team_metric_rows.rename(
            columns={
                "Team1": "MetricTeam",
                "TI": "MetricTI",
                "PI": "MetricPI",
                "Rank": "MetricRank",
            }
        )

        # Attach metric to Home if Home == MetricTeam
        g = g.merge(
            team_metric_rows[
                ["GameID", "MetricTeam", "MetricTI", "MetricPI", "MetricRank"]
            ],
            how="left",
            left_on=["GameID", "Home"],
            right_on=["GameID", "MetricTeam"],
            suffixes=("", "_home"),
        )
        g = g.rename(
            columns={
                "MetricTI": "HomeTI",
                "MetricPI": "HomePI",
                "MetricRank": "HomeRank",
            }
        )
        g = g.drop(columns=["MetricTeam"], errors="ignore")

        # Attach metric to Away if Away == MetricTeam
        g = g.merge(
            team_metric_rows[
                ["GameID", "MetricTeam", "MetricTI", "MetricPI", "MetricRank"]
            ],
            how="left",
            left_on=["GameID", "Away"],
            right_on=["GameID", "MetricTeam"],
            suffixes=("", "_away"),
        )
        g = g.rename(
            columns={
                "MetricTI": "AwayTI",
                "MetricPI": "AwayPI",
                "MetricRank": "AwayRank",
            }
        )
        g = g.drop(columns=["MetricTeam"], errors="ignore")
    else:
        g["HomeTI"] = np.nan
        g["HomePI"] = np.nan
        g["HomeRank"] = np.nan
        g["AwayTI"] = np.nan
        g["AwayPI"] = np.nan
        g["AwayRank"] = np.nan

    # Core columns
    keep_cols = [
        "GameID",
        "Date",
        "Season",
        "Gender",
        "Home",
        "Away",
        "HomeKey",
        "AwayKey",
        "HomeClass",
        "AwayClass",
        "HomeRegion",
        "AwayRegion",
        "HomeDivision",
        "AwayDivision",
        "HomeScore",
        "AwayScore",
        "Played",
        "Margin",
        "IsNeutral",
        "WinnerTeam",
        "RecordText",
        "GamesPlayed",
        "GamesScheduled",
        "TI",
        "PI",
        "Rank",
        "WinPoints",
        "OppPreliminaryIndex",
        "WinFlag",
        "LossFlag",
        "TieFlag",
        "GameNum",
        "ScrapedAt",
        "HomeTI",
        "HomePI",
        "HomeRank",
        "AwayTI",
        "AwayPI",
        "AwayRank",
    ]
    keep_cols = [c for c in keep_cols if c in g.columns]

    games_core = g.drop_duplicates(subset=["GameID"]).reset_index(drop=True)
    games_core = games_core[keep_cols].copy()
    games_core["CoreVersion"] = "v30"

    return games_core


#-------------------- BEGIN _iter_team_views__agg_team --------------------
def _iter_team_views(games_core: pd.DataFrame):
    """
    Yield per-team game views (each game appears twice: once per team),
    with opponent fields and neutral/home/away flags available.
    """
    g = games_core.copy()

    home = g.copy()
    home["TeamKey"] = home["HomeKey"]
    home["Team"] = home["Home"]
    home["Opponent"] = home["Away"]
    home["OpponentKey"] = home["AwayKey"]
    home["IsHome"] = True
    home["IsAway"] = False
    home["IsNeutralTeam"] = home["IsNeutral"].fillna(False)
    home["For"] = home["HomeScore"]
    home["Against"] = home["AwayScore"]
    home["TeamTI"] = home.get("HomeTI", np.nan)
    home["TeamPI"] = home.get("HomePI", np.nan)
    home["TeamRank"] = home.get("HomeRank", np.nan)
    home["OppTI"] = home.get("AwayTI", np.nan)
    home["OppPI"] = home.get("AwayPI", np.nan)
    home["OppRank"] = home.get("AwayRank", np.nan)

    away = g.copy()
    away["TeamKey"] = away["AwayKey"]
    away["Team"] = away["Away"]
    away["Opponent"] = away["Home"]
    away["OpponentKey"] = away["HomeKey"]
    away["IsHome"] = False
    away["IsAway"] = True
    away["IsNeutralTeam"] = away["IsNeutral"].fillna(False)
    away["For"] = away["AwayScore"]
    away["Against"] = away["HomeScore"]
    away["TeamTI"] = away.get("AwayTI", np.nan)
    away["TeamPI"] = away.get("AwayPI", np.nan)
    away["TeamRank"] = away.get("AwayRank", np.nan)
    away["OppTI"] = away.get("HomeTI", np.nan)
    away["OppPI"] = away.get("HomePI", np.nan)
    away["OppRank"] = away.get("HomeRank", np.nan)

    combined = pd.concat([home, away], ignore_index=True)
    combined = combined[combined["TeamKey"].notna()]

    for key, grp in combined.groupby("TeamKey"):
        yield key, grp


#-------------------- BEGIN _agg_team --------------------
def _agg_team(df: pd.DataFrame) -> dict:
    df = df.sort_values("Date")
    teamkey = df["TeamKey"].iloc[0]
    team = df["Team"].mode().iloc[0]

    gender = df["Gender"].mode().iloc[0] if "Gender" in df.columns else ""
    cls = df.get("HomeClass", pd.Series([""])).mode().iloc[0] if "HomeClass" in df.columns else ""
    region = df.get("HomeRegion", pd.Series([""])).mode().iloc[0] if "HomeRegion" in df.columns else ""
    season = df.get("Season", pd.Series([""])).mode().iloc[0] if "Season" in df.columns else ""

    played = df["Played"].fillna(False)
    d = df.loc[played].copy()

    games = int(played.sum())
    if games == 0:
        return dict(
            TeamKey=teamkey,
            Team=team,
            Gender=gender,
            Class=cls,
            Region=region,
            Season=season,
            Games=0,
            Wins=0,
            Losses=0,
            Ties=0,
            Record="0-0-0",
            WinPct=np.nan,
            PointsFor=0.0,
            PointsAgainst=0.0,
            PPG=np.nan,
            OPPG=np.nan,
            MarginPG=np.nan,
            OffEff=np.nan,
            DefEff=np.nan,
            NetEff=np.nan,
            MarginStd=np.nan,
            BlowoutRate=np.nan,
            CloseGameRate=np.nan,
            OnePossessionRate=np.nan,
            Last5MarginPG=np.nan,
            Last10MarginPG=np.nan,
            ClutchCloseGameWinPct=np.nan,
            NetEffVsTop=np.nan,
            NetEffVsMiddle=np.nan,
            NetEffVsBottom=np.nan,
            HomeGames=0,
            HomeWins=0,
            HomeLosses=0,
            HomeWinPct=np.nan,
            HomeMarginPG=np.nan,
            RoadGames=0,
            RoadWins=0,
            RoadLosses=0,
            RoadWinPct=np.nan,
            RoadMarginPG=np.nan,
            NeutralGames=0,
            NeutralWins=0,
            NeutralLosses=0,
            NeutralWinPct=np.nan,
            NeutralMarginPG=np.nan,
            GamesVsTop=0,
            WinsVsTop=0,
            LossesVsTop=0,
            WinPctVsTop=np.nan,
            MarginVsTop=np.nan,
            GamesVsMiddle=0,
            WinsVsMiddle=0,
            LossesVsMiddle=0,
            WinPctVsMiddle=np.nan,
            MarginVsMiddle=np.nan,
            GamesVsBottom=0,
            WinsVsBottom=0,
            LossesVsBottom=0,
            WinPctVsBottom=np.nan,
            MarginVsBottom=np.nan,
            GamesVsTop25=0,
            WinsVsTop25=0,
            LossesVsTop25=0,
            WinPctVsTop25=np.nan,
            MarginVsTop25=np.nan,
            BestWin=None,
            BestWinMargin=np.nan,
            WorstLoss=None,
            WorstLossMargin=np.nan,
            QualityWins=0,
            BadLosses=0,
            Top25Wins=0,
            Top25Losses=0,
        )

    for_pts = d["For"].fillna(0)
    ag_pts = d["Against"].fillna(0)
    margins = (for_pts - ag_pts).astype(float)

    wins_mask = margins > 0
    losses_mask = margins < 0
    ties_mask = margins == 0

    wins = int(wins_mask.sum())
    losses = int(losses_mask.sum())
    ties = int(ties_mask.sum())

    pts_for = float(for_pts.sum())
    pts_against = float(ag_pts.sum())

    ppg = float(for_pts.mean()) if games else np.nan
    oppg = float(ag_pts.mean()) if games else np.nan
    marginpg = float(margins.mean()) if games else np.nan

    # Efficiency-style stats
    off_eff = ppg
    def_eff = oppg
    net_eff = off_eff - def_eff if off_eff == off_eff and def_eff == def_eff else np.nan

    # Volatility and close/blowout rates
    margin_std = float(margins.std(ddof=0)) if games > 0 else np.nan
    blowout_mask = margins.abs() >= 21
    close_mask = margins.abs() <= 5
    one_poss_mask = margins.abs() <= 3

    blowout_rate = float(blowout_mask.mean()) if games > 0 else np.nan
    close_rate = float(close_mask.mean()) if games > 0 else np.nan
    one_poss_rate = float(one_poss_mask.mean()) if games > 0 else np.nan

    # Clutch: win% in close games (<= 5 points)
    close_games = int(close_mask.sum())
    if close_games > 0:
        close_wins = int((close_mask & wins_mask).sum())
        clutch_close_win_pct = close_wins / close_games
    else:
        clutch_close_win_pct = np.nan

    # Recent form margins
    last5 = margins.tail(5)
    last10 = margins.tail(10)
    last5_marginpg = float(last5.mean()) if len(last5) > 0 else np.nan
    last10_marginpg = float(last10.mean()) if len(last10) > 0 else np.nan

    # Home/road/neutral splits
    is_home = d["IsHome"].fillna(False).astype(bool)
    is_away = d["IsAway"].fillna(False).astype(bool)
    is_neutral = d.get("IsNeutralTeam", pd.Series([False] * len(d))).fillna(False).astype(bool)

    home_mask = is_home & (~is_neutral)
    road_mask = is_away & (~is_neutral)
    neutral_mask = is_neutral

    def _split(mask: pd.Series):
        sub = d.loc[mask]
        if sub.empty:
            return 0, 0, 0, np.nan, np.nan
        m = (sub["For"] - sub["Against"]).astype(float)
        w = int((m > 0).sum())
        l = int((m < 0).sum())
        g = int(len(sub))
        wp = (w / g) if g else np.nan
        mpg = float(m.mean()) if g else np.nan
        return g, w, l, float(wp) if wp == wp else np.nan, mpg

    hg, hw, hl, hwp, hmpg = _split(home_mask)
    rg, rw, rl, rwp, rmpg = _split(road_mask)
    ng, nw, nl, nwp, nmpg = _split(neutral_mask)

    # Opponent strength scalar: TI -> PI -> Rank (lower Rank is stronger)
    opp_ti = pd.to_numeric(d.get("OppTI", np.nan), errors="coerce")
    opp_pi = pd.to_numeric(d.get("OppPI", np.nan), errors="coerce")
    opp_rank = pd.to_numeric(d.get("OppRank", np.nan), errors="coerce")

    opp_strength = opp_ti.copy()
    opp_strength = opp_strength.where(opp_strength.notna(), opp_pi)
    opp_strength = opp_strength.where(
        opp_strength.notna(),
        np.where(opp_rank.notna(), -opp_rank, np.nan),
    )

    valid = opp_strength.dropna()
    if len(valid) >= 6:
        q33 = float(valid.quantile(1 / 3))
        q67 = float(valid.quantile(2 / 3))
    else:
        q33, q67 = np.nan, np.nan

    def _tier_masks():
        if np.isnan(q33) or np.isnan(q67):
            empty = pd.Series(False, index=d.index)
            return empty, empty, empty
        top = (opp_strength >= q67)
        bot = (opp_strength <= q33)
        mid = ~(top | bot) & opp_strength.notna()
        top = top.reindex(d.index, fill_value=False)
        mid = mid.reindex(d.index, fill_value=False)
        bot = bot.reindex(d.index, fill_value=False)
        return top, mid, bot

    top_mask, mid_mask, bot_mask = _tier_masks()

    def _tier_rollup(mask: pd.Series):
        sub = d.loc[mask]
        if sub.empty:
            return 0, 0, 0, np.nan, np.nan
        m = (sub["For"] - sub["Against"]).astype(float)
        g = int(len(sub))
        w = int((m > 0).sum())
        l = int((m < 0).sum())
        wp = (w / g) if g else np.nan
        return g, w, l, (float(wp) if wp == wp else np.nan), float(m.mean())

    gtop, wtop, ltop, wptop, mtop = _tier_rollup(top_mask)
    gmid, wmid, lmid, wpmid, mmid = _tier_rollup(mid_mask)
    gbot, wbot, lbot, wpbot, mbot = _tier_rollup(bot_mask)

    top25_mask = (opp_rank.notna() & (opp_rank <= 25))
    top25_mask = top25_mask.reindex(d.index, fill_value=False)
    g25, w25, l25, wp25, m25 = _tier_rollup(top25_mask)

    d = d.assign(Margin=margins, Win=wins_mask, Loss=losses_mask)

    if d.loc[d["Win"]].empty:
        best_win_team = None
        best_win_margin = np.nan
    else:
        wins_df = d.loc[d["Win"]].copy()
        wins_df["OppStrength"] = opp_strength.loc[wins_df.index]
        wins_df = wins_df.sort_values(["OppStrength", "Margin"], ascending=[False, False])
        best_win_team = wins_df["Opponent"].iloc[0]
        best_win_margin = float(wins_df["Margin"].iloc[0])

    if d.loc[d["Loss"]].empty:
        worst_loss_team = None
        worst_loss_margin = np.nan
    else:
        loss_df = d.loc[d["Loss"]].copy()
        loss_df["OppStrength"] = opp_strength.loc[loss_df.index]
        loss_df = loss_df.sort_values(["OppStrength", "Margin"], ascending=[True, True])
        worst_loss_team = loss_df["Opponent"].iloc[0]
        worst_loss_margin = float(loss_df["Margin"].iloc[0])

    quality_wins = int((top_mask & wins_mask).sum()) if len(d) else 0
    bad_losses = int((bot_mask & losses_mask).sum()) if len(d) else 0

    top25_wins = int((top25_mask & wins_mask).sum())
    top25_losses = int((top25_mask & losses_mask).sum())

    record = f"{wins}-{losses}-{ties}"

    return dict(
        TeamKey=teamkey,
        Team=team,
        Gender=gender,
        Class=cls,
        Region=region,
        Season=season,
        Games=games,
        Wins=wins,
        Losses=losses,
        Ties=ties,
        Record=record,
        WinPct=(wins / games) if games else np.nan,
        PointsFor=pts_for,
        PointsAgainst=pts_against,
        PPG=ppg,
        OPPG=oppg,
        MarginPG=marginpg,
        OffEff=off_eff,
        DefEff=def_eff,
        NetEff=net_eff,
        MarginStd=margin_std,
        BlowoutRate=blowout_rate,
        CloseGameRate=close_rate,
        OnePossessionRate=one_poss_rate,
        Last5MarginPG=last5_marginpg,
        Last10MarginPG=last10_marginpg,
        ClutchCloseGameWinPct=clutch_close_win_pct,
        NetEffVsTop=mtop,
        NetEffVsMiddle=mmid,
        NetEffVsBottom=mbot,
        HomeGames=hg,
        HomeWins=hw,
        HomeLosses=hl,
        HomeWinPct=hwp,
        HomeMarginPG=hmpg,
        RoadGames=rg,
        RoadWins=rw,
        RoadLosses=rl,
        RoadWinPct=rwp,
        RoadMarginPG=rmpg,
        NeutralGames=ng,
        NeutralWins=nw,
        NeutralLosses=nl,
        NeutralWinPct=nwp,
        NeutralMarginPG=nmpg,
        GamesVsTop=gtop,
        WinsVsTop=wtop,
        LossesVsTop=ltop,
        WinPctVsTop=wptop,
        MarginVsTop=mtop,
        GamesVsMiddle=gmid,
        WinsVsMiddle=wmid,
        LossesVsMiddle=lmid,
        WinPctVsMiddle=wpmid,
        MarginVsMiddle=mmid,
        GamesVsBottom=gbot,
        WinsVsBottom=wbot,
        LossesVsBottom=lbot,
        WinPctVsBottom=wpbot,
        MarginVsBottom=mbot,
        GamesVsTop25=g25,
        WinsVsTop25=w25,
        LossesVsTop25=l25,
        WinPctVsTop25=wp25,
        MarginVsTop25=m25,
        BestWin=best_win_team,
        BestWinMargin=best_win_margin,
        WorstLoss=worst_loss_team,
        WorstLossMargin=worst_loss_margin,
        QualityWins=quality_wins,
        BadLosses=bad_losses,
        Top25Wins=top25_wins,
        Top25Losses=top25_losses,
    )
#-------------------- END _agg_team --------------------

#-------------------- END _iter_team_views__agg_team --------------------


def annotate_seeds_and_qualified(teams_core: pd.DataFrame) -> pd.DataFrame:
    df = teams_core.copy()
    if "TI" not in df.columns:
        df["TI"] = np.nan

    DEFAULT_CUT = 11
    df["ProjectedSeed"] = np.nan
    df["Qualified"] = "OUT"

    group_cols = ["Gender", "Class", "Region", "Season"]

    def _annotate_group(g: pd.DataFrame) -> pd.DataFrame:
        g = g.copy()
        g = g.sort_values(["TI", "WinPct"], ascending=[False, False]).reset_index(drop=True)
        g["ProjectedSeed"] = g.index + 1
        g["Qualified"] = np.where(g["ProjectedSeed"] <= DEFAULT_CUT, "IN", "OUT")
        return g

    df = (
        df.groupby(group_cols, dropna=False, group_keys=False)
          .apply(_annotate_group, include_groups=False)
          .reset_index(drop=True)
    )
    return df


def build_teams_core(games_core: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, grp in _iter_team_views(games_core):
        rows.append(_agg_team(grp))
    teams_core = pd.DataFrame(rows)
    teams_core["CoreVersion"] = "v30"
    teams_core = annotate_seeds_and_qualified(teams_core)
    return teams_core


def annotate_expected_wins_and_sos(
    teams_core: pd.DataFrame,
    games_core: pd.DataFrame,
    *,
    hfa_points: float = 3.0,
    neutral_hfa_points: float = 0.0,
    spread_sigma: float = 11.0,
) -> pd.DataFrame:
    """
    Adds ExpectedWins, SOS_EWP, ScheduleAdjWins to teams_core.

    Rating backbone:
    - Use NetEff as team strength; if missing, fall back to MarginPG.
    - Expected margin for home team:
        ExpMarginHome = (NetEff_home - NetEff_away) + HFA (or 0 for neutral).
    - Convert expected margin -> win probability via logistic:
        p_home = 1 / (1 + exp(-k * ExpMarginHome)),
      where k ~= pi / (sqrt(3) * spread_sigma).
    """

    df = teams_core.copy()

    # Map TeamKey -> rating
    if "NetEff" in df.columns:
        rating = df.set_index("TeamKey")["NetEff"].astype(float)
    else:
        rating = df.set_index("TeamKey")["MarginPG"].astype(float)

    # Games actually played
    g = games_core.copy()
    g = g[g["Played"].fillna(False)].copy()

    # Attach ratings to each side
    g["HomeRating"] = g["HomeKey"].map(rating)
    g["AwayRating"] = g["AwayKey"].map(rating)

    # Any missing ratings -> league-average 0.0
    g["HomeRating"] = g["HomeRating"].fillna(0.0)
    g["AwayRating"] = g["AwayRating"].fillna(0.0)

    # Home-court adjustment
    is_neutral = g.get("IsNeutral", False).fillna(False).astype(bool)
    hfa = np.where(is_neutral, neutral_hfa_points, hfa_points)

    # Expected margin from home perspective
    g["ExpMarginHome"] = (g["HomeRating"] - g["AwayRating"]) + hfa

    # Logistic approximation for win probability
    k = np.pi / (np.sqrt(3.0) * float(spread_sigma))
    g["WinProbHome"] = 1.0 / (1.0 + np.exp(-k * g["ExpMarginHome"]))
    g["WinProbAway"] = 1.0 - g["WinProbHome"]

    # Build per-team expected wins rows
    home_exp = g[["HomeKey", "Season", "WinProbHome"]].copy()
    home_exp = home_exp.rename(columns={"HomeKey": "TeamKey", "WinProbHome": "WinProb"})

    away_exp = g[["AwayKey", "Season", "WinProbAway"]].copy()
    away_exp = away_exp.rename(columns={"AwayKey": "TeamKey", "WinProbAway": "WinProb"})

    exp = pd.concat([home_exp, away_exp], ignore_index=True)

    # Aggregate to team-season ExpectedWins
    exp_agg = (
        exp.groupby(["TeamKey", "Season"], dropna=False, as_index=False)
           .agg(ExpectedWins=("WinProb", "sum"))
    )

    # Merge back into teams_core
    df = df.merge(exp_agg[["TeamKey", "ExpectedWins"]], on="TeamKey", how="left")
    df["ExpectedWins"] = df["ExpectedWins"].fillna(0.0)

    # SOS_EWP and ScheduleAdjWins
    df["SOS_EWP"] = np.where(df["Games"].fillna(0) > 0, df["ExpectedWins"] / df["Games"], np.nan)
    df["ScheduleAdjWins"] = df["Wins"].fillna(0) - df["ExpectedWins"]

    return df


def build_core_v30(path: Path = TRUTH_CSV):
    raw = load_truth_csv(path)
    games_core = build_games_core(raw)
    teams_core = build_teams_core(games_core)

    # Add expected wins / SOS metrics
    teams_core = annotate_expected_wins_and_sos(teams_core, games_core)

    # Add per-game predictions and evaluation fields
    games_core = _add_game_predictions_v30(games_core, teams_core)

    # Ensure team schema is stable for downstream pages
    teams_core = _ensure_team_schema_v30(teams_core)
    games_core = _ensure_game_schema_v30(games_core)
    return teams_core, games_core

