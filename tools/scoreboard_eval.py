
import pandas as pd
from pathlib import Path
import numpy as np
from math import log

DATA = Path(r"C:\ANALYTICS207\data")
PROD_CURRENT = DATA / "games_predictions_current.parquet"
TRUTH = DATA / "truth.csv"

def _logloss(y, p):
    eps = 1e-9
    p = np.clip(p, eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

def main():
    if not PROD_CURRENT.exists():
        raise FileNotFoundError(PROD_CURRENT)
    if not TRUTH.exists():
        raise FileNotFoundError(TRUTH)

    pred = pd.read_parquet(PROD_CURRENT)
    truth = pd.read_csv(TRUTH)

    # rename truth scores so we never collide with any pred columns
    if "HomeScore" not in truth.columns or "AwayScore" not in truth.columns:
        raise KeyError(f"truth.csv missing HomeScore/AwayScore. Columns: {list(truth.columns)}")

    t = truth[["GameID","HomeScore","AwayScore"]].rename(
        columns={"HomeScore":"TruthHomeScore","AwayScore":"TruthAwayScore"}
    )

    merged = pred.merge(t, on="GameID", how="left")

    has_score = merged["TruthHomeScore"].notna() & merged["TruthAwayScore"].notna()
    df = merged.loc[has_score].copy()

    if len(df) == 0:
        raise RuntimeError("No scored games after merge. Check GameID alignment.")

    actual_margin = (df["TruthHomeScore"] - df["TruthAwayScore"]).astype(float)
    actual_total = (df["TruthHomeScore"] + df["TruthAwayScore"]).astype(float)

    for c in ["PredMarginHome","PredTotal","PredHomeScore","PredAwayScore"]:
        if c not in df.columns:
            raise KeyError(f"predictions missing {c}. Columns: {list(df.columns)}")

    pred_margin = pd.to_numeric(df["PredMarginHome"], errors="coerce")
    pred_total = pd.to_numeric(df["PredTotal"], errors="coerce")

    spread_mae = float((pred_margin - actual_margin).abs().mean())
    total_mae = float((pred_total - actual_total).abs().mean())

    team_mae = float(
        (
            (pd.to_numeric(df["PredHomeScore"], errors="coerce") - df["TruthHomeScore"]).abs()
            + (pd.to_numeric(df["PredAwayScore"], errors="coerce") - df["TruthAwayScore"]).abs()
        ).mean() / 2.0
    )

    # win prob column detection
    prob_col = None
    for cand in ["PredHomeWinProb","PredWinProbCal","PredWinProbRaw"]:
        if cand in df.columns:
            prob_col = cand
            break

    brier = None
    logloss = None
    if prob_col is not None:
        p = pd.to_numeric(df[prob_col], errors="coerce").astype(float).to_numpy()
        y = (df["TruthHomeScore"].to_numpy() > df["TruthAwayScore"].to_numpy()).astype(int)
        brier = float(np.mean((p - y) ** 2))
        logloss = _logloss(y.astype(float), p.astype(float))

    actual_blowout = actual_margin.abs() >= 30
    actual_close = actual_margin.abs() <= 10
    pred_blowout = pred_margin.abs() >= 30
    pred_close = pred_margin.abs() <= 10

    pct_actual_blowout_pred_close = float((actual_blowout & pred_close).mean())
    pct_actual_close_pred_blowout = float((actual_close & pred_blowout).mean())

    print()
    print("SCOREBOARD EVAL")
    print("scored games", int(len(df)))
    print("SpreadMAE", spread_mae)
    print("TotalMAE", total_mae)
    print("TeamScoreMAE", team_mae)
    print("PctActualBlowoutPredClose", pct_actual_blowout_pred_close)
    print("PctActualClosePredBlowout", pct_actual_close_pred_blowout)
    if prob_col is not None:
        print("WinProbCol", prob_col)
        print("Brier", brier)
        print("LogLoss", logloss)
    else:
        print("WinProbCol", "not found in predictions")

if __name__ == "__main__":
    main()
