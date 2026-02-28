import pandas as pd
from pathlib import Path
import numpy as np

BASE = Path(r"C:\ANALYTICS207")

def build_games_analytics_v40():
    # --- 1. Load base inputs (minimal cores + truth + travel) ---

    games_v40 = pd.read_parquet(
        BASE / r"data\core\games_game_core_v40.parquet"
    )
    # rich v30 game metrics (we'll cherry-pick descriptive ones later if needed)
    games_v30 = pd.read_parquet(
        BASE / r"data\core\gamesgamecorev30.parquet"
    )
    # travel v30 (has travel + some model fields)
    travel_v30 = pd.read_parquet(
        BASE / r"data\travel_core_v30.parquet"
    )
    truth = pd.read_csv(
        BASE / r"truth.csv",
        parse_dates=["Date"]
    )

    # --- 2. Standardize keys / basic fields from v40 core ---

    df = games_v40.copy()

    # Ensure we have consistent dtypes
    df["Season"] = df["Season"].astype(str)
    df["GameID"] = df["GameID"].astype(int)

    # Basic derived from v40 core
    df["TotalPoints"] = df["HomeScore"] + df["AwayScore"]
    df["AbsMargin"] = df["Margin"].abs()

    # Winner flags
    df["HomeWinFlag"] = (df["HomeScore"] > df["AwayScore"]).astype(int)
    df["AwayWinFlag"] = (df["AwayScore"] > df["HomeScore"]).astype(int)
    df["TieFlag"] = (df["HomeScore"] == df["AwayScore"]).astype(int)

    # --- 3. Join in truth-game context (one row per GameID) ---

    # truth is one row per team snapshot; we want game-level aggregation.
    # We'll take the "Team1 perspective" row as canonical for game-level context.
    # (If you prefer Home perspective, we can adjust later.)

    truth_game = (
        truth
        .sort_values(["GameID", "GamesPlayed"])  # deterministic pick if dupe
        .drop_duplicates(subset=["GameID"], keep="first")
        .rename(columns={
            "Date": "TruthDate",
            "Gender": "TruthGender",
            "SchoolClass": "TruthClass",
            "SchoolRegion": "TruthRegion",
            "SchoolDivision": "TruthDivision",
            "OppDiv": "TruthOppDivision",
            "GameNum": "TruthGameNum",
            "Rank": "TruthRank",
            "RecordText": "TruthRecordText",
            "GamesPlayed": "TruthGamesPlayed",
            "GamesScheduled": "TruthGamesScheduled",
            "PI": "TruthPI",
            "TI": "TruthTI",
            "Result": "TruthResult",
            "Winner": "TruthWinner",
            "Loser": "TruthLoser",
            "WinPoints": "TruthWinPoints",
            "OppPreliminaryIndex": "TruthOppPrelimIndex",
            "WinFlag": "TruthWinFlag",
            "LossFlag": "TruthLossFlag",
            "TieFlag": "TruthTieFlag",
        })
        [["GameID", "TruthDate", "TruthGender", "TruthClass", "TruthRegion",
          "TruthDivision", "TruthOppDivision", "TruthGameNum", "TruthRank",
          "TruthRecordText", "TruthGamesPlayed", "TruthGamesScheduled",
          "TruthPI", "TruthTI", "TruthResult", "TruthWinner", "TruthLoser",
          "TruthWinPoints", "TruthOppPrelimIndex", "TruthWinFlag",
          "TruthLossFlag", "TruthTieFlag"]]
    )

    df = df.merge(truth_game, on="GameID", how="left")

    # --- 4. Site / role / matchup type metrics ---

    # Site from existing IsNeutral + home/away labels
    df["Site"] = np.select(
        [
            df["IsNeutral"] == 1,
            df["Home"].eq(df["WinnerTeam"]),
            df["Away"].eq(df["WinnerTeam"]),
        ],
        [
            "Neutral",
            "HomeWin" ,
            "AwayWin",
        ],
        default="Unknown",
    )

    # Class / region / division matchup types (same vs up/down/cross)
    # Using truth "SchoolClass/Region/Division" as Team1 perspective vs opponent.
    # This is game-level context; team-level splits will be aggregated later.

    def _class_order(c):
        order = {"A": 4, "B": 3, "C": 2, "D": 1, "S": 5}
        return order.get(c, np.nan)

    df["TruthClassOrder"] = df["TruthClass"].map(_class_order)
    df["TruthOppClassOrder"] = df["TruthOppDivision"].map(_class_order)  # if OppDiv is class-like; adjust if not

    df["ClassMatchupType"] = np.where(
        df["TruthClassOrder"].isna() | df["TruthOppClassOrder"].isna(),
        "Unknown",
        np.where(
            df["TruthClassOrder"] == df["TruthOppClassOrder"],
            "SameClass",
            np.where(
                df["TruthClassOrder"] > df["TruthOppClassOrder"],
                "DownClass",  # playing down in class
                "UpClass",    # playing up in class
            ),
        ),
    )

    df["RegionMatchupType"] = np.where(
        df["TruthRegion"].isna(),
        "Unknown",
        np.where(
            df["TruthRegion"] == df["TruthRegion"],  # same region vs itself not meaningful
            "SameOrUnknown",  # placeholder; adjust when you have opp region
            "CrossRegion",
        ),
    )

    df["DivisionMatchupType"] = np.where(
        df["TruthDivision"].isna() | df["TruthOppDivision"].isna(),
        "Unknown",
        np.where(
            df["TruthDivision"] == df["TruthOppDivision"],
            "SameDivision",
            "CrossDivision",
        ),
    )

    # --- 5. Rank / rating context & upset flags ---

    # For now we only have "TruthRank/TI/PI" from one side; later we can join opp.
    # Upset by TI/PI: if winner has lower TI/PI but wins (direction depends on scale).
    # Assuming higher TI/PI = better.

    df["IsUpsetByTI"] = False
    df["IsUpsetByPI"] = False

    # If you later join opponent TI/PI at game time, compute proper diffs here.

    # --- 6. Season phase / sequence from TruthGameNum & Date ---

    df["TruthGameNum"] = df["TruthGameNum"].fillna(0).astype(int)

    df["SeasonPhase"] = pd.cut(
        df["TruthGameNum"],
        bins=[-1, 5, 10, 1000],
        labels=["Early", "Mid", "Late"]
    )

    # You can add more refined phases later if you want.

    # --- 7. Join descriptive travel fields from travel_core_v30 ---

    # travel_core_v30 is game-grain; we drop all prediction-ish columns here.
    travel_cols_keep = [
        "GameID",
        "MilesOneWay",
        "MilesRoundTrip",
        "BusHours",
        "ParentGasCost",
        "BusGasCost",
        # keep other descriptive fields you trust here if any
    ]
    travel_desc = travel_v30[travel_cols_keep].drop_duplicates("GameID")

    df = df.merge(travel_desc, on="GameID", how="left")

    # --- 8. Optionally bring in extra descriptive fields from games_v30 ---

    # Identify descriptive-only columns in v30 (no Pred/Prob/Fav/ModelCorrect/MarginError)
    drop_patterns = ("Pred", "Prob", "Favorite", "Fav", "ModelCorrect", "MarginError")
    extra_cols_v30 = [
        c for c in games_v30.columns
        if c not in df.columns   # not already present
        and not any(pat in c for pat in drop_patterns)
    ]
    games_v30_extra = games_v30[["GameID"] + extra_cols_v30].drop_duplicates("GameID")

    df = df.merge(games_v30_extra, on="GameID", how="left")

    # --- 9. Final cleanup & write ---

    # Drop helpers we don't want to expose (e.g., TruthClassOrder ints)
    df = df.drop(columns=["TruthClassOrder", "TruthOppClassOrder"], errors="ignore")

    out_path = BASE / r"data\core\games_analytics_v40.parquet"
    df.to_parquet(out_path, index=False)
    print("WROTE games analytics:", out_path, "rows:", len(df), "cols:", len(df.columns))


if __name__ == "__main__":
    build_games_analytics_v40()
