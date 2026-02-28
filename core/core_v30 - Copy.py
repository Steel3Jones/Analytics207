# C:\ANALYTICS207\core\core_v30.py
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CORE_V30_IDENTITY = "core_v30_with_gender_class_region_v1"

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
                    "Correct": int(pd.Series(sub["ModelCorrect"]).fillna(False).sum()),
                    "HitRate": float(
                        100.0 * pd.Series(sub["ModelCorrect"]).fillna(False).mean()
                    )
                    if len(sub)
                    else 0.0,
                    "AvgSpread": float(sub["AbsSpread"].mean()) if len(sub) else 0.0,
                    "MAE": _mae_bucket(sub),
                }
            ),
            include_groups=False,
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
    "TeamKey", "Team", "Gender", "Class", "Region", "Division", "Season",
    "Games", "Wins", "Losses", "Ties", "Record", "WinPct", "GamesScheduled", "GamesRemaining",
    "PointsFor", "PointsAgainst", "PPG", "OPPG", "MarginPG", "MarginStd", "MarginStdL10",

    # NEW: Model rating fields
    "TSR", "TSR_Display",
    "TSR_Tier_State", "TSR_Tier_Class", "TSR_Tier_Slice",

    "L5PPG", "L5MarginPG", "HighestScore", "LowestScore", "HighestMargin", "LowestMargin",
    "HomeGames", "HomeWins", "HomeLosses", "HomeWinPct", "HomeMarginPG",
    "RoadGames", "RoadWins", "RoadLosses", "RoadWinPct", "RoadMarginPG",
    "NeutralGames", "NeutralWins", "NeutralLosses", "NeutralWinPct", "NeutralMarginPG",
    "CloseGames", "CloseWins", "CloseLosses", "CloseWinPct",
    "BlowoutGames", "BlowoutRate", "BlowoutMarginPG",
    "GamesMargin0to3", "WinsMargin0to3", "WinPctMargin0to3",
    "GamesMargin4to10", "WinsMargin4to10", "WinPctMargin4to10",
    "GamesMargin11to20", "WinsMargin11to20", "WinPctMargin11to20",
    "GamesMargin21plus", "WinsMargin21plus", "WinPctMargin21plus",
    "Streak", "StreakLabel",
    "EarlyGames", "EarlyWins", "EarlyMarginPG",
    "LateGames", "LateWins", "LateMarginPG", "IsLateSkew",
    "InDivisionWins", "CrossDivisionWins",
    "AvgRestDays", "ShortRestGames", "ShortRestShare", "LongRestGames", "LongRestShare",
    "ScrapedAt", "CoreVersion", "LastGameDate",
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


