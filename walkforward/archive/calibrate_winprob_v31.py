from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import numpy as np
import pandas as pd


DATA_DIR = Path("data")
EVAL_IN = DATA_DIR / "model_eval_walkforward_v31.parquet"
CAL_TABLE_OUT = DATA_DIR / "calibration_winprob_table_v31.parquet"
EVAL_OUT = DATA_DIR / "model_eval_walkforward_v31_calibrated.parquet"


@dataclass
class CalConfig:
    prob_col: str = "PredWinProbHome"
    y_col: str = "HomeWin"
    n_bins: int = 40
    clip_eps: float = 1e-6


def _clip_prob(p: np.ndarray, eps: float) -> np.ndarray:
    return np.clip(p, eps, 1.0 - eps)


def build_monotone_calibration_table(p: np.ndarray, y: np.ndarray, n_bins: int) -> pd.DataFrame:
    df = pd.DataFrame({"p": p, "y": y}).sort_values("p").reset_index(drop=True)
    n = len(df)
    if n == 0:
        raise ValueError("No rows to calibrate")

    bin_id = np.floor(np.linspace(0, n_bins, n, endpoint=False)).astype(int)
    bin_id = np.minimum(bin_id, n_bins - 1)
    df["bin"] = bin_id

    agg = (
        df.groupby("bin", observed=False)
        .agg(p_lo=("p", "min"), p_hi=("p", "max"), p_mean=("p", "mean"), win_rate=("y", "mean"), n=("y", "size"))
        .reset_index(drop=True)
    )

    vals = agg["win_rate"].to_numpy(dtype=float)

    weights = agg["n"].to_numpy(dtype=float)
    blocks = []
    for i, v in enumerate(vals):
        blocks.append([v, weights[i], agg.loc[i, "p_lo"], agg.loc[i, "p_hi"]])

        while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
            v1, w1, lo1, hi1 = blocks[-2]
            v2, w2, lo2, hi2 = blocks[-1]
            v_new = (v1 * w1 + v2 * w2) / (w1 + w2)
            blocks[-2] = [v_new, w1 + w2, lo1, hi2]
            blocks.pop()

    rows = []
    for v, w, lo, hi in blocks:
        rows.append({"p_lo": float(lo), "p_hi": float(hi), "p_cal": float(v), "n": int(w)})

    out = pd.DataFrame(rows).sort_values("p_lo").reset_index(drop=True)
    out["p_mid"] = (out["p_lo"] + out["p_hi"]) / 2.0
    return out


def apply_table(p: np.ndarray, table: pd.DataFrame) -> np.ndarray:
    p_out = np.empty_like(p, dtype=float)
    p_lo = table["p_lo"].to_numpy(dtype=float)
    p_hi = table["p_hi"].to_numpy(dtype=float)
    p_cal = table["p_cal"].to_numpy(dtype=float)

    for i, x in enumerate(p):
        j = np.searchsorted(p_hi, x, side="left")
        if j >= len(p_hi):
            j = len(p_hi) - 1
        if x < p_lo[j]:
            j = max(j - 1, 0)
        p_out[i] = p_cal[j]

    return p_out


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def logloss(p: np.ndarray, y: np.ndarray, eps: float) -> float:
    p = _clip_prob(p, eps)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def main() -> None:
    cfg = CalConfig()

    if not EVAL_IN.exists():
        raise SystemExit(f"Missing {EVAL_IN}")

    df = pd.read_parquet(EVAL_IN).copy()

    if cfg.prob_col not in df.columns:
        raise SystemExit(f"Missing column {cfg.prob_col} in {EVAL_IN}")

    if "HomeScore" not in df.columns or "AwayScore" not in df.columns:
        raise SystemExit("Need HomeScore and AwayScore in eval parquet to derive outcome")

    y = (df["HomeScore"].to_numpy(dtype=float) > df["AwayScore"].to_numpy(dtype=float)).astype(float)
    p = df[cfg.prob_col].to_numpy(dtype=float)
    p = _clip_prob(p, cfg.clip_eps)

    table = build_monotone_calibration_table(p, y, cfg.n_bins)
    p_cal = apply_table(p, table)
    p_cal = _clip_prob(p_cal, cfg.clip_eps)

    df["PredWinProbCal"] = p_cal
    df["BrierCal"] = (p_cal - y) ** 2

    print("raw  brier", brier(p, y))
    print("raw  logloss", logloss(p, y, cfg.clip_eps))
    print("cal  brier", brier(p_cal, y))
    print("cal  logloss", logloss(p_cal, y, cfg.clip_eps))

    table.to_parquet(CAL_TABLE_OUT, index=False)
    df.to_parquet(EVAL_OUT, index=False)

    print("wrote", CAL_TABLE_OUT)
    print("wrote", EVAL_OUT)


if __name__ == "__main__":
    main()
