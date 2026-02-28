import sys
import pandas as pd

try:
    from sklearn.metrics import brier_score_loss
except Exception as e:
    raise RuntimeError("pip install scikit-learn") from e


REQ = ["GameID", "PredHomeWinProb", "ResultHomeWin"]

def load_preds(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path, columns=REQ)  # fast: column subset
    df["GameID"] = df["GameID"].astype(str).str.strip()
    df["PredHomeWinProb"] = pd.to_numeric(df["PredHomeWinProb"], errors="coerce")
    df["ResultHomeWin"] = pd.to_numeric(df["ResultHomeWin"], errors="coerce")

    # keep only played games (ResultHomeWin is 0/1)
    df = df[df["ResultHomeWin"].isin([0, 1])].copy()

    # clamp probs
    df["PredHomeWinProb"] = df["PredHomeWinProb"].clip(1e-6, 1 - 1e-6)

    # de-dupe just in case
    df = df.drop_duplicates(subset=["GameID"], keep="last")
    return df


def metrics(df: pd.DataFrame) -> dict:
    y = df["ResultHomeWin"].astype(int).to_numpy()
    p = df["PredHomeWinProb"].astype(float).to_numpy()
    acc = ((p >= 0.5) == (y == 1)).mean()
    brier = float(brier_score_loss(y, p))  # lower is better
    return {"Games": len(df), "Accuracy": acc, "Brier": brier}


def calib_table(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    # favorite probability (align with your v40-style favorite-based calibration idea)
    d["FavProb"] = d["PredHomeWinProb"].where(d["PredHomeWinProb"] >= 0.5, 1 - d["PredHomeWinProb"])
    d["FavWon"] = ((d["PredHomeWinProb"] >= 0.5) & (d["ResultHomeWin"] == 1)) | (
        (d["PredHomeWinProb"] < 0.5) & (d["ResultHomeWin"] == 0)
    )

    bins = [0.50, 0.60, 0.70, 0.80, 0.90, 1.0000001]
    labels = ["50-59", "60-69", "70-79", "80-89", "90-100"]
    d["Bin"] = pd.cut(d["FavProb"], bins=bins, labels=labels, right=False, include_lowest=True)

    out = (
        d.groupby("Bin", observed=True)
         .agg(Games=("FavWon", "size"),
              WinRate=("FavWon", "mean"),
              AvgFavProb=("FavProb", "mean"))
         .reset_index()
    )
    out["WinRate"] = out["WinRate"].round(4)
    out["AvgFavProb"] = out["AvgFavProb"].round(4)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: py compare_archived_preds.py <elo_or_old.parquet> <joint_or_new.parquet>")
        sys.exit(2)

    p1, p2 = sys.argv[1], sys.argv[2]
    a = load_preds(p1)
    b = load_preds(p2)

    print("\n=== METRICS ===")
    print("A:", p1)
    print(metrics(a))
    print("B:", p2)
    print(metrics(b))

    print("\n=== CALIBRATION (favorite bins) A ===")
    print(calib_table(a).to_string(index=False))

    print("\n=== CALIBRATION (favorite bins) B ===")
    print(calib_table(b).to_string(index=False))