def _enrich_teams_core_v30(teams_core: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived team-season metrics that are in the catalog but not yet computed:
    - HomeRoadDiff
    - CloseGames / CloseWins / CloseLosses / CloseWinPct
    - BlowoutGames / BlowoutWins / BlowoutLosses / BlowoutMarginPG
    - Margin bucket counts and win pcts (0-3, 4-10, 11-20, 21+)
    - WinsInRow / LossesInRow placeholders
    """
    df = teams_core.copy()

    # HomeRoadDiff
    if {"HomeWinPct", "RoadWinPct"}.issubset(df.columns):
        df["HomeRoadDiff"] = df["HomeWinPct"] - df["RoadWinPct"]

    # Use Games plus existing rates to approximate counts
    games = df.get("Games")
    if games is not None:
        games = games.fillna(0)

        # Close games from CloseGameRate
        if "CloseGameRate" in df.columns:
            close_games = (games * df["CloseGameRate"].fillna(0)).round().astype("Int64")
            df["CloseGames"] = close_games
            if "WinPct" in df.columns:
                df["CloseWins"] = (df["WinPct"].fillna(0) * close_games).round().astype("Int64")
                df["CloseLosses"] = (close_games - df["CloseWins"]).astype("Int64")
                df["CloseWinPct"] = df["CloseWins"] / df["CloseGames"].where(
                    df["CloseGames"] > 0, np.nan
                )

        # Blowout games from BlowoutRate
        if "BlowoutRate" in df.columns:
            blowout_games = (games * df["BlowoutRate"].fillna(0)).round().astype("Int64")
            df["BlowoutGames"] = blowout_games
            df["BlowoutWins"] = (blowout_games * 0.8).round().astype("Int64")
            df["BlowoutLosses"] = (blowout_games - df["BlowoutWins"]).astype("Int64")
            if "MarginPG" in df.columns:
                df["BlowoutMarginPG"] = 1.5 * df["MarginPG"]

    # Margin bucket placeholders
    for bucket in ["0to3", "4to10", "11to20", "21plus"]:
        col_g = f"GamesMargin{bucket}"
        col_w = f"WinsMargin{bucket}"
        col_p = f"WinPctMargin{bucket}"
        if col_g not in df.columns:
            df[col_g] = np.nan
        if col_w not in df.columns:
            df[col_w] = np.nan
        if col_p not in df.columns:
            df[col_p] = np.nan

    # Streak placeholders
    if "WinsInRow" not in df.columns:
        df["WinsInRow"] = np.nan
    if "LossesInRow" not in df.columns:
        df["LossesInRow"] = np.nan

    return df


def compute_tsr_elo_v30(
    teams_core: pd.DataFrame,
    games_core: pd.DataFrame,
) -> pd.Series:
    """
    Compute TSR using a single-season MOV-Elo style system.

    Returns:
      pd.Series indexed by TeamKey with final TSR values (centered around 0).
    """
    teams = teams_core.copy()
    games = games_core.copy()

    # --- 1) Seed TSR from NetEff, centered at 0, scaled ---
    if "NetEff" not in teams.columns:
        raise ValueError("NetEff is required to seed TSR Elo.")

    ne = pd.to_numeric(teams["NetEff"], errors="coerce")
    mu_ne = ne.mean(skipna=True)
    sigma_ne = ne.std(skipna=True)

    k = 0.8 if sigma_ne and sigma_ne > 0 else 1.0
    tsr_seed = (ne - mu_ne) * k

    teamkey = teams["TeamKey"].astype(str).str.strip()
    tsr_current = pd.Series(tsr_seed.values, index=teamkey, dtype=float)

    # --- 2) Simple class offset ladder stub ---
    classes = ["A", "B", "C", "D", "S"]
    class_offsets = {
        "A": 8.0,
        "B": 4.0,
        "C": 0.0,
        "D": -4.0,
        "S": -8.0,
    }

    def get_class_offset(cls: str) -> float:
        return float(class_offsets.get(str(cls).strip().upper(), 0.0))

    # --- 3) Prepare games for Elo loop ---
    g = games.copy()
    g = g[g["Played"].fillna(False)].copy()
    if g.empty:
        mu_final = tsr_current.mean()
        return tsr_current - mu_final

    needed_cols = [
        "HomeKey", "AwayKey", "HomeScore", "AwayScore",
        "IsNeutral", "HomeClass", "AwayClass", "Date",
    ]
    for col in needed_cols:
        if col not in g.columns:
            raise ValueError(f"games_core missing required column: {col}")

    g["Date"] = pd.to_datetime(g["Date"], errors="coerce")
    g["HomeKey"] = g["HomeKey"].astype(str).str.strip()
    g["AwayKey"] = g["AwayKey"].astype(str).str.strip()
    g = g.sort_values("Date")

    games_played = pd.Series(0, index=tsr_current.index, dtype=int)

    HCA_TSR = 3.0
    TAU = 12.0
    K_EARLY = 20.0
    K_MID = 10.0
    K_LATE = 5.0

    # --- 4) Elo loop over games ---
    for _, row in g.iterrows():
        home_key = row["HomeKey"]
        away_key = row["AwayKey"]

        if home_key not in tsr_current.index or away_key not in tsr_current.index:
            continue

        home_tsr = tsr_current[home_key]
        away_tsr = tsr_current[away_key]

        is_neutral = bool(row.get("IsNeutral", False))
        hca = 0.0 if is_neutral else HCA_TSR

        home_cls = row.get("HomeClass", "")
        away_cls = row.get("AwayClass", "")
        class_diff = get_class_offset(home_cls) - get_class_offset(away_cls)

        d = home_tsr - away_tsr + hca + class_diff

        p_home = 1.0 / (1.0 + 10.0 ** (-d / TAU))

        hs = float(row["HomeScore"])
        as_ = float(row["AwayScore"])
        if hs > as_:
            actual_home = 1.0
        elif hs < as_:
            actual_home = 0.0
        else:
            actual_home = 0.5

        margin = hs - as_
        base_mov = np.log1p(abs(margin))

        opp_tsr_home = away_tsr

        def mov_factor(base_mov_val: float, opp_tsr_val: float) -> float:
            mf = base_mov_val
            if opp_tsr_val < -10.0:
                mf *= 0.3
            elif opp_tsr_val > 10.0:
                mf *= 1.3
            return min(mf, 3.0)

        mov_home = mov_factor(base_mov, opp_tsr_home)

        gp_home = games_played.get(home_key, 0)
        gp_away = games_played.get(away_key, 0)
        gp_min = min(gp_home, gp_away)

        if gp_min < 8:
            K = K_EARLY
        elif gp_min < 15:
            K = K_MID
        else:
            K = K_LATE

        delta = K * mov_home * (actual_home - p_home)

        tsr_current[home_key] = home_tsr + delta
        tsr_current[away_key] = away_tsr - delta

        games_played[home_key] = gp_home + 1
        games_played[away_key] = gp_away + 1

    mu_final = tsr_current.mean()
    tsr_current = tsr_current - mu_final

    return tsr_current


def _add_tsr_and_tiers_v30(teams_core: pd.DataFrame) -> pd.DataFrame:
    df = teams_core.copy()

    tsr = pd.to_numeric(df.get("TSR"), errors="coerce")

    mu = tsr.mean(skipna=True)
    sigma = tsr.std(skipna=True)

    if pd.notna(mu) and pd.notna(sigma) and sigma > 0:
        z = (tsr - mu) / sigma
        df["TSR_Display"] = 100.0 + 8.0 * z
    else:
        df["TSR_Display"] = 100.0 + 0.5 * (tsr - mu)

    df["TSR_Display"] = df["TSR_Display"].round(1)

    def _assign_tiers(sub: pd.DataFrame, col: str = "TSR") -> pd.Series:
        vals = pd.to_numeric(sub[col], errors="coerce")
        ranks = vals.rank(method="average", ascending=False)
        n = len(sub)
        if n == 0:
            return pd.Series([], index=sub.index, dtype=object)

        q1, q2, q3 = n * 0.25, n * 0.50, n * 0.75
        tiers = pd.Series(index=sub.index, dtype=object)
        for idx, r in ranks.items():
            if pd.isna(r):
                tiers.loc[idx] = "Tier 4"
            elif r <= q1:
                tiers.loc[idx] = "Tier 1"
            elif r <= q2:
                tiers.loc[idx] = "Tier 2"
            elif r <= q3:
                tiers.loc[idx] = "Tier 3"
            else:
                tiers.loc[idx] = "Tier 4"
        return tiers

    df["TSR_Tier_State"] = None
    if {"Gender", "TSR"}.issubset(df.columns):
        for _, sub in df.groupby("Gender", dropna=False):
            df.loc[sub.index, "TSR_Tier_State"] = _assign_tiers(sub)

    df["TSR_Tier_Class"] = None
    if {"Gender", "Class", "TSR"}.issubset(df.columns):
        for _, sub in df.groupby(["Gender", "Class"], dropna=False):
            df.loc[sub.index, "TSR_Tier_Class"] = _assign_tiers(sub)

    df["TSR_Tier_Slice"] = None
    if {"Gender", "Class", "Region", "TSR"}.issubset(df.columns):
        for _, sub in df.groupby(["Gender", "Class", "Region"], dropna=False):
            df.loc[sub.index, "TSR_Tier_Slice"] = _assign_tiers(sub)

    return df


def _compute_team_streaks_v30(games_core: pd.DataFrame) -> pd.DataFrame:
    """
    Compute current win/loss streaks per team from played games.
    Returns a DataFrame with columns: TeamKey, WinsInRow, LossesInRow
    """
    g = games_core.copy()

    # Only played games with a known winner
    g = g[g["Played"].fillna(False)]
    g = g.dropna(subset=["HomeKey", "AwayKey", "Winner"])

    home_log = pd.DataFrame(
        {
            "TeamKey": g["HomeKey"],
            "Date": g["Date"],
            "IsWin": (g["Winner"] == g["HomeKey"]),
        }
    )
    away_log = pd.DataFrame(
        {
            "TeamKey": g["AwayKey"],
            "Date": g["Date"],
            "IsWin": (g["Winner"] == g["AwayKey"]),
        }
    )

    log = pd.concat([home_log, away_log], ignore_index=True)
    log = log.sort_values(["TeamKey", "Date"])

    def _streak(sub: pd.DataFrame) -> pd.Series:
        if sub.empty:
            return pd.Series({"WinsInRow": 0, "LossesInRow": 0})

        is_win = sub["IsWin"].astype(bool).to_numpy()
        last = is_win[-1]

        if last:
            k = 0
            for v in is_win[::-1]:
                if v:
                    k += 1
                else:
                    break
            return pd.Series({"WinsInRow": int(k), "LossesInRow": 0})
        else:
            k = 0
            for v in is_win[::-1]:
                if not v:
                    k += 1
                else:
                    break
            return pd.Series({"WinsInRow": 0, "LossesInRow": int(k)})

    streaks = (
        log.groupby("TeamKey", dropna=False, observed=False)
        .apply(_streak, include_groups=False)
        .reset_index()
    )

    streaks["WinsInRow"] = streaks["WinsInRow"].astype("Int64")
    streaks["LossesInRow"] = streaks["LossesInRow"].astype("Int64")

    return streaks


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

    # Team division map
    teamdivmap: dict[str, str] = {}

    team_cols = [c for c in ["Team1", "Team2", "HomeTeam", "AwayTeam"] if c in g.columns]
    has_div = "SchoolDivision" in g.columns

    if team_cols and has_div:
        for _, row in g.iterrows():
            div = row.get("SchoolDivision", None)
            div = str(div).strip() if div is not None else ""
            if not div:
                continue

            for tc in team_cols:
                t = row.get(tc, None)
                t = str(t).strip() if t is not None else ""
                if t and t not in teamdivmap:
                    teamdivmap[t] = div

    def get_team_div(team: str) -> str:
        return teamdivmap.get(str(team).strip(), "Unknown-Unknown")

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
#-------------------- END _iter_team_views__agg_team --------------------


#-------------------- BEGIN _agg_team --------------------
def _agg_team(df: pd.DataFrame) -> dict:
    df = df.sort_values("Date")
    teamkey = df["TeamKey"].iloc[0]
    team = df["Team"].mode().iloc[0]

    # NEW: derive Gender / Class / Region directly from per-game fields
    if "Gender" in df.columns:
        gender = df["Gender"].dropna().astype(str).str.strip().str.title()
        gender = gender.mode().iloc[0] if not gender.empty else ""
    else:
        gender = ""

    if "HomeClass" in df.columns:
        cls_series = df["HomeClass"].dropna().astype(str).str.strip().str.upper()
        cls = cls_series.mode().iloc[0] if not cls_series.empty else ""
    else:
        cls = ""

    if "HomeRegion" in df.columns:
        region_series = df["HomeRegion"].dropna().astype(str).str.strip().str.title()
        region = region_series.mode().iloc[0] if not region_series.empty else ""
    else:
        region = ""

    if "Season" in df.columns:
        season_series = df["Season"].dropna().astype(str).str.strip()
        season = season_series.mode().iloc[0] if not season_series.empty else ""
    else:
        season = ""

    played = df["Played"].fillna(False)
    d = df.loc[played].copy()

    games = int(played.sum())

    # Scraped PI per team: latest non-null TeamPI from this season
    team_pi_series = pd.to_numeric(d.get("TeamPI"), errors="coerce").dropna()
    team_pi = float(team_pi_series.iloc[-1]) if len(team_pi_series) else np.nan

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
            PI=team_pi,
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
        PI=team_pi,
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
    rows: list[dict] = []
    for key, grp in _iter_team_views(games_core):
        rows.append(_agg_team(grp))

    teams_core = pd.DataFrame(rows)

    if teams_core.empty:
        teams_core["CoreVersion"] = "v30"
        return teams_core

    # Collapse to a single row per TeamKey + Gender + Class + Region + Season
    numeric_cols = teams_core.select_dtypes(include=["number", "bool"]).columns.tolist()

    candidate_group_cols = ["TeamKey", "Gender", "Class", "Region", "Season"]
    group_cols = [c for c in candidate_group_cols if c in teams_core.columns]

    agg_spec: dict[str, str] = {}
    for col in teams_core.columns:
        if col in group_cols:
            continue
        if col in numeric_cols:
            agg_spec[col] = "mean"
        else:
            agg_spec[col] = "first"

    teams_core = (
        teams_core.groupby(group_cols, dropna=False, as_index=False)
        .agg(agg_spec)
    )

    teams_core["CoreVersion"] = "v30"
    return teams_core


def _enrich_teams_core_v30(teams_core: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived team-season metrics that are in the catalog but not yet computed:
    - HomeRoadDiff
    - CloseGames / CloseWins / CloseLosses / CloseWinPct
    - BlowoutGames / BlowoutWins / BlowoutLosses / BlowoutMarginPG
    - Margin bucket counts and win pcts (0-3, 4-10, 11-20, 21plus)
    - WinsInRow / LossesInRow placeholders
    """
    df = teams_core.copy()

    # HomeRoadDiff
    if {"HomeWinPct", "RoadWinPct"}.issubset(df.columns):
        df["HomeRoadDiff"] = df["HomeWinPct"] - df["RoadWinPct"]

    # Use Games plus existing rates to approximate counts
    games = df.get("Games")
    if games is not None:
        games = games.fillna(0)

        # Close games from CloseGameRate
        if "CloseGameRate" in df.columns:
            close_games = (games * df["CloseGameRate"].fillna(0)).round().astype("Int64")
            df["CloseGames"] = close_games
            if "WinPct" in df.columns:
                df["CloseWins"] = (
                    df["WinPct"].fillna(0) * close_games
                ).round().astype("Int64")
                df["CloseLosses"] = (close_games - df["CloseWins"]).astype("Int64")
                df["CloseWinPct"] = df["CloseWins"] / df["CloseGames"].where(
                    df["CloseGames"] > 0, np.nan
                )

        # Blowout games from BlowoutRate
        if "BlowoutRate" in df.columns:
            blowout_games = (games * df["BlowoutRate"].fillna(0)).round().astype("Int64")
            df["BlowoutGames"] = blowout_games
            df["BlowoutWins"] = (blowout_games * 0.8).round().astype("Int64")
            df["BlowoutLosses"] = (blowout_games - df["BlowoutWins"]).astype("Int64")
            if "MarginPG" in df.columns:
                df["BlowoutMarginPG"] = 1.5 * df["MarginPG"]

    # Margin bucket placeholders
    for bucket in ["0to3", "4to10", "11to20", "21plus"]:
        col_g = f"GamesMargin{bucket}"
        col_w = f"WinsMargin{bucket}"
        col_p = f"WinPctMargin{bucket}"
        if col_g not in df.columns:
            df[col_g] = np.nan
        if col_w not in df.columns:
            df[col_w] = np.nan
        if col_p not in df.columns:
            df[col_p] = np.nan

    # Streak placeholders
    if "WinsInRow" not in df.columns:
        df["WinsInRow"] = np.nan
    if "LossesInRow" not in df.columns:
        df["LossesInRow"] = np.nan

    return df


def _enrich_games_v30(games_core: pd.DataFrame) -> pd.DataFrame:
    """
    Fill obvious nulls in games_game_core_v30 without changing any existing non-null values.

    - ActualMargin
    - Played
    - FavoriteIsHome (when prediction fields exist)
    """
    g = games_core.copy()

    # ActualMargin from scores
    if "ActualMargin" in g.columns and g["ActualMargin"].isna().any():
        if {"HomeScore", "AwayScore"}.issubset(g.columns):
            hs = pd.to_numeric(g["HomeScore"], errors="coerce")
            as_ = pd.to_numeric(g["AwayScore"], errors="coerce")
            calc_margin = hs - as_
            mask = g["ActualMargin"].isna() & hs.notna() & as_.notna()
            g.loc[mask, "ActualMargin"] = calc_margin[mask]

    # Played flag: true when both scores are present
    if "Played" in g.columns and g["Played"].isna().any():
        if {"HomeScore", "AwayScore"}.issubset(g.columns):
            hs = pd.to_numeric(g["HomeScore"], errors="coerce")
            as_ = pd.to_numeric(g["AwayScore"], errors="coerce")
            mask = g["Played"].isna()
            g.loc[mask, "Played"] = (hs.notna() & as_.notna())[mask]

    # FavoriteIsHome
    if "FavoriteIsHome" in g.columns and g["FavoriteIsHome"].isna().any():
        if "PredHomeWinProb" in g.columns:
            ph = pd.to_numeric(g["PredHomeWinProb"], errors="coerce")
            mask = g["FavoriteIsHome"].isna() & ph.notna()
            g.loc[mask, "FavoriteIsHome"] = (ph >= 0.5)[mask]

    return g


def _build_long_team_games_v30(games_core: pd.DataFrame) -> pd.DataFrame:
    """
    Convert games into a per-team-per-game 'long' frame used for team enrichment.

    Columns (at minimum):
      TeamKey, Team, Date, Location, PointsFor, PointsAgainst, Margin,
      IsWin, IsLoss
    """
    g = games_core.copy()
    if "Date" in g.columns:
        g["Date"] = pd.to_datetime(g["Date"], errors="coerce")

    for col in ["HomeScore", "AwayScore"]:
        if col in g.columns:
            g[col] = pd.to_numeric(g[col], errors="coerce")

    played = g.copy()
    if {"HomeScore", "AwayScore"}.issubset(played.columns):
        played = played[played["HomeScore"].notna() & played["AwayScore"].notna()]

    # Home view
    home = played.rename(
        columns={
            "Home": "Team",
            "HomeScore": "PointsFor",
            "AwayScore": "PointsAgainst",
            "HomeKey": "TeamKey",
        }
    )
    home["Location"] = "Home"

    # Away view
    away = played.rename(
        columns={
            "Away": "Team",
            "AwayScore": "PointsFor",
            "HomeScore": "PointsAgainst",
            "AwayKey": "TeamKey",
        }
    )
    away["Location"] = "Away"

    long = pd.concat([home, away], ignore_index=True)

    if {"PointsFor", "PointsAgainst"}.issubset(long.columns):
        long["Margin"] = (
            pd.to_numeric(long["PointsFor"], errors="coerce")
            - pd.to_numeric(long["PointsAgainst"], errors="coerce")
        )
    else:
        long["Margin"] = np.nan

    long["IsWin"] = long["Margin"] > 0
    long["IsLoss"] = long["Margin"] < 0

    return long


def _safe_backfill_team_cols(
    teams_core: pd.DataFrame, extra: pd.DataFrame, *, key_cols: list[str]
) -> pd.DataFrame:
    """
    Merge extra metrics into teams_core, but ONLY into columns that are
    currently all-null or missing in teams_core.
    """
    out = teams_core.copy()
    extra = extra.copy()

    for col in extra.columns:
        if col in key_cols:
            continue

        can_fill = False
        if col not in out.columns:
            can_fill = True
        else:
            non_null_count = out[col].notna().sum()
            if non_null_count == 0:
                can_fill = True

        if not can_fill:
            continue

        out = out.drop(columns=[col], errors="ignore")
        out = out.merge(extra[key_cols + [col]], on=key_cols, how="left")

    return out


def _add_quality_and_vs_tier_stats_v30(
    teams: pd.DataFrame,
    games: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add vs-top/mid/bottom, vs-top-band ("Top25-style"), QualityWins, BadLosses.

    Rules:
    - Buckets are within Season x Gender x Class x Region based on TSR rank.
    - Top band ~ top 30% of TSR in slice (min 1 team).
    - Quality win: win vs same/higher class opponent with TSR_opp >= 1.20 * TSR_team.
    - Bad loss: loss vs opponent with TSR_opp <= 0.75 * TSR_team.
    - Playing down a class never creates a quality win.
    """

    if teams.empty or games.empty:
        return teams

    t = teams.copy()
    g = games.copy()

    # --- 1) Per-team TSR context and tiers ---
    required_team_cols = ["TeamKey", "Season", "Gender", "Class", "Region", "TSR"]
    missing_team_cols = [c for c in required_team_cols if c not in t.columns]
    if missing_team_cols:
        return t

    ctx = t[required_team_cols].copy()
    ctx["TSR"] = pd.to_numeric(ctx["TSR"], errors="coerce")

    group_keys = ["Season", "Gender", "Class", "Region"]
    ctx["TSRRankInSlice"] = (
        ctx.groupby(group_keys, dropna=False)["TSR"]
        .rank(method="min", ascending=False)
    )
    slice_sizes = (
        ctx.groupby(group_keys, dropna=False)["TeamKey"]
        .transform("count")
    )
    ctx["SliceSize"] = slice_sizes

    frac = 0.30
    ctx["TopCut"] = (ctx["SliceSize"] * frac).round().clip(lower=1)
    ctx["BottomCut"] = ctx["SliceSize"] - ctx["TopCut"] + 1

    ctx["IsTopBand"] = ctx["TSRRankInSlice"] <= ctx["TopCut"]
    ctx["IsBottomBand"] = ctx["TSRRankInSlice"] >= ctx["BottomCut"]

    def _bucket_row(row: pd.Series) -> str:
        if pd.isna(row["TSRRankInSlice"]):
            return "Middle"
        if row["IsTopBand"]:
            return "Top"
        if row["IsBottomBand"]:
            return "Bottom"
        return "Middle"

    ctx["TierBucket"] = ctx.apply(_bucket_row, axis=1)

    team_ctx = ctx[
        ["TeamKey", "Season", "Gender", "Class", "Region", "TSR", "TierBucket", "IsTopBand"]
    ].copy()

    # --- 2) Attach context to games ---
    required_game_cols = [
        "GameID",
        "Season",
        "Played",
        "HomeKey",
        "AwayKey",
        "HomeScore",
        "AwayScore",
    ]
    missing_game_cols = [c for c in required_game_cols if c not in g.columns]
    if missing_game_cols:
        return t

    g = g[g["Played"].fillna(False)].copy()
    if g.empty:
        return t

    home = g.merge(
        team_ctx.add_prefix("Home_"),
        left_on=["HomeKey", "Season"],
        right_on=["Home_TeamKey", "Home_Season"],
        how="left",
    )
    away = home.merge(
        team_ctx.add_prefix("Away_"),
        left_on=["AwayKey", "Season"],
        right_on=["Away_TeamKey", "Away_Season"],
        how="left",
    )

    mask_ok = away["Home_TSR"].notna() & away["Away_TSR"].notna()
    away = away[mask_ok].copy()
    if away.empty:
        return t

    # --- 3) Build long (team-game) view ---
    hs = pd.to_numeric(away["HomeScore"], errors="coerce")
    as_ = pd.to_numeric(away["AwayScore"], errors="coerce")
    outcome_home = (hs > as_).astype(float)
    outcome_home = outcome_home.where(hs != as_, 0.5)
    away["OutcomeHome"] = outcome_home

    home_rows = pd.DataFrame(
        {
            "TeamKey": away["HomeKey"],
            "Season": away["Season"],
            "Gender": away["Home_Gender"],
            "Class": away["Home_Class"],
            "Region": away["Home_Region"],
            "OppTeamKey": away["AwayKey"],
            "OppClass": away["Away_Class"],
            "OppRegion": away["Away_Region"],
            "TSR_team": away["Home_TSR"],
            "TSR_opp": away["Away_TSR"],
            "TierBucketOpp": away["Away_TierBucket"],
            "OppIsTopBand": away["Away_IsTopBand"],
            "Outcome": away["OutcomeHome"],
        }
    )

    outcome_away = 1.0 - away["OutcomeHome"]
    outcome_away = outcome_away.where(away["OutcomeHome"] != 0.5, 0.5)

    away_rows = pd.DataFrame(
        {
            "TeamKey": away["AwayKey"],
            "Season": away["Season"],
            "Gender": away["Away_Gender"],
            "Class": away["Away_Class"],
            "Region": away["Away_Region"],
            "OppTeamKey": away["HomeKey"],
            "OppClass": away["Home_Class"],
            "OppRegion": away["Home_Region"],
            "TSR_team": away["Away_TSR"],
            "TSR_opp": away["Home_TSR"],
            "TierBucketOpp": away["Home_TierBucket"],
            "OppIsTopBand": away["Home_IsTopBand"],
            "Outcome": outcome_away,
        }
    )

    long_df = pd.concat([home_rows, away_rows], ignore_index=True)
    long_df = long_df.dropna(subset=["TSR_team", "TSR_opp"])

    if long_df.empty:
        return t

    # --- 4) Flags per team-game row ---
    long_df["IsWin"] = long_df["Outcome"] == 1.0
    long_df["IsLoss"] = long_df["Outcome"] == 0.0

    tsr_team = long_df["TSR_team"].replace(0, pd.NA)
    long_df["TSRGapPct"] = (long_df["TSR_opp"] - long_df["TSR_team"]) / tsr_team.abs()
    long_df["TSRGapPct"] = long_df["TSRGapPct"].fillna(0.0)

    long_df["SameOrHigherClass"] = long_df["OppClass"] >= long_df["Class"]

    long_df["IsQualityWin"] = (
        long_df["IsWin"]
        & long_df["SameOrHigherClass"]
        & (long_df["TSR_opp"] >= 1.20 * long_df["TSR_team"])
    )

    long_df["IsBadLoss"] = (
        long_df["IsLoss"]
        & (long_df["TSR_opp"] <= 0.75 * long_df["TSR_team"])
    )

    long_df["IsVsTop"] = long_df["TierBucketOpp"] == "Top"
    long_df["IsVsMiddle"] = long_df["TierBucketOpp"] == "Middle"
    long_df["IsVsBottom"] = long_df["TierBucketOpp"] == "Bottom"
    long_df["IsVsTopBand"] = long_df["OppIsTopBand"].fillna(False)

    # --- 5) Aggregate per team ---
    grp = long_df.groupby("TeamKey", dropna=False)

    def _sum_bool(s: pd.Series) -> int:
        return int(s.fillna(False).sum())

    agg = grp.agg(
        GamesVsTop=("IsVsTop", lambda s: int(s.sum())),
        WinsVsTop=("IsVsTop", lambda s: _sum_bool(s & long_df.loc[s.index, "IsWin"])),
        LossesVsTop=("IsVsTop", lambda s: _sum_bool(s & long_df.loc[s.index, "IsLoss"])),
        GamesVsMiddle=("IsVsMiddle", lambda s: int(s.sum())),
        WinsVsMiddle=("IsVsMiddle", lambda s: _sum_bool(s & long_df.loc[s.index, "IsWin"])),
        LossesVsMiddle=("IsVsMiddle", lambda s: _sum_bool(s & long_df.loc[s.index, "IsLoss"])),
        GamesVsBottom=("IsVsBottom", lambda s: int(s.sum())),
        WinsVsBottom=("IsVsBottom", lambda s: _sum_bool(s & long_df.loc[s.index, "IsWin"])),
        LossesVsBottom=("IsVsBottom", lambda s: _sum_bool(s & long_df.loc[s.index, "IsLoss"])),
        GamesVsTopBand=("IsVsTopBand", lambda s: int(s.sum())),
        WinsVsTopBand=("IsVsTopBand", lambda s: _sum_bool(s & long_df.loc[s.index, "IsWin"])),
        LossesVsTopBand=("IsVsTopBand", lambda s: _sum_bool(s & long_df.loc[s.index, "IsLoss"])),
        QualityWins=("IsQualityWin", lambda s: _sum_bool(s)),
        BadLosses=("IsBadLoss", lambda s: _sum_bool(s)),
    ).reset_index()

    for prefix in ["Top", "Middle", "Bottom", "TopBand"]:
        gcol = f"GamesVs{prefix}"
        wcol = f"WinsVs{prefix}"
        pctcol = f"WinPctVs{prefix}"
        if gcol in agg.columns and wcol in agg.columns:
            games_nonzero = agg[gcol].replace(0, pd.NA)
            agg[pctcol] = agg[wcol] / games_nonzero

    out = t.copy()
    out = out.merge(agg, on="TeamKey", how="left")

    return out



def _enrich_teams_from_games_v30(
    teams_core: pd.DataFrame,
    games_core: pd.DataFrame,
) -> pd.DataFrame:
    """
    Use played games to backfill missing team metrics (only into null/missing cols):

    - Last5 / Last10 style scoring and margin:
        L5PPG, L5MarginPG, Last5MarginPG, Last10MarginPG
    - Early/late season performance:
        EarlyGames, EarlyWins, EarlyMarginPG,
        LateGames, LateWins, LateMarginPG, IsLateSkew
    - Margin buckets:
        GamesMargin0to3, WinsMargin0to3, WinPctMargin0to3,
        GamesMargin4to10, WinsMargin4to10, WinPctMargin4to10,
        GamesMargin11to20, WinsMargin11to20, WinPctMargin11to20,
        GamesMargin21plus, WinsMargin21plus, WinPctMargin21plus
    - Rest metrics:
        AvgRestDays, ShortRestGames, ShortRestShare,
        LongRestGames, LongRestShare
    - Streaks:
        WinsInRow, LossesInRow
    """
    if "TeamKey" not in teams_core.columns:
        return teams_core

    long = _build_long_team_games_v30(games_core)

    # Keys we group/merge on
    key_cols = ["TeamKey"]
    if "Team" in teams_core.columns:
        key_cols = ["TeamKey", "Team"]

    # Ensure long table has Team column if teams_core has it
    if "Team" not in long.columns and "Team" in teams_core.columns:
        long["Team"] = np.nan

    # ---------- Last5 / Last10 metrics ----------
    last_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        df_t["L5PPG"] = df_t["PointsFor"].rolling(window=5, min_periods=1).mean()
        df_t["L5MarginPG"] = df_t["Margin"].rolling(window=5, min_periods=1).mean()
        df_t["Last5MarginPG"] = df_t["Margin"].rolling(window=5, min_periods=1).mean()
        df_t["Last10MarginPG"] = df_t["Margin"].rolling(window=10, min_periods=1).mean()
        last = df_t.iloc[-1]

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["L5PPG"] = last["L5PPG"]
        row["L5MarginPG"] = last["L5MarginPG"]
        row["Last5MarginPG"] = last["Last5MarginPG"]
        row["Last10MarginPG"] = last["Last10MarginPG"]
        last_rows.append(row)

    last5_df = pd.DataFrame(last_rows)

    # ---------- Early / Late metrics ----------
    early_late_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        n = len(df_t)
        if n == 0:
            continue
        split = max(n // 2, 1)

        early = df_t.iloc[:split]
        late = df_t.iloc[split:]

        early_games = len(early)
        late_games = len(late)

        early_margin = early["Margin"].mean() if early_games > 0 else np.nan
        late_margin = late["Margin"].mean() if late_games > 0 else np.nan

        early_wins = (early["Margin"] > 0).sum()
        late_wins = (late["Margin"] > 0).sum()

        is_late_skew = int(
            (late_margin if not np.isnan(late_margin) else 0.0)
            > (early_margin if not np.isnan(early_margin) else 0.0)
        )

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["EarlyGames"] = early_games
        row["EarlyWins"] = early_wins
        row["EarlyMarginPG"] = early_margin
        row["LateGames"] = late_games
        row["LateWins"] = late_wins
        row["LateMarginPG"] = late_margin
        row["IsLateSkew"] = is_late_skew
        early_late_rows.append(row)

    early_late_df = pd.DataFrame(early_late_rows)

    # ---------- Margin buckets ----------
    bucket_rows = []
    for key, df_t in long.groupby(key_cols):
        df_t = df_t.copy()
        df_t["abs_margin"] = df_t["Margin"].abs()

        def bucket(lo, hi=None):
            if hi is None:
                mask = df_t["abs_margin"] >= lo
            else:
                mask = (df_t["abs_margin"] >= lo) & (df_t["abs_margin"] <= hi)
            sub = df_t[mask]
            games = len(sub)
            if games == 0:
                return games, 0, np.nan
            wins = (sub["Margin"] > 0).sum()
            win_pct = wins / games
            return games, wins, win_pct

        g0, w0, p0 = bucket(0, 3)
        g4, w4, p4 = bucket(4, 10)
        g11, w11, p11 = bucket(11, 20)
        g21, w21, p21 = bucket(21, None)

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["GamesMargin0to3"] = g0
        row["WinsMargin0to3"] = w0
        row["WinPctMargin0to3"] = p0

        row["GamesMargin4to10"] = g4
        row["WinsMargin4to10"] = w4
        row["WinPctMargin4to10"] = p4

        row["GamesMargin11to20"] = g11
        row["WinsMargin11to20"] = w11
        row["WinPctMargin11to20"] = p11

        row["GamesMargin21plus"] = g21
        row["WinsMargin21plus"] = w21
        row["WinPctMargin21plus"] = p21

        bucket_rows.append(row)

    buckets_df = pd.DataFrame(bucket_rows)

    # ---------- Rest metrics ----------
    rest_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        dates = df_t["Date"].dropna()
        if dates.empty:
            avg_rest = np.nan
            short_games = 0
            long_games = 0
            short_share = np.nan
            long_share = np.nan
        else:
            deltas = dates.diff().dt.days.iloc[1:]
            short_mask = deltas <= 1
            long_mask = deltas >= 5
            short_games = int(short_mask.sum())
            long_games = int(long_mask.sum())
            total = len(deltas)
            avg_rest = deltas.mean() if total > 0 else np.nan
            short_share = short_games / total if total > 0 else np.nan
            long_share = long_games / total if total > 0 else np.nan

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["AvgRestDays"] = avg_rest
        row["ShortRestGames"] = short_games
        row["ShortRestShare"] = short_share
        row["LongRestGames"] = long_games
        row["LongRestShare"] = long_share
        rest_rows.append(row)

    rest_df = pd.DataFrame(rest_rows)

    # ---------- Streaks (WinsInRow, LossesInRow) ----------
    streak_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        margins = df_t["Margin"].tolist()

        wins_in_row = 0
        losses_in_row = 0
        for m in reversed(margins):
            if pd.isna(m):
                break
            if m > 0:
                if losses_in_row > 0:
                    break
                wins_in_row += 1
            elif m < 0:
                if wins_in_row > 0:
                    break
                losses_in_row += 1
            else:
                break

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["WinsInRow"] = wins_in_row if wins_in_row > 0 else np.nan
        row["LossesInRow"] = losses_in_row if losses_in_row > 0 else np.nan
        streak_rows.append(row)

    streak_df = pd.DataFrame(streak_rows)

    # ---------- Safe backfill into teams_core ----------
    out = teams_core.copy()
    out = _safe_backfill_team_cols(out, last5_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, early_late_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, buckets_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, rest_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, streak_df, key_cols=key_cols)

    return out


    # ---------- Last5 / Last10 metrics ----------
    last_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        df_t["L5PPG"] = df_t["PointsFor"].rolling(window=5, min_periods=1).mean()
        df_t["L5MarginPG"] = df_t["Margin"].rolling(window=5, min_periods=1).mean()
        df_t["Last5MarginPG"] = df_t["Margin"].rolling(window=5, min_periods=1).mean()
        df_t["Last10MarginPG"] = df_t["Margin"].rolling(window=10, min_periods=1).mean()
        last = df_t.iloc[-1]

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["L5PPG"] = last["L5PPG"]
        row["L5MarginPG"] = last["L5MarginPG"]
        row["Last5MarginPG"] = last["Last5MarginPG"]
        row["Last10MarginPG"] = last["Last10MarginPG"]
        last_rows.append(row)

    last5_df = pd.DataFrame(last_rows)

    # ---------- Early / Late metrics ----------
    early_late_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        n = len(df_t)
        if n == 0:
            continue
        split = max(n // 2, 1)

        early = df_t.iloc[:split]
        late = df_t.iloc[split:]

        early_games = len(early)
        late_games = len(late)

        early_margin = early["Margin"].mean() if early_games > 0 else np.nan
        late_margin = late["Margin"].mean() if late_games > 0 else np.nan

        early_wins = (early["Margin"] > 0).sum()
        late_wins = (late["Margin"] > 0).sum()

        is_late_skew = int(
            (late_margin if not np.isnan(late_margin) else 0.0)
            > (early_margin if not np.isnan(early_margin) else 0.0)
        )

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["EarlyGames"] = early_games
        row["EarlyWins"] = early_wins
        row["EarlyMarginPG"] = early_margin
        row["LateGames"] = late_games
        row["LateWins"] = late_wins
        row["LateMarginPG"] = late_margin
        row["IsLateSkew"] = is_late_skew
        early_late_rows.append(row)

    early_late_df = pd.DataFrame(early_late_rows)

    # ---------- Margin buckets ----------
    bucket_rows = []
    for key, df_t in long.groupby(key_cols):
        df_t = df_t.copy()
        df_t["abs_margin"] = df_t["Margin"].abs()

        def bucket(lo, hi=None):
            if hi is None:
                mask = df_t["abs_margin"] >= lo
            else:
                mask = (df_t["abs_margin"] >= lo) & (df_t["abs_margin"] <= hi)
            sub = df_t[mask]
            games = len(sub)
            if games == 0:
                return games, 0, np.nan
            wins = (sub["Margin"] > 0).sum()
            win_pct = wins / games
            return games, wins, win_pct

        g0, w0, p0 = bucket(0, 3)
        g4, w4, p4 = bucket(4, 10)
        g11, w11, p11 = bucket(11, 20)
        g21, w21, p21 = bucket(21, None)

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["GamesMargin0to3"] = g0
        row["WinsMargin0to3"] = w0
        row["WinPctMargin0to3"] = p0

        row["GamesMargin4to10"] = g4
        row["WinsMargin4to10"] = w4
        row["WinPctMargin4to10"] = p4

        row["GamesMargin11to20"] = g11
        row["WinsMargin11to20"] = w11
        row["WinPctMargin11to20"] = p11

        row["GamesMargin21plus"] = g21
        row["WinsMargin21plus"] = w21
        row["WinPctMargin21plus"] = p21

        bucket_rows.append(row)

    buckets_df = pd.DataFrame(bucket_rows)

    # ---------- Rest metrics ----------
    rest_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        dates = df_t["Date"].dropna()
        if dates.empty:
            avg_rest = np.nan
            short_games = 0
            long_games = 0
            short_share = np.nan
            long_share = np.nan
        else:
            deltas = dates.diff().dt.days.iloc[1:]
            short_mask = deltas <= 1
            long_mask = deltas >= 5
            short_games = int(short_mask.sum())
            long_games = int(long_mask.sum())
            total = len(deltas)
            avg_rest = deltas.mean() if total > 0 else np.nan
            short_share = short_games / total if total > 0 else np.nan
            long_share = long_games / total if total > 0 else np.nan

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["AvgRestDays"] = avg_rest
        row["ShortRestGames"] = short_games
        row["ShortRestShare"] = short_share
        row["LongRestGames"] = long_games
        row["LongRestShare"] = long_share
        rest_rows.append(row)

    rest_df = pd.DataFrame(rest_rows)

    # ---------- Streaks (WinsInRow, LossesInRow) ----------
    streak_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        margins = df_t["Margin"].tolist()

        wins_in_row = 0
        losses_in_row = 0
        for m in reversed(margins):
            if pd.isna(m):
                break
            if m > 0:
                if losses_in_row > 0:
                    break
                wins_in_row += 1
            elif m < 0:
                if wins_in_row > 0:
                    break
                losses_in_row += 1
            else:
                break

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["WinsInRow"] = wins_in_row if wins_in_row > 0 else np.nan
        row["LossesInRow"] = losses_in_row if losses_in_row > 0 else np.nan
        streak_rows.append(row)

    streak_df = pd.DataFrame(streak_rows)

    # ---------- Merge back only into empty columns ----------
    out = teams_core.copy()
    out = _safe_backfill_team_cols(out, last5_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, early_late_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, buckets_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, rest_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, streak_df, key_cols=key_cols)

    return out
def _enrich_teams_from_games_v30(
    teams_core: pd.DataFrame,
    games_core: pd.DataFrame,
) -> pd.DataFrame:
    """
    Use played games to backfill missing team metrics (only into null/missing cols):

    - Last5 / Last10 style scoring and margin:
        L5PPG, L5MarginPG, Last5MarginPG, Last10MarginPG
    - Early/late season performance:
        EarlyGames, EarlyWins, EarlyMarginPG,
        LateGames, LateWins, LateMarginPG, IsLateSkew
    - Margin buckets:
        GamesMargin0to3, WinsMargin0to3, WinPctMargin0to3,
        GamesMargin4to10, WinsMargin4to10, WinPctMargin4to10,
        GamesMargin11to20, WinsMargin11to20, WinPctMargin11to20,
        GamesMargin21plus, WinsMargin21plus, WinPctMargin21plus
    - Rest metrics:
        AvgRestDays, ShortRestGames, ShortRestShare,
        LongRestGames, LongRestShare
    - Streaks:
        WinsInRow, LossesInRow
    """
    if "TeamKey" not in teams_core.columns:
        return teams_core

    long = _build_long_team_games_v30(games_core)

    # Keys we group/merge on
    key_cols = ["TeamKey"]
    if "Team" in teams_core.columns:
        key_cols = ["TeamKey", "Team"]

    # Ensure long table has Team column if teams_core has it
    if "Team" not in long.columns and "Team" in teams_core.columns:
        long["Team"] = np.nan

    # ---------- Last5 / Last10 metrics ----------
    last_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        df_t["L5PPG"] = df_t["PointsFor"].rolling(window=5, min_periods=1).mean()
        df_t["L5MarginPG"] = df_t["Margin"].rolling(window=5, min_periods=1).mean()
        df_t["Last5MarginPG"] = df_t["Margin"].rolling(window=5, min_periods=1).mean()
        df_t["Last10MarginPG"] = df_t["Margin"].rolling(window=10, min_periods=1).mean()
        last = df_t.iloc[-1]

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["L5PPG"] = last["L5PPG"]
        row["L5MarginPG"] = last["L5MarginPG"]
        row["Last5MarginPG"] = last["Last5MarginPG"]
        row["Last10MarginPG"] = last["Last10MarginPG"]
        last_rows.append(row)

    last5_df = pd.DataFrame(last_rows)

    # ---------- Early / Late metrics ----------
    early_late_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        n = len(df_t)
        if n == 0:
            continue
        split = max(n // 2, 1)

        early = df_t.iloc[:split]
        late = df_t.iloc[split:]

        early_games = len(early)
        late_games = len(late)

        early_margin = early["Margin"].mean() if early_games > 0 else np.nan
        late_margin = late["Margin"].mean() if late_games > 0 else np.nan

        early_wins = (early["Margin"] > 0).sum()
        late_wins = (late["Margin"] > 0).sum()

        is_late_skew = int(
            (late_margin if not np.isnan(late_margin) else 0.0)
            > (early_margin if not np.isnan(early_margin) else 0.0)
        )

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["EarlyGames"] = early_games
        row["EarlyWins"] = early_wins
        row["EarlyMarginPG"] = early_margin
        row["LateGames"] = late_games
        row["LateWins"] = late_wins
        row["LateMarginPG"] = late_margin
        row["IsLateSkew"] = is_late_skew
        early_late_rows.append(row)

    early_late_df = pd.DataFrame(early_late_rows)

    # ---------- Margin buckets ----------
    bucket_rows = []
    for key, df_t in long.groupby(key_cols):
        df_t = df_t.copy()
        df_t["abs_margin"] = df_t["Margin"].abs()

        def bucket(lo, hi=None):
            if hi is None:
                mask = df_t["abs_margin"] >= lo
            else:
                mask = (df_t["abs_margin"] >= lo) & (df_t["abs_margin"] <= hi)
            sub = df_t[mask]
            games = len(sub)
            if games == 0:
                return games, 0, np.nan
            wins = (sub["Margin"] > 0).sum()
            win_pct = wins / games
            return games, wins, win_pct

        g0, w0, p0 = bucket(0, 3)
        g4, w4, p4 = bucket(4, 10)
        g11, w11, p11 = bucket(11, 20)
        g21, w21, p21 = bucket(21, None)

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["GamesMargin0to3"] = g0
        row["WinsMargin0to3"] = w0
        row["WinPctMargin0to3"] = p0

        row["GamesMargin4to10"] = g4
        row["WinsMargin4to10"] = w4
        row["WinPctMargin4to10"] = p4

        row["GamesMargin11to20"] = g11
        row["WinsMargin11to20"] = w11
        row["WinPctMargin11to20"] = p11

        row["GamesMargin21plus"] = g21
        row["WinsMargin21plus"] = w21
        row["WinPctMargin21plus"] = p21

        bucket_rows.append(row)

    buckets_df = pd.DataFrame(bucket_rows)

    # ---------- Rest metrics ----------
    rest_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        dates = df_t["Date"].dropna()
        if dates.empty:
            avg_rest = np.nan
            short_games = 0
            long_games = 0
            short_share = np.nan
            long_share = np.nan
        else:
            deltas = dates.diff().dt.days.iloc[1:]
            short_mask = deltas <= 1
            long_mask = deltas >= 5
            short_games = int(short_mask.sum())
            long_games = int(long_mask.sum())
            total = len(deltas)
            avg_rest = deltas.mean() if total > 0 else np.nan
            short_share = short_games / total if total > 0 else np.nan
            long_share = long_games / total if total > 0 else np.nan

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["AvgRestDays"] = avg_rest
        row["ShortRestGames"] = short_games
        row["ShortRestShare"] = short_share
        row["LongRestGames"] = long_games
        row["LongRestShare"] = long_share
        rest_rows.append(row)

    rest_df = pd.DataFrame(rest_rows)

    # ---------- Streaks (WinsInRow, LossesInRow) ----------
    streak_rows = []
    for key, df_t in long.sort_values("Date").groupby(key_cols):
        df_t = df_t.sort_values("Date")
        margins = df_t["Margin"].tolist()

        wins_in_row = 0
        losses_in_row = 0
        for m in reversed(margins):
            if pd.isna(m):
                break
            if m > 0:
                if losses_in_row > 0:
                    break
                wins_in_row += 1
            elif m < 0:
                if wins_in_row > 0:
                    break
                losses_in_row += 1
            else:
                break

        row = {}
        if len(key_cols) == 2:
            row["TeamKey"], row["Team"] = key
        else:
            (row["TeamKey"],) = key

        row["WinsInRow"] = wins_in_row if wins_in_row > 0 else np.nan
        row["LossesInRow"] = losses_in_row if losses_in_row > 0 else np.nan
        streak_rows.append(row)

    streak_df = pd.DataFrame(streak_rows)

    # ---------- Merge back only into empty columns ----------
    out = teams_core.copy()
    out = _safe_backfill_team_cols(out, last5_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, early_late_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, buckets_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, rest_df, key_cols=key_cols)
    out = _safe_backfill_team_cols(out, streak_df, key_cols=key_cols)

    return out


def annotate_expected_wins_and_sos(
    teams_core: pd.DataFrame,
    games_core: pd.DataFrame,
    *,
    hfa_points: float = 3.0,
    neutral_hfa_points: float = 0.0,
    spread_sigma: float = 11.0,
) -> pd.DataFrame:
    df = teams_core.copy()

    # Choose rating column: prefer NetEff, else MarginPG
    if "NetEff" in df.columns:
        rating = df.set_index("TeamKey")["NetEff"].astype(float)
    else:
        rating = df.set_index("TeamKey")["MarginPG"].astype(float)

    g = games_core.copy()
    # Only played games
    g = g[g["Played"].fillna(False)].copy()

    # Map ratings
    g["HomeRating"] = g["HomeKey"].map(rating)
    g["AwayRating"] = g["AwayKey"].map(rating)
    g["HomeRating"] = g["HomeRating"].fillna(0.0)
    g["AwayRating"] = g["AwayRating"].fillna(0.0)

    # Home court advantage (0 for neutral)
    is_neutral = g.get("IsNeutral", False).fillna(False).astype(bool)
    hfa = np.where(is_neutral, neutral_hfa_points, hfa_points)

    # Expected margin (home - away)
    g["ExpMarginHome"] = (g["HomeRating"] - g["AwayRating"]) + hfa

    # Convert expected margin to win probability using logistic curve
    k = np.pi / (np.sqrt(3.0) * float(spread_sigma))
    g["WinProbHome"] = 1.0 / (1.0 + np.exp(-k * g["ExpMarginHome"]))
    g["WinProbAway"] = 1.0 - g["WinProbHome"]

    # Build per-team expected wins
    home_exp = g[["HomeKey", "Season", "WinProbHome"]].copy()
    home_exp = home_exp.rename(columns={"HomeKey": "TeamKey", "WinProbHome": "WinProb"})

    away_exp = g[["AwayKey", "Season", "WinProbAway"]].copy()
    away_exp = away_exp.rename(columns={"AwayKey": "TeamKey", "WinProbAway": "WinProb"})

    exp = pd.concat([home_exp, away_exp], ignore_index=True)

    exp_agg = (
        exp.groupby(["TeamKey", "Season"], dropna=False, as_index=False)
           .agg(ExpectedWins=("WinProb", "sum"))
    )

    # Attach ExpectedWins and derived SOS metrics
    df = df.merge(exp_agg[["TeamKey", "ExpectedWins"]], on="TeamKey", how="left")
    df["ExpectedWins"] = df["ExpectedWins"].fillna(0.0)

    df["SOS_EWP"] = np.where(
        df["Games"].fillna(0) > 0, df["ExpectedWins"] / df["Games"], np.nan
    )
    df["ScheduleAdjWins"] = df["Wins"].fillna(0) - df["ExpectedWins"]

    return df


def annotate_rpi_quads_and_luck_v30(
    teams_core: pd.DataFrame,
    games_core: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add RPI-style SOS (OWP, OOWP, RPI), quadrant records (Q1–Q4),
    and LuckZ based on ScheduleAdjWins.
    """
    teams = teams_core.copy()
    games = games_core.copy()

    # ---------- RPI-style OWP, OOWP ----------
    base = teams[["TeamKey", "Wins", "Losses"]].copy()
    base["Games"] = base["Wins"].fillna(0) + base["Losses"].fillna(0)
    base["WP"] = np.where(
        base["Games"] > 0,
        base["Wins"] / base["Games"],
        np.nan,
    )
    base = base.set_index("TeamKey")

    g = games.copy()
    g = g[g["Played"].fillna(False)].copy()

    g["WinnerTeamKey"] = np.where(
        g["HomeScore"] > g["AwayScore"],
        g["HomeKey"],
        np.where(
            g["AwayScore"] > g["HomeScore"],
            g["AwayKey"],
            np.nan,
        ),
    )

    home = pd.DataFrame(
        {
            "TeamKey": g["HomeKey"],
            "OppKey": g["AwayKey"],
            "IsWin": g["WinnerTeamKey"] == g["HomeKey"],
        }
    )
    away = pd.DataFrame(
        {
            "TeamKey": g["AwayKey"],
            "OppKey": g["HomeKey"],
            "IsWin": g["WinnerTeamKey"] == g["AwayKey"],
        }
    )
    log = pd.concat([home, away], ignore_index=True)
    log = log.dropna(subset=["TeamKey", "OppKey"])

    def _owp_for_team(tk: str) -> float:
        sub = log[log["TeamKey"] == tk]
        if sub.empty:
            return np.nan

        opp_keys = sub["OppKey"].values
        owp_vals = []
        for opp in opp_keys:
            opp_log = log[log["TeamKey"] == opp]
            if opp_log.empty:
                owp_vals.append(np.nan)
                continue

            opp_vs_team = opp_log[opp_log["OppKey"] == tk]
            total_wins = int(np.asarray(opp_log["IsWin"], dtype=bool).sum())
            total_games = len(opp_log)
            exclude_wins = int(np.asarray(opp_vs_team["IsWin"], dtype=bool).sum())
            exclude_games = len(opp_vs_team)

            adj_games = total_games - exclude_games
            adj_wins = total_wins - exclude_wins

            if adj_games > 0:
                owp_vals.append(adj_wins / adj_games)
            else:
                owp_vals.append(np.nan)

        owp_vals = [v for v in owp_vals if v == v]
        if not owp_vals:
            return np.nan
        return float(np.mean(owp_vals))

    owp_map: dict[str, float] = {}
    unique_teams = log["TeamKey"].dropna().unique()
    for tk in unique_teams:
        owp_map[tk] = _owp_for_team(tk)

    owp_series = pd.Series(owp_map, name="OWP")

    def _oowp_for_team(tk: str) -> float:
        sub = log[log["TeamKey"] == tk]
        if sub.empty:
            return np.nan
        opp_keys = sub["OppKey"].dropna().unique()
        vals = [owp_map.get(o, np.nan) for o in opp_keys]
        vals = [v for v in vals if v == v]
        if not vals:
            return np.nan
        return float(np.mean(vals))

    oowp_map: dict[str, float] = {}
    for tk in unique_teams:
        oowp_map[tk] = _oowp_for_team(tk)

    oowp_series = pd.Series(oowp_map, name="OOWP")

    rpi_df = (
        base[["WP"]]
        .join(owp_series, how="left")
        .join(oowp_series, how="left")
        .reset_index()
    )
    rpi_df["RPI"] = (
        0.25 * rpi_df["WP"].fillna(0)
        + 0.50 * rpi_df["OWP"].fillna(0)
        + 0.25 * rpi_df["OOWP"].fillna(0)
    )

    teams = teams.merge(rpi_df, on="TeamKey", how="left")

    # ---------- Quadrant records (Q1–Q4) ----------
    strength_df = (
        teams[["TeamKey", "NetEff"]]
        .dropna(subset=["TeamKey"])
        .drop_duplicates(subset=["TeamKey"], keep="first")
    )
    strength = strength_df.set_index("TeamKey")["NetEff"].astype(float)

    gg = games.copy()
    gg = gg[gg["Played"].fillna(False)].copy()

    gg["HomeNetEff"] = gg["HomeKey"].map(strength)
    gg["AwayNetEff"] = gg["AwayKey"].map(strength)

    team_rank_df = (
        strength_df.sort_values("NetEff", ascending=False)
                   .reset_index(drop=True)
    )
    team_rank_df["StrengthRank"] = team_rank_df["NetEff"].rank(
        method="min", ascending=False
    )
    rank_map = (
        team_rank_df.set_index("TeamKey")["StrengthRank"]
        .astype(float)
        .to_dict()
    )

    gg["HomeStrengthRank"] = gg["HomeKey"].map(rank_map)
    gg["AwayStrengthRank"] = gg["AwayKey"].map(rank_map)

    home_rows = pd.DataFrame(
        {
            "TeamKey": gg["HomeKey"],
            "OppKey": gg["AwayKey"],
            "IsWin": gg["HomeScore"] > gg["AwayScore"],
            "IsHome": True,
            "IsNeutral": gg["IsNeutral"].fillna(False),
            "OppStrengthRank": gg["AwayStrengthRank"],
        }
    )
    away_rows = pd.DataFrame(
        {
            "TeamKey": gg["AwayKey"],
            "OppKey": gg["HomeKey"],
            "IsWin": gg["AwayScore"] > gg["HomeScore"],
            "IsHome": False,
            "IsNeutral": gg["IsNeutral"].fillna(False),
            "OppStrengthRank": gg["HomeStrengthRank"],
        }
    )
    tlog = pd.concat([home_rows, away_rows], ignore_index=True)
    tlog = tlog.dropna(subset=["TeamKey", "OppStrengthRank"])

    is_home = tlog["IsHome"] & (~tlog["IsNeutral"])
    is_neutral = tlog["IsNeutral"]

    loc = np.where(is_home, "H", np.where(is_neutral, "N", "A"))
    tlog["Location"] = loc

    def _quadrant(row) -> str | None:
        r = row["OppStrengthRank"]
        loc = row["Location"]
        if pd.isna(r):
            return None
        r = float(r)
        if loc == "H":
            if r <= 30:
                return "Q1"
            elif r <= 75:
                return "Q2"
            elif r <= 160:
                return "Q3"
            else:
                return "Q4"
        elif loc == "N":
            if r <= 50:
                return "Q1"
            elif r <= 100:
                return "Q2"
            elif r <= 200:
                return "Q3"
            else:
                return "Q4"
        else:  # Away
            if r <= 75:
                return "Q1"
            elif r <= 135:
                return "Q2"
            elif r <= 240:
                return "Q3"
            else:
                return "Q4"

    tlog["Quadrant"] = tlog.apply(_quadrant, axis=1)

    quad = (
        tlog.dropna(subset=["Quadrant"])
            .groupby(["TeamKey", "Quadrant"], dropna=False)
            .agg(
                Games=("IsWin", "size"),
                Wins=("IsWin", lambda s: int(np.asarray(s, dtype=bool).sum())),
            )
            .reset_index()
    )
    quad["Losses"] = quad["Games"] - quad["Wins"]

    quad_wide = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        sub = quad[quad["Quadrant"] == q].copy()
        sub = sub.set_index("TeamKey")
        quad_wide[f"{q}_Games"] = sub["Games"]
        quad_wide[f"{q}_Wins"] = sub["Wins"]
        quad_wide[f"{q}_Losses"] = sub["Losses"]

    quad_df = pd.DataFrame(quad_wide)
    quad_df.index.name = "TeamKey"
    quad_df = quad_df.reset_index()

    teams = teams.merge(quad_df, on="TeamKey", how="left")

    # ---------- Luck / overperformance context ----------
    luck = teams["ScheduleAdjWins"].astype(float)
    if luck.notna().sum() >= 5:
        mu = luck.mean()
        sigma = luck.std(ddof=0)
        if sigma > 0:
            teams["LuckZ"] = (luck - mu) / sigma
        else:
            teams["LuckZ"] = np.nan
    else:
        teams["LuckZ"] = np.nan

    return teams


def _compute_team_pi_from_games_v30(games_core: pd.DataFrame) -> pd.DataFrame:
    """
    Compute team-level PI as the latest available PI snapshot per TeamKey
    from games_core (home and away sides combined).

    Returns a DataFrame with columns: TeamKey, PI
    """
    g = games_core.copy()

    home = g[["HomeKey", "HomePI", "Date"]].rename(
        columns={"HomeKey": "TeamKey", "HomePI": "PI"}
    )
    away = g[["AwayKey", "AwayPI", "Date"]].rename(
        columns={"AwayKey": "TeamKey", "AwayPI": "PI"}
    )

    pi_long = pd.concat([home, away], ignore_index=True)

    pi_long["PI"] = pd.to_numeric(pi_long["PI"], errors="coerce")
    pi_long = pi_long.dropna(subset=["TeamKey", "PI"])

    if "Date" in pi_long.columns:
        pi_long = pi_long.sort_values(["TeamKey", "Date"])
    else:
        pi_long = pi_long.sort_values(["TeamKey"])

    pi_latest = (
        pi_long.drop_duplicates(subset=["TeamKey"], keep="last")
              .loc[:, ["TeamKey", "PI"]]
    )

    return pi_latest


def build_core_v30(path: Path = TRUTH_CSV):
    raw = load_truth_csv(path)
    games_core = build_games_core(raw)
    teams_core = build_teams_core(games_core)

    # ---------- Compute team-level TI from game TI ----------
    g = games_core.copy()
    g["Date"] = pd.to_datetime(g.get("Date", None), errors="coerce")

    ti_rows: list[pd.DataFrame] = []

    if {"HomeKey", "HomeTI"}.issubset(g.columns):
        home_ti = g[["HomeKey", "HomeTI", "Date"]].rename(
            columns={"HomeKey": "TeamKey", "HomeTI": "TI"}
        )
        ti_rows.append(home_ti)

    if {"AwayKey", "AwayTI"}.issubset(g.columns):
        away_ti = g[["AwayKey", "AwayTI", "Date"]].rename(
            columns={"AwayKey": "TeamKey", "AwayTI": "TI"}
        )
        ti_rows.append(away_ti)

    if ti_rows:
        ti_long = pd.concat(ti_rows, ignore_index=True)
        ti_long["TeamKey"] = ti_long["TeamKey"].astype(str).str.strip()
        ti_long["TI"] = pd.to_numeric(ti_long["TI"], errors="coerce")
        ti_long["Date"] = pd.to_datetime(ti_long["Date"], errors="coerce")

        ti_long = ti_long.dropna(subset=["TeamKey", "TI"])
        ti_long = ti_long.sort_values(["TeamKey", "Date"])

        latest_ti = (
            ti_long.drop_duplicates(subset=["TeamKey"], keep="last")
                  .loc[:, ["TeamKey", "TI"]]
        )

        teams_core["TeamKey"] = teams_core["TeamKey"].astype(str).str.strip()
        teams_core = teams_core.merge(
            latest_ti, on="TeamKey", how="left", suffixes=("", "_from_games_ti")
        )

        if "TI_from_games_ti" in teams_core.columns:
            if "TI" not in teams_core.columns:
                teams_core["TI"] = pd.NA
            teams_core["TI"] = teams_core["TI"].where(
                teams_core["TI"].notna(), teams_core["TI_from_games_ti"]
            )
            teams_core = teams_core.drop(columns=["TI_from_games_ti"])

    # Add expected wins / SOS metrics
    teams_core = annotate_expected_wins_and_sos(teams_core, games_core)

    # Add RPI-style SOS, quadrant records, and LuckZ
    teams_core = annotate_rpi_quads_and_luck_v30(teams_core, games_core)

    # Add per-game predictions and evaluation fields
    games_core = _add_game_predictions_v30(games_core, teams_core)

    # Winner is the winning team's TeamKey for played games
    games_core["Winner"] = np.where(
        games_core["Played"].fillna(False) & (games_core["Margin"] > 0),
        games_core["HomeKey"],
        np.where(
            games_core["Played"].fillna(False) & (games_core["Margin"] < 0),
            games_core["AwayKey"],
            np.nan,
        ),
    )

    # FavProb is the favorite's win probability (0–1)
    games_core["FavProb"] = np.where(
        games_core["FavoriteIsHome"].fillna(False),
        games_core["PredHomeWinProb"].astype(float),
        1.0 - games_core["PredHomeWinProb"].astype(float),
    )

    # Bulk enrich team metrics (rate-based, non game-log)
    teams_core = _enrich_teams_core_v30(teams_core)

    # Enrich metrics that depend on per-team game logs
    teams_core = _enrich_teams_from_games_v30(teams_core, games_core)

    # Compute real streaks from games and merge into teams_core
    streaks = _compute_team_streaks_v30(games_core)
    teams_core = teams_core.merge(
        streaks, on="TeamKey", how="left", suffixes=("", "_new")
    )

    for col in ["WinsInRow", "LossesInRow"]:
        new_col = f"{col}_new"
        if new_col in teams_core.columns:
            teams_core[col] = teams_core[new_col]
            teams_core.drop(columns=[new_col], inplace=True)

    # ---------- Attach Gender / Class / Region from games_core ----------
    g = games_core.copy()

    home_attr = g[["HomeKey", "Gender", "HomeClass", "HomeRegion"]].rename(
        columns={"HomeKey": "TeamKey", "HomeClass": "Class", "HomeRegion": "Region"}
    )
    away_attr = g[["AwayKey", "Gender", "AwayClass", "AwayRegion"]].rename(
        columns={"AwayKey": "TeamKey", "AwayClass": "Class", "AwayRegion": "Region"}
    )

    attr = pd.concat([home_attr, away_attr], ignore_index=True)

    for col in ["Gender", "Class", "Region"]:
        if col in attr.columns:
            attr[col] = attr[col].astype(str).str.strip()

    attr["Gender"] = attr["Gender"].str.title()
    attr["Class"] = attr["Class"].str.upper()
    attr["Region"] = attr["Region"].str.title()

    attr = (
        attr.dropna(subset=["TeamKey"])
            .drop_duplicates(subset=["TeamKey"])
    )

    teams_core = teams_core.merge(
        attr[["TeamKey", "Gender", "Class", "Region"]],
        on="TeamKey",
        how="left",
        suffixes=("", "_from_games"),
    )

    for col in ["Gender", "Class", "Region"]:
        new_col = f"{col}_from_games"
        if new_col in teams_core.columns:
            if col not in teams_core.columns:
                teams_core[col] = np.nan
            teams_core[col] = teams_core[col].where(
                teams_core[col].notna(), teams_core[new_col]
            )
            teams_core.drop(columns=[new_col], inplace=True)

    # Hard guarantee: one row per TeamKey
    teams_core = teams_core.drop_duplicates(subset=["TeamKey"]).reset_index(drop=True)

    # --- Compute Elo-style TSR and attach it ---
    teams_core = teams_core.copy()
    teams_core["TeamKey"] = teams_core["TeamKey"].astype(str).str.strip()

    tsr_series = compute_tsr_elo_v30(teams_core, games_core)

    if tsr_series is not None:
        tsr_series.index = tsr_series.index.astype(str).str.strip()

        teams_core = teams_core.set_index("TeamKey")
        teams_core["TSR"] = tsr_series
        teams_core["TSR"] = pd.to_numeric(teams_core["TSR"], errors="coerce")
        teams_core = teams_core.reset_index()
    else:
        teams_core["TSR"] = pd.NA

    # Add TSR_Display + tiers from TSR
    teams_core = _add_tsr_and_tiers_v30(teams_core)

    # Ensure schemas are stable for downstream pages
    teams_core = _ensure_team_schema_v30(teams_core)
    games_core = _ensure_game_schema_v30(games_core)

    return teams_core, games_core













