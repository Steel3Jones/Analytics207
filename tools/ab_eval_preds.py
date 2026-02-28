from __future__ import annotations

import argparse
import numpy as np
import pandas as pd


def _to_num(s):
    return pd.to_numeric(s, errors="coerce")


def _mae(err: pd.Series) -> float:
    return float(np.nanmean(np.abs(err)))


def _rmse(err: pd.Series) -> float:
    return float(np.sqrt(np.nanmean(err * err)))


def _summarize(df: pd.DataFrame, mask: pd.Series, label: str) -> dict:
    ph = _to_num(df["PredHomeScore"])
    pa = _to_num(df["PredAwayScore"])
    pm = _to_num(df["PredMargin"])
    pt = _to_num(df["PredTotalPoints"])

    hs = _to_num(df["HomeScore"])
    aws = _to_num(df["AwayScore"])

    played = mask & hs.notna() & aws.notna()

    actual_margin = hs - aws
    actual_total = hs + aws

    out = {
        "group": label,
        "n_played": int(played.sum()),
        "total_mae": _mae((pt - actual_total)[played]),
        "total_rmse": _rmse((pt - actual_total)[played]),
        "margin_mae": _mae((pm - actual_margin)[played]),
        "margin_rmse": _rmse((pm - actual_margin)[played]),
        "home_mae": _mae((ph - hs)[played]),
        "away_mae": _mae((pa - aws)[played]),
    }

    if "PredHomeWinProb" in df.columns:
        p = _to_num(df["PredHomeWinProb"]).clip(1e-6, 1 - 1e-6)
        y = (actual_margin > 0).astype(float)
        ll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
        out["winprob_logloss"] = float(np.nanmean(ll[played]))
        out["winprob_brier"] = float(np.nanmean(((p - y) ** 2)[played]))
    else:
        out["winprob_logloss"] = np.nan
        out["winprob_brier"] = np.nan

    return out


def _calibration_bins(df: pd.DataFrame, bins: int) -> pd.DataFrame:
    if "PredHomeWinProb" not in df.columns:
        return pd.DataFrame()

    hs = _to_num(df["HomeScore"])
    aws = _to_num(df["AwayScore"])
    played = hs.notna() & aws.notna()

    p = _to_num(df["PredHomeWinProb"]).clip(1e-6, 1 - 1e-6)
    y = ((hs - aws) > 0).astype(float)

    tmp = pd.DataFrame({"p": p, "y": y, "played": played})
    tmp = tmp[tmp["played"] & tmp["p"].notna() & tmp["y"].notna()]
    if tmp.empty:
        return pd.DataFrame()

    edges = np.linspace(0.0, 1.0, int(bins) + 1)
    tmp["bin"] = pd.cut(tmp["p"], bins=edges, include_lowest=True)

    cal = (
        tmp.groupby("bin", dropna=False)
        .agg(n=("p", "size"), avg_pred=("p", "mean"), avg_actual=("y", "mean"))
        .reset_index()
    )
    return cal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True, help="Parquet with preds + actuals (use games_public_v40.parquet)")
    ap.add_argument("--bins", type=int, default=10, help="Calibration bins for PredHomeWinProb")
    args = ap.parse_args()

    df = pd.read_parquet(args.preds).copy()

    required = ["PredHomeScore", "PredAwayScore", "PredMargin", "PredTotalPoints", "HomeScore", "AwayScore"]
    for c in required:
        if c not in df.columns:
            raise RuntimeError(f"Missing column: {c}")

    base_mask = pd.Series(True, index=df.index)

    rows = []
    rows.append(_summarize(df, base_mask, "ALL"))

    # By gender if present
    if "Gender" in df.columns:
        g = df["Gender"].astype(str).str.strip().str.title()
        rows.append(_summarize(df, g == "Boys", "Boys"))
        rows.append(_summarize(df, g == "Girls", "Girls"))

    # By abs predicted spread buckets
    spread_abs = _to_num(df["PredMargin"]).abs()
    rows.append(_summarize(df, spread_abs.notna() & (spread_abs < 5), "SpreadAbs_[0,5)"))
    rows.append(_summarize(df, spread_abs.notna() & (spread_abs >= 5) & (spread_abs < 10), "SpreadAbs_[5,10)"))
    rows.append(_summarize(df, spread_abs.notna() & (spread_abs >= 10) & (spread_abs < 15), "SpreadAbs_[10,15)"))
    rows.append(_summarize(df, spread_abs.notna() & (spread_abs >= 15), "SpreadAbs_[15,+)"))

    out = pd.DataFrame(rows)

    print("\n=== Prediction accuracy summary ===")
    print(out.to_string(index=False))

    cal = _calibration_bins(df, bins=int(args.bins))
    if not cal.empty:
        print("\n=== Winprob calibration bins ===")
        print(cal.to_string(index=False))


if __name__ == "__main__":
    main()
