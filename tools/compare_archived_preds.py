import sys
import numpy as np
import pandas as pd

from sklearn.metrics import brier_score_loss, log_loss

GAMES_CORE = r"C:\ANALYTICS207\data\core\games_game_core_v40.parquet"

PRED_REQ = [
    "GameID",
    "PredHomeWinProb",
    "ResultHomeWin",
    "PredHomeScore",
    "PredAwayScore",
    "PredMargin",
    "PredTotalPoints",
]

TRUTH_REQ = ["GameID", "HomeScore", "AwayScore", "Played"]


EPS = 1e-15


def load_preds(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path, columns=PRED_REQ)
    df["GameID"] = df["GameID"].astype(str).str.strip()

    df["PredHomeWinProb"] = pd.to_numeric(df["PredHomeWinProb"], errors="coerce").clip(EPS, 1 - EPS)
    df["ResultHomeWin"] = pd.to_numeric(df["ResultHomeWin"], errors="coerce")

    for c in ["PredHomeScore", "PredAwayScore", "PredMargin", "PredTotalPoints"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.drop_duplicates(subset=["GameID"], keep="last")
    return df


def load_truth() -> pd.DataFrame:
    t = pd.read_parquet(GAMES_CORE, columns=TRUTH_REQ)
    t["GameID"] = t["GameID"].astype(str).str.strip()
    t["HomeScore"] = pd.to_numeric(t["HomeScore"], errors="coerce")
    t["AwayScore"] = pd.to_numeric(t["AwayScore"], errors="coerce")
    t["Played"] = t["Played"].fillna(False).astype(bool)

    t = t[t["Played"]].copy()
    t = t.dropna(subset=["HomeScore", "AwayScore"])
    t = t.drop_duplicates(subset=["GameID"], keep="last")
    return t


def headline_metrics(df: pd.DataFrame) -> dict:
    d = df[df["ResultHomeWin"].isin([0, 1])].copy()
    y = d["ResultHomeWin"].astype(int).to_numpy()
    p = d["PredHomeWinProb"].astype(float).to_numpy()

    acc = float(((p >= 0.5) == (y == 1)).mean())
    brier = float(brier_score_loss(y, p))
    ll = float(log_loss(y, np.clip(p, EPS, 1 - EPS)))

    return {"Games": int(len(d)), "Accuracy": acc, "Brier": brier, "LogLoss": ll}


def add_favorite_cols(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    p = d["PredHomeWinProb"].astype(float)
    d["FavProb"] = np.where(p >= 0.5, p, 1 - p)
    d["FavWon"] = ((p >= 0.5) & (d["ResultHomeWin"] == 1)) | ((p < 0.5) & (d["ResultHomeWin"] == 0))
    d["FavWon"] = d["FavWon"].astype(int)
    return d


def reliability_table(y_true, p, n_bins=10) -> pd.DataFrame:
    d = pd.DataFrame({"y": y_true, "p": np.clip(p, EPS, 1 - EPS)}).dropna()
    d["Decile"] = pd.qcut(d["p"], q=n_bins, duplicates="drop")

    out = (
        d.groupby("Decile", observed=True)
        .agg(
            Games=("y", "size"),
            EmpiricalWinRate=("y", "mean"),
            AvgPredProb=("p", "mean"),
            MinProb=("p", "min"),
            MaxProb=("p", "max"),
        )
        .reset_index()
    )
    for c in ["EmpiricalWinRate", "AvgPredProb", "MinProb", "MaxProb"]:
        out[c] = out[c].astype(float).round(4)
    return out


def regression_metrics_from_preds(pred_df: pd.DataFrame, truth_df: pd.DataFrame) -> dict:
    d = pred_df.merge(truth_df, on="GameID", how="inner")

    d = d.dropna(
        subset=["PredHomeScore", "PredAwayScore", "PredMargin", "PredTotalPoints", "HomeScore", "AwayScore"]
    ).copy()

    actual_margin = (d["HomeScore"] - d["AwayScore"]).to_numpy(float)
    actual_total = (d["HomeScore"] + d["AwayScore"]).to_numpy(float)

    em = actual_margin - d["PredMargin"].to_numpy(float)
    et = actual_total - d["PredTotalPoints"].to_numpy(float)
    eh = d["HomeScore"].to_numpy(float) - d["PredHomeScore"].to_numpy(float)
    ea = d["AwayScore"].to_numpy(float) - d["PredAwayScore"].to_numpy(float)

    def mae(x): return float(np.mean(np.abs(x)))
    def rmse(x): return float(np.sqrt(np.mean(x * x)))

    return {
        "Games_scored": int(len(d)),
        "Margin_MAE": mae(em),
        "Margin_RMSE": rmse(em),
        "Total_MAE": mae(et),
        "Total_RMSE": rmse(et),
        "Home_MAE": mae(eh),
        "Away_MAE": mae(ea),
    }


def print_block(name: str, df: pd.DataFrame, truth: pd.DataFrame):
    print("\n=== HEADLINE ===")
    print(name, headline_metrics(df))

    print("\n=== SPREAD / SCORE ===")
    pred_cols = ["GameID", "PredHomeScore", "PredAwayScore", "PredMargin", "PredTotalPoints"]
    print(name, regression_metrics_from_preds(df[pred_cols], truth))

    print("\n=== RELIABILITY: HomeWinProb deciles ===")
    d = df[df["ResultHomeWin"].isin([0, 1])].copy()
    print(
        reliability_table(
            y_true=d["ResultHomeWin"].astype(int).to_numpy(),
            p=d["PredHomeWinProb"].astype(float).to_numpy(),
            n_bins=10,
        ).to_string(index=False)
    )

    print("\n=== RELIABILITY: FavoriteProb deciles ===")
    dd = add_favorite_cols(d)
    print(
        reliability_table(
            y_true=dd["FavWon"].to_numpy(dtype=int),
            p=dd["FavProb"].to_numpy(dtype=float),
            n_bins=10,
        ).to_string(index=False)
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: py compare_archived_preds.py <A.parquet> <B.parquet>")
        sys.exit(2)

    p1, p2 = sys.argv[1], sys.argv[2]
    truth = load_truth()

    a = load_preds(p1)
    b = load_preds(p2)

    print("\nA:", p1)
    print_block("A", a, truth)

    print("\nB:", p2)
    print_block("B", b, truth)
