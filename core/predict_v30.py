# C:\ANALYTICS207\core\predict_v30.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd


@dataclass
class WalkForwardConfig:
    min_games_before_scoring: int = 25
    rolling_window: int = 200


def _safe_to_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def _ensure_pred_cols(g: pd.DataFrame) -> pd.DataFrame:
    out = g.copy()
    for c in ["PredHomeWinProb", "PredMargin", "PredHomeScore", "PredAwayScore", "PredTotalPoints"]:
        if c not in out.columns:
            out[c] = np.nan
    return out


def _compute_actuals(g: pd.DataFrame) -> pd.DataFrame:
    out = g.copy()

    out["PlayedBool"] = out.get("Played", False).fillna(False).astype(bool)

    hs = pd.to_numeric(out.get("HomeScore", np.nan), errors="coerce")
    aw = pd.to_numeric(out.get("AwayScore", np.nan), errors="coerce")

    out["ActualMargin"] = np.where(out["PlayedBool"], hs - aw, np.nan)
    out["ActualHomeWin"] = np.where(out["PlayedBool"], np.where(hs > aw, 1.0, np.where(hs < aw, 0.0, 0.5)), np.nan)

    return out


def _brier(p: np.ndarray, y: np.ndarray) -> float:
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() == 0:
        return float("nan")
    return float(np.mean((p[ok] - y[ok]) ** 2))


def _mae(pred: np.ndarray, actual: np.ndarray) -> float:
    ok = np.isfinite(pred) & np.isfinite(actual)
    if ok.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs(pred[ok] - actual[ok])))


def _rmse(pred: np.ndarray, actual: np.ndarray) -> float:
    ok = np.isfinite(pred) & np.isfinite(actual)
    if ok.sum() == 0:
        return float("nan")
    return float(np.sqrt(np.mean((pred[ok] - actual[ok]) ** 2)))


def build_predictions_walkforward_v30(
    games_core: pd.DataFrame,
    teams_core: pd.DataFrame,
    cfg: WalkForwardConfig | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    This does not retrain a second model yet.
    It produces a clean predicted games table using the existing v30 per game prediction fields,
    then evaluates them in date order with rolling metrics so you can see early season vs late season behavior.
    """

    cfg = cfg or WalkForwardConfig()

    g = games_core.copy()
    g = _ensure_pred_cols(g)
    g["Date"] = _safe_to_datetime(g.get("Date", pd.Series([pd.NaT] * len(g))))

    g = _compute_actuals(g)

    keep_cols = [
        "GameID",
        "Date",
        "Season",
        "Gender",
        "Home",
        "Away",
        "HomeKey",
        "AwayKey",
        "IsNeutral",
        "HomeScore",
        "AwayScore",
        "PlayedBool",
        "PredHomeWinProb",
        "PredMargin",
        "PredHomeScore",
        "PredAwayScore",
        "PredTotalPoints",
        "ActualHomeWin",
        "ActualMargin",
    ]
    keep_cols = [c for c in keep_cols if c in g.columns]
    pred_games = g[keep_cols].copy()

    pred_games = pred_games.sort_values(["Date", "GameID"], na_position="last").reset_index(drop=True)

    played = pred_games[pred_games["PlayedBool"]].copy()
    if played.empty:
        eval_df = pd.DataFrame(
            [
                {
                    "AsOfDate": pd.NaT,
                    "GamesScored": 0,
                    "WinAccuracyPct": np.nan,
                    "Brier": np.nan,
                    "MAE_Margin": np.nan,
                    "RMSE_Margin": np.nan,
                }
            ]
        )
        return pred_games, eval_df

    ph = pd.to_numeric(played["PredHomeWinProb"], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(played["ActualHomeWin"], errors="coerce").to_numpy(dtype=float)
    pm = pd.to_numeric(played["PredMargin"], errors="coerce").to_numpy(dtype=float)
    am = pd.to_numeric(played["ActualMargin"], errors="coerce").to_numpy(dtype=float)

    pred_home_win = ph >= 0.5
    actual_home_win = y >= 0.5
    correct = (pred_home_win == actual_home_win) & np.isfinite(ph) & np.isfinite(y)

    dates = played["Date"].to_numpy()

    rows = []
    for i in range(len(played)):
        if i + 1 < cfg.min_games_before_scoring:
            continue

        start = max(0, (i + 1) - cfg.rolling_window)
        idx = slice(start, i + 1)

        correct_rate = float(np.mean(correct[idx])) if (i + 1 - start) > 0 else float("nan")
        rows.append(
            {
                "AsOfDate": pd.to_datetime(dates[i]),
                "GamesScored": int(i + 1),
                "RollingWindow": int(i + 1 - start),
                "WinAccuracyPct": 100.0 * correct_rate if correct_rate == correct_rate else np.nan,
                "Brier": _brier(ph[idx], y[idx]),
                "MAE_Margin": _mae(pm[idx], am[idx]),
                "RMSE_Margin": _rmse(pm[idx], am[idx]),
            }
        )

    eval_df = pd.DataFrame(rows)
    if eval_df.empty:
        eval_df = pd.DataFrame(
            [
                {
                    "AsOfDate": played["Date"].max(),
                    "GamesScored": int(len(played)),
                    "RollingWindow": int(min(len(played), cfg.rolling_window)),
                    "WinAccuracyPct": 100.0 * float(np.mean(correct)) if len(played) else np.nan,
                    "Brier": _brier(ph, y),
                    "MAE_Margin": _mae(pm, am),
                    "RMSE_Margin": _rmse(pm, am),
                }
            ]
        )

    for c in ["WinAccuracyPct", "Brier", "MAE_Margin", "RMSE_Margin"]:
        if c in eval_df.columns:
            eval_df[c] = pd.to_numeric(eval_df[c], errors="coerce").round(4)

    return pred_games, eval_df
